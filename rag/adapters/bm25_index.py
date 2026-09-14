import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"\w+")


class BM25Clinet:
    def __init__(self, documents: list[Document]):
        self._documents = documents
        corpus = [_TOKEN_RE.findall(doc.page_content.lower()) for doc in documents]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_TOKEN_RE.findall(query.lower()))
        ranked = sorted(
            zip(self._documents, scores, strict=True),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return [(doc, score) for doc, score in ranked[:k] if score > 0]
