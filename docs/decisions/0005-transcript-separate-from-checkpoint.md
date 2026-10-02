# 0005. Transcript separate from the agent checkpoint

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

History was rebuilt from the agent checkpoint. The checkpoint holds the model's memory, rejected drafts included. Reasoning, plans and searches were lost on reload.

## Decision

Store each turn's question and streamed events in `conversation_turns`. The history endpoint reads that transcript. The frontend replays it through `applyEvent`.

## Consequences

* A reloaded chat renders as it did live.
* Two copies of each conversation.
* Migration `0010` deleted older conversations.
