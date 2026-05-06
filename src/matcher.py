from __future__ import annotations


def matches(comment_text: str, keywords: list[str]) -> str | None:
    """Return the first keyword found in comment_text (case-insensitive), or None."""
    if not comment_text or not keywords:
        return None
    haystack = comment_text.casefold()
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.casefold() in haystack:
            return kw
    return None
