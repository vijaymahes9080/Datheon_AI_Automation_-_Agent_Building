# GitHub Pages Hosting & Deployment Guide

This guide provides step-by-step instructions for enabling, configuring, and publishing **ORBIT AI Operations Studio** on **GitHub Pages**.

---

## 🌐 Live Site URL
Once enabled, your interactive Operations Studio will be live at:  
👉 **`https://vijaymahes9080.github.io/Datheon_AI_Automation_-_Agent_Building/`**

---

## 🛠️ Step-by-Step Configuration in GitHub Settings

Navigate to your repository on GitHub:  
`https://github.com/vijaymahes9080/Datheon_AI_Automation_-_Agent_Building`

1. Click on **Settings** (the gear icon on the top tab bar).
2. In the left navigation sidebar under *Code and automation*, click **Pages**.
3. Under the **Build and deployment** section, configure the **Source** using either of the two options below:

```
+-----------------------------------------------------------------------------------------+
| GitHub Pages Configuration                                                             |
|                                                                                         |
| Build and deployment                                                                    |
|                                                                                         |
| Source:  [ GitHub Actions (Recommended)  ▼ ]                                            |
|          -----------------------------------                                            |
|          OR                                                                             |
| Source:  [ Deploy from a branch          ▼ ]                                            |
| Branch:  [ gh-pages (or main)   ▼ ]  /  [ / (root)    ▼ ]   [ Save ]                    |
+-----------------------------------------------------------------------------------------+
```

---

### Option A: GitHub Actions (Recommended)

1. Under **Source**, select **`GitHub Actions`** from the dropdown menu.
2. That's it! GitHub will automatically trigger the workflow defined in [`.github/workflows/deploy-pages.yml`](../.github/workflows/deploy-pages.yml).
3. Click on the **Actions** tab in your repository to watch the deployment progress.
4. Once completed (typically ~40–60 seconds), your live URL will be displayed at the top of the Pages settings.

---

### Option B: Deploy from a Branch

If you prefer branch-based publishing:

1. Under **Source**, select **`Deploy from a branch`**.
2. Under **Branch**, select **`gh-pages`** (or **`main`**).
3. In the folder dropdown next to the branch, keep **`/ (root)`**.
4. Click **Save**.
5. GitHub Pages will build and deploy the site in 1–2 minutes.

---

## ⚡ What Runs on GitHub Pages?

GitHub Pages hosts the complete interactive **Operations Studio single-page application**:
- **In-Browser Client Simulator (`static/js/simulator.js`):** Intercepts API requests and provides an in-memory & `localStorage` simulation engine.
- **100% Interactive Features:**
  - **Lead Intelligence:** Submit form leads, calculate AI scores (85/100 HIGH), view talking points, and simulate Airtable/Slack sync.
  - **Support Intelligence:** Triage emails, classify intents, view grounded RAG policies, and observe the hardcoded Draft-Only safety guard.
  - **Invoice Intelligence:** Inspect invoice details, view line items, detect arithmetic discrepancies ($\pm \$0.05$ variance), and approve records.
  - **Enterprise Orchestration:** Onboard clients with sequential project codes (`PRJ-2026-001`), generate MSA contracts, simulate Stripe HMAC-SHA256 verified webhooks, and compile weekly executive digests.
  - **Workflow Studio & Agent Registry:** Inspect the 10 workforce personas, step DAGs, and approval queues.
- **Zero Server Overhead:** Runs directly in any modern web browser with zero server hosting fees.
- **Optional Backend Connection:** If you host the FastAPI Python backend (e.g. on Render, Railway, or localhost), the studio seamlessly connects to the live backend.
