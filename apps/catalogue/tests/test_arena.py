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
from apps.catalogue.models import (
    ArenaBallot,
    ArenaGuest,
    Design,
    DesignRating,
    SavedDesign,
    Tag,
    TasteProfile,
)

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


@pytest.mark.parametrize("url", ["/rankings/?mode=personal", "/rankings/reset/"])
def test_personal_features_require_an_active_account(client, user, url):
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
    assert b"Vote saved" not in response.content
    assert ArenaBallot.objects.count() == 1
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


@pytest.mark.django_db(transaction=True)
def test_concurrent_distinct_votes_cannot_exceed_account_rate_limit(user, designs):
    TasteProfile.objects.create(user=user, rate_window=timezone.now(), rate_count=29)
    pairs = [designs[:2], designs[1:]]
    signed_pairs = [(token(user, pair), str(pair[0].pk)) for pair in pairs]

    def submit(signed_pair):
        close_old_connections()
        try:
            return arena.submit_comparison(user, *signed_pair)[0]
        except arena.ArenaError as exc:
            assert "wait a minute" in str(exc)
            return "rate_limited"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, signed_pairs))
    assert sorted(outcomes) == ["rate_limited", "saved"]
    assert TasteProfile.objects.get(user=user).rate_count == 30
    assert ArenaBallot.objects.count() == 1
    assert sum(DesignRating.objects.values_list("comparisons", flat=True)) == 2


def test_guest_browser_flow_counts_globally_without_personal_profile(client, designs):
    page = client.get("/arena/")
    assert page.status_code == 200
    assert "no-store" in page.headers["Cache-Control"]
    assert b"No account needed" in page.content
    assert b"in your taste profile" not in page.content
    assert not ArenaGuest.objects.exists()  # Browsing does not create rate-limit rows.
    pair = page.context["pair"]
    data = {"token": page.context["token"], "choice": str(pair[0].pk)}
    response = client.post("/arena/vote/", data, follow=True)
    assert b"Vote saved" not in response.content
    ballot = ArenaBallot.objects.get()
    assert ballot.user_id is None and ballot.guest_id is not None and ballot.global_counted
    assert not TasteProfile.objects.exists()
    assert sorted(row[1] for row in ratings_snapshot()) == [984, 1016]
    before = ratings_snapshot()
    client.post("/arena/vote/", data)
    assert ratings_snapshot() == before and ArenaBallot.objects.count() == 1
    assert {d.pk for d in response.context["pair"]} != {d.pk for d in pair}
    assert response.context["vote_count"] == 1
    ranking = client.get("/rankings/")
    assert ranking.status_code == 200 and ranking.context["summary"] == {}
    assert ranking.context["page"][0].pk == pair[0].pk
    assert "no-store" in ranking.headers["Cache-Control"]
    assert b"tk-taste-reset" not in ranking.content
    owner = designs[0].submitted_by
    client.force_login(owner)
    assert client.get("/rankings/").status_code == 200
    assert client.get("/rankings/?mode=personal").status_code == 200
    ranking = client.get("/rankings/")
    assert ranking.status_code == 200 and ranking.context["summary"] == {}
    assert ranking.context["page"][0].pk == pair[0].pk
    assert not client.get("/rankings/?mode=personal").context["summary"]["has_taste"]
    assert not TasteProfile.objects.exists()


def test_guest_skip_revisit_empty_and_filter(client, designs):
    designs[2].kind = "hero"
    designs[2].save()
    page = client.get("/arena/?kind=landing_page")
    response = client.post(
        "/arena/vote/",
        {"token": page.context["token"], "choice": "skip", "kind": "landing_page"},
        follow=True,
    )
    assert not response.context["pair"] and not ArenaBallot.objects.exists()
    assert b"See global rankings" in response.content
    assert b"See your rankings" not in response.content
    response = client.post("/arena/revisit/", follow=True)
    assert len(response.context["pair"]) == 2
    ranking = client.get("/rankings/?kind=hero")
    assert ranking.status_code == 200
    assert all(design.kind == "landing_page" for design in ranking.context["page"])


def test_guest_tokens_are_session_bound_and_cannot_be_used_after_login(client, user, designs):
    page = client.get("/arena/")
    data = {"token": page.context["token"], "choice": str(page.context["pair"][0].pk)}
    other = Client()
    other.get("/arena/")
    assert b"comparison expired" in other.post("/arena/vote/", data, follow=True).content
    client.force_login(user)
    assert b"comparison expired" in client.post("/arena/vote/", data, follow=True).content
    assert not ArenaBallot.objects.exists()
    assert not ArenaGuest.objects.exists()


def test_guest_posts_require_csrf_and_get_cannot_mutate(designs):
    client = Client(enforce_csrf_checks=True)
    page = client.get("/arena/")
    data = {"token": page.context["token"], "choice": str(page.context["pair"][0].pk)}
    for path in ("/arena/vote/", "/arena/revisit/"):
        assert client.get(path).status_code == 405
        assert client.post(path, data).status_code == 403
    data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
    assert client.post("/arena/vote/", data).status_code == 302
    assert ArenaBallot.objects.count() == 1


def test_guest_rate_limit_is_durable_and_independent(user, designs):
    guest = ArenaGuest.objects.create(rate_window=timezone.now(), rate_count=30)
    signed = arena.pair_token(guest, 0, designs[:2])
    with pytest.raises(arena.ArenaError, match="wait a minute"):
        arena.submit_comparison(guest, signed, str(designs[0].pk))
    with pytest.raises(arena.ArenaError, match="wait a minute"):
        arena.submit_comparison(guest, signed, "skip")
    another = ArenaGuest(pk=uuid4())
    assert (
        arena.submit_comparison(
            another, arena.pair_token(another, 0, designs[:2]), str(designs[0].pk)
        )[0]
        == "saved"
    )
    assert vote(user, designs)[0] == "saved"
    with patch(
        "apps.catalogue.arena.timezone.now",
        return_value=timezone.now() + timezone.timedelta(minutes=1),
    ):
        assert arena.submit_comparison(guest, signed, str(designs[0].pk))[0] == "saved"
    assert not TasteProfile.objects.filter(user_id=None).exists()


def test_guest_validation_and_rebuild_preserve_history(designs):
    guest = ArenaGuest(pk=uuid4())
    signed = arena.pair_token(guest, 0, designs[:2])
    for bad in ("", signed + "tampered"):
        with pytest.raises(arena.ArenaError):
            arena.submit_comparison(guest, bad, str(designs[0].pk))
    with patch("django.core.signing.time.time", return_value=timezone.now().timestamp() + 3601):
        with pytest.raises(arena.ArenaError):
            arena.submit_comparison(guest, signed, str(designs[0].pk))
    designs[0].published = False
    designs[0].save()
    with pytest.raises(arena.ArenaError):
        arena.submit_comparison(guest, signed, str(designs[0].pk))
    assert not ArenaGuest.objects.exists()
    designs[0].published = True
    designs[0].save()
    with patch("apps.catalogue.arena.update_global", side_effect=RuntimeError("failure")):
        with pytest.raises(RuntimeError):
            arena.submit_comparison(guest, signed, str(designs[0].pk))
    assert not ArenaGuest.objects.exists() and not ArenaBallot.objects.exists()
    arena.submit_comparison(guest, signed, str(designs[0].pk))
    reverse = arena.pair_token(guest, 0, list(reversed(designs[:2])))
    assert arena.submit_comparison(guest, reverse, str(designs[1].pk))[0] == "duplicate"
    before = ratings_snapshot()
    guest.delete()
    call_command("rebuild_arena_ratings")
    assert ratings_snapshot() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_pair", [True, False])
def test_concurrent_guest_votes_are_idempotent_and_rate_limited(designs, same_pair):
    guest = ArenaGuest.objects.create(rate_window=timezone.now(), rate_count=29)
    signed = arena.pair_token(guest, 0, designs[:2])

    def submit(pair):
        close_old_connections()
        try:
            return arena.submit_comparison(guest, *pair)[0]
        except arena.ArenaError as exc:
            assert "wait a minute" in str(exc)
            return "rate_limited"
        finally:
            close_old_connections()

    submissions = [(signed, str(designs[0].pk))] * 2
    if not same_pair:
        submissions[1] = (arena.pair_token(guest, 0, designs[1:]), str(designs[1].pk))
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, submissions))
    assert sorted(outcomes) == (["duplicate", "saved"] if same_pair else ["rate_limited", "saved"])
    guest.refresh_from_db()
    assert guest.rate_count == 30
    other_pair = arena.pair_token(guest, 0, [designs[0], designs[2]])
    assert submit((other_pair, str(designs[2].pk))) == "rate_limited"
    assert ArenaBallot.objects.count() == 1


def test_screenshots_are_vote_buttons_and_no_element_controls(client, designs):
    from html.parser import HTMLParser

    buttons = []
    images = []

    class PreviewParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "button" and attrs.get("class") == "tk-arena-preview":
                buttons.append(attrs)
            if tag == "img" and "data-arena-full-src" in attrs:
                images.append(attrs)

    page = client.get("/arena/?kind=hero")
    PreviewParser().feed(page.content.decode())
    assert len(buttons) == 2
    assert {button["value"] for button in buttons} == {str(d.pk) for d in page.context["pair"]}
    assert all(button["type"] == "submit" and button["name"] == "choice" for button in buttons)
    assert len(images) == 2
    for image, design in zip(images, page.context["pair"], strict=True):
        assert image["src"] == design.thumbnail.url
        assert image["data-arena-full-src"] == design.screenshot.url
        assert image["loading"] == "eager"
    assert b"<select" not in page.content
    assert b"tk-arena-count" not in page.content
    assert b"tk-arena-intro" not in page.content
