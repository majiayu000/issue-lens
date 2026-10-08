from click.utils import _make_default_short_help


def test_A_TC001_marker_only_first_paragraph():
    assert _make_default_short_help("\b\n\nSecond paragraph help.", 45) == ""


def test_A_TC002_B_TC001_eg_abbreviation():
    value = "Choose fruit e.g. apples and pears."
    assert _make_default_short_help(value, 45) == value


def test_B_TC002_empty_and_whitespace_and_marker():
    for value in ["", " \t\n ", "\n\b\n "]:
        assert _make_default_short_help(value, 10) == ""

