# planning-poker-jira-service

Stateless FastAPI microservice: Jira Cloud search, Story Points writes, scope-board enrichment, ADF comments, optional GitLab role evidence.

**Port:** 8001 (local, internal in prod) · **Caller:** `planning-poker-voting-service` only

## Role in the stack

| Owns | Does **not** |
|---|---|
| All Jira Cloud REST calls | Postgres, Redis, sessions, RBAC |
| Scope issue enrichment (changelog, milestones, contributors) | Public exposure (Caddy proxies only web + voting) |
| In-memory Jira issue cache (singleton client) | Scope board persistence |

Canonical architecture: [planning-poker-dev/docs/architecture/SERVICES.md](https://github.com/shulzpavel/planning-poker-dev/blob/main/docs/architecture/SERVICES.md)

API contracts: [contracts/JIRA-SERVICE.md](https://github.com/shulzpavel/planning-poker-dev/blob/main/docs/contracts/JIRA-SERVICE.md)

## Run locally

**Recommended** — from `planning-poker-dev`:

```bash
docker compose up -d jira-service
```

**Bare metal:**

```bash
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python -m services.jira_service.main
```

| URL | Purpose |
|---|---|
| http://localhost:8001/health/ready | Jira config + singleton client ready |
| http://localhost:8001/docs | OpenAPI |
| http://localhost:8001/metrics/ | Cache hits/misses, inflight |

## Docker

```bash
docker build -t planning-poker-jira-service .
docker run --rm planning-poker-jira-service python -c "import planning_poker_common"
```

Shared lib: **tarball URL** in `requirements.txt` — never `git+https://` in Docker ([PYTHON-LIB.md](https://github.com/shulzpavel/planning-poker-dev/blob/main/docs/architecture/PYTHON-LIB.md)).

## Key endpoints

| Path | Use case |
|---|---|
| `POST /api/v1/parse` | Session task import (JQL / keys) |
| `POST /api/v1/search/scope` | Scope board refresh (enriched issues) |
| `GET /api/v1/issue/{key}/context` | AI prompt context |
| `PUT /api/v1/issue/{key}/story-points` | Write Story Points |
| `POST /api/v1/issue/{key}/comment/adf` | Rich ADF comments (AI export) |

## Rules

- **Singleton** `JiraServiceClient` in app lifespan — per-request clients break the cache.
- No rate limiting here; quotas enforced in voting-service + Atlassian.
- `JIRA_DEMO_FALLBACK=true` only for local/dev misconfiguration.

## Tests

```bash
PYTHONPATH=. python -m pytest -q
```

Scope enrichment: `tests/test_scope_board.py`.

From `planning-poker-dev`: `make jira-test` or `make check`.

CI: pytest + `docker build` + `import planning_poker_common`. Push to `main` deploys via GitHub Actions.

## Related repos

- [planning-poker-voting-service](https://github.com/shulzpavel/planning-poker-voting-service) — sole HTTP client
- [planning-poker-python-lib](https://github.com/shulzpavel/planning-poker-python-lib) — shared pure modules
- [planning-poker-dev](https://github.com/shulzpavel/planning-poker-dev) — compose & deploy
