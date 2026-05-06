from src.watcher import _META_LINE, _NAME_FROM_ARIA, _commenter_id_from_url


def _name(label: str) -> str | None:
    m = _NAME_FROM_ARIA.match(label)
    return m.group(1) if m else None


def test_name_from_aria_simple():
    assert _name("Comment by Jane Doe") == "Jane Doe"


def test_name_strips_trailing_timestamp_english():
    assert _name("Comment by Edevard Hvide 17 minutes ago") == "Edevard Hvide"
    assert _name("Comment by Jane Doe 2 hours ago") == "Jane Doe"


def test_name_norwegian():
    assert _name("Kommentar av Edevard Hvide") == "Edevard Hvide"
    assert _name("Kommentar av Edevard Hvide 17 minutter siden") == "Edevard Hvide"


def test_meta_line_matches():
    for s in ["17m", "2h", "5d", "Like", "Reply", "Like  Reply", "Edited", "Share"]:
        assert _META_LINE.match(s), s


def test_meta_line_does_not_match_real_content():
    for s in ["jeg selger en billett", "Hello world", "interested!", "yes"]:
        assert not _META_LINE.match(s), s


def test_profile_php():
    assert _commenter_id_from_url("https://www.facebook.com/profile.php?id=12345") == "12345"


def test_vanity():
    assert _commenter_id_from_url("https://www.facebook.com/jane.doe") == "jane.doe"
    assert _commenter_id_from_url("https://www.facebook.com/jane.doe/") == "jane.doe"


def test_group_user_link():
    url = "https://www.facebook.com/groups/584048631673669/user/100012345678901/"
    assert _commenter_id_from_url(url) == "100012345678901"


def test_skip_groups_root():
    assert _commenter_id_from_url("https://www.facebook.com/groups/123/permalink/456") is None


def test_skip_share():
    assert _commenter_id_from_url("https://www.facebook.com/share/p/abc/") is None


def test_relative_normalized_externally():
    assert _commenter_id_from_url("") is None
    assert _commenter_id_from_url(None) is None  # type: ignore[arg-type]
