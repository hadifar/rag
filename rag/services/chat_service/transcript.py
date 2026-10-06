from rag.domain.models import ReasoningDelta, StreamEvent, TextDelta


class TranscriptBuilder:
    """Collects a turn's stream as the user saw it, to be replayed as it was:
    consecutive text or reasoning deltas are merged into one, which the client shows
    the same.
    """

    def __init__(self):
        self.events: list[StreamEvent] = []

    def add(self, event: StreamEvent) -> None:
        match event:
            case TextDelta() | ReasoningDelta() if self._continues(event):
                last = self.events[-1]
                assert isinstance(last, TextDelta | ReasoningDelta)
                self.events[-1] = type(last)(text=last.text + event.text)
            case _:
                self.events.append(event)

    def _continues(self, event: TextDelta | ReasoningDelta) -> bool:
        return bool(self.events) and type(self.events[-1]) is type(event)
