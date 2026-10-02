from rag.domain.models import (
    AnswerRetracted,
    ReasoningDelta,
    StreamEvent,
    TextDelta,
    TodosUpdated,
    ToolCall,
)


class TranscriptBuilder:
    """Collects a turn's stream as the user ends up seeing it, to be replayed as it was:
    the text of a retracted answer is dropped, as the client drops it, and consecutive
    text or reasoning deltas are merged into one, which the client shows the same.
    """

    def __init__(self):
        self.events: list[StreamEvent] = []
        # Off right after a retraction: what streams next is a new bubble, not a
        # continuation of what came before the dropped text.
        self._merge = True

    def add(self, event: StreamEvent) -> None:
        match event:
            case AnswerRetracted():
                self._drop_answer_text()
                self._merge = False
            case TextDelta() | ReasoningDelta() if self._continues(event):
                last = self.events[-1]
                assert isinstance(last, TextDelta | ReasoningDelta)
                self.events[-1] = type(last)(text=last.text + event.text)
            case _:
                self.events.append(event)
                self._merge = True

    def _continues(self, event: TextDelta | ReasoningDelta) -> bool:
        return (
            self._merge and bool(self.events) and type(self.events[-1]) is type(event)
        )

    def _drop_answer_text(self) -> None:
        """The answer is the text since the last tool call or plan, as the client's
        bubble is; the reasoning that led to it stays.
        """
        start = next(
            (
                i + 1
                for i in range(len(self.events) - 1, -1, -1)
                if isinstance(self.events[i], ToolCall | TodosUpdated)
            ),
            0,
        )
        self.events[start:] = [
            e for e in self.events[start:] if not isinstance(e, TextDelta)
        ]
