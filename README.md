# Planning Poker — Jira Service

Stateless FastAPI microservice for Jira search, Story Points writes, scope-board enrichment, and ADF comments.

## Documentation

Central docs in [planning-poker-dev/docs](https://github.com/shulzpavel/planning-poker-dev/tree/main/docs):

- [architecture/SERVICES.md](https://github.com/shulzpavel/planning-poker-dev/blob/main/docs/architecture/SERVICES.md) — what this service owns
- [contracts/JIRA-SERVICE.md](https://github.com/shulzpavel/planning-poker-dev/blob/main/docs/contracts/JIRA-SERVICE.md) — API contracts

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python -m services.jira_service.main
```

Health: http://localhost:8001/health  
OpenAPI: http://localhost:8001/docs

## Endpoints

| Path | Use case |
|---|---|
| `POST /api/v1/parse` | Session task import (JQL / keys) |
| `POST /api/v1/search/scope` | Scope board refresh (enriched issues) |
| `GET /api/v1/issue/{key}/context` | AI prompt context |
| `POST /api/v1/issue/{key}/comment/adf` | Rich ADF comments (AI export) |
| `PUT /api/v1/issue/{key}/story-points` | Write Story Points |

Optional GitLab integration enriches role contributors for scope workload charts.

## Tests

```bash
PYTHONPATH=. python -m pytest -q
```

Scope enrichment tests: `tests/test_scope_board.py`.
