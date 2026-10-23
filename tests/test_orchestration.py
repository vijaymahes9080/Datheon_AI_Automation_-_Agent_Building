"""Unit and cryptographic tests for Project 4: Enterprise Multi-Agent Orchestration."""

import json
import pytest
from integrations.stripe_adapter import StripeAdapter


def test_customer_onboarding_and_contract_generation(client):
    """Verify customer intake assigns stable project code and prepares template contract."""
    payload = {
        "customer_name": "Alexander Wright",
        "customer_email": "a.wright@hyperion-global.com",
        "company_name": "Hyperion Global Retail Inc.",
        "service_tier": "ENTERPRISE",
        "contract_value": 45000,
    }

    res = client.post("/api/orchestration/onboard", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert "PRJ-" in data["project"]["project_code"]
    assert "MASTER SERVICES & AUTOMATION AGREEMENT" in data["contract_draft"]
    assert "$45,000.00" in data["contract_draft"]


def test_stripe_cryptographic_signature_verification_success(client):
    """Verify authentic Stripe HMAC-SHA256 signature is accepted."""
    onboard = client.post(
        "/api/orchestration/onboard",
        json={
            "customer_name": "Test Client",
            "customer_email": "test@stripe-test.com",
            "company_name": "Stripe Test Corp",
            "service_tier": "ENTERPRISE",
            "contract_value": 15000,
        },
    ).json()
    proj_id = onboard["project"]["id"]

    sim_res = client.post(
        "/api/orchestration/simulate-stripe-payment",
        json={"project_id": proj_id, "amount": 15000, "corrupt_signature": False},
    )
    assert sim_res.status_code == 200
    data = sim_res.json()
    assert data["success"] is True
    assert data["result"]["verified"] is True
    assert data["result"]["amount"] == 15000


def test_stripe_corrupted_signature_rejected(client):
    """Verify that forged/corrupted Stripe signature is rejected."""
    sim_res = client.post(
        "/api/orchestration/simulate-stripe-payment",
        json={"project_id": "PRJ-FAKE", "amount": 5000, "corrupt_signature": True},
    )
    assert sim_res.status_code == 200
    data = sim_res.json()
    assert data["success"] is False
    assert "Signature" in data["error"] or "rejected" in data["error"]


def test_executive_digest_generation(client):
    """Verify evidence-grounded executive digest compiles stored metrics."""
    res = client.get("/api/orchestration/executive-digest")
    assert res.status_code == 200
    data = res.json()
    assert "Weekly Operational Executive Digest" in data["executive_narrative"]
    assert "Data Freshness:" in data["executive_narrative"]
    assert data["verified_metrics"]["leads"]["total"] >= 0
