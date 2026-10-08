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
	load_skills(load_skills)
	model(model)
	decline(decline)
	tools(tools)
	check_answer(check_answer)
	__end__([<p>__end__</p>]):::last
	__start__ --> check_input;
	check_answer -. &nbsp;accept&nbsp; .-> __end__;
	check_answer -. &nbsp;revise&nbsp; .-> model;
	check_input -. &nbsp;block&nbsp; .-> __end__;
	check_input -. &nbsp;off_topic&nbsp; .-> decline;
	check_input -. &nbsp;allow&nbsp; .-> load_skills;
	load_skills --> model;
	model -.-> __end__;
	model -.-> check_answer;
	model -.-> tools;
	tools --> model;
	decline --> __end__;
```

* `check_input` ends the turn for a blocked question, sends an off-topic one to `decline`, and the rest to `load_skills`; `load_skills` lists the user's skills for the model and starts a turn whose question begins with `/<name>` with that skill loaded; `check_answer` ends it, or sends a rejected answer back to `model` to revise.
* `model` builds each call's system prompt (planning and the user's skills) and binds the tools; `decline` answers an off-topic question with the decline prompt and no tools, and ends the turn. Neither prompt is saved to the thread.
