import re
from dataclasses import dataclass

import yaml

from rag.domain.errors import InvalidSkillError
from rag.domain.models import SKILL_NAME_PATTERN
from rag.shared.text_normalizer import normalize_text

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

_NAME = re.compile(SKILL_NAME_PATTERN)

# The frontmatter: a block of YAML between two `---` lines, at the very start.
_FRONTMATTER = re.compile(r"---\n(.*?)\n---[ \t]*(?:\n|$)", re.DOTALL)


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    description: str  # on one line
    instructions: str  # the file's body, after its frontmatter


def parse_skill(data: bytes) -> ParsedSkill:
    """A SKILL.md file: YAML frontmatter with a `name` and a `description`, then the
    instructions as markdown. Raises `InvalidSkillError` saying what's wrong. The text
    is normalized as users' free text is (`normalize_text`), so nothing hidden in it
    reaches the model.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise InvalidSkillError("it isn't UTF-8 text") from None
    # Line breaks only: normalize_text would also tidy the whitespace YAML reads.
    text = text.replace("\r\n", "\n")
    match = _FRONTMATTER.match(text)
    if match is None:
        raise InvalidSkillError(
            "it must start with frontmatter between --- lines, "
            "holding its name and description"
        )
    fields = _frontmatter(match.group(1))
    return ParsedSkill(
        name=_name(fields.get("name")),
        description=_description(fields.get("description")),
        instructions=_instructions(text[match.end() :]),
    )


def _frontmatter(source: str) -> dict[object, object]:
    try:
        fields = yaml.safe_load(source)
    except yaml.YAMLError:
        raise InvalidSkillError("its frontmatter isn't valid YAML") from None
    if not isinstance(fields, dict):
        raise InvalidSkillError("its frontmatter must be a set of `key: value` fields")
    return fields


def _name(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSkillError("its frontmatter has no `name`")
    name = value.strip()
    if len(name) > MAX_NAME_LENGTH or not _NAME.fullmatch(name):
        raise InvalidSkillError(
            f"its name must be up to {MAX_NAME_LENGTH} lowercase letters, digits "
            "and hyphens, e.g. `release-notes`"
        )
    return name


def _description(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSkillError("its frontmatter has no `description`")
    description = " ".join(normalize_text(value).split())
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise InvalidSkillError(
            f"its description is longer than {MAX_DESCRIPTION_LENGTH} characters"
        )
    return description


def _instructions(body: str) -> str:
    instructions = normalize_text(body)
    if not instructions:
        raise InvalidSkillError("it has no instructions after its frontmatter")
    return instructions
