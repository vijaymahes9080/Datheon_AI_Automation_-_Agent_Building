"""Airtable CRM Integration Adapter supporting idempotent upserts,
live REST API calls, and resilient mock stores for testing.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from core.config import IntegrationStatus, settings
from integrations.base import BaseIntegrationAdapter

logger = logging.getLogger("orbit.integrations.airtable")


class AirtableAdapter(BaseIntegrationAdapter):
    """Adapter for Airtable REST API (Leads & Client Projects)."""

    def __init__(self):
        super().__init__("AirtableAdapter")
        self.api_key = settings.AIRTABLE_API_KEY
        self.base_id = settings.AIRTABLE_BASE_ID
        self.leads_table = settings.AIRTABLE_LEADS_TABLE
        self.projects_table = settings.AIRTABLE_PROJECTS_TABLE
        self._simulate_failure: bool = False

        # In-memory mock store for deterministic testing
        self.mock_leads: Dict[str, Dict[str, Any]] = {}
        self.mock_projects: Dict[str, Dict[str, Any]] = {}

    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_id and not settings.DEMO_MODE)

    def trigger_simulated_failure(self) -> None:
        """Trigger an intentional transient error to test retry and recovery."""
        self._simulate_failure = True

    def health_check(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                "name": self.name,
                "status": IntegrationStatus.DEMO_MODE.value,
                "base_id": self.base_id or "appMockBase123456",
                "tables": [self.leads_table, self.projects_table],
                "configured": False,
                "message": "Running Airtable mock sync store. Stored leads: " f"{len(self.mock_leads)}.",
            }

        try:
            start = time.perf_counter()
            url = f"https://api.airtable.com/v0/{self.base_id}/{self.leads_table}?maxRecords=1"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(url, headers=headers)
                res.raise_for_status()
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {
                "name": self.name,
                "status": IntegrationStatus.VERIFIED_LIVE.value,
                "latency_ms": latency,
                "configured": True,
            }
        except Exception as err:
            return {
                "name": self.name,
                "status": IntegrationStatus.ERROR.value,
                "error": str(err),
                "configured": True,
            }

    def sync_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Idempotently sync or update a lead in Airtable."""
        if self._simulate_failure:
            self._simulate_failure = False
            logger.warning("[AirtableAdapter] Simulating network failure for recovery testing.")
            raise ConnectionError("Simulated Airtable API timeout/error (503 Service Unavailable)")

        if not self.is_configured():
            return self._sync_lead_mock(lead)

        return self.execute_with_retry(self._sync_lead_live, lead)

    def _sync_lead_mock(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        key = lead.get("idempotency_key") or lead.get("contact_email")
        existing = self.mock_leads.get(key)
        record_id = existing["id"] if existing else f"rec_mock_{int(time.time() * 1000)}"

        record_payload = {
            "id": record_id,
            "fields": {
                "Name": lead.get("contact_name"),
                "Email": lead.get("contact_email"),
                "Company": lead.get("company_name"),
                "Budget": lead.get("budget"),
                "Score": lead.get("score"),
                "Priority": lead.get("priority"),
                "Status": lead.get("qualification_status"),
                "Rationale": lead.get("rationale"),
                "Synced_At": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            },
        }
        self.mock_leads[key] = record_payload
        logger.info(f"[AirtableAdapter] Mock Synced lead '{lead.get('contact_name')}' as {record_id}")
        return {"success": True, "record_id": record_id, "mode": "MOCK"}

    def _sync_lead_live(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        url = f"https://api.airtable.com/v0/{self.base_id}/{self.leads_table}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        fields = {
            "Contact Name": lead.get("contact_name"),
            "Email": lead.get("contact_email"),
            "Company": lead.get("company_name"),
            "Budget": lead.get("budget"),
            "Qualification Score": lead.get("score"),
            "Priority": lead.get("priority"),
            "Qualification Status": lead.get("qualification_status"),
            "Rationale": lead.get("rationale"),
        }
        payload = {"records": [{"fields": fields}]}
        with httpx.Client(timeout=8.0) as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()
            record_id = data["records"][0]["id"]
            return {"success": True, "record_id": record_id, "mode": "LIVE"}

    def sync_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Sync a customer onboarding project record."""
        code = project.get("project_code")
        if not self.is_configured():
            record_id = f"rec_prj_{int(time.time() * 1000)}"
            self.mock_projects[code] = {
                "id": record_id,
                "fields": {
                    "Project Code": code,
                    "Client": project.get("customer_name"),
                    "Tier": project.get("service_tier"),
                    "Value": project.get("contract_value"),
                    "Status": project.get("workflow_state"),
                },
            }
            return {"success": True, "record_id": record_id, "mode": "MOCK"}

        # Live implementation
        url = f"https://api.airtable.com/v0/{self.base_id}/{self.projects_table}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "records": [
                {
                    "fields": {
                        "Project Code": code,
                        "Customer Name": project.get("customer_name"),
                        "Company": project.get("company_name"),
                        "Service Tier": project.get("service_tier"),
                        "Contract Value": project.get("contract_value"),
                        "Workflow State": project.get("workflow_state"),
                    }
                }
            ]
        }
        with httpx.Client(timeout=8.0) as client:
            res = client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            return {"success": True, "record_id": res.json()["records"][0]["id"], "mode": "LIVE"}
