import pytest
from pydantic import ValidationError

from rag.api.schema.conversation import MAX_MESSAGE_LENGTH, MessageRequest
from rag.api.schema.setting import PreferenceRequest
from rag.shared.text_normalizer import normalize_text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ｉｇｎｏｒｅ ﬁle", "ignore file"),  # full-width letters and ligatures
        ("x²", "x2"),  # NFKC's cost: superscripts lose their form
        ("ig​nore­ me﻿", "ignore me"),  # zero-width, soft hyphen, BOM
        ("hi\U000e0069\U000e0067\U000e006e", "hi"),  # tag characters (smuggled text)
        ("evil‮txt.exe⁦", "eviltxt.exe"),  # bidi overrides and isolates
        ("a︀b\U000e0100c", "abc"),  # variation selectors that carry no emoji form
        ("bell\x07 null\x00", "bell null"),  # control characters
    ],
)
def test_hidden_and_compatibility_characters_are_normalized_away(
    text: str, expected: str
) -> None:
    assert normalize_text(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "می‌خواهم",  # Persian needs the zero-width non-joiner
        "👨‍👩‍👧",  # emoji sequences need the zero-width joiner
        "❤️",  # an emoji's color form
        "AtlasFlow ‏سلام",  # right-to-left mark in mixed-direction text
    ],
)
def test_characters_real_text_needs_are_kept(text: str) -> None:
    assert normalize_text(text) == text


def test_whitespace_is_tidied_but_line_breaks_and_indentation_are_kept() -> None:
    text = "  why?\r\n\r\n\r\n\r\ndef f():\r    return   1   \tdone \t"

    assert normalize_text(text) == "why?\n\ndef f():\n    return 1\n\tdone"


def test_a_message_of_only_hidden_characters_and_spaces_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 1 character"):
        MessageRequest(message=" ​‮\n\t ")


def test_a_message_is_measured_after_it_is_normalized() -> None:
    padded = "a" * MAX_MESSAGE_LENGTH + "​" * 10 + "   "

    assert MessageRequest(message=padded).message == "a" * MAX_MESSAGE_LENGTH


def test_a_preference_is_normalized() -> None:
    assert PreferenceRequest(text=" Answer  in​ Dutch ").text == "Answer in Dutch"
