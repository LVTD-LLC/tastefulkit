"""Authenticated comparisons, reproducible Elo, and private metadata-based taste."""

import random
from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from math import sqrt
from uuid import UUID

from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.catalogue.models import ArenaBallot, ArenaState, DesignRating, SavedDesign, TasteProfile
from apps.catalogue.services import visible_designs

TOKEN_SALT = "catalogue.arena.v1"


class ArenaError(ValueError):
    pass


def eligible_designs():
    return (
        visible_designs()
        .exclude(screenshot="")
        .exclude(thumbnail="")
        .defer("design_markdown", "description")
    )


def comparison_group(design):
    return design.kind, design.viewport_width < 768


def personal_ballots(user, generation):
    return ArenaBallot.objects.filter(user=user, generation=generation)


def choose_pair(user, generation, kind="", skipped=()):
    """Shuffle anchors and sides; compare like elements and viewport families."""
    designs = eligible_designs()
    if kind:
        designs = designs.filter(kind=kind)
    candidates = list(designs.only("id", "kind", "viewport_width"))
    random.SystemRandom().shuffle(candidates)
    seen_pairs = defaultdict(set)
    for a, b in personal_ballots(user, generation).values_list("design_a", "design_b"):
        seen_pairs[a].add(b)
        seen_pairs[b].add(a)
    skipped = set(skipped)
    for anchor in candidates:
        seen = seen_pairs[anchor.pk]
        opponents = [
            item
            for item in candidates
            if item.pk != anchor.pk
            and item.pk not in seen
            and comparison_group(item) == comparison_group(anchor)
            and ":".join(sorted([str(anchor.pk), str(item.pk)])) not in skipped
        ]
        if opponents:
            opponent = random.SystemRandom().choice(opponents)
            pair = {d.pk: d for d in designs.filter(pk__in=[anchor.pk, opponent.pk])}
            if len(pair) == 2:
                return [pair[anchor.pk], pair[opponent.pk]]
    return []


def pair_token(user, generation, pair):
    return signing.dumps(
        {"user": user.pk, "generation": generation, "pair": [str(d.pk) for d in pair]},
        salt=TOKEN_SALT,
    )


def parse_token(user, token):
    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=3600)
        ids = sorted(UUID(value) for value in data["pair"])
        if data["user"] != user.pk or len(ids) != 2 or ids[0] == ids[1]:
            raise ValueError
        return data["generation"], ids
    except (signing.BadSignature, ValueError, KeyError, TypeError) as exc:
        raise ArenaError("This comparison expired. Refresh the arena and try again.") from exc


def elo_update(a, b, a_won):
    expected = 1 / (1 + 10 ** max(-20, min(20, (b - a) / 400)))
    change = 32 * (int(a_won) - expected)
    return a + change, b - change


def lock_arena():
    ArenaState.objects.get_or_create(pk=1)
    return ArenaState.objects.select_for_update().get(pk=1)


def update_global(ballot):
    a, _ = DesignRating.objects.get_or_create(design_id=ballot.design_a)
    b, _ = DesignRating.objects.get_or_create(design_id=ballot.design_b)
    a_won = ballot.winner == ballot.design_a
    a.score, b.score = elo_update(a.score, b.score, a_won)
    for rating, won in [(a, a_won), (b, not a_won)]:
        rating.comparisons += 1
        rating.wins += int(won)
        rating.save()


@transaction.atomic
def submit_comparison(user, token, choice):
    generation, ids = parse_token(user, token)
    lock_arena()
    profile, _ = TasteProfile.objects.get_or_create(user=user)
    if generation != profile.generation:
        raise ArenaError("Your taste profile changed. Refresh the arena and try again.")
    designs = list(eligible_designs().select_for_update().filter(pk__in=ids).order_by("id"))
    if len(designs) != 2 or comparison_group(designs[0]) != comparison_group(designs[1]):
        raise ArenaError("These designs are no longer available to compare. Try the next pair.")
    if choice not in [str(pk) for pk in ids] + ["skip"]:
        raise ArenaError("Choose one of the two designs, or skip this comparison.")
    existing = personal_ballots(user, generation).filter(design_a=ids[0], design_b=ids[1])
    if existing.exists():
        return "duplicate", ids
    now = timezone.now()
    if profile.rate_window is None or now - profile.rate_window >= timedelta(minutes=1):
        profile.rate_window, profile.rate_count = now, 0
    if profile.rate_count >= 30:
        raise ArenaError("You've compared a lot of designs. Please wait a minute and try again.")
    profile.rate_count += 1
    profile.save(update_fields=["rate_window", "rate_count"])
    if choice == "skip":
        return "skipped", ids
    counted = not ArenaBallot.objects.filter(
        user=user, design_a=ids[0], design_b=ids[1], global_counted=True
    ).exists()
    ballot = ArenaBallot.objects.create(
        user=user,
        generation=generation,
        design_a=ids[0],
        design_b=ids[1],
        winner=UUID(choice),
        global_counted=counted,
    )
    if counted:
        update_global(ballot)
    return "saved", ids


@transaction.atomic
def reset_taste(user):
    lock_arena()
    profile, _ = TasteProfile.objects.get_or_create(user=user)
    profile.generation += 1
    profile.reset_at = timezone.now()
    profile.save(update_fields=["generation", "reset_at"])


def features(design):
    """A transparent style proxy, not image/embedding inference."""
    result = {f"kind:{design.kind}": 0.25}
    if design.industry:
        result[f"industry:{design.industry.casefold()}"] = 0.5
    tags = list(design.tags.all())
    for tag in tags:
        result[f"tag:{tag.name.casefold()}"] = 1 / sqrt(len(tags))
    return result


def taste_scores(user, designs):
    profile = TasteProfile.objects.filter(user=user).first()
    generation = profile.generation if profile else 0
    by_id = {d.pk: d for d in designs}
    ratings, counts, affinity = defaultdict(lambda: 1000.0), defaultdict(int), defaultdict(float)
    used = 0
    for ballot in personal_ballots(user, generation):
        if ballot.design_a not in by_id or ballot.design_b not in by_id:
            continue
        a, b = ballot.design_a, ballot.design_b
        ratings[a], ratings[b] = elo_update(ratings[a], ratings[b], ballot.winner == a)
        for pk in (a, b):
            counts[pk] += 1
            for key, value in features(by_id[pk]).items():
                affinity[key] += value * (1 if pk == ballot.winner else -1)
        used += 1
    saves = SavedDesign.objects.filter(user=user, design_id__in=by_id)
    if profile and profile.reset_at:
        saves = saves.filter(created_at__gt=profile.reset_at)
    saved_ids = set(saves.values_list("design_id", flat=True))
    for pk in saved_ids:
        for key, value in features(by_id[pk]).items():
            affinity[key] += value * 0.5
    scale = max(1, sqrt(used + len(saved_ids)))
    for design in designs:
        similarity = sum(affinity[key] * value for key, value in features(design).items()) / scale
        design.personal_score = (
            ratings[design.pk] + 16 * similarity + (8 if design.pk in saved_ids else 0)
        )
        design.personal_comparisons = counts[design.pk]
    return {"votes": used, "saves": len(saved_ids), "has_taste": bool(used or saved_ids)}


def ranked_designs(user, mode="global", kind=""):
    designs = list(eligible_designs().prefetch_related("tags"))
    ratings = DesignRating.objects.in_bulk([d.pk for d in designs])
    summary = taste_scores(user, designs) if mode == "personal" else {}
    for design in designs:
        rating = ratings.get(design.pk)
        design.elo = rating.score if rating else 1000
        design.comparisons = rating.comparisons if rating else 0
        design.wins = rating.wins if rating else 0
        design.rank_score = design.personal_score if summary.get("has_taste") else design.elo
    if kind:
        designs = [d for d in designs if d.kind == kind]
    designs.sort(key=lambda d: (-d.rank_score, str(d.pk)))
    for _, group in groupby(enumerate(designs, 1), key=lambda entry: entry[1].rank_score):
        entries = list(group)
        for _, design in entries:
            design.rank = entries[0][0]
    return designs, summary
