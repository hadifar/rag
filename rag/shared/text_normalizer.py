import re
import unicodedata

# Every line break as "\n", so the rest only deals with one.
_LINE_BREAKS = re.compile("\r\n|[\r\v\f\x85  ]")

# Format characters (Unicode category Cf) are invisible, and text hidden in them still
# reaches the model (e.g. tag characters, U+E0000–E007F). Kept: the zero-width
# non-joiner and joiner, which Persian, Indic scripts and emoji sequences need, and the
# left-to-right and right-to-left marks, which only steer how mixed-direction text shows.
_KEPT_FORMAT = frozenset("‌‍‎‏")

# Variation selectors can carry hidden bytes too. Kept: FE0E and FE0F, which pick an
# emoji's text or color form.
_VARIATION_SELECTORS = re.compile("[︀-︍\U000e0100-\U000e01ef]")

_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)
# A run after the line's first text; the indentation before it is kept, for code.
_INNER_SPACE_RUN = re.compile(r"(?<=\S)[ \t]{2,}")
_BLANK_LINE_RUN = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """`text` as users' free text is stored and sent on: NFKC (full-width letters and
    ligatures become plain ones), without control, invisible or bidi-override
    characters, and with whitespace tidied: no trailing or doubled spaces, at most one
    blank line in a row, nothing around it. Line breaks and indentation are kept.
    """
    text = _LINE_BREAKS.sub("\n", unicodedata.normalize("NFKC", text))
    text = _VARIATION_SELECTORS.sub("", "".join(filter(_is_visible, text)))
    text = _INNER_SPACE_RUN.sub(" ", _TRAILING_SPACE.sub("", text))
    return _BLANK_LINE_RUN.sub("\n\n", text).strip()


def _is_visible(char: str) -> bool:
    """False for control characters but newline and tab, and for format characters
    but the ones in `_KEPT_FORMAT`.
    """
    match unicodedata.category(char):
        case "Cc":
            return char in "\n\t"
        case "Cf":
            return char in _KEPT_FORMAT
        case _:
            return True
