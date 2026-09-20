"""Branded PNG cards built from bounded text and already-stored thumbnails."""

from functools import lru_cache
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont, ImageOps

SIZE = (1200, 630)
PAPER = "#f8f7f3"
INK = "#242922"
MUTED = "#62675e"
ACCENT = "#b34424"
FONT_PATH = Path(__file__).parent / "assets" / "Inter.ttf"


@lru_cache(maxsize=64)
def font(size, weight=400):
    result = ImageFont.truetype(str(FONT_PATH), size)
    result.set_variation_by_axes([14, weight])
    return result


def wrap_text(text, face, width):
    """Wrap even unbroken titles; cap input before measuring it."""
    lines = [""]
    for word in " ".join(str(text).split())[:240].split(" "):
        candidate = (lines[-1] + " " + word).strip()
        if face.getlength(candidate) <= width:
            lines[-1] = candidate
            continue
        if lines[-1]:
            lines.append("")
        for char in word:
            if lines[-1] and face.getlength(lines[-1] + char) > width:
                lines.append("")
            lines[-1] += char
    return lines


def fitted_title(text, width):
    for size in range(104, 43, -2):
        face = font(size, 700)
        lines = wrap_text(text, face, width)
        if len(lines) <= 3 and len(lines) * (size + 10) <= 270:
            return face, lines
    lines = lines[:3]
    while face.getlength(lines[-1] + "…") > width:
        lines[-1] = lines[-1][:-1]
    lines[-1] += "…"
    return face, lines


def render_social_image(title, subtitle, label, thumbnail=None):
    """Return a 1200×630 PNG without browsers, network calls, or remote fonts."""
    image = Image.new("RGB", SIZE, PAPER)
    draw = ImageDraw.Draw(image)
    with Image.open(settings.BASE_DIR / "frontend/static/brand/apple-touch-icon.png") as logo:
        image.paste(logo.convert("RGB").resize((48, 48), Image.Resampling.LANCZOS), (48, 40))
    draw.text((110, 47), "TastefulKit", fill=INK, font=font(32, 700))
    draw.text((48, 137), label[:60], fill=ACCENT, font=font(26, 600))
    width = 430 if thumbnail else 1104
    face, lines = fitted_title(title, width)
    y = 190
    for line in lines:
        draw.text((48, y), line, fill=INK, font=face, anchor="lt")
        y += face.size + 10
    for line in wrap_text(subtitle, font(25), width)[:2]:
        draw.text((48, y + 22), line, fill=MUTED, font=font(25), anchor="lt")
        y += 34
    if thumbnail:
        preview = ImageOps.fit(
            thumbnail.convert("RGB"), (620, 430), Image.Resampling.LANCZOS, centering=(0.5, 0)
        )
        image.paste(preview, (532, 118))
        draw.rectangle((532, 118, 1151, 547), outline="#dddfd6", width=2)
    draw.line((48, 566, 1152, 566), fill="#dddfd6", width=2)
    draw.text((48, 587), "tastefulkit.com", fill=MUTED, font=font(22), anchor="lt")
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
