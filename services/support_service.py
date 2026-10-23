"""Project 2: Customer Support & Email Intelligence Service.

Implements the pipeline:
Receive -> Classify -> Assess -> Retrieve -> Draft -> Review -> Label -> Audit
Enforces strict draft-only default, mandatory escalation gates, and prompt injection defense.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from core.audit import timed_execution
from core.models import ApprovalRequest, SupportTicket
from core.schemas import SupportEmailIngestRequest, SupportTriageResult
from integrations.email_adapter import EmailAdapter
from integrations.openai_adapter import OpenAIAdapter
from integrations.slack_adapter import SlackAdapter
from services.knowledge_service import KnowledgeService

logger = logging.getLogger("orbit.services.support")


class SupportService:
    """Customer Support triage and grounded draft generation engine."""

    def __init__(
        self,
        openai_adapter: Optional[OpenAIAdapter] = None,
        email_adapter: Optional[EmailAdapter] = None,
        slack_adapter: Optional[SlackAdapter] = None,
        knowledge_service: Optional[KnowledgeService] = None,
    ):
        self.openai = openai_adapter or OpenAIAdapter()
        self.email = email_adapter or EmailAdapter()
        self.slack = slack_adapter or SlackAdapter()
        self.knowledge = knowledge_service or KnowledgeService()

    def process_email(
        self,
        request: SupportEmailIngestRequest,
        db: Session,
    ) -> Dict[str, Any]:
        """Triage inbound customer message, retrieve evidence, and prepare safe response draft."""
        message_id = request.message_id or f"msg-{uuid.uuid4().hex[:12]}"

        with timed_execution("support_email_triage", module="support", trigger_type="EMAIL", db=db) as ctx:
            # 1. Deduplication: Check if message_id was already processed
            existing_ticket = db.query(SupportTicket).filter(SupportTicket.message_id == message_id).first()
            if existing_ticket:
                logger.info(f"Duplicate email message ID '{message_id}' detected (Idempotent).")
                ctx["metadata"] = {"duplicate": True, "ticket_id": existing_ticket.id}
                ctx["related_record_id"] = existing_ticket.id
                return {
                    "ticket": existing_ticket,
                    "duplicate": True,
                    "message": "Duplicate email ignored: message already ingested and triaged.",
                }

            # 2. Knowledge Retrieval (RAG)
            search_query = f"{request.subject} {request.body}"
            grounded_snippets = self.knowledge.search_knowledge(search_query, top_k=2)

            # 3. AI Triage, Classification & Escalation Assessment
            email_payload = {
                "sender_name": request.sender_name,
                "sender_email": str(request.sender_email),
                "subject": request.subject,
                "body": request.body,
            }
            triage_res: SupportTriageResult = self.openai.triage_support_ticket(email_payload, grounded_snippets)

            # 4. Save draft in email provider (Draft-Only Safety Enforced)
            draft_res = self.email.save_draft(
                recipient=str(request.sender_email),
                subject=f"Re: {request.subject}",
                body=triage_res.draft_response,
                thread_id=message_id,
            )

            # 5. Persist to Database
            initial_status = "ESCALATED" if triage_res.requires_escalation else "DRAFT_READY"
            ticket = SupportTicket(
                message_id=message_id,
                sender_name=request.sender_name,
                sender_email=str(request.sender_email),
                subject=request.subject,
                raw_body=request.body,
                clean_body=request.body,
                intent=triage_res.intent,
                urgency=triage_res.urgency,
                sentiment=triage_res.sentiment,
                requires_escalation=triage_res.requires_escalation,
                escalation_reason=triage_res.escalation_reason,
                retrieved_knowledge=json.dumps(grounded_snippets),
                draft_response=triage_res.draft_response,
                status=initial_status,
                is_draft_only=True,
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)

            ctx["related_record_id"] = ticket.id

            # 6. If Escalation required, create human approval request and post to Slack
            if triage_res.requires_escalation:
                approval_req = ApprovalRequest(
                    entity_type="SUPPORT_ESCALATION",
                    entity_id=ticket.id,
                    title=f"Support Escalation: {ticket.subject} ({ticket.urgency})",
                    details=f"Sender: {ticket.sender_email}\nReason: {ticket.escalation_reason}",
                    status="PENDING",
                    requested_by="Support Triage Agent",
                )
                db.add(approval_req)
                db.commit()

                self.slack.post_support_escalation(
                    {
                        "subject": ticket.subject,
                        "sender_name": ticket.sender_name,
                        "sender_email": ticket.sender_email,
                        "urgency": ticket.urgency,
                        "intent": ticket.intent,
                        "escalation_reason": ticket.escalation_reason,
                        "clean_body": ticket.clean_body,
                    }
                )

            ctx["metadata"] = {
                "intent": ticket.intent,
                "urgency": ticket.urgency,
                "sentiment": ticket.sentiment,
                "escalated": ticket.requires_escalation,
                "draft_id": draft_res.get("draft_id"),
            }

            return {
                "ticket": ticket,
                "duplicate": False,
                "triage": triage_res,
                "draft": draft_res,
                "draft_only_enforced": True,
            }

    def get_tickets(
        self,
        db: Session,
        intent: Optional[str] = None,
        urgency: Optional[str] = None,
        status: Optional[str] = None,
        requires_escalation: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SupportTicket]:
        """Query support inbox with filtering and pagination."""
        query = db.query(SupportTicket)

        if intent:
            query = query.filter(SupportTicket.intent == intent.upper())
        if urgency:
            query = query.filter(SupportTicket.urgency == urgency.upper())
        if status:
            query = query.filter(SupportTicket.status == status.upper())
        if requires_escalation is not None:
            query = query.filter(SupportTicket.requires_escalation == requires_escalation)

        return query.order_by(SupportTicket.created_at.desc()).offset(offset).limit(limit).all()

    def get_ticket_by_id(self, ticket_id: str, db: Session) -> Optional[SupportTicket]:
        """Retrieve ticket by ID."""
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    def update_draft(self, ticket_id: str, new_draft: str, db: Session) -> SupportTicket:
        """Edit and update draft response before approval."""
        ticket = self.get_ticket_by_id(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")
        ticket.draft_response = new_draft
        db.commit()
        db.refresh(ticket)
        return ticket

    def approve_ticket_draft(self, ticket_id: str, approved_by: str, db: Session) -> Dict[str, Any]:
        """Approve support ticket draft, fulfilling human gate."""
        ticket = self.get_ticket_by_id(ticket_id, db)
        if not ticket:
            raise ValueError(f"Ticket '{ticket_id}' not found.")

        ticket.status = "APPROVED"
        db.commit()
        db.refresh(ticket)

        logger.info(f"Ticket {ticket.id} approved by {approved_by}. Ready in provider drafts.")
        return {
            "success": True,
            "ticket_id": ticket.id,
            "status": "APPROVED",
            "approved_by": approved_by,
            "note": "Draft verified and approved. Send action remains restricted to email provider.",
        }
