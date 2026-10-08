# Add an SSE event

## Description

Add an event to the chat stream. Use when the agent must send the client a new kind of information. Read [Streaming](../../architecture/backend.md#streaming) first.

## Steps

1. Add a dataclass with a `type: Literal[...]` field to `rag/domain/models/agent/stream.py`.
2. Add the dataclass to the `StreamEvent` union.
3. Re-export the dataclass from `rag/domain/models/__init__.py`.
4. Emit the event in `parse_event` in `rag/services/agent_service/streaming.py`.
5. If a graph node emits the event, name the custom event in `rag/services/agent_service/streaming.py`, add an async helper there that dispatches it with `adispatch_custom_event`, and call the helper from the node. Example: `AnswerChecked` (`answer_check_started`, `answer_checked`).
6. If the event changes events already sent, apply it in `TranscriptBuilder` in `rag/services/chat_service/transcript.py`.
7. Add a Pydantic model with `type: Literal[...]` to `rag/api/schema/chat.py`.
8. Add the model to the `StreamEventResponse` union. `to_stream_event` maps the dataclass by its fields and `type`, so the two must match.
9. Add the type line to `frontend/src/shared/types/api.ts`.
10. Add the case to `applyEvent` in `frontend/src/features/chat/model/transcript.ts`.
11. If the event makes a new bubble, add:
    * the variant to `Bubble` in `frontend/src/features/chat/types.ts`;
    * a component in `frontend/src/features/chat/components/`;
    * the entry in `bubbleViews` in `frontend/src/features/chat/components/MessageList.tsx`.
12. Test `applyEvent` in `frontend/tests/unit/utils/transcript.test.ts`.
13. Test the backend in `tests/unit/test_streaming.py` and `tests/unit/test_transcript.py`.
14. Validate the change. See [Run validation](../run-validation.md).

## Rules

* `applyEvent` has a `satisfies never` default. The frontend fails to compile until step 10 is done.
* History replays through `applyEvent`. History needs no extra code.
