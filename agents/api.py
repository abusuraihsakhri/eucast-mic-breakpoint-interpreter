"""
FastAPI REST API Server for Eucast Mic Breakpoint Interpreter.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from eucast_interpreter import interpret_mic
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Eucast Mic Breakpoint Interpreter API",
    description="EUCAST MIC evaluation with explicit breakpoints; auxiliary nonclinical audit prototype",
    version="3.0.1",
)


class ChatRequest(BaseModel):
    query: str


class MICRequest(BaseModel):
    organism: str
    antimicrobial: str
    mic: str
    s_le: str
    r_gt: str
    breakpoint_version: str
    atu_low: str | None = None
    atu_high: str | None = None


@app.post("/api/interpret")
def api_interpret(payload: MICRequest):
    try:
        return interpret_mic(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "eucast-mic-breakpoint-interpreter", "domain": "MIC interpretation and auxiliary audit", "version": "3.0.1"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
