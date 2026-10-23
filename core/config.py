"""Centralized configuration management for ORBIT AI Operations Studio.

Handles environment variables, demo mode defaults, security policies,
and masked status reporting for external adapters.
"""

from enum import Enum
import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic_settings import BaseSettings


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class IntegrationStatus(str, Enum):
    DEMO_MODE = "DEMO_MODE"
    CONFIGURED = "CONFIGURED"
    VERIFIED_LIVE = "VERIFIED_LIVE"
    SETUP_REQUIRED = "SETUP_REQUIRED"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Application configuration and external service settings."""

    # Application metadata
    APP_NAME: str = "ORBIT AI Operations Studio"
    APP_VERSION: str = "3.0.0"
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = BASE_DIR / "uploads"

    # Persistence
    DATABASE_URL: str = "sqlite:///./orbit_operations.db"

    # System Operation Flags
    DEMO_MODE: bool = True
    DRAFT_ONLY_MODE: bool = True
    STRICT_ARITHMETIC_CHECKS: bool = True
    STRIPE_VERIFY_SIGNATURES: bool = True

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Airtable Settings
    AIRTABLE_API_KEY: Optional[str] = None
    AIRTABLE_BASE_ID: Optional[str] = None
    AIRTABLE_LEADS_TABLE: str = "Leads"
    AIRTABLE_PROJECTS_TABLE: str = "Projects"

    # Slack Settings
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_SALES_CHANNEL: str = "#leads-alerts"
    SLACK_SUPPORT_CHANNEL: str = "#support-triage"
    SLACK_FINANCE_CHANNEL: str = "#finance-approvals"

    # Email Settings
    EMAIL_PROVIDER: str = "mock"  # "mock", "gmail", "smtp"
    EMAIL_SMTP_HOST: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None

    # Google Sheets Settings
    GOOGLE_SHEETS_CREDENTIALS_JSON: Optional[str] = None
    GOOGLE_SHEET_ID: Optional[str] = None

    # Stripe Settings
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def get_masked_secret(self, secret: Optional[str]) -> Optional[str]:
        """Return masked secret string for UI/API display."""
        if not secret:
            return None
        if len(secret) <= 8:
            return "***"
        return f"{secret[:4]}...{secret[-4:]}"

    def get_integration_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return health and connection statuses of all integrated systems."""
        return {
            "openai": {
                "name": "OpenAI Reasoning & Structured Synthesis",
                "status": IntegrationStatus.CONFIGURED.value
                if self.OPENAI_API_KEY and not self.DEMO_MODE
                else IntegrationStatus.DEMO_MODE.value,
                "configured": bool(self.OPENAI_API_KEY),
                "demo_mode": self.DEMO_MODE or not bool(self.OPENAI_API_KEY),
                "model": self.OPENAI_MODEL,
                "description": "Structured lead scoring, support intent classification, talking point generation",
            },
            "airtable": {
                "name": "Airtable CRM & Lead Operations",
                "status": IntegrationStatus.CONFIGURED.value
                if (self.AIRTABLE_API_KEY and self.AIRTABLE_BASE_ID and not self.DEMO_MODE)
                else IntegrationStatus.DEMO_MODE.value,
                "configured": bool(self.AIRTABLE_API_KEY and self.AIRTABLE_BASE_ID),
                "demo_mode": self.DEMO_MODE or not bool(self.AIRTABLE_API_KEY),
                "description": "Two-way lead synchronization and client onboarding project tracking",
            },
            "slack": {
                "name": "Slack Operations Collaboration",
                "status": IntegrationStatus.CONFIGURED.value
                if (self.SLACK_BOT_TOKEN or self.SLACK_WEBHOOK_URL) and not self.DEMO_MODE
                else IntegrationStatus.DEMO_MODE.value,
                "configured": bool(self.SLACK_BOT_TOKEN or self.SLACK_WEBHOOK_URL),
                "demo_mode": self.DEMO_MODE or not bool(self.SLACK_BOT_TOKEN or self.SLACK_WEBHOOK_URL),
                "channels": [self.SLACK_SALES_CHANNEL, self.SLACK_SUPPORT_CHANNEL, self.SLACK_FINANCE_CHANNEL],
                "description": "Real-time sales alerts, support escalation, and project workspace channels",
            },
            "email": {
                "name": "Customer Support Email (Gmail / SMTP)",
                "status": IntegrationStatus.DEMO_MODE.value
                if self.DEMO_MODE or not self.EMAIL_USER
                else IntegrationStatus.CONFIGURED.value,
                "configured": bool(self.EMAIL_USER),
                "demo_mode": self.DEMO_MODE or not bool(self.EMAIL_USER),
                "draft_only_enforced": self.DRAFT_ONLY_MODE,
                "description": "Inbound support ticket ingestion and draft-only response staging",
            },
            "google_sheets": {
                "name": "Google Sheets Financial Ledger Export",
                "status": IntegrationStatus.CONFIGURED.value
                if (self.GOOGLE_SHEETS_CREDENTIALS_JSON and self.GOOGLE_SHEET_ID and not self.DEMO_MODE)
                else IntegrationStatus.DEMO_MODE.value,
                "configured": bool(self.GOOGLE_SHEETS_CREDENTIALS_JSON and self.GOOGLE_SHEET_ID),
                "demo_mode": self.DEMO_MODE or not bool(self.GOOGLE_SHEET_ID),
                "description": "Reconciled invoice export for accounting and cashflow auditing",
            },
            "stripe": {
                "name": "Stripe Payment Verification",
                "status": IntegrationStatus.CONFIGURED.value
                if (self.STRIPE_WEBHOOK_SECRET and not self.DEMO_MODE)
                else IntegrationStatus.DEMO_MODE.value,
                "configured": bool(self.STRIPE_WEBHOOK_SECRET),
                "demo_mode": self.DEMO_MODE or not bool(self.STRIPE_WEBHOOK_SECRET),
                "description": "Cryptographic webhook HMAC validation and contract milestone reconciliation",
            },
        }


settings = Settings()

# Ensure directories exist
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
