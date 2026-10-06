import uuid

from rag.adapters.langchain.observability import _logging_trace_config
from rag.domain.models import RunContext


def test_a_named_run_is_tagged_and_traced_under_its_user_and_conversation() -> None:
    ctx = RunContext(user_id=uuid.uuid4(), conversation_id=uuid.uuid4())

    config = _logging_trace_config("chat", ctx)

    assert config.get("run_name") == "chat"
    assert config.get("tags") == ["chat"]
    assert config.get("metadata") == {
        "langfuse_user_id": str(ctx.user_id),
        "langfuse_session_id": str(ctx.conversation_id),
    }


def test_an_unnamed_run_without_context_carries_only_its_callbacks() -> None:
    config = _logging_trace_config()

    assert set(config) == {"callbacks"}
