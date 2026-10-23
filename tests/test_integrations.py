"""Unit tests for integration adapters and circuit breaker mechanics."""

import pytest
from integrations.airtable_adapter import AirtableAdapter
from integrations.email_adapter import EmailAdapter
from integrations.openai_adapter import OpenAIAdapter
from integrations.sheets_adapter import GoogleSheetsAdapter
from integrations.slack_adapter import SlackAdapter
from integrations.stripe_adapter import StripeAdapter


def test_adapters_health_diagnostics(client):
    """Verify health check diagnostics for all 6 adapters."""
    res = client.get("/api/integrations/status")
    assert res.status_code == 200
    data = res.json()
    assert "openai" in data
    assert "airtable" in data
    assert "slack" in data
    assert "email" in data
    assert "google_sheets" in data
    assert "stripe" in data


def test_circuit_breaker_tripping():
    """Verify circuit breaker opens after consecutive failures."""
    adapter = AirtableAdapter()
    adapter.error_threshold = 2

    # Cause 2 failures
    adapter.record_failure(Exception("Error 1"))
    assert adapter.circuit_open is False
    adapter.record_failure(Exception("Error 2"))
    assert adapter.circuit_open is True

    # Next call should raise ConnectionError due to open circuit
    with pytest.raises(ConnectionError) as exc_info:
        adapter.check_circuit_breaker()
    assert "is OPEN" in str(exc_info.value)
