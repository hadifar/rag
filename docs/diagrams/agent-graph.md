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
	check_input(check_input)
	invoke_skill(invoke_skill)
	model(model)
	tools(tools)
	check_answer(check_answer)
	__end__([<p>__end__</p>]):::last
	__start__ --> check_input;
	check_answer -.-> __end__;
	check_answer -.-> model;
	check_input -.-> __end__;
	check_input -.-> invoke_skill;
	check_input -.-> model;
	invoke_skill --> model;
	model -.-> __end__;
	model -.-> check_answer;
	model -.-> tools;
	tools --> model;
```

* `check_input` ends the turn for a blocked question and sends an off-topic one straight to `model`; `invoke_skill` starts a turn whose question begins with `/<name>` with that skill loaded; `check_answer` ends it, or sends a rejected answer back to `model` to revise.
* `model` builds each call's system prompt (planning or the off-topic decline) and picks its tools; neither is saved to the thread.
