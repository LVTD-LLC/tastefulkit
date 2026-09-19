from urllib.parse import urlencode
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from apps.billing.access import paid_required
from apps.catalogue import arena
from apps.catalogue.models import ArenaGuest, Design, TasteProfile


def selected_kind(request):
    return Design.Kind.LANDING


def participant(request):
    if request.user.is_authenticated:
        return request.user
    if "arena_guest" not in request.session:
        request.session["arena_guest"] = str(uuid4())
    return ArenaGuest(pk=request.session["arena_guest"])


@never_cache
def voting_arena(request):
    voter = participant(request)
    profile = (
        TasteProfile.objects.filter(user=request.user).first()
        if request.user.is_authenticated
        else None
    )
    generation = profile.generation if profile else 0
    kind = selected_kind(request)
    skipped = request.session.get("arena_skipped", [])
    pair = arena.choose_pair(voter, generation, kind, skipped)
    return render(
        request,
        "catalogue/arena.html",
        {
            "pair": pair,
            "token": arena.pair_token(voter, generation, pair) if pair else "",
            "kind": kind,
            "kinds": Design.Kind.choices,
            "skipped": bool(skipped),
            "vote_count": arena.comparison_ballots(voter, generation).count(),
        },
    )


@require_POST
@never_cache
def vote(request):
    kind = selected_kind(request)
    try:
        outcome, ids = arena.submit_comparison(
            participant(request), request.POST.get("token", ""), request.POST.get("choice", "")
        )
    except arena.ArenaError as exc:
        messages.error(request, str(exc))
    else:
        if outcome == "skipped":
            skipped = request.session.get("arena_skipped", [])
            key = ":".join(str(pk) for pk in ids)
            request.session["arena_skipped"] = list(dict.fromkeys([*skipped, key]))[-100:]
        elif outcome == "duplicate":
            messages.info(request, "That comparison was already recorded. Here's the next one.")
    return redirect(reverse("voting_arena") + ("?" + urlencode({"kind": kind}) if kind else ""))


@require_POST
@never_cache
def revisit_skipped(request):
    request.session.pop("arena_skipped", None)
    return redirect("voting_arena")


@paid_required
@never_cache
def rankings(request):
    mode = "personal" if request.GET.get("mode") == "personal" else "global"
    if mode == "personal" and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    kind = selected_kind(request)
    designs, summary = arena.ranked_designs(request.user, mode, kind)
    page = Paginator(designs, 24).get_page(request.GET.get("page"))
    return render(
        request,
        "catalogue/rankings.html",
        {
            "page": page,
            "mode": mode,
            "kind": kind,
            "kinds": Design.Kind.choices,
            "summary": summary,
            "query_params": urlencode({"mode": mode, "kind": kind}),
        },
    )


@paid_required
@require_POST
@never_cache
def reset_taste(request):
    if request.POST.get("confirm") != "reset":
        messages.error(request, "Confirm the reset to start a new taste profile.")
    else:
        arena.reset_taste(request.user)
        request.session.pop("arena_skipped", None)
        messages.success(
            request,
            "Personal taste reset. Saved references and original global votes are unchanged.",
        )
    return redirect(reverse("design_rankings") + "?mode=personal")
