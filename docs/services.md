# Services

## Generation service

- **`TopicalGuard`** classifies the user's message once per turn (`before_agent`). For an
  off-topic message it adds the decline instruction to the system prompt and removes every tool
  but the `kind="user"` ones (e.g. the preference tools) — for that turn's model calls only (`wrap_model_call`), so the decline text is still generated
  and streamed by `model`.
- **`GroundednessGuard`** checks each final answer against **this turn's** `search_kb` results
  (not the `kind="user"` tools' replies; `after_model`), and on an ungrounded one jumps back to `model` with a revision instruction,
  capped at `MAX_REVISIONS`. It keeps no state: a rejected answer stays in the thread, so
  the revisions so far are this turn's final answers minus one.
- **`CapabilityInstructions`** (`agent_service/middleware/capabilities.py`) adds each of the
  spec's `Capability` instructions to the system prompt on every model call, read fresh, so a
  preference saved mid-turn applies from the next call on. The agent service knows no feature
  by name: the user's preferences are one capability, from `PreferenceService.capability()`
  (`preference_service/service.py`) — the saved preferences with their ids as instructions, plus
  `save_user_preference` and `forget_user_preference` as `kind="user"` tools. The user comes from
  the turn's `RunContext` (set from the access token), never from the model. The rules (at most
  20 per user, 200 characters each, no case-insensitive duplicates) are the service's; the
  storage is `PreferenceRepositoryPort` (today `adapters/lang_preference_store.py`, on the
  LangGraph store under `("users", <id>, "preferences")`).
- **`ModelRetryMiddleware`** retries the model call, then ends the turn with a fixed apology.

Guard instructions are never saved to the thread: the checkpoint holds only what the user and
the assistant said, so nothing carries over into later turns. "This turn" is everything after
the latest `HumanMessage` (`agent_service/turn.py`); `search_kb` returns its source ids as
the `ToolMessage` artifact, and the `references` event is built from this turn's artifacts.
