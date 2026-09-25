# RAG (Retrieval Augmented Generation)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![pre-commit](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml)

A ~~prod~~ ready to use RAG implementation. Support chatbot over the AtlasFlow knowledge base ([data/](data/)), built on FastAPI + LangGraph + Pinecone, with a React frontend.


![Chat UI](docs/images/screenshot.png)

## Quick start
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
# fill in .env (see .example.env), then:
docker compose up --build
```
Full setup and other ways to run it, are in [docs/setup.md](docs/setup.md).

## Docs
See [docs/README.md](docs/README.md).

## Contribution
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
[LICENSE](LICENSE)
