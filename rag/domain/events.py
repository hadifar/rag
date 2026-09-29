from dataclasses import dataclass


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolCallStart:
    name: str
    query: str


@dataclass
class ToolCallResult:
    name: str
    output: str


@dataclass
class SourcesReady:
    sources: list[str]


StreamEvent = TextDelta | ToolCallStart | ToolCallResult | SourcesReady
