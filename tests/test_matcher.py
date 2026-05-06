from src.matcher import matches


def test_hits_first_keyword():
    assert matches("I am Interested in this", ["interested", "info"]) == "interested"


def test_case_insensitive():
    assert matches("Send INFO please", ["info"]) == "info"


def test_no_match():
    assert matches("hello world", ["interested"]) is None


def test_empty_inputs():
    assert matches("", ["x"]) is None
    assert matches("text", []) is None
    assert matches("text", ["", "  "]) is None


def test_multiple_keywords_returns_first_found():
    assert matches("info please", ["interested", "info"]) == "info"
