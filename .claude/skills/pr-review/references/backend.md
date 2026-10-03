# Backend Review Guide (Python + FastAPI)

> **This repo:** layered FastAPI app. Routers reach services only through `rag/api/deps.py`. Services hold business rules and raise `AppError` subclasses (`rag/domain/errors.py`). Repositories hold raw SQL on a psycopg `AsyncConnectionPool`. Everything long-lived is built once in `rag/container.py`. Another user's resource answers **404**, not 403, so ids can't be probed.

Code reaching review already passes ruff, pyright, and import-linter. Flag only `# type: ignore`, `# noqa`, `cast(...)`, or `Any` added without a stated reason.

## Layers and design

- **Logic in a router.** Business rules or SQL belong in a service or repository. Routers validate, call one service, and map to a response schema.
- **Concrete dependencies.** A service should take a domain `Protocol` port, not an adapter or repository class.
- **Construction outside the container.** An adapter, pool, or SDK client built anywhere but `rag/container.py`, and especially one built per request.
- **Error classes.** A new `AppError` needs the right `status_code` (400/404/409/413/502) and a message with no internals or other users' data. Reuse an existing class if one fits.
- **Swallowed errors.** `except Exception:` that logs and carries on (`BLE001` allows this) hides bugs on paths where failing loudly is correct. Catch what you can handle.
- **Module-level mutable state** in a server process is shared by every concurrent request.

## Async correctness

One blocking call on the event loop stalls *every* in-flight request, including every open chat stream.

- **Blocking SDK calls ruff can't see.** LangChain `.invoke`/`.stream`/`.embed_*` instead of `.ainvoke`/`.astream`/`.aembed_*`. Sync `azure.storage.blob` instead of `.aio`. Sync `psycopg.Connection`.
- **Bolting sync code onto the loop.** `asyncio.run`, a new event loop, or a manual thread inside request handling (`asyncio.run` raises under a running loop). The threadpool (`def` route, `run_in_threadpool`, `asyncio.to_thread`) holds about 40 threads. That is fine for a rare call with no async SDK, but a scaling bug on a hot path.
- **CPU-heavy work in a request**: zip extraction, chunking large archives, local embedding or tokenizing. Neither the loop nor threads help under the GIL. Use a background process, or record progress in state as `ingestion_runs` does.
- **Cancellation.** `except asyncio.CancelledError` (or `BaseException`) without re-raising makes the task unstoppable.
- **Fan-out.** `gather` over a large or user-controlled list hitting the LLM, embeddings, or the DB pool needs a `Semaphore`. Plain `gather` doesn't cancel siblings on failure. Use `TaskGroup` when they must stop together.
- **Unawaited coroutines** are silently dropped. `BackgroundTasks` is in-process, best-effort, and dies with the process.
- **SSE stream.** The generator must stop on client disconnect. Saving the transcript must not depend on the stream finishing normally. Events go through `to_stream_event`, never as raw domain objects.
- **Caches.** `@cache` on an `async def` caches a one-shot coroutine. A cache keyed by user input grows without bound. A cache of per-user data must not be shared across users.

## Validation (Pydantic v2)

- **Trust boundary.** Request and response are distinct schemas in `rag/api/schema/`. Returning a domain or storage object leaks fields like `password_hash`, and accepting one lets clients set `id` or `is_admin`. A new response field also changes `api.generated.ts`.
- **Create vs update.** These need separate schemas. PATCH uses `model_dump(exclude_unset=True)`, so "not sent" is not "null".
- **Constraints at the boundary.** Use `Field(gt=…, max_length=…)` before the write, not after. Check free text reaching the LLM or DB, upload sizes, and list lengths.

## Database

- **Holding connections.** A connection held across a slow `await` (LLM, HTTP) pins a pool slot for seconds and starves other requests.
- **Atomic writes.** Multi-statement writes that must be atomic need one connection and `conn.transaction()`, not several `_execute` calls.
- **N+1.** A repository call inside a loop over rows. Use a JOIN or `= ANY(%s)`.
- **Aggregation in Python** (loops that group, count, or join). Push it into SQL.
- **List endpoints** reuse cursor pagination with `PageLimit` (`rag/api/schema/conversation.py`).
- **Indexes.** A new query pattern on a large table needs an index in the migration.
- **Dynamic SQL.** Identifiers go through `psycopg.sql.Identifier`, never string building. `LIKE` patterns must escape `%` and `_`.

## Security

- **Authentication is not authorization.** `get_current_user` proves who the caller is, not that they may touch *this* resource. Every id-taking path must scope by `user_id` in the service or SQL (`WHERE id = %s AND user_id = %s`). Missing and not-yours both raise the same `*NotFoundError`. Admin routes need the admin check.
- **`_PUBLIC_ROUTES`.** Any addition in `tests/unit/test_app.py` needs explicit sign-off.
- **LLM.** Retrieved documents, user messages, and tool output are untrusted. Don't move them into the system prompt or let them trigger privileged tools. One user's data (preferences, conversations) must never reach another user's prompt or cache.
- **Leaks.** Error messages and logs must not contain SQL, stack traces, paths, tokens, passwords, or other users' emails. Auth endpoints need some lockout or rate limit.
- **CORS.** The browser uses a same-origin proxy ([ADR 0009](../../../../docs/decisions/0009-same-origin-proxy.md)), so a PR adding `CORSMiddleware` needs a reason. Never combine `allow_origins=["*"]` with credentials.

## Test-driven verification

A prose verdict like "this looks safe" is a fallible hypothesis. A failing test is ground truth. For a suspected P0 or P1 bug, **reproduce it and watch it fail** before reporting it.

The app is built from a `Container` of fakes. The `client` fixture in `tests/unit/test_app.py` seeds two users (`_TEST_EMAIL`, `_OTHER_EMAIL`) and an admin, and `_login(client, email)` returns auth headers. Write a scratch test outside the repo:

```python
# <scratchpad>/test_review_repro.py
from fastapi.testclient import TestClient

from tests.unit.test_app import _OTHER_EMAIL, _TEST_EMAIL, _login, client  # noqa: F401  (fixture)


def test_user_cannot_delete_another_users_preference(client: TestClient) -> None:
    alice = _login(client, _TEST_EMAIL)
    bob = _login(client, _OTHER_EMAIL)
    created = client.post(
        "/api/settings/preferences", json={"text": "Answer in French"}, headers=alice
    )

    resp = client.delete(
        f"/api/settings/preferences/{created.json()['id']}", headers=bob
    )

    assert resp.status_code == 404
```

```bash
uv run pytest <scratchpad>/test_review_repro.py -p no:cacheprovider -q
# FAILED  assert 204 == 404   <- Bob deleted Alice's preference: confirmed
```

The failure must be the bug, not an import error, a fixture error, or a 422 from a bad payload. Quote the failing assertion in the finding and offer the test to the author. For service-level bugs, build the service directly with the fakes in `tests/unit/fakes.py`.

## The PR's own tests

- **Behavior changed with no test.** Postgres-only tests in `tests/integration/` don't run in CI, so also want a unit test with fakes.
- **Happy path only.** Check 401, 404, 409, and 422 too.
- **Testing the mock.** A test whose only assertion is "the mock was called". Prefer fakes and constructor injection to `patch` on import paths.
- **Unfaithful fakes.** A fake that skips a constraint the real repository enforces (ownership filter, uniqueness, ordering). Check the fake changed alongside the repository.
- **Shared mutable fixtures.** A `module` or `session` scope on mutable state makes tests order-dependent.
- **Tests that can't fail.** A test green from birth proves little.
