# Agent graph

Output of `graph.get_graph().draw_mermaid()` for the chat agent.

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	model(model)
	tools(tools)
	TopicalGuard\2ebefore_agent(TopicalGuard.before_agent)
	GroundednessGuard\2eafter_model(GroundednessGuard.after_model)
	TodoListMiddleware\2eafter_model(TodoListMiddleware.after_model)
	__end__([<p>__end__</p>]):::last
	GroundednessGuard\2eafter_model -.-> __end__;
	GroundednessGuard\2eafter_model -.-> model;
	GroundednessGuard\2eafter_model -.-> tools;
	TodoListMiddleware\2eafter_model --> GroundednessGuard\2eafter_model;
	TopicalGuard\2ebefore_agent --> model;
	__start__ --> TopicalGuard\2ebefore_agent;
	model --> TodoListMiddleware\2eafter_model;
	tools -.-> model;
```

* `CapabilityInstructions` and `ModelRetryMiddleware` wrap each model call and add no node.
* `after_model` hooks run in reverse middleware order.
