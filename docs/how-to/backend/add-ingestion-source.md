# Add an ingestion source

## Description

Load documents from a new source type. Use for PDF, Confluence or another non-markdown source.

## Steps

1. Add a `load_<source>` function to `rag/services/ingestion_service/loaders.py`.
2. Return `list[RawDocument]`. Use a stable `source_id` per document.
3. If `rag ingest` must read the source, route it in `load_path`.
4. If the source needs a client, add an adapter. See [Add an adapter](add-adapter.md).
5. Add tests to `tests/unit/test_ingestion.py`.
6. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not change `IngestionService.ingest`. `IngestionService.ingest` takes documents, not a loader.
* A new chunking strategy is a new `ChunkerPort` class. Do not add a parameter to `WholeDocumentChunker`.
