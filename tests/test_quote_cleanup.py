"""
Tests for the metadata quote normalisation utility.
"""

from metadata_exporter.cleanup import normalise_quotes


def test_normalise_quotes_replaces_curly_single_marks() -> None:
    text = "It\u2019s a farmer\u2018s field."
    expected = "It's a farmer's field."
    assert normalise_quotes(text) == expected


def test_normalise_quotes_replaces_curly_double_marks() -> None:
    text = "\u201cSoil\u201d sampled \u201ein situ\u201f."
    expected = '"Soil" sampled "in situ".'
    assert normalise_quotes(text) == expected


def test_normalise_quotes_replaces_inverted_question_mark() -> None:
    text = "¿Hello?"
    expected = "'Hello?"
    assert normalise_quotes(text) == expected


def test_normalise_quotes_returns_original_when_no_changes() -> None:
    text = 'Plain ASCII text with "double" and \'single\' quotes.'
    assert normalise_quotes(text) == text

