"""Audit logging engine, execution telemetry, and operational metric aggregator.

Tracks step-by-step traces, execution latency, retry tracking,
and provides unified telemetry across all four modules.
"""

from contextlib import contextmanager
from datetime import datetime, timedelta
import json
import logging
import time
from typing import Any, Dict, Generator, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from core.models import (
    ApprovalRequest,
    CustomerProject,
    ExecutionAuditLog,
    InvoiceRecord,
    LeadRecord,
    PaymentEvent,
    SupportTicket,
)

logger = logging.getLogger("orbit.audit")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


@contextmanager
def timed_execution(
    workflow_name: str,
    module: str,
    trigger_type: str = "API",
    related_record_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Measure pipeline execution latency and persist structured telemetry log."""
    start_time = time.perf_counter()
    context: Dict[str, Any] = {
        "workflow_name": workflow_name,
        "module": module,
        "trigger_type": trigger_type,
        "related_record_id": related_record_id,
        "status": "SUCCESS",
        "error": None,
        "metadata": {},
    }

    try:
        yield context
    except Exception as exc:
        context["status"] = "FAILED"
        context["error"] = str(exc)
        logger.error(f"Workflow '{workflow_name}' failed: {exc}", exc_info=True)
        raise
    finally:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        context["duration_ms"] = duration_ms

        logger.info(
            f"Execution Telemetry: [{module}] {workflow_name} - {context['status']} "
            f"in {duration_ms}ms (Trigger: {trigger_type})"
        )

        if db is not None:
            try:
                log_entry = ExecutionAuditLog(
                    workflow_name=workflow_name,
                    module=module,
                    trigger_type=trigger_type,
                    status=context["status"],
                    duration_ms=duration_ms,
                    related_record_id=context.get("related_record_id"),
                    details=json.dumps(context.get("metadata", {})),
                    error_message=context.get("error"),
                )
                db.add(log_entry)
                db.commit()
            except Exception as log_err:
                logger.error(f"Failed to persist audit log to database: {log_err}")
                db.rollback()


def record_audit_event(
    db: Session,
    workflow_name: str,
    module: str,
    status: str,
    duration_ms: float,
    details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    related_record_id: Optional[str] = None,
    trigger_type: str = "API",
) -> ExecutionAuditLog:
    """Manually insert an execution telemetry event into the database."""
    log_entry = ExecutionAuditLog(
        workflow_name=workflow_name,
        module=module,
        trigger_type=trigger_type,
        status=status,
        duration_ms=duration_ms,
        related_record_id=related_record_id,
        details=json.dumps(details or {}),
        error_message=error_message,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def get_operations_summary(db: Session) -> Dict[str, Any]:
    """Aggregate actual stored operational metrics across all modules."""
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)

    # Lead metrics
    total_leads = db.query(func.count(LeadRecord.id)).scalar() or 0
    qualified_leads = (
        db.query(func.count(LeadRecord.id)).filter(LeadRecord.qualification_status == "QUALIFIED").scalar() or 0
    )
    urgent_leads = db.query(func.count(LeadRecord.id)).filter(LeadRecord.priority == "URGENT").scalar() or 0

    # Support metrics
    total_tickets = db.query(func.count(SupportTicket.id)).scalar() or 0
    urgent_tickets = (
        db.query(func.count(SupportTicket.id))
        .filter(SupportTicket.urgency.in_(["CRITICAL", "HIGH"]))
        .scalar()
        or 0
    )
    escalated_tickets = (
        db.query(func.count(SupportTicket.id)).filter(SupportTicket.requires_escalation == True).scalar() or 0
    )

    # Invoice metrics
    total_invoices = db.query(func.count(InvoiceRecord.id)).scalar() or 0
    pending_invoices = (
        db.query(func.count(InvoiceRecord.id)).filter(InvoiceRecord.approval_status == "PENDING_REVIEW").scalar() or 0
    )
    exported_invoices = (
        db.query(func.count(InvoiceRecord.id))
        .filter(InvoiceRecord.export_status == "EXPORTED_GOOGLE_SHEETS")
        .scalar()
        or 0
    )
    discrepancy_invoices = (
        db.query(func.count(InvoiceRecord.id)).filter(InvoiceRecord.has_arithmetic_discrepancy == True).scalar() or 0
    )

    # Project & Payment metrics
    active_projects = (
        db.query(func.count(CustomerProject.id)).filter(CustomerProject.workflow_state != "FAILED").scalar() or 0
    )
    verified_payments_total = (
        db.query(func.sum(PaymentEvent.amount)).filter(PaymentEvent.signature_verified == True).scalar() or 0.0
    )

    # System Health
    failed_runs = (
        db.query(func.count(ExecutionAuditLog.id))
        .filter(ExecutionAuditLog.status == "FAILED", ExecutionAuditLog.created_at >= one_week_ago)
        .scalar()
        or 0
    )
    pending_approvals = (
        db.query(func.count(ApprovalRequest.id)).filter(ApprovalRequest.status == "PENDING").scalar() or 0
    )

    # Avg lead processing latency
    avg_latency = (
        db.query(func.avg(LeadRecord.processing_time_ms)).filter(LeadRecord.processing_time_ms > 0).scalar() or 0.0
    )

    return {
        "timestamp": now.isoformat(),
        "leads": {
            "total": total_leads,
            "qualified": qualified_leads,
            "urgent": urgent_leads,
            "avg_latency_ms": round(float(avg_latency), 2),
        },
        "support": {
            "total": total_tickets,
            "urgent_incidents": urgent_tickets,
            "escalated": escalated_tickets,
            "draft_only_enforced": True,
        },
        "invoices": {
            "total": total_invoices,
            "pending_review": pending_invoices,
            "exported_sheets": exported_invoices,
            "discrepancies_detected": discrepancy_invoices,
        },
        "orchestration": {
            "active_projects": active_projects,
            "verified_payments_amount": round(float(verified_payments_total), 2),
        },
        "system": {
            "failed_automation_runs": failed_runs,
            "pending_approvals": pending_approvals,
            "status": "OPERATIONAL" if failed_runs == 0 else "ATTENTION_REQUIRED",
        },
    }
