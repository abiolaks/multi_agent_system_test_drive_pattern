"""FastAPI backend wrapping fabric_qa.workflow.ask() for the web frontend.

Wires the same real adapters as main.py (see main.py for the CLI
equivalent), but as HTTP endpoints instead of an input() loop. No live
event streaming yet (ADR 0012) - a run blocks until the Report is ready.
Identity comes from Azure Container Apps Easy Auth headers, decoded by
GET /api/auth (ADR 0011); locally, where those headers don't exist, it
returns 204.

Usage:
    uv run uvicorn fabric_qa.api:app --reload
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from functools import lru_cache

import agent_framework as af
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field

from fabric_qa.adapters.azure_search import AzureSearchKnowledgeBasePort
from fabric_qa.adapters.fabric_agent import FabricDataAgentPort
from fabric_qa.adapters.graph_email import GraphEmailPort
from fabric_qa.adapters.llm_client import build_vllm_chat_client
from fabric_qa.adapters.scheduler import APSchedulerPort
from fabric_qa.adapters.web_search import BraveWebSearchPort
from fabric_qa.models import EmailDraft, Report
from fabric_qa.workflow import ask

load_dotenv()


@dataclass
class Adapters:
    chat_client: af.SupportsChatGetResponse
    fabric: FabricDataAgentPort
    knowledge_base: AzureSearchKnowledgeBasePort
    web_search: BraveWebSearchPort
    email: GraphEmailPort
    scheduler: APSchedulerPort


@lru_cache(maxsize=1)
def get_adapters() -> Adapters:
    # built once and cached, same as main.py's one-time wiring before its
    # input() loop - overridden in tests via app.dependency_overrides so
    # tests never construct real Azure/Graph/vLLM clients
    return Adapters(
        chat_client=build_vllm_chat_client(),
        fabric=FabricDataAgentPort.from_env(),
        knowledge_base=AzureSearchKnowledgeBasePort.from_env(),
        web_search=BraveWebSearchPort.from_env(),
        email=GraphEmailPort.from_env(),
        scheduler=APSchedulerPort.from_env(),
    )


# run_id -> EmailDraft awaiting the ADR 0009 send/cancel decision.
# In-memory only, lost on restart - acceptable for the same POV reasons
# ADR 0003 accepts in-process scheduling; a real deployment needs this
# durable before it's more than a demo.
_pending_drafts: dict[str, EmailDraft] = {}

app = FastAPI(title="Fabric Data Q&A")


class RunRequest(BaseModel):
    question: str = Field(min_length=1)


class VerdictOut(BaseModel):
    parameter: str
    value: float
    health: str


class RecommendationOut(BaseModel):
    fault_signature: str
    next_step: str
    citation: str


class DiagnosisOut(BaseModel):
    summary: str
    what_data_shows: str
    what_guidance_says: str
    combined_finding: str
    recommendation: RecommendationOut
    caveats: str


class ReportOut(BaseModel):
    summary: str
    images: list[str]  # base64-encoded, per image
    verdicts: list[VerdictOut]
    diagnosis: DiagnosisOut | None


class RunResponse(BaseModel):
    run_id: str
    report: ReportOut
    email_pending: bool


class MailActionRequest(BaseModel):
    run_id: str


class MailActionResponse(BaseModel):
    sent: bool


class AuthResponse(BaseModel):
    name: str
    email: str


def _to_report_out(report: Report) -> ReportOut:
    diagnosis_out = None
    if report.diagnosis is not None:
        d = report.diagnosis
        diagnosis_out = DiagnosisOut(
            summary=d.summary,
            what_data_shows=d.what_data_shows,
            what_guidance_says=d.what_guidance_says,
            combined_finding=d.combined_finding,
            recommendation=RecommendationOut(
                fault_signature=d.recommendation.fault_signature,
                next_step=d.recommendation.next_step,
                citation=d.recommendation.citation,
            ),
            caveats=d.caveats,
        )
    return ReportOut(
        summary=report.summary,
        images=[base64.b64encode(image).decode("ascii") for image in report.images],
        verdicts=[VerdictOut(parameter=v.parameter, value=v.value, health=v.health) for v in report.verdicts],
        diagnosis=diagnosis_out,
    )


@app.post("/api/run", response_model=RunResponse)
async def run(body: RunRequest, adapters: Adapters = Depends(get_adapters)) -> RunResponse:
    run_id = str(uuid.uuid4())

    # captures the EmailDraft ask() produces internally - ask() only
    # returns the Report, so this is how the pending-drafts store gets a
    # handle on the draft for the /api/mail/confirm|cancel gate below
    def email_draft(report: Report) -> EmailDraft:
        draft = adapters.email.draft(report)
        _pending_drafts[run_id] = draft
        return draft

    try:
        report = await ask(
            body.question,
            chat_client=adapters.chat_client,
            fetch=adapters.fabric.fetch,
            fetch_readings=adapters.fabric.fetch_readings,
            fetch_maintenance_history=adapters.fabric.fetch_maintenance_history,
            retrieve_guidance=adapters.knowledge_base.retrieve,
            web_search=adapters.web_search.search,
            email_draft=email_draft,
            schedule=adapters.scheduler.schedule,
        )
    except Exception as exc:  # surfaced to the caller, mirrors main.py's try/except
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RunResponse(run_id=run_id, report=_to_report_out(report), email_pending=run_id in _pending_drafts)


@app.post("/api/mail/confirm", response_model=MailActionResponse)
async def mail_confirm(body: MailActionRequest, adapters: Adapters = Depends(get_adapters)) -> MailActionResponse:
    draft = _pending_drafts.get(body.run_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"No pending email draft for run_id={body.run_id!r}")

    # ADR 0009: drafting is automatic, sending never is - this is the
    # only path that calls email.send()
    adapters.email.send(draft)
    del _pending_drafts[body.run_id]
    return MailActionResponse(sent=True)


@app.post("/api/mail/cancel", response_model=MailActionResponse)
async def mail_cancel(body: MailActionRequest) -> MailActionResponse:
    if _pending_drafts.pop(body.run_id, None) is None:
        raise HTTPException(status_code=404, detail=f"No pending email draft for run_id={body.run_id!r}")
    return MailActionResponse(sent=False)


@app.get("/api/auth", response_model=None)
async def auth(request: Request) -> AuthResponse | Response:
    """ADR 0011: identity comes from ACA Easy Auth headers, not app code.

    Mirrors maf_multi_agent_new/frontend's app/api/auth/route.ts exactly,
    including the 204-when-absent local-dev behavior.
    """
    principal_header = request.headers.get("x-ms-client-principal")
    principal_name = request.headers.get("x-ms-client-principal-name")

    if not principal_header:
        return Response(status_code=204)

    try:
        decoded = base64.b64decode(principal_header).decode("utf-8")
        claims = json.loads(decoded).get("claims", [])
    except (ValueError, json.JSONDecodeError):
        return AuthResponse(name=principal_name or "User", email=principal_name or "")

    def claim(*types: str) -> str | None:
        for typ in types:
            for c in claims:
                if c.get("typ") == typ:
                    return c.get("val")
        return None

    name = claim("name", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name") or ""
    email = (
        claim("preferred_username", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        or principal_name
        or ""
    )
    return AuthResponse(name=name or email, email=email)
