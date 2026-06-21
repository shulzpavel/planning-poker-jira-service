import os
from enum import Enum

from jira_fields import (
    JIRA_BACK_ASSIGNEE_FIELD,
    JIRA_FRONT_ASSIGNEE_FIELD,
    JIRA_PLAN_CHANGE_REASON_FIELD,
    JIRA_PLAN_STATUS_FIELD,
    JIRA_QA_ASSIGNEE_FIELD,
    JIRA_SIGNIFICANCE_FIELD,
    JIRA_SP_BACK_FIELD,
    JIRA_SP_DEV_FIELD,
    JIRA_SP_FRONT_FIELD,
    JIRA_SP_QA_FIELD,
    JIRA_SP_TEST_FIELD,
    JIRA_START_DATE_FIELD,
    STORY_POINTS_FIELD,
)


class UserRole(Enum):
    PARTICIPANT = "participant"
    LEAD = "lead"
    ADMIN = "admin"


# Microservices configuration (REQUIRED)
JIRA_SERVICE_URL = os.getenv("JIRA_SERVICE_URL", "http://localhost:8001")
VOTING_SERVICE_URL = os.getenv("VOTING_SERVICE_URL", "http://localhost:8002")

# Postgres metrics storage
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")

# Redis configuration (for Voting Service)
REDIS_URL = os.getenv("REDIS_URL", "")

# Jira Cloud (jira-service only — field IDs in jira_fields.py)
JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "your-email@domain.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "YOUR_JIRA_API_TOKEN_HERE")

JIRA_DEV_STATUS_KEYWORDS = os.getenv(
    "JIRA_DEV_STATUS_KEYWORDS",
    "dev,development,in progress,разработ,в работе,к выполнению,ready for dev",
).strip()

# Web UI base URL (e.g. https://poker.example.com); leave empty to disable web links
WEB_UI_URL = os.getenv("WEB_UI_URL", "")

# GitLab API (scope role attribution — jira-service only)
GITLAB_BASE_URL = os.getenv("GITLAB_BASE_URL", os.getenv("GITLAB_URL", "")).strip().rstrip("/")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", os.getenv("GITLAB_PRIVATE_TOKEN", "")).strip()
GITLAB_GROUP_ID = os.getenv("GITLAB_GROUP_ID", "").strip()
