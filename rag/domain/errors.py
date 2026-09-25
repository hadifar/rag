class RagError(Exception):
    """Base for every exception the domain/services layer raises deliberately."""


class DocumentNotFoundError(RagError):
    """Raised when a document lookup by source_id finds nothing."""

    def __init__(self, source_id: str):
        super().__init__(f"No document found for source_id={source_id!r}")
        self.source_id = source_id


class VectorStoreConfigurationError(RagError):
    """Raised when the configured vector store backend can't be used as configured."""
