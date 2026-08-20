"""
Minimal frontmatter parser for the '---\\nkey: value\\n---\\nbody' format used
by every document in data/source/ and data/policies/. Deliberately not pulling
in a full YAML parser dependency for a handful of flat key: value pairs.
"""
from __future__ import annotations


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Returns (metadata_dict, body_text). If the text has no frontmatter
    block, returns an empty dict and the original text unchanged."""
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    _, raw_meta, body = parts
    metadata: dict[str, str] = {}
    for line in raw_meta.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip()

    return metadata, body.strip()
