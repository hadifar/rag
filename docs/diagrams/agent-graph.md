# Agent graph

Output of `graph.get_graph().draw_mermaid()` for the chat agent (`RagAgent.graph` in `rag/services/agent_service/agent.py`).

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	classify(classify)
	invoke_skill(invoke_skill)
	model(model)
	tools(tools)
	verify(verify)
	__end__([<p>__end__</p>]):::last
	__start__ --> classify;
	classify -.-> __end__;
	classify -.-> invoke_skill;
	classify -.-> model;
	invoke_skill --> model;
	model -.-> __end__;
	model -.-> tools;
	model -.-> verify;
	tools --> model;
	verify -.-> __end__;
	verify -.-> model;
```

* `classify` ends the turn for a blocked question and sends an off-topic one straight to `model`; `invoke_skill` starts a turn whose question begins with `/<name>` with that skill loaded; `verify` ends it, or sends a rejected answer back to `model` to revise.
* `model` builds each call's system prompt (planning or the off-topic decline) and picks its tools; neither is saved to the thread.
