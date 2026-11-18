"""Export stable candidates or publish reviewed guides without replacing their media."""

import json
import sys
from io import BytesIO
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.catalogue.artifacts import read_design_markdown
from apps.catalogue.models import Design
from apps.catalogue.services import visible_designs


def candidates():
    return visible_designs().filter(kind=Design.Kind.LANDING, selector="").exclude(screenshot="")


@transaction.atomic
def apply_review(row, *, write):
    design = candidates().select_for_update().get(pk=row["id"])
    summary = row["summary"].strip()
    if not summary or len(summary) > 600:
        raise ValueError("Supply a reviewed summary of at most 600 characters.")
    guide = read_design_markdown(BytesIO(row["design_markdown"].encode()))
    if summary not in guide:
        raise ValueError("The guide must include the reviewed summary.")
    if design.design_markdown == guide and design.review_summary == summary:
        return "unchanged"
    if design.updated_at != parse_datetime(row["updated_at"]):
        raise ValueError("Reference changed since export. Review a fresh capture.")
    if write:
        design.design_markdown = guide
        design.review_summary = summary
        design.save(update_fields=["design_markdown", "review_summary", "updated_at"])
    return "published" if write else "validated"


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        export = sub.add_parser("export")
        export.add_argument("--limit", type=int, default=100)
        apply = sub.add_parser("apply")
        apply.add_argument("manifest", help="Reviewed JSON array or - for stdin")
        apply.add_argument("--write", action="store_true")

    def handle(self, *args, **options):
        if options["action"] == "export":
            if options["limit"] < 1:
                raise CommandError("--limit must be positive.")
            rows = (
                candidates()
                .filter(review_summary="")
                .exclude(design_markdown="")
                .order_by("created_at", "id")
                .values(
                    "id",
                    "source_url",
                    "title",
                    "viewport_width",
                    "captured_at",
                    "updated_at",
                    "design_markdown",
                )[: options["limit"]]
            )
            return json.dumps(list(rows), default=str)
        path = options["manifest"]
        rows = json.loads(sys.stdin.read() if path == "-" else Path(path).read_text())
        for row in rows:
            try:
                status = apply_review(row, write=options["write"])
            except (Design.DoesNotExist, ValueError, KeyError) as exc:
                raise CommandError(f"{row.get('id')}: {exc}") from exc
            self.stdout.write(f"{row['id']} {status}")
