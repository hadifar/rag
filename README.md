# RAG (Retrieval Augmented Generation)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![pre-commit](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml)

A ready to use RAG implementation! built on FastAPI + LangGraph + Postgress(pgvector), with a React frontend.


![Chat UI](docs/images/screenshot.png)

## Quick start
```bash
git clone https://github.com/hadifar/rag.git && cd rag && bash scripts/setup.sh
docker compose up --build
```
Then create a login and load the knowledge base: see [docs/setup.md](docs/setup.md), which also
covers the other ways to run it.

## Docs
See [docs/README.md](docs/README.md) & [docs/](docs/)

## Contribution
See [CONTRIBUTING.md](CONTRIBUTING.md)

## License
[LICENSE](LICENSE)
