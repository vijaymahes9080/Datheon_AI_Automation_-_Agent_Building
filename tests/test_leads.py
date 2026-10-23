"""Unit and integration tests for Project 1: Lead Intelligence & Revenue Routing."""

import pytest
from core.schemas import LeadSubmissionRequest
from services.lead_service import LeadService


def test_lead_submission_success(client):
    """Verify valid lead intake, qualification scoring, and talking points synthesis."""
    payload = {
        "contact_name": "Marcus Aurelius",
        "contact_email": "m.aurelius@rome-enterprises.com",
        "company_name": "Rome Enterprises",
        "company_size": "100-250",
        "budget": 30000,
        "timeline": "Immediate (30 Days)",
        "needs": "Need to automate multi-channel supply routing, order reconciliation, and Airtable syncing.",
        "consent_given": True,
    }

    res = client.post("/api/leads/submit", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["duplicate"] is False
    assert data["lead"]["score"] >= 70
    assert data["lead"]["qualification_status"] == "QUALIFIED"
    assert len(data["lead"]["sales_talking_points"]) > 0
    assert data["processing_time_ms"] > 0


def test_lead_submission_duplicate_prevention(client):
    """Verify duplicate webhook/form submissions are identified without duplicating records."""
    payload = {
        "contact_name": "Marcus Aurelius",
        "contact_email": "m.aurelius@rome-enterprises.com",
        "company_name": "Rome Enterprises",
        "company_size": "100-250",
        "budget": 30000,
        "timeline": "Immediate (30 Days)",
        "needs": "Need to automate multi-channel supply routing, order reconciliation, and Airtable syncing.",
        "consent_given": True,
    }

    # First call
    res1 = client.post("/api/leads/submit", json=payload)
    assert res1.status_code == 201
    lead_id = res1.json()["lead"]["id"]

    # Duplicate call with identical details
    res2 = client.post("/api/leads/submit", json=payload)
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["duplicate"] is True
    assert data2["lead"]["id"] == lead_id


def test_lead_submission_consent_rejection(client):
    """Verify that submissions lacking explicit consent are rejected with 422."""
    payload = {
        "contact_name": "Test User",
        "contact_email": "user@test.com",
        "company_name": "Test Co",
        "company_size": "10-50",
        "budget": 5000,
        "needs": "General automation needs",
        "consent_given": False,  # Missing consent
    }

    res = client.post("/api/leads/submit", json=payload)
    assert res.status_code == 422


def test_lead_low_budget_disqualification(client):
    """Verify low budget leads are classified as DISQUALIFIED or NEEDS_REVIEW."""
    payload = {
        "contact_name": "Budget User",
        "contact_email": "budget@smallshop.com",
        "company_name": "Small Shop",
        "company_size": "1-5",
        "budget": 200,  # Below threshold
        "needs": "Simple script",
        "consent_given": True,
    }

    res = client.post("/api/leads/submit", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["lead"]["priority"] == "LOW"
    assert data["lead"]["qualification_status"] in ["DISQUALIFIED", "NEEDS_REVIEW"]
