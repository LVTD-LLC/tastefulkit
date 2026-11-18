# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.55,<2", "pillow", "beautifulsoup4", "requests"]
# ///
"""Capture local review evidence for exported, public landing-page references."""

import argparse
import asyncio
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.async_api import async_playwright

MEASURE = Path(__file__).with_name("measure.js").read_text()


def archive_image(origin, design_id, directory):
    detail = requests.get(f"{origin}/designs/{design_id}/", timeout=20)
    detail.raise_for_status()
    image = BeautifulSoup(detail.content, "html.parser").select_one("img.tk-fullshot")
    with requests.get(image["src"], stream=True, timeout=20) as response:
        response.raise_for_status()
        data = io.BytesIO()
        for part in response.iter_content(64 * 1024):
            data.write(part)
            if data.tell() > 20 * 1024 * 1024:
                raise ValueError("oversize archive image")
    with Image.open(data) as shot:
        preview = shot.crop((0, 0, shot.width, min(shot.height, 900)))
        preview.thumbnail((900, 900))
        preview.convert("RGB").save(directory / "archive.jpg", quality=90)


async def capture(browser, row, directory, origin):
    url = row["source_url"]
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("unsupported protocol")
    await asyncio.to_thread(archive_image, origin, UUID(row["id"]), directory)
    viewport = {"width": row["viewport_width"], "height": 900}
    context = await browser.new_context(viewport=viewport, accept_downloads=False)
    try:
        page = await context.new_page()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=26000)
        if not response or response.status >= 400:
            raise ValueError(f"source HTTP {response.status if response else 'unknown'}")
        await page.evaluate(
            "() => Promise.race([document.fonts.ready, new Promise(r=>setTimeout(r,4500))])"
        )
        await page.wait_for_timeout(1600)
        samples = await page.evaluate(MEASURE)
        await page.screenshot(path=directory / "live.jpg", type="jpeg", quality=82, timeout=9000)
        evidence = dict(
            id=row["id"],
            revision=row["updated_at"],
            source=url,
            final_url=page.url,
            viewport=viewport,
            measured_at=datetime.now(UTC).isoformat(),
            chromium=browser.version,
            samples=samples,
        )
        tmp = directory / "evidence.tmp"
        tmp.write_text(json.dumps(evidence, indent=2))
        tmp.replace(directory / "evidence.json")
    finally:
        await context.close()


async def main(args):
    rows = json.loads(args.manifest.read_text())
    semaphore = asyncio.Semaphore(args.jobs)
    async with async_playwright() as driver:

        async def run(row):
            directory = args.output / str(UUID(row["id"]))
            directory.mkdir(parents=True, exist_ok=True)
            evidence_path = directory / "evidence.json"
            if evidence_path.exists():
                previous = json.loads(evidence_path.read_text())
                if (
                    previous.get("revision") == row["updated_at"]
                    and previous["source"] == row["source_url"]
                ):
                    return
                evidence_path.unlink()
                (directory / "archive.jpg").unlink(missing_ok=True)
            async with semaphore:
                try:
                    browser = await driver.chromium.launch(
                        executable_path=args.chromium, chromium_sandbox=True, args=["--disable-gpu"]
                    )
                    try:
                        await asyncio.wait_for(
                            capture(browser, row, directory, args.origin), timeout=80
                        )
                    finally:
                        await browser.close()
                    (directory / "error.txt").unlink(missing_ok=True)
                except Exception as exc:
                    # Signed asset URLs can appear in exception messages.
                    (directory / "error.txt").write_text(type(exc).__name__ + "\n")

        await asyncio.gather(*(run(row) for row in rows[: args.limit]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--origin", default="https://tastefulkit.com")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--jobs", type=int, choices=range(1, 9), default=3)
    parser.add_argument("--chromium")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    asyncio.run(main(args))
