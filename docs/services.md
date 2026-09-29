# Services

## Generation service

- **`TopicalGuard`** classifies the user's message once per turn (`before_agent`). For an
  off-topic message it adds the decline instruction to the system prompt and removes the tools
  — for that turn's model calls only (`wrap_model_call`), so the decline text is still generated
  and streamed by `model`.
- **`GroundednessGuard`** checks each final answer against **this turn's** `search_kb` results
  (`after_model`), and on an ungrounded one jumps back to `model` with a revision instruction,
  capped at `MAX_REVISIONS`. It keeps no state: a rejected answer stays in the thread, so
  the revisions so far are this turn's final answers minus one.
- **`ModelRetryMiddleware`** retries the model call, then ends the turn with a fixed apology.

Guard instructions are never saved to the thread: the checkpoint holds only what the user and
the assistant said, so nothing carries over into later turns. "This turn" is everything after
the latest `HumanMessage` (`agent_service/turn.py`); `search_kb` returns its source ids as
the `ToolMessage` artifact, and the `sources` event is built from this turn's artifacts.
