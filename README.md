# RAG (Retrieval Augmented Generation)
A ~~production~~ ready to use RAG implementation. Support chatbot over the AtlasFlow knowledge base ([data/](data/)), built on FastAPI + Gradio + LangGraph + Pinecone. Architecture: [docs/engineering_design.md](docs/engineering_design.md).

## Setup
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```
Then create & fill in `.env` via `OPENAI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`.

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

Once running: chat UI at `/ui`, API at `POST /chat/stream`, health checks at `/health/live` and `/health/ready`.

## Coding style
Follows PEP 20 and the [Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md).

## Contribution
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
[LICENSE](LICENSE)
