"""Workflow Studio engine, retry supervisor, and centralized approval center.

Manages state transitions, execution monitoring, retry eligibility, and
human-in-the-loop gates across all four business modules.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from core.models import ApprovalRequest, CustomerProject, ExecutionAuditLog, InvoiceRecord, SupportTicket

logger = logging.getLogger("orbit.services.workflows")

REGISTERED_WORKFLOWS: List[Dict[str, Any]] = [
    {
        "id": "wf-lead-routing",
        "name": "Lead Intelligence & Revenue Routing",
        "module": "leads",
        "trigger_type": "WEBHOOK / FORM",
        "retry_eligible": True,
        "dependencies": ["OpenAI", "Airtable", "Slack"],
        "description": "Capture, validate, score leads, synthesize talking points, and route to CRM and sales channels.",
        "steps": [
            "Capture Submission",
            "Deduplicate (SHA-256)",
            "Validate & Normalize",
            "Score & Synthesize",
            "Airtable Sync",
            "Slack Sales Alert",
            "Audit & SLA Measurement",
        ],
    },
    {
        "id": "wf-support-triage",
        "name": "Customer Support & Email Intelligence",
        "module": "support",
        "trigger_type": "EMAIL / WEBHOOK",
        "retry_eligible": True,
        "dependencies": ["Email Provider", "Local Knowledge RAG", "OpenAI", "Slack"],
        "description": "Ingest inbound customer messages, assess urgency/intent, retrieve evidence, and stage draft-only responses.",
        "steps": [
            "Receive Email",
            "Deduplicate Message ID",
            "Knowledge RAG Search",
            "Intent & Urgency Classification",
            "Mandatory Escalation Check",
            "Safe Draft Creation",
            "Human Approval Gate",
        ],
    },
    {
        "id": "wf-invoice-reconcile",
        "name": "Invoice Intelligence & Financial Operations",
        "module": "invoices",
        "trigger_type": "FILE UPLOAD",
        "retry_eligible": True,
        "dependencies": ["pypdf Parser", "Google Sheets"],
        "description": "Extract structured data from PDF invoices, verify arithmetic accuracy, detect duplicates, and export to Google Sheets.",
        "steps": [
            "PDF Upload & Header Check",
            "Duplicate File Hash Check",
            "Text & Line Item Extraction",
            "Arithmetic Reconciliation",
            "Human Approval Gate",
            "Google Sheets Export",
            "Audit Log Record",
        ],
    },
    {
        "id": "wf-client-orchestration",
        "name": "Enterprise Multi-Agent Orchestration",
        "module": "orchestration",
        "trigger_type": "API / STRIPE WEBHOOK",
        "retry_eligible": True,
        "dependencies": ["Airtable", "Slack", "Stripe HMAC", "Contract Engine"],
        "description": "Coordinate customer intake, template-governed contracts, Stripe cryptographic payment verification, and Slack workspaces.",
        "steps": [
            "Intake & Project ID Allocation",
            "Airtable Record Sync",
            "MSA Contract Drafting",
            "Executive Countersignature Gate",
            "Stripe HMAC Webhook Verification",
            "Replay Prevention Check",
            "Slack Channel Provisioning",
        ],
    },
    {
        "id": "wf-executive-digest",
        "name": "Weekly Executive Operations Digest",
        "module": "orchestration",
        "trigger_type": "CRON / MANUAL",
        "retry_eligible": False,
        "dependencies": ["Audit Telemetry", "OpenAI"],
        "description": "Aggregate actual stored operational metrics and synthesize an evidence-grounded executive briefing.",
        "steps": [
            "Query Database Metrics",
            "Audit Error Ledger Analysis",
            "Evidence Grounding Validation",
            "Executive Narrative Generation",
            "Digest Markdown Export",
        ],
    },
]


class WorkflowEngine:
    """Manages workflow telemetry, status lookups, and approval fulfillment."""

    @staticmethod
    def get_workflows_telemetry(db: Session) -> List[Dict[str, Any]]:
        """Combine static workflow definitions with live execution metrics from database."""
        result = []
        for wf in REGISTERED_WORKFLOWS:
            # Query last execution log for this workflow
            last_run = (
                db.query(ExecutionAuditLog)
                .filter(ExecutionAuditLog.module == wf["module"])
                .order_by(ExecutionAuditLog.created_at.desc())
                .first()
            )

            status = "HEALTHY"
            last_executed_at = None
            last_duration_ms = 0.0
            last_error = None
            related_record_id = None

            if last_run:
                last_executed_at = last_run.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                last_duration_ms = last_run.duration_ms
                last_error = last_run.error_message
                related_record_id = last_run.related_record_id
                if last_run.status == "FAILED":
                    status = "ERROR"

            result.append(
                {
                    "id": wf["id"],
                    "name": wf["name"],
                    "module": wf["module"],
                    "trigger_type": wf["trigger_type"],
                    "status": status,
                    "last_execution": last_executed_at or "Awaiting First Trigger",
                    "duration_ms": last_duration_ms,
                    "error_summary": last_error,
                    "retry_eligible": wf["retry_eligible"],
                    "related_record": related_record_id,
                    "dependencies": wf["dependencies"],
                    "description": wf["description"],
                    "steps": wf["steps"],
                }
            )
        return result

    @staticmethod
    def get_pending_approvals(db: Session) -> List[ApprovalRequest]:
        """Query all pending human approval requests."""
        return db.query(ApprovalRequest).filter(ApprovalRequest.status == "PENDING").order_by(ApprovalRequest.created_at.desc()).all()

    @staticmethod
    def resolve_approval(
        approval_id: str,
        action: str,  # "APPROVED" or "REJECTED"
        resolved_by: str,
        notes: Optional[str],
        db: Session,
    ) -> Dict[str, Any]:
        """Resolve a human-in-the-loop approval gate and trigger downstream execution."""
        app_req = db.query(ApprovalRequest).filter(ApprovalRequest.id == approval_id).first()
        if not app_req:
            raise ValueError(f"Approval request '{approval_id}' not found.")

        app_req.status = action.upper()
        app_req.resolved_by = resolved_by
        app_req.resolved_at = datetime.utcnow()
        app_req.resolution_notes = notes

        downstream_effect = "None"

        # Fulfill entity-specific downstream states
        if app_req.entity_type == "INVOICE":
            invoice = db.query(InvoiceRecord).filter(InvoiceRecord.id == app_req.entity_id).first()
            if invoice:
                invoice.approval_status = action.upper()
                invoice.approved_by = resolved_by
                invoice.approved_at = datetime.utcnow()
                downstream_effect = f"Invoice {invoice.invoice_number} marked as {action.upper()}."

        elif app_req.entity_type == "CONTRACT":
            project = db.query(CustomerProject).filter(CustomerProject.id == app_req.entity_id).first()
            if project:
                if action.upper() == "APPROVED":
                    project.contract_status = "APPROVED"
                    project.contract_approved_by = resolved_by
                    project.workflow_state = "PAYMENT_PENDING"
                    downstream_effect = f"Project {project.project_code} contract APPROVED; Payment unlocked."
                else:
                    project.contract_status = "REJECTED"
                    project.workflow_state = "FAILED"
                    downstream_effect = f"Project {project.project_code} contract REJECTED."

        elif app_req.entity_type == "SUPPORT_ESCALATION":
            ticket = db.query(SupportTicket).filter(SupportTicket.id == app_req.entity_id).first()
            if ticket:
                ticket.status = "APPROVED" if action.upper() == "APPROVED" else "CLOSED"
                downstream_effect = f"Support Ticket {ticket.subject} status updated to {ticket.status}."

        db.commit()
        db.refresh(app_req)

        logger.info(f"Approval {app_req.id} ({app_req.entity_type}) resolved as {action.upper()} by {resolved_by}")
        return {
            "success": True,
            "approval_id": app_req.id,
            "status": app_req.status,
            "resolved_by": app_req.resolved_by,
            "downstream_effect": downstream_effect,
        }
