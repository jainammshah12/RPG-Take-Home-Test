"""Normalize merchant / client names for grouping and display."""

from __future__ import annotations

import re

# Multi-word brands kept together when matching substrings in descriptions
_MULTI_WORD_BRANDS: tuple[tuple[str, str], ...] = (
    (r"tim\s+hortons", "Tim Hortons"),
    (r"amazon\s+web\s+services|amzn\s+web", "Amazon Web Services"),
    (r"brightpath\s+marketing", "BrightPath Marketing"),
    (r"greenloop\s+technologies", "GreenLoop Technologies"),
    (r"atelier\s+nomade", "Atelier Nomade"),
    (r"nonna'?s?\s+kitchen", "Nonna's Kitchen"),
    (r"bloom\s*&\s*co", "Bloom & Co"),
)


def primary_entity_name(full: str) -> str:
    """Client/vendor name before em-dash or double-dash description suffix."""
    if not full or str(full).lower() in ("none", "nan"):
        return ""
    trimmed = str(full).strip()
    parts = re.split(r"\s*[—–]\s*|\s+--\s+", trimmed, maxsplit=1)
    return (parts[0] or trimmed).strip()


def merchant_group_key(full: str) -> str:
    """Canonical key for aggregating spend/revenue charts (one bar per brand/client)."""
    if not full or str(full).lower() in ("none", "nan"):
        return ""

    text = str(full).strip()
    low = text.lower()

    for pattern, label in _MULTI_WORD_BRANDS:
        if re.search(pattern, low):
            return label

    primary = primary_entity_name(text)
    primary = re.sub(r"\s+#\d+", "", primary, flags=re.IGNORECASE)
    primary = re.sub(r"\s{2,}", " ", primary).strip()
    if not primary:
        return ""

    return primary.title()
