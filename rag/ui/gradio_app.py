import re
import uuid

import gradio as gr

from rag.container import ContainerHandle
from rag.services.generation_service.streaming import (
    StreamEvent,
    TextDelta,
    ToolCallResult,
    ToolCallStart,
)

_SOURCE_RE = re.compile(r"\[source: ([^\]]+)\]")


class _RenderState:
    """Accumulates one turn's events into Gradio's `messages`-style chat list."""

    def __init__(self) -> None:
        self._answer = {"role": "assistant", "content": ""}
        self._tool_block: dict | None = None
        self._rendered: list[dict] = []
        self._sources: set[str] = set()

    def apply(self, event: StreamEvent) -> None:
        match event:
            case ToolCallStart(name=name, args=args):
                self._tool_block = {
                    "role": "assistant",
                    "content": f"Searching for: {args.get('query', args)}",
                    "metadata": {"title": f"🔧 {name}"},
                }
                self._rendered.append(self._tool_block)
            case ToolCallResult(output=output):
                if self._tool_block is not None:
                    self._tool_block["content"] = output
                self._sources.update(_SOURCE_RE.findall(output))
            case TextDelta(text=text):
                self._answer["content"] += text

    def render(self) -> list[dict]:
        # Reflects what was actually retrieved for this turn, not what the model
        # claims it cited — more reliable than parsing/trusting free-text citations.
        messages = [*self._rendered, self._answer]
        if self._sources:
            links = ", ".join(f"[{name}](/kb/{name})" for name in sorted(self._sources))
            messages.append(
                {
                    "role": "assistant",
                    "content": links,
                    "metadata": {"title": "📚 Sources"},
                }
            )
        return messages


def build_gradio_ui(handle: ContainerHandle) -> gr.Blocks:
    async def respond(message: str, history: list, thread_id: str):
        generation_service = handle.get().generation_service
        state = _RenderState()
        async for event in generation_service.stream_chat(message, thread_id):
            state.apply(event)
            yield state.render()

    with gr.Blocks(title="RAG") as demo:
        thread_id = gr.State(lambda: str(uuid.uuid4()))
        gr.ChatInterface(fn=respond, additional_inputs=[thread_id])

    return demo
