"""Bounded validation of supplied files; never transform or generate assets."""

import io
import re
import warnings

import yaml
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_DESIGN_BYTES = 128 * 1024
IMAGE_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def read_image(upload, *, thumbnail=False, viewport_width=None):
    limit = 2 * 1024 * 1024 if thumbnail else MAX_IMAGE_BYTES
    content = upload.read(limit + 1)
    if not content or len(content) > limit:
        raise ValueError(f"{'Thumbnail' if thumbnail else 'Screenshot'} exceeds its size limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.width * image.height > 40_000_000:
                    raise ValueError("Images must contain at most 40 million pixels.")
                extension = IMAGE_EXTENSIONS.get(image.format)
                if not extension or getattr(image, "is_animated", False):
                    raise ValueError("Supply a static PNG, JPEG or WebP image.")
                if thumbnail and (image.width > 1440 or image.height > 1440):
                    raise ValueError("Supply a prepared thumbnail no larger than 1440 × 1440.")
                if viewport_width and image.width != viewport_width:
                    raise ValueError("Full-page screenshot width must match viewport_width.")
                image.verify()
            # verify() alone does not decode JPEG pixels, so reject truncated files too.
            with Image.open(io.BytesIO(content)) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        SyntaxError,
    ) as exc:
        raise ValueError("Supply a valid, bounded PNG, JPEG or WebP image.") from exc
    return content, extension


class DesignLoader(yaml.SafeLoader):
    """No aliases, duplicate keys or deeply nested token trees."""

    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ValueError("DESIGN.md YAML aliases are not supported.")
        self.depth = getattr(self, "depth", 0) + 1
        if self.depth > 12:
            raise ValueError("DESIGN.md YAML is nested too deeply.")
        try:
            return super().compose_node(parent, index)
        finally:
            self.depth -= 1

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError("DESIGN.md YAML requires unique string keys.")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _check_references(value, root, trail, checked):
    if len(trail) > 32:
        raise ValueError("DESIGN.md token reference chains are too long.")
    if isinstance(value, dict):
        for item in value.values():
            _check_references(item, root, trail, checked)
    elif isinstance(value, list):
        for item in value:
            _check_references(item, root, trail, checked)
    elif isinstance(value, str):
        for reference in re.findall(r"\{([\w.-]+)\}", value):
            if reference in trail:
                raise ValueError("DESIGN.md contains circular token references.")
            if reference in checked:
                continue
            target = _reference_target(root, reference)
            _check_references(target, root, (*trail, reference), checked)
            checked.add(reference)


def _reference_target(root, reference):
    target = root
    for part in reference.split("."):
        if not isinstance(target, dict) or part not in target:
            raise ValueError("DESIGN.md contains an unresolved token reference.")
        target = target[part]
    return target


def read_design_markdown(upload):
    content = upload.read(MAX_DESIGN_BYTES + 1)
    if not content or len(content) > MAX_DESIGN_BYTES:
        raise ValueError("DESIGN.md must be non-empty and at most 128 KiB.")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("DESIGN.md must be UTF-8 text.") from exc
    if "\x00" in text:
        raise ValueError("DESIGN.md contains invalid characters.")
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError("DESIGN.md requires YAML front matter and Markdown guidance.")
    end = lines.index("---", 1)
    try:
        tokens = yaml.load("\n".join(lines[1:end]), Loader=DesignLoader)
    except yaml.YAMLError as exc:
        raise ValueError("DESIGN.md contains invalid YAML.") from exc
    if (
        not isinstance(tokens, dict)
        or not isinstance(tokens.get("name"), str)
        or not tokens["name"].strip()
    ):
        raise ValueError("DESIGN.md requires a non-empty design name.")
    for group in ("colors", "typography"):
        if not isinstance(tokens.get(group), dict) or not tokens[group]:
            raise ValueError(f"DESIGN.md requires {group} tokens.")
    body = "\n".join(lines[end + 1 :]).strip()
    if len(body) < 80 or not re.search(r"^## .+", body, re.MULTILINE):
        raise ValueError("DESIGN.md requires actionable Markdown sections, not just tokens.")
    _check_references(tokens, tokens, (), set())
    return text
