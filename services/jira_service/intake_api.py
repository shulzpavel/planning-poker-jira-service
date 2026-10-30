"""Internal, completeness-checked intake source contract."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adapters.intake_history import fetch_intake_source
from services.jira_service.api import get_jira_client
from services.jira_service.client import JiraServiceClient

router = APIRouter()

class IntakeSourceRequest(BaseModel):
    jql: str = Field(min_length=1, max_length=4000)
    source_field: str = Field(default="", pattern=r"^(customfield_\d+)?$")
    max_issues: int = Field(default=2000, ge=1, le=5000)

@router.post("/intake/source")
async def intake_source(body: IntakeSourceRequest, client: JiraServiceClient = Depends(get_jira_client)) -> dict:
    try:
        http = client._client
        return await fetch_intake_source(http._make_request, jql=body.jql, source_field=body.source_field,
                                         max_issues=body.max_issues, base_url=http.base_url)
    except (RuntimeError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Complete Jira history unavailable") from exc
