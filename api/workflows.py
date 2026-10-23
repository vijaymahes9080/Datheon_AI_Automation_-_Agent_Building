"""REST API endpoints for Workflow Studio, Agent Registry, and Approval Center."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.audit import get_operations_summary
from core.database import get_db
from core.models import ExecutionAuditLog
from services.agent_registry import get_agent_registry
from services.workflow_engine import WorkflowEngine

router = APIRouter(prefix="/api/workflows", tags=["Workflow Studio"])


class ApprovalResolveRequest(BaseModel):
    action: str  # "APPROVED" or "REJECTED"
    resolved_by: str = "Lead System Administrator"
    notes: Optional[str] = None


@router.get("", response_model=List[dict])
def list_workflows(db: Session = Depends(get_db)):
    """Retrieve all monitored workflows with real-time execution status and duration."""
    return WorkflowEngine.get_workflows_telemetry(db)


@router.get("/summary", response_model=dict)
def get_operations_kpi_summary(db: Session = Depends(get_db)):
    """Operations summary aggregating data across all four modules."""
    return get_operations_summary(db)


@router.get("/approvals", response_model=List[dict])
def list_pending_approvals(db: Session = Depends(get_db)):
    """Query pending human approval gates."""
    approvals = WorkflowEngine.get_pending_approvals(db)
    return [
        {
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "title": a.title,
            "details": a.details,
            "status": a.status,
            "requested_by": a.requested_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/resolve", response_model=dict)
def resolve_approval_gate(
    approval_id: str,
    payload: ApprovalResolveRequest,
    db: Session = Depends(get_db),
):
    """Resolve human approval gate and trigger downstream automation."""
    try:
        return WorkflowEngine.resolve_approval(
            approval_id=approval_id,
            action=payload.action,
            resolved_by=payload.resolved_by,
            notes=payload.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agents", response_model=List[dict])
def list_agents():
    """Retrieve full workforce Agent Registry (10 personas)."""
    return get_agent_registry()


@router.get("/history", response_model=List[dict])
def list_execution_history(
    module: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve granular execution audit logs and latency traces."""
    query = db.query(ExecutionAuditLog)
    if module:
        query = query.filter(ExecutionAuditLog.module == module.lower())
    if status:
        query = query.filter(ExecutionAuditLog.status == status.upper())

    logs = query.order_by(ExecutionAuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "workflow_name": l.workflow_name,
            "module": l.module,
            "trigger_type": l.trigger_type,
            "status": l.status,
            "duration_ms": l.duration_ms,
            "related_record_id": l.related_record_id,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
