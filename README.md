# RAG (Retrieval Augmented Generation)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![pre-commit](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/hadifar/rag/actions/workflows/pre-commit.yml)

A ready to use RAG implementation! built on FastAPI + LangGraph + Postgress(pgvector), with a React frontend.


![Chat UI](docs/images/screenshot.png)

## Quick start
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
# fill in .env (see .example.env), then:
docker compose up --build   # applies database migrations before the backend starts
# once it's up, create a login (no public signup — see docs/setup.md):
docker compose exec backend rag create-user you@example.com --admin
```
Then sign in at http://localhost:3000 and load the knowledge base: upload `data/data.zip` under
**Settings → Knowledge base**.
Full setup and other ways to run it, are in [docs/setup.md](docs/setup.md).

## Docs
See [docs/README.md](docs/README.md) & [docs/](docs/).

## Contribution
See [CONTRIBUTING.md](CONTRIBUTING.md).

## License
[LICENSE](LICENSE)
