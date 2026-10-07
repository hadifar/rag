import base64
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage

from rag.domain.models import AttachmentFile

# The user's message keeps its attachments' ids here, never their content: the thread,
# and so the agent's memory, refers to them, and each model call reads them afresh.
ATTACHMENT_IDS = "attachment_ids"

ContentBlock = dict[str, Any]


def _text_block(file: AttachmentFile) -> ContentBlock:
    name = json.dumps(file.attachment.name)  # quoted and escaped
    text = file.data.decode("utf-8")
    return {"type": "text", "text": f"<attachment name={name}>\n{text}\n</attachment>"}


def _image_block(file: AttachmentFile) -> ContentBlock:
    return {
        "type": "image",
        "base64": base64.b64encode(file.data).decode("ascii"),
        "mime_type": file.attachment.media_type,
    }


def _unreadable_block(file: AttachmentFile) -> ContentBlock:
    name = json.dumps(file.attachment.name)
    return {
        "type": "text",
        "text": f"<attachment name={name}>(unreadable)</attachment>",
    }


# How the model reads each kind of attachment (see attachment_service/kinds.py).
_RENDERERS: dict[str, Callable[[AttachmentFile], ContentBlock]] = {
    "text/markdown": _text_block,
    "image/png": _image_block,
    "image/jpeg": _image_block,
}


def render(file: AttachmentFile) -> ContentBlock:
    """The attachment as one content block of a message to the model."""
    return _RENDERERS.get(file.attachment.media_type, _unreadable_block)(file)


def text_of(files: Sequence[AttachmentFile]) -> str:
    """The text the attachments render to; nothing for one that isn't text (images)."""
    blocks = [render(f) for f in files]
    return "\n\n".join(b["text"] for b in blocks if b["type"] == "text")


def question_message(message: str, files: Sequence[AttachmentFile]) -> HumanMessage:
    """The user's message as the thread keeps it: its text, and its attachments' ids."""
    kwargs = {ATTACHMENT_IDS: [str(f.attachment.id) for f in files]} if files else {}
    return HumanMessage(content=message, id=str(uuid.uuid4()), additional_kwargs=kwargs)


def attachments_of(
    message: BaseMessage, files: Mapping[str, AttachmentFile]
) -> list[AttachmentFile]:
    """The message's attachments, among `files` (by id), in the order it lists them."""
    ids: list[str] = message.additional_kwargs.get(ATTACHMENT_IDS, [])
    return [files[i] for i in ids if i in files]


def with_attachments(
    messages: Sequence[BaseMessage], files: Mapping[str, AttachmentFile]
) -> list[BaseMessage]:
    """The messages as the model is to read them: each user message that lists
    attachments gets their content after its text.
    """
    return [_with_attachments(m, files) for m in messages]


def _with_attachments(
    message: BaseMessage, files: Mapping[str, AttachmentFile]
) -> BaseMessage:
    attached = attachments_of(message, files)
    if not isinstance(message, HumanMessage) or not attached:
        return message
    text: list[ContentBlock] = (
        [{"type": "text", "text": message.text}] if message.text else []
    )
    return HumanMessage(content=[*text, *(render(f) for f in attached)], id=message.id)
