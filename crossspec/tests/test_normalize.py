from crossspec.normalize import normalize_light


def test_normalize_light_collapses_whitespace():
    text = "Line one\n\nLine   two\t\tLine three"
    assert normalize_light(text) == "Line one Line two Line three"


def test_normalize_light_strips_edges():
    text = "   leading and trailing   "
    assert normalize_light(text) == "leading and trailing"
