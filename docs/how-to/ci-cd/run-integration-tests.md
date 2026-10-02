# Run integration tests

## Description

Run `tests/integration` in CI against a throwaway Postgres and the real LLM provider.

## Steps

1. Open **Actions → integration-tests** on GitHub.
2. Run the workflow on the branch.
3. The job migrates, checks `downgrade base` and `upgrade head`, then runs `pytest tests/integration`.

## Rules

* Run the workflow before you merge a change to a repository, a migration or the agent.
* The workflow needs `secrets.OPENAI_API_KEY` and `vars.OPENAI_MODEL`.
* To run locally, see [Run backend tests](../backend/run-tests.md).
