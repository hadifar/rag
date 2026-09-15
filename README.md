# RAG (Retrieval Augmented Generation)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![pre-commit](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml)

A ~~production~~ ready to use RAG implementation. Support chatbot over the AtlasFlow knowledge base ([data/](data/)), built on FastAPI + Gradio + LangGraph + Pinecone. Architecture: [docs/engineering_design.md](docs/engineering_design.md).

![Chat UI](docs/images/screenshot.png)

## Setup
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```
Then fill in `.env` (see .example.env) `OPENAI_API_KEY`, `PINECONE_API_KEY`, etc.

**You must have a folder (`~/data/`) with .md files**
## Running

### Python (uv)
```bash
uv run python -m rag serve
```

### CLI
```bash
rag ingest   # embeds data/*.md and upserts into Pinecone — run once before serving
rag serve
```

### Docker
```bash
docker compose up
```

Once running: UI at `http://localhost:8000/ui`

## Coding style
Follows PEP 20 and the [Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md).

## Contribution
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
[LICENSE](LICENSE)
