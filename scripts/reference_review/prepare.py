"""Record visual reviews, then build a publishable batch from matching evidence."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from uuid import UUID

GROUPS = {"h": "headings", "p": "paragraphs", "c": "controls", "n": "navigation"}


def evidence_for(root, row):
    directory = root / str(UUID(row["id"]))
    raw = (directory / "evidence.json").read_bytes()
    evidence = json.loads(raw)
    if (
        evidence["id"] != row["id"]
        or evidence["source"] != row["source_url"]
        or evidence["viewport"]["width"] != row["viewport_width"]
        or evidence["revision"] != row["updated_at"]
    ):
        raise ValueError("Capture a fresh reference at the exported revision and viewport.")
    digest = hashlib.sha256(raw)
    for name in ("archive.jpg", "live.jpg"):
        digest.update(hashlib.sha256((directory / name).read_bytes()).digest())
    return directory, evidence, digest.hexdigest()


def measured_elements(evidence, choices):
    if len(set(choices)) < 2:
        raise ValueError("Select at least two distinct, visually confirmed text elements.")
    for key in choices:
        if not re.fullmatch("[hpcn][0-9]+", key):
            raise ValueError(f"Unknown sample {key}")
        yield evidence["samples"][GROUPS[key[0]]][int(key[1:])]


def render(row, evidence, review):
    viewport = evidence["viewport"]
    lines = [
        "## Browser-checked implementation notes",
        "",
        review["summary"],
        "",
        f"Measured at {viewport['width']} × {viewport['height']} CSS pixels in Chromium "
        f"{evidence['chromium']} on {evidence['measured_at'][:10]} at {evidence['final_url']}. "
        "The samples below describe this live desktop viewport. The original guide follows.",
        "",
    ]
    for element in measured_elements(evidence, review["choices"]):
        label = element["text"].replace("\x60", "'")[:56]
        css = element["css"]
        props = [
            "font-family",
            "font-size",
            "font-weight",
            "line-height",
            "letter-spacing",
            "color",
        ]
        if css["background-color"] != "rgba(0, 0, 0, 0)":
            props.append("background-color")
        for prop in ("padding", "border-radius", "gap"):
            if css[prop] not in ("0px", "normal"):
                props.append(prop)
        lines.extend(
            [
                f"### Element with text “{label}”",
                "",
                "`" + element["selector"] + "`",
                "",
                "```css",
                *[f"{prop}: {css[prop]};" for prop in props],
                "```",
                "",
            ]
        )
    frontmatter, body = row["design_markdown"].split("\n---\n", 1)
    return frontmatter + "\n---\n" + "\n".join(lines) + "\n" + body.lstrip("\n")


def main(args):
    rows = json.loads(args.manifest.read_text())
    if args.action == "approve":
        row = next(r for r in rows if r["id"] == str(args.id))
        directory, evidence, digest = evidence_for(args.root, row)
        review = {"summary": args.summary.strip(), "choices": args.samples, "digest": digest}
        if not 1 <= len(review["summary"]) <= 600:
            raise ValueError("Supply a review of 1 to 600 characters.")
        list(measured_elements(evidence, args.samples))
        tmp = directory / "review.tmp"
        tmp.write_text(json.dumps(review, indent=2))
        tmp.replace(directory / "review.json")
    else:
        batch = []
        for row in rows:
            path = args.root / str(UUID(row["id"])) / "review.json"
            if not path.exists():
                continue
            review = json.loads(path.read_text())
            _, evidence, digest = evidence_for(args.root, row)
            if review["digest"] != digest:
                raise ValueError(f"Evidence changed for {row['id']}. Repeat the visual review.")
            batch.append(
                {
                    "id": row["id"],
                    "updated_at": row["updated_at"],
                    "summary": review["summary"],
                    "design_markdown": render(row, evidence, review),
                }
            )
        print(json.dumps(batch, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("root", type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    approve = sub.add_parser("approve")
    approve.add_argument("id", type=UUID)
    approve.add_argument("summary")
    approve.add_argument("samples", nargs="+", help="Sample group (h/p/c/n) and zero-based index")
    sub.add_parser("build")
    main(parser.parse_args())
