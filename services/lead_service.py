"""Project 1: Lead Intelligence & Revenue Routing Service.

Implements the end-to-end pipeline:
Capture -> Validate -> Normalize -> Qualify -> Persist -> Route -> Notify -> Audit
Guarantees duplicate delivery prevention, SLA tracking (<10s), and recoverable external sync.
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from core.audit import timed_execution
from core.models import LeadRecord
from core.schemas import LeadQualificationResult, LeadSubmissionRequest
from integrations.airtable_adapter import AirtableAdapter
from integrations.openai_adapter import OpenAIAdapter
from integrations.slack_adapter import SlackAdapter

logger = logging.getLogger("orbit.services.leads")


class LeadService:
    """Lead Intelligence and Revenue Routing orchestration engine."""

    def __init__(
        self,
        openai_adapter: Optional[OpenAIAdapter] = None,
        airtable_adapter: Optional[AirtableAdapter] = None,
        slack_adapter: Optional[SlackAdapter] = None,
    ):
        self.openai = openai_adapter or OpenAIAdapter()
        self.airtable = airtable_adapter or AirtableAdapter()
        self.slack = slack_adapter or SlackAdapter()

    @staticmethod
    def compute_idempotency_key(payload: LeadSubmissionRequest) -> str:
        """Compute stable idempotency key to prevent duplicate webhook/form submissions."""
        raw_key = f"{payload.contact_email.strip().lower()}:{payload.company_name.strip().lower()}:{payload.budget}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def process_lead(
        self,
        request: LeadSubmissionRequest,
        db: Session,
        source: str = "web_form",
    ) -> Dict[str, Any]:
        """Execute the full 8-stage Lead Intelligence pipeline."""
        start_time = time.perf_counter()
        idempotency_key = self.compute_idempotency_key(request)

        with timed_execution("lead_intelligence_routing", module="leads", trigger_type=source.upper(), db=db) as ctx:
            # Stage 1 & 2: Deduplication & Idempotency check
            existing_lead = db.query(LeadRecord).filter(LeadRecord.idempotency_key == idempotency_key).first()
            if existing_lead:
                logger.info(f"Duplicate lead submission detected for {request.contact_email} (Idempotent).")
                ctx["metadata"] = {"duplicate": True, "lead_id": existing_lead.id}
                ctx["related_record_id"] = existing_lead.id
                return {
                    "lead": existing_lead,
                    "duplicate": True,
                    "message": "Duplicate lead submission detected: existing record preserved without re-processing.",
                }

            # Stage 3: Normalization
            normalized_data = {
                "contact_name": request.contact_name.strip().title(),
                "contact_email": request.contact_email.strip().lower(),
                "company_name": request.company_name.strip(),
                "company_size": request.company_size.strip(),
                "budget": float(request.budget),
                "timeline": request.timeline.strip() if request.timeline else "1-3 months",
                "needs": request.needs.strip(),
                "consent_given": request.consent_given,
            }

            # Stage 4: AI & Heuristic Qualification
            qualification: LeadQualificationResult = self.openai.qualify_lead(normalized_data)

            # Stage 5: Persistence to SQLite
            lead_record = LeadRecord(
                idempotency_key=idempotency_key,
                submission_source=source,
                contact_name=normalized_data["contact_name"],
                contact_email=normalized_data["contact_email"],
                company_name=normalized_data["company_name"],
                company_size=normalized_data["company_size"],
                budget=normalized_data["budget"],
                timeline=normalized_data["timeline"],
                needs=normalized_data["needs"],
                consent_given=normalized_data["consent_given"],
                score=qualification.score,
                priority=qualification.priority,
                qualification_status=qualification.qualification_status,
                rationale=qualification.rationale,
                confidence=qualification.confidence,
                missing_information=json.dumps(qualification.missing_information),
                sales_talking_points=json.dumps(qualification.sales_talking_points),
                routing_status="PENDING",
            )
            db.add(lead_record)
            db.commit()
            db.refresh(lead_record)

            ctx["related_record_id"] = lead_record.id

            # Stage 6 & 7: Routing & Notification (Airtable & Slack)
            airtable_res = self._route_to_airtable(lead_record)
            slack_res = self._notify_slack(lead_record)

            # Update routing audit status
            lead_record.airtable_record_id = airtable_res.get("record_id")
            lead_record.slack_ts = slack_res.get("ts")

            if airtable_res.get("success") and slack_res.get("success"):
                lead_record.routing_status = "ROUTED_ALL"
            elif airtable_res.get("success") or slack_res.get("success"):
                lead_record.routing_status = "PARTIAL_SYNC"
            else:
                lead_record.routing_status = "SYNC_FAILED"

            # Stage 8: Latency Measurement (< 10 seconds SLA target)
            total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            lead_record.processing_time_ms = total_duration_ms
            db.commit()
            db.refresh(lead_record)

            ctx["metadata"] = {
                "score": lead_record.score,
                "priority": lead_record.priority,
                "routing_status": lead_record.routing_status,
                "processing_time_ms": total_duration_ms,
            }

            return {
                "lead": lead_record,
                "duplicate": False,
                "qualification": qualification,
                "airtable_sync": airtable_res,
                "slack_notification": slack_res,
                "processing_time_ms": total_duration_ms,
            }

    def _route_to_airtable(self, lead: LeadRecord) -> Dict[str, Any]:
        """Safely push lead to Airtable with graceful error trapping."""
        try:
            return self.airtable.sync_lead(
                {
                    "idempotency_key": lead.idempotency_key,
                    "contact_name": lead.contact_name,
                    "contact_email": lead.contact_email,
                    "company_name": lead.company_name,
                    "budget": lead.budget,
                    "score": lead.score,
                    "priority": lead.priority,
                    "qualification_status": lead.qualification_status,
                    "rationale": lead.rationale,
                }
            )
        except Exception as exc:
            logger.error(f"Airtable sync error for lead {lead.id}: {exc}")
            return {"success": False, "error": str(exc)}

    def _notify_slack(self, lead: LeadRecord) -> Dict[str, Any]:
        """Safely post sales alert to Slack with graceful error trapping."""
        try:
            return self.slack.post_lead_alert(
                {
                    "company_name": lead.company_name,
                    "contact_name": lead.contact_name,
                    "contact_email": lead.contact_email,
                    "budget": lead.budget,
                    "score": lead.score,
                    "priority": lead.priority,
                    "qualification_status": lead.qualification_status,
                    "timeline": lead.timeline,
                    "needs": lead.needs,
                    "rationale": lead.rationale,
                }
            )
        except Exception as exc:
            logger.error(f"Slack alert error for lead {lead.id}: {exc}")
            return {"success": False, "error": str(exc)}

    def retry_routing(self, lead_id: str, db: Session) -> Dict[str, Any]:
        """Recover and re-attempt routing for a failed external integration."""
        lead = db.query(LeadRecord).filter(LeadRecord.id == lead_id).first()
        if not lead:
            raise ValueError(f"Lead '{lead_id}' not found.")

        airtable_res = self._route_to_airtable(lead)
        slack_res = self._notify_slack(lead)

        if airtable_res.get("record_id"):
            lead.airtable_record_id = airtable_res.get("record_id")
        if slack_res.get("ts"):
            lead.slack_ts = slack_res.get("ts")

        if airtable_res.get("success") and slack_res.get("success"):
            lead.routing_status = "ROUTED_ALL"
        else:
            lead.routing_status = "PARTIAL_SYNC" if (airtable_res.get("success") or slack_res.get("success")) else "SYNC_FAILED"

        db.commit()
        db.refresh(lead)

    def get_leads(
        self,
        db: Session,
        priority: Optional[str] = None,
        qualification_status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LeadRecord]:
        """Query leads with multi-field filtering, search, and pagination."""
        query = db.query(LeadRecord)

        if priority:
            query = query.filter(LeadRecord.priority == priority.upper())
        if qualification_status:
            query = query.filter(LeadRecord.qualification_status == qualification_status.upper())
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                (LeadRecord.company_name.ilike(search_pattern))
                | (LeadRecord.contact_name.ilike(search_pattern))
                | (LeadRecord.contact_email.ilike(search_pattern))
            )

        return query.order_by(LeadRecord.created_at.desc()).offset(offset).limit(limit).all()

    def get_lead_by_id(self, lead_id: str, db: Session) -> Optional[LeadRecord]:
        """Retrieve lead by ID."""
        return db.query(LeadRecord).filter(LeadRecord.id == lead_id).first()

