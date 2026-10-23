"""Project 4: Enterprise Multi-Agent Business Orchestration Service.

Coordinates:
Customer Intake -> Contract Preparation -> Stripe Payment Verification ->
Slack Collaboration Provisioning -> Weekly Executive Digest.
"""

from datetime import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from core.audit import get_operations_summary, timed_execution
from core.models import ApprovalRequest, CustomerProject, PaymentEvent
from core.schemas import CustomerOnboardRequest, ExecutiveDigestResponse
from integrations.airtable_adapter import AirtableAdapter
from integrations.openai_adapter import OpenAIAdapter
from integrations.slack_adapter import SlackAdapter
from integrations.stripe_adapter import StripeAdapter
from services.contract_templates import render_contract_template

logger = logging.getLogger("orbit.services.orchestration")


class OrchestrationService:
    """Multi-Agent client onboarding and operations orchestrator."""

    def __init__(
        self,
        airtable_adapter: Optional[AirtableAdapter] = None,
        slack_adapter: Optional[SlackAdapter] = None,
        stripe_adapter: Optional[StripeAdapter] = None,
        openai_adapter: Optional[OpenAIAdapter] = None,
    ):
        self.airtable = airtable_adapter or AirtableAdapter()
        self.slack = slack_adapter or SlackAdapter()
        self.stripe = stripe_adapter or StripeAdapter()
        self.openai = openai_adapter or OpenAIAdapter()

    def generate_next_project_code(self, db: Session) -> str:
        """Allocate a stable, unique project identifier (e.g. PRJ-2026-001)."""
        year = datetime.utcnow().year
        count = db.query(func.count(CustomerProject.id)).scalar() or 0
        return f"PRJ-{year}-{(count + 1):03d}"

    def onboard_customer(
        self,
        request: CustomerOnboardRequest,
        db: Session,
    ) -> Dict[str, Any]:
        """A & B: Customer Intake and Contract Preparation."""
        with timed_execution("customer_onboarding", module="orchestration", trigger_type="API", db=db) as ctx:
            # Duplicate check
            existing = (
                db.query(CustomerProject)
                .filter(
                    CustomerProject.customer_email == str(request.customer_email),
                    CustomerProject.company_name == request.company_name,
                )
                .first()
            )
            if existing:
                ctx["metadata"] = {"duplicate": True, "project_id": existing.id}
                ctx["related_record_id"] = existing.id
                return {
                    "project": existing,
                    "duplicate": True,
                    "message": f"Customer project already exists ({existing.project_code}).",
                }

            project_code = self.generate_next_project_code(db)
            today_str = time.strftime("%Y-%m-%d", time.gmtime())

            # Generate contract draft from authorized template
            contract_text = render_contract_template(
                {
                    "effective_date": today_str,
                    "customer_name": request.customer_name,
                    "company_name": request.company_name,
                    "service_tier": request.service_tier,
                    "contract_value": request.contract_value,
                    "approval_status": "PENDING_APPROVAL",
                    "approved_by": "Pending Legal/Executive Review",
                }
            )

            # Persist project record
            project = CustomerProject(
                project_code=project_code,
                customer_name=request.customer_name,
                customer_email=str(request.customer_email),
                company_name=request.company_name,
                service_tier=request.service_tier,
                contract_value=request.contract_value,
                contract_template_version="v3.1-standard-enterprise",
                contract_status="PENDING_APPROVAL",
                contract_content=contract_text,
                workflow_state="CONTRACT_PENDING",
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            ctx["related_record_id"] = project.id

            # Sync to Airtable
            airtable_res = self.airtable.sync_project(
                {
                    "project_code": project.project_code,
                    "customer_name": project.customer_name,
                    "company_name": project.company_name,
                    "service_tier": project.service_tier,
                    "contract_value": project.contract_value,
                    "workflow_state": project.workflow_state,
                }
            )
            project.airtable_project_id = airtable_res.get("record_id")
            db.commit()

            # Create Approval Request for Contract review
            app_req = ApprovalRequest(
                entity_type="CONTRACT",
                entity_id=project.id,
                title=f"Contract Approval: {project.company_name} ({project.project_code}) - ${project.contract_value:,.2f}",
                details=f"Template: {project.contract_template_version}\nClient: {project.customer_name}",
                status="PENDING",
                requested_by="Contract Preparation Agent",
            )
            db.add(app_req)
            db.commit()

            ctx["metadata"] = {
                "project_code": project.project_code,
                "contract_value": project.contract_value,
                "workflow_state": project.workflow_state,
            }

            return {
                "project": project,
                "duplicate": False,
                "contract_draft": contract_text,
                "airtable_sync": airtable_res,
            }

    def approve_contract(self, project_id: str, approved_by: str, db: Session) -> Dict[str, Any]:
        """Approve contract, unlocking payment step and provisioning Slack channel."""
        project = db.query(CustomerProject).filter(CustomerProject.id == project_id).first()
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        project.contract_status = "APPROVED"
        project.contract_approved_by = approved_by
        project.workflow_state = "PAYMENT_PENDING"

        # Update contract content with approved officer
        project.contract_content = render_contract_template(
            {
                "effective_date": time.strftime("%Y-%m-%d", time.gmtime()),
                "customer_name": project.customer_name,
                "company_name": project.company_name,
                "service_tier": project.service_tier,
                "contract_value": project.contract_value,
                "approval_status": "APPROVED",
                "approved_by": approved_by,
            }
        )

        # D: Provision Slack project channel
        slack_res = self.slack.provision_project_channel(project.project_code, project.customer_name)
        project.slack_channel_id = slack_res.get("channel_id")
        project.slack_channel_name = slack_res.get("channel_name")

        db.commit()
        db.refresh(project)

        logger.info(f"Contract for {project.project_code} approved by {approved_by}. Channel #{project.slack_channel_name} provisioned.")
        return {
            "success": True,
            "project_id": project.id,
            "contract_status": "APPROVED",
            "workflow_state": project.workflow_state,
            "slack_channel": slack_res,
        }

    def verify_stripe_payment(
        self,
        event_id: str,
        event_type: str,
        raw_payload_bytes: bytes,
        signature_header: str,
        project_id: Optional[str],
        amount: float,
        currency: str,
        db: Session,
    ) -> Dict[str, Any]:
        """C: Cryptographic Stripe Webhook verification and project reconciliation."""
        with timed_execution("stripe_payment_verification", module="orchestration", trigger_type="WEBHOOK", db=db) as ctx:
            # 1. Cryptographic Signature Verification
            valid, reason = self.stripe.verify_webhook_signature(raw_payload_bytes, signature_header)
            if not valid:
                logger.error(f"Stripe signature rejected: {reason}")
                raise PermissionError(f"Stripe Webhook Signature Verification Failed: {reason}")

            # 2. Replay & Duplicate Event Check in DB
            existing_event = db.query(PaymentEvent).filter(PaymentEvent.stripe_event_id == event_id).first()
            if existing_event:
                logger.info(f"Payment event '{event_id}' was already processed (Replay protection).")
                ctx["metadata"] = {"duplicate": True, "event_id": event_id}
                return {
                    "success": True,
                    "event_id": event_id,
                    "duplicate": True,
                    "message": "Payment event already verified and recorded (Idempotent).",
                }

            # 3. Process with Stripe Adapter
            stripe_res = self.stripe.process_payment_event(
                event_id=event_id,
                event_type=event_type,
                project_id=project_id,
                amount=amount,
                currency=currency,
                signature_verified=True,
            )

            # 4. Record to Database
            payment_record = PaymentEvent(
                stripe_event_id=event_id,
                event_type=event_type,
                project_id=project_id,
                amount=amount,
                currency=currency,
                signature_verified=True,
                raw_payload=raw_payload_bytes.decode("utf-8", errors="replace"),
            )
            db.add(payment_record)

            # 5. Reconcile with Customer Project if project_id provided
            target_project = None
            if project_id:
                target_project = db.query(CustomerProject).filter(
                    (CustomerProject.id == project_id) | (CustomerProject.project_code == project_id)
                ).first()

            if target_project:
                target_project.payment_status = "VERIFIED"
                target_project.stripe_payment_intent_id = event_id
                target_project.workflow_state = "ONBOARDED"
                ctx["related_record_id"] = target_project.id

            db.commit()

            ctx["metadata"] = {
                "event_id": event_id,
                "amount": amount,
                "reconciled_project": target_project.project_code if target_project else None,
            }

            return {
                "success": True,
                "event_id": event_id,
                "verified": True,
                "reconciled_project": target_project.project_code if target_project else None,
                "amount": amount,
                "currency": currency,
            }

    def generate_weekly_executive_digest(self, db: Session) -> ExecutiveDigestResponse:
        """E: Synthesize evidence-grounded executive digest from actual stored records."""
        metrics = get_operations_summary(db)
        narrative = self.openai.generate_executive_narrative(metrics)

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        return ExecutiveDigestResponse(
            period="Last 7 Days (Rolling Operational Window)",
            data_freshness=f"As of {now_str}",
            total_leads=metrics["leads"]["total"],
            qualified_leads=metrics["leads"]["qualified"],
            support_workload=metrics["support"]["total"],
            urgent_support_cases=metrics["support"]["urgent_incidents"],
            invoices_awaiting_review=metrics["invoices"]["pending_review"],
            approved_accounting_exports=metrics["invoices"]["exported_sheets"],
            verified_payments_total=metrics["orchestration"]["verified_payments_amount"],
            active_projects=metrics["orchestration"]["active_projects"],
            failed_automation_runs=metrics["system"]["failed_automation_runs"],
            pending_approvals=metrics["system"]["pending_approvals"],
            verified_metrics=metrics,
            executive_narrative=narrative,
        )

    def get_projects(self, db: Session, limit: int = 50, offset: int = 0) -> List[CustomerProject]:
        """Query projects list."""
        return db.query(CustomerProject).order_by(CustomerProject.created_at.desc()).offset(offset).limit(limit).all()

    def get_project_by_id(self, project_id: str, db: Session) -> Optional[CustomerProject]:
        """Query single project."""
        return (
            db.query(CustomerProject)
            .filter((CustomerProject.id == project_id) | (CustomerProject.project_code == project_id))
            .first()
        )
