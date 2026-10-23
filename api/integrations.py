"""REST API endpoints for Integration Settings and Diagnostics."""

from typing import Dict
from fastapi import APIRouter
from core.config import settings
from integrations.airtable_adapter import AirtableAdapter
from integrations.email_adapter import EmailAdapter
from integrations.openai_adapter import OpenAIAdapter
from integrations.sheets_adapter import GoogleSheetsAdapter
from integrations.slack_adapter import SlackAdapter
from integrations.stripe_adapter import StripeAdapter

router = APIRouter(prefix="/api/integrations", tags=["Integrations"])

adapters = {
    "openai": OpenAIAdapter(),
    "airtable": AirtableAdapter(),
    "slack": SlackAdapter(),
    "email": EmailAdapter(),
    "google_sheets": GoogleSheetsAdapter(),
    "stripe": StripeAdapter(),
}


@router.get("/status", response_model=Dict[str, dict])
def get_integration_health_matrix():
    """Retrieve health and configuration state for all external adapters."""
    results = {}
    for key, adapter in adapters.items():
        results[key] = adapter.health_check()
    return results


@router.post("/test/{adapter_name}", response_model=dict)
def test_single_adapter(adapter_name: str):
    """Trigger on-demand connectivity test for a specific adapter."""
    adapter = adapters.get(adapter_name.lower())
    if not adapter:
        return {"success": False, "error": f"Unknown adapter: {adapter_name}"}
    return adapter.health_check()
