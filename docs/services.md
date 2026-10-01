# Services

## Generation service

- **`TopicalGuard`** classifies the user's message once per turn (`before_agent`). For an
  off-topic message it adds the decline instruction to the system prompt and removes the tools
  but the preference tools — for that turn's model calls only (`wrap_model_call`), so the decline text is still generated
  and streamed by `model`.
- **`GroundednessGuard`** checks each final answer against **this turn's** `search_kb` results
  (not the preference tools' replies; `after_model`), and on an ungrounded one jumps back to `model` with a revision instruction,
  capped at `MAX_REVISIONS`. It keeps no state: a rejected answer stays in the thread, so
  the revisions so far are this turn's final answers minus one.
- **`PreferencesMiddleware`** (`agent_service/preferences.py`) reads the user's preferences from
  the LangGraph store on every model call and adds them, with their ids, to the system prompt;
  it also gives the model `save_user_preference` and `forget_user_preference`. The user comes
  from the turn's runtime context (`ChatContext`, set from the access token), never from the
  model, and each user's preferences live under their own store namespace
  (`("users", <id>, "preferences")`, one item each; at most 20, 200 characters each).
- **`ModelRetryMiddleware`** retries the model call, then ends the turn with a fixed apology.

Guard instructions are never saved to the thread: the checkpoint holds only what the user and
the assistant said, so nothing carries over into later turns. "This turn" is everything after
the latest `HumanMessage` (`agent_service/turn.py`); `search_kb` returns its source ids as
the `ToolMessage` artifact, and the `sources` event is built from this turn's artifacts.
