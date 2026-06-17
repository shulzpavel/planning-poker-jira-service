# Planning Poker — Jira Service

Stateless FastAPI microservice for Jira search, Story Points writes, and scope-board enrichment.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python -m services.jira_service.main
```

Health: `http://localhost:8001/health`
