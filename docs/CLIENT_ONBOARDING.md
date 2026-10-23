# Client Handover & Production Onboarding Guide

This document defines the formal handover protocol, production readiness checklist, and operational transition procedures for deploying **ORBIT AI Operations Studio** to an enterprise client.

---

## 1. Executive Handover Protocol

ORBIT AI Operations Studio is delivered with **zero vendor lock-in**, completely modular integration adapters, and high-fidelity mock engines that enable offline evaluation prior to provisioning live enterprise credentials.

### Transition Roadmap
```
[Phase 1: Local / Staging Acceptance]
  - Execute 19/19 pytest suite in mock mode
  - Review 14 demo scenarios in Operations Studio Web UI
          │
          ▼
[Phase 2: Enterprise Credential Provisioning]
  - Obtain API keys for OpenAI, Airtable, Slack, Google Cloud, Stripe
  - Populate production .env file
          │
          ▼
[Phase 3: Webhook Registration & SSL Binding]
  - Configure public HTTPS domain via Reverse Proxy (Nginx / Cloudflare)
  - Register Stripe & n8n webhook URLs
          │
          ▼
[Phase 4: Staff Training & Go-Live]
  - Train operations team on Approval Center & Escalation Queue
  - Toggle live integration switches (e.g. OPENAI_ENABLED=true)
```

---

## 2. Production Readiness Checklist

| Category | Requirement | Verification Method | Status |
|---|---|---|---|
| **Environment** | Python 3.10+ installed with virtual environment | `python --version` | Verified (3.12) |
| **Dependencies** | All packages in `requirements.txt` installed | `pip check` | Verified |
| **Security** | `EMAIL_DRAFT_ONLY=true` enforced | Verified in `core/config.py` | Enforced |
| **Security** | Secrets absent from git and client JavaScript | Code audit | Verified |
| **Security** | Stripe HMAC signature validation active | `test_stripe_webhook_hmac_verification` | Passed |
| **Data Integrity**| Invoice discrepancy audit threshold ($0.05) | `test_invoice_discrepancy_detection` | Passed |
| **Compliance** | RAG retrieval grounded to approved policy | `test_knowledge_retrieval_rag` | Passed |
| **Auditability** | Execution logging enabled for all events | `execution_logs` table inspection | Active |

---

## 3. Step-by-Step Production Configuration

### Step 1: Cloud Host Provisioning
Deploy the server onto a Linux virtual instance (e.g., AWS EC2, DigitalOcean Droplet, Ubuntu 22.04 LTS):
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git nginx
git clone git@github.com:vijaymahes9080/Datheon_AI_Automation_-_Agent_Building.git /opt/orbit
cd /opt/orbit/vj
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Systemd Daemon Service Configuration
Create `/etc/systemd/system/orbit.service`:
```ini
[Unit]
Description=ORBIT AI Operations Studio Daemon
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/orbit/vj
EnvironmentFile=/opt/orbit/vj/.env
ExecStart=/opt/orbit/vj/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and launch the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable orbit
sudo systemctl start orbit
```

### Step 3: Nginx Reverse Proxy & SSL Configuration
Configure Nginx with Certbot Let's Encrypt SSL:
```nginx
server {
    server_name orbit.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 4. Operational Maintenance & Backup

1. **Database Backups:**
   SQLite in WAL mode supports safe online backups without interrupting active operations:
   ```bash
   sqlite3 orbit_studio.db ".backup './backups/orbit_studio_$(date +%Y%m%d).db'"
   ```
2. **Log Retention:**
   Telemetry logs in `execution_logs` are preserved indefinitely. A scheduled cron job can archive records older than 90 days if storage optimization is desired.
3. **Knowledge Base Updates:**
   To update support policies, edit `data/knowledge_base.json` and restart or reload the service; changes take effect immediately without database schema modifications.
