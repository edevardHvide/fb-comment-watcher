from __future__ import annotations


def matches(
    comment_text: str,
    keywords: list[str],
    exclude_keywords: list[str] | None = None,
) -> str | None:
    """Return the first keyword found in comment_text (case-insensitive), or None.

    If any exclude_keyword is present, returns None even if an include keyword matches.
    """
    if not comment_text or not keywords:
        return None
    haystack = comment_text.casefold()
    for ex in exclude_keywords or []:
        ex = ex.strip()
        if ex and ex.casefold() in haystack:
            return None
    for kw in keywords:
        kw = kw.strip()
        if kw and kw.casefold() in haystack:
            return kw
    return None
