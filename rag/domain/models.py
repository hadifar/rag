from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class IngestionReport:
    documents: int
    chunks: int
