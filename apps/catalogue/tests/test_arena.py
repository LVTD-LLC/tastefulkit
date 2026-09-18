from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import close_old_connections
from django.test import Client
from django.utils import timezone

from apps.catalogue import arena
from apps.catalogue.models import ArenaBallot, Design, DesignRating, SavedDesign, Tag, TasteProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def designs(user):
    result = []
    for name in ("Warm", "Bold", "Warm related"):
        design = Design.objects.create(
            title=name,
            source_url=f"https://example.com/{name}",
            fingerprint=str(uuid4()),
            description=name,
            submitted_by=user,
            capture_status="ready",
            screenshot="shot.png",
            thumbnail="thumb.png",
        )
        tag, _ = Tag.objects.get_or_create(name="warm" if "Warm" in name else "bold")
        design.tags.add(tag)
        result.append(design)
    return result


def token(user, designs):
    profile = TasteProfile.objects.filter(user=user).first()
    return arena.pair_token(user, profile.generation if profile else 0, designs[:2])


def vote(user, designs, winner=0):
    return arena.submit_comparison(user, token(user, designs), str(designs[winner].pk))


def ratings_snapshot():
    return list(
        DesignRating.objects.order_by("design_id").values_list(
            "design_id", "score", "comparisons", "wins"
        )
    )


@pytest.mark.parametrize(
    "url", ["/arena/", "/arena/vote/", "/arena/revisit/", "/rankings/", "/rankings/reset/"]
)
def test_anonymous_and_inactive_accounts_cannot_participate(client, user, url):
    assert client.get(url).status_code == 302
    assert client.post(url).status_code == 302
    user.is_active = False
    user.save()
    client.force_login(user)
    assert client.post(url).status_code == 302
    assert ArenaBallot.objects.count() == 0


def test_votes_are_csrf_protected_and_post_only(user, designs):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.get("/arena/vote/").status_code == 405
    assert (
        client.post(
            "/arena/vote/", {"token": token(user, designs), "choice": str(designs[0].pk)}
        ).status_code
        == 403
    )
    assert not ArenaBallot.objects.exists()


def test_vote_updates_elo_once_even_for_reversed_pair_and_retries(user, designs):
    assert vote(user, designs)[0] == "saved"
    first = ratings_snapshot()
    assert sorted(row[1] for row in first) == [984, 1016]
    assert sum(row[2] for row in first) == 2
    assert vote(user, designs, 1)[0] == "duplicate"
    assert vote(user, list(reversed(designs[:2])))[0] == "duplicate"
    assert ratings_snapshot() == first
    assert ArenaBallot.objects.count() == 1
    assert arena.choose_pair(user, 0)


def test_durable_history_replays_exactly_after_user_and_design_removal(user, designs):
    other = User.objects.create_user(username="voter")
    vote(other, designs)
    vote(other, [designs[0], designs[2]], 1)
    vote(user, designs, 1)
    before = ratings_snapshot()
    other.delete()
    designs[1].delete()
    assert ArenaBallot.objects.filter(user=None).count() == 2
    call_command("rebuild_arena_ratings")
    assert ratings_snapshot() == before


def test_rollback_keeps_ballots_and_ratings_atomic(user, designs):
    with patch("apps.catalogue.arena.update_global", side_effect=RuntimeError("failure")):
        with pytest.raises(RuntimeError):
            vote(user, designs)
    assert not ArenaBallot.objects.exists()
    assert not DesignRating.objects.exists()
    assert vote(user, designs)[0] == "saved"


def test_token_validation_visibility_and_pair_compatibility(user, designs):
    other = User.objects.create_user(username="other-voter")
    signed = token(user, designs)
    for bad in ("", signed + "tampered", token(other, designs)):
        with pytest.raises(arena.ArenaError):
            arena.submit_comparison(user, bad, str(designs[0].pk))
    with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 3601):
        with pytest.raises(arena.ArenaError):
            arena.submit_comparison(user, signed, str(designs[0].pk))
    with pytest.raises(arena.ArenaError):
        arena.submit_comparison(user, signed, str(designs[2].pk))
    for field, value in (
        ("published", False),
        ("capture_status", "failed"),
        ("kind", "hero"),
        ("viewport_width", 390),
        ("screenshot", ""),
    ):
        original = getattr(designs[0], field)
        setattr(designs[0], field, value)
        designs[0].save()
        with pytest.raises(arena.ArenaError):
            arena.submit_comparison(user, signed, str(designs[0].pk))
        setattr(designs[0], field, original)
        designs[0].save()
    assert not ArenaBallot.objects.exists()


def test_selection_excludes_incompatible_hidden_seen_and_skipped_pairs(user, designs):
    designs[2].kind = "hero"
    designs[2].save()
    pair = arena.choose_pair(user, 0)
    assert {d.pk for d in pair} == {d.pk for d in designs[:2]}
    assert not arena.choose_pair(user, 0, "hero")
    skipped = [":".join(sorted(str(d.pk) for d in designs[:2]))]
    assert not arena.choose_pair(user, 0, skipped=skipped)
    vote(user, designs)
    assert not arena.choose_pair(user, 0)


def test_personal_preferences_are_private_and_recommend_related_unseen_designs(user, designs):
    other = User.objects.create_user(username="opposite-taste")
    vote(user, designs)
    vote(other, designs, 1)
    yours, summary = arena.ranked_designs(user, "personal")
    theirs, _ = arena.ranked_designs(other, "personal")
    assert [d.pk for d in yours] == [designs[0].pk, designs[2].pk, designs[1].pk]
    assert theirs[0].pk == designs[1].pk
    assert summary == {"votes": 1, "saves": 0, "has_taste": True}
    assert yours[1].personal_comparisons == 0
    assert yours[1].personal_score > 1000
    newcomer = User.objects.create_user(username="newcomer")
    fallback, summary = arena.ranked_designs(newcomer, "personal")
    global_designs, _ = arena.ranked_designs(user)
    assert [d.pk for d in fallback] == [d.pk for d in global_designs]
    assert not summary["has_taste"]


def test_saves_and_reset_start_fresh_without_duplicate_global_votes(user, designs):
    SavedDesign.objects.create(user=user, design=designs[1])
    ranked, summary = arena.ranked_designs(user, "personal")
    assert ranked[0].pk == designs[1].pk and summary["has_taste"]
    vote(user, designs)
    stale = token(user, designs)
    before = ratings_snapshot()
    arena.reset_taste(user)
    assert SavedDesign.objects.filter(user=user).count() == 1
    assert not arena.ranked_designs(user, "personal")[1]["has_taste"]
    with pytest.raises(arena.ArenaError):
        arena.submit_comparison(user, stale, str(designs[1].pk))
    vote(user, designs, 1)
    assert ratings_snapshot() == before
    assert ArenaBallot.objects.filter(global_counted=True).count() == 1
    assert arena.ranked_designs(user, "personal")[0][0].pk == designs[1].pk
    SavedDesign.objects.create(user=user, design=designs[2])
    assert arena.ranked_designs(user, "personal")[1]["saves"] == 1


def test_rate_limit_is_account_scoped_and_reset_does_not_bypass_it(user, designs):
    TasteProfile.objects.create(user=user, rate_window=timezone.now(), rate_count=30)
    with pytest.raises(arena.ArenaError, match="wait a minute"):
        vote(user, designs)
    arena.reset_taste(user)
    with pytest.raises(arena.ArenaError, match="wait a minute"):
        vote(user, designs)
    assert not ArenaBallot.objects.exists()


def test_rankings_filter_hidden_entries_and_share_ties(user, designs):
    ranked, _ = arena.ranked_designs(user)
    assert {d.rank for d in ranked} == {1}
    designs[0].published = False
    designs[0].save()
    designs[1].kind = "hero"
    designs[1].save()
    for mode in ("global", "personal"):
        ranked, _ = arena.ranked_designs(user, mode, "hero")
        assert [d.pk for d in ranked] == [designs[1].pk]


def test_web_flow_skip_vote_empty_ranking_and_explicit_reset(auth_client, user, designs):
    page = auth_client.get("/arena/")
    assert page.status_code == 200 and "no-store" in page.headers["Cache-Control"]
    pair = page.context["pair"]
    response = auth_client.post(
        "/arena/vote/", {"token": page.context["token"], "choice": "skip"}, follow=True
    )
    assert response.status_code == 200
    assert not ArenaBallot.objects.exists()
    assert {d.pk for d in response.context["pair"]} != {d.pk for d in pair}
    auth_client.post("/arena/revisit/")
    assert "arena_skipped" not in auth_client.session
    response = auth_client.post(
        "/arena/vote/", {"token": token(user, designs), "choice": str(designs[0].pk)}, follow=True
    )
    assert b"Vote saved" in response.content
    response = auth_client.get("/rankings/?mode=personal")
    assert response.context["summary"]["votes"] == 1
    assert b"personal fit" in response.content
    assert "private" in response.headers["Cache-Control"]
    auth_client.post("/rankings/reset/")
    assert TasteProfile.objects.get(user=user).generation == 0
    auth_client.post("/rankings/reset/", {"confirm": "reset"})
    assert TasteProfile.objects.get(user=user).generation == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_duplicate_submissions_do_not_double_count(user, designs):
    signed = token(user, designs)

    def submit():
        close_old_connections()
        try:
            return arena.submit_comparison(user, signed, str(designs[0].pk))[0]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(outcomes) == ["duplicate", "saved"]
    assert ArenaBallot.objects.count() == 1
    assert sum(DesignRating.objects.values_list("comparisons", flat=True)) == 2
