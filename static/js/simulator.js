/**
 * ORBIT AI Operations Studio — In-Browser Client Simulator
 * Enables 100% full interactive functionality on static hosting (GitHub Pages).
 * Intercepts /api/ calls with an in-memory & localStorage mock engine when the
 * Python FastAPI backend is not running or unreachable.
 */

(function () {
  console.log("🚀 ORBIT In-Browser Simulator Engine Initialized.");

  const isGitHubPages =
    window.location.hostname.includes("github.io") ||
    window.location.protocol === "file:" ||
    window.location.hostname === "localhost" && window.location.port !== "8000";

  let backendAvailable = false;

  // Initialize Mock Database in localStorage if not already present
  function initMockDatabase() {
    if (!localStorage.getItem("orbit_mock_initialized")) {
      const initialLeads = [
        {
          id: "lead_01",
          contact_name: "Elena Rostova",
          contact_email: "elena.rostova@apexlogistics.com",
          company_name: "Apex Global Logistics",
          company_size: "100-250",
          budget: 35000,
          timeline: "immediate",
          needs: "Automate multi-carrier shipping rate comparison, webhook routing, and warehouse order fulfillment.",
          score: 85,
          priority: "HIGH",
          qualification_status: "QUALIFIED",
          processing_time_ms: 42,
          rationale: "Enterprise logistics provider with $35,000 budget and immediate deployment timeline. Strong product-market fit.",
          sales_talking_points: [
            "Demonstrate automated multi-carrier webhook ingestion and SLA latency tracking.",
            "Highlight Airtable CRM integration for automated fulfillment queue sync.",
            "Showcase Slack Block Kit alert dispatches for high-priority exception handling."
          ],
          airtable_record_id: "rec_mock_apex8892",
          slack_ts: "1729648900.123400",
          created_at: new Date(Date.now() - 3600000).toISOString()
        },
        {
          id: "lead_02",
          contact_name: "Marcus Vance",
          contact_email: "marcus@vancedirect.com",
          company_name: "Vance Direct eCommerce",
          company_size: "50-100",
          budget: 15000,
          timeline: "Q4",
          needs: "Automate customer support ticket triage and supplier invoice reconciliation.",
          score: 72,
          priority: "HIGH",
          qualification_status: "QUALIFIED",
          processing_time_ms: 38,
          rationale: "High-volume DTC retailer looking to reduce operational overhead in Q4 peak season.",
          sales_talking_points: [
            "Emphasize Draft-Only email safety to eliminate autonomous customer miscommunication.",
            "Demonstrate mathematical invoice reconciliation to prevent supplier overbilling."
          ],
          airtable_record_id: "rec_mock_vance4412",
          slack_ts: "1729645200.567800",
          created_at: new Date(Date.now() - 7200000).toISOString()
        },
        {
          id: "lead_03",
          contact_name: "Alex Croft",
          contact_email: "alex@localmart.com",
          company_name: "LocalMart Corner Shop",
          company_size: "1-10",
          budget: 1200,
          timeline: "exploring",
          needs: "Basic email auto-responder for weekend store hours.",
          score: 28,
          priority: "LOW",
          qualification_status: "DISQUALIFIED",
          processing_time_ms: 31,
          rationale: "Budget ($1,200) below minimum enterprise automation engagement threshold ($5,000).",
          sales_talking_points: [
            "Refer to starter community tier or self-serve documentation.",
            "Follow up in 6 months when regional expansion begins."
          ],
          airtable_record_id: null,
          slack_ts: null,
          created_at: new Date(Date.now() - 14400000).toISOString()
        }
      ];

      const initialTickets = [
        {
          id: "tkt_01",
          sender: "ops-lead@enterprise-client.com",
          subject: "CRITICAL: Payment gateway down on EU store",
          body: "Our European checkout is throwing 500 errors on all Stripe transactions. Customers cannot pay! Fix this immediately!",
          intent: "urgent_incident",
          urgency: "CRITICAL",
          sentiment: -0.85,
          draft_response: "Hello, our engineering on-call team has been paged immediately regarding the European checkout gateway 500 errors. We are investigating payment connectivity right now. Ticket escalated to P0.",
          escalated: true,
          status: "ESCALATED",
          created_at: new Date(Date.now() - 1800000).toISOString()
        },
        {
          id: "tkt_02",
          sender: "accounting@retailpartner.com",
          subject: "What is your refund policy for annual subscriptions?",
          body: "Can I get a refund if I cancel 15 days into my annual contract? Please advise how charges are credited.",
          intent: "billing",
          urgency: "MEDIUM",
          sentiment: 0.1,
          draft_response: "Thank you for reaching out. Under our approved corporate policy, annual contracts canceled within 30 days are eligible for a prorated refund subject to managerial sign-off. I have queued this draft for managerial review.",
          escalated: true,
          status: "DRAFT_PENDING_REVIEW",
          created_at: new Date(Date.now() - 5400000).toISOString()
        },
        {
          id: "tkt_03",
          sender: "developer@partnerapi.io",
          subject: "Webhook HMAC signature mismatch on endpoint",
          body: "We are attempting to verify Stripe events using your Python SDK but receiving invalid signature warnings.",
          intent: "technical_support",
          urgency: "HIGH",
          sentiment: -0.2,
          draft_response: "Hello! Please ensure you are extracting the raw payload bytes before parsing JSON, and verifying the 't=' timestamp against the 300-second replay window. See docs/INTEGRATIONS.md for reference code.",
          escalated: false,
          status: "DRAFT_READY",
          created_at: new Date(Date.now() - 9000000).toISOString()
        }
      ];

      const initialInvoices = [
        {
          id: "inv_01",
          vendor: "CloudScale Infrastructure Services",
          invoice_number: "INV-2026-0091",
          invoice_date: "2026-10-15",
          subtotal: 1250.00,
          discount: 0.00,
          tax_amount: 125.00,
          total_amount: 1375.00,
          calculated_total: 1375.00,
          discrepancy_amount: 0.00,
          has_discrepancy: false,
          is_duplicate: false,
          is_approved: true,
          is_exported: true,
          exported_at: new Date(Date.now() - 86400000).toISOString(),
          status: "EXPORTED_TO_SHEETS",
          items: [
            { description: "Managed Kubernetes Cluster Node Pool", quantity: 3, unit_price: 350.00, amount: 1050.00 },
            { description: "Redis In-Memory Cache Cluster", quantity: 1, unit_price: 200.00, amount: 200.00 }
          ],
          created_at: new Date(Date.now() - 86400000).toISOString()
        },
        {
          id: "inv_02",
          vendor: "Apex Global Fulfillment",
          invoice_number: "INV-2026-8842",
          invoice_date: "2026-10-20",
          subtotal: 7500.00,
          discount: 100.00,
          tax_amount: 750.00,
          total_amount: 8260.00,
          calculated_total: 8150.00,
          discrepancy_amount: 110.00,
          has_discrepancy: true,
          is_duplicate: false,
          is_approved: false,
          is_exported: false,
          status: "FLAGGED_DISCREPANCY",
          items: [
            { description: "Freight Drayage & Port Handling", quantity: 5, unit_price: 1500.00, amount: 7500.00 }
          ],
          created_at: new Date(Date.now() - 17280000).toISOString()
        }
      ];

      const initialProjects = [
        {
          id: "proj_01",
          project_code: "PRJ-2026-001",
          client_name: "Sterling Growth Partners",
          client_email: "david@sterlinggrowth.com",
          company_name: "Sterling Growth Partners Ltd",
          service_tier: "ENTERPRISE",
          contract_value: 75000.00,
          contract_status: "APPROVED",
          contract_template_version: "v3.2",
          payment_status: "PAID",
          stripe_payment_intent: "pi_3MtwBwLkdIwHu7ix28a3tqPa",
          slack_channel_id: "C0897213456",
          slack_channel_name: "prj-2026-001-sterling",
          status: "ACTIVE_ONBOARDED",
          created_at: new Date(Date.now() - 120000000).toISOString()
        },
        {
          id: "proj_02",
          project_code: "PRJ-2026-002",
          client_name: "Elena Rostova",
          client_email: "elena@apexlogistics.com",
          company_name: "Apex Global Logistics",
          service_tier: "PROFESSIONAL",
          contract_value: 35000.00,
          contract_status: "DRAFT",
          contract_template_version: "v3.2",
          payment_status: "PENDING_WEBHOOK",
          slack_channel_id: null,
          status: "CONTRACT_REVIEW",
          created_at: new Date(Date.now() - 25000000).toISOString()
        }
      ];

      const initialApprovals = [
        {
          id: "appr_01",
          module: "invoices",
          title: "Invoice #INV-2026-8842 Discrepancy ($110.00 variance)",
          description: "Subtotal $7,500 - Discount $100 + Tax $750 = $8,150. Vendor stated $8,260.00. Approval required prior to Google Sheets export.",
          entity_id: "inv_02",
          status: "PENDING",
          requested_at: new Date(Date.now() - 17280000).toISOString()
        },
        {
          id: "appr_02",
          module: "orchestration",
          title: "Contract MSA Sign-Off: Apex Global Logistics (PRJ-2026-002)",
          description: "Standard Enterprise MSA template v3.2 drafted for $35,000 professional tier engagement. Ready for executive sign-off.",
          entity_id: "proj_02",
          status: "PENDING",
          requested_at: new Date(Date.now() - 25000000).toISOString()
        }
      ];

      const initialLogs = [
        {
          id: "log_01",
          module: "orchestration",
          workflow_name: "Stripe HMAC Signature Verification",
          trigger_type: "WEBHOOK",
          status: "SUCCESS",
          duration_ms: 18,
          created_at: new Date(Date.now() - 600000).toISOString()
        },
        {
          id: "log_02",
          module: "leads",
          workflow_name: "Lead Intelligence Pipeline",
          trigger_type: "FORM_SUBMIT",
          status: "SUCCESS",
          duration_ms: 42,
          created_at: new Date(Date.now() - 1200000).toISOString()
        },
        {
          id: "log_03",
          module: "invoices",
          workflow_name: "Arithmetic Reconciliation Audit",
          trigger_type: "PDF_UPLOAD",
          status: "WARNING",
          error_message: "Arithmetic variance $110.00 flagged. Export locked.",
          duration_ms: 65,
          created_at: new Date(Date.now() - 2400000).toISOString()
        },
        {
          id: "log_04",
          module: "support",
          workflow_name: "Grounded RAG Triage & Draft",
          trigger_type: "EMAIL_INGEST",
          status: "SUCCESS",
          duration_ms: 36,
          created_at: new Date(Date.now() - 3600000).toISOString()
        }
      ];

      localStorage.setItem("orbit_leads", JSON.stringify(initialLeads));
      localStorage.setItem("orbit_tickets", JSON.stringify(initialTickets));
      localStorage.setItem("orbit_invoices", JSON.stringify(initialInvoices));
      localStorage.setItem("orbit_projects", JSON.stringify(initialProjects));
      localStorage.setItem("orbit_approvals", JSON.stringify(initialApprovals));
      localStorage.setItem("orbit_logs", JSON.stringify(initialLogs));
      localStorage.setItem("orbit_mock_initialized", "true");
    }
  }

  initMockDatabase();

  function getDB(key) {
    return JSON.parse(localStorage.getItem(key) || "[]");
  }

  function setDB(key, data) {
    localStorage.setItem(key, JSON.stringify(data));
  }

  // Intercept fetch calls to /api/*
  const nativeFetch = window.fetch;
  window.fetch = async function (resource, options = {}) {
    let url = typeof resource === "string" ? resource : resource.url;

    // Check if URL targets ORBIT /api endpoints
    if (url.includes("/api/")) {
      const parsedUrl = new URL(url, window.location.origin);
      const path = parsedUrl.pathname;
      const method = (options.method || "GET").toUpperCase();

      // If backend is running locally on port 8000 and not GitHub pages, attempt live fetch
      if (!isGitHubPages) {
        try {
          const res = await nativeFetch(resource, options);
          if (res.ok || res.status < 500) {
            return res;
          }
        } catch (e) {
          console.warn("Backend server not responding, falling back to In-Browser Simulator.");
        }
      }

      // Handle with In-Browser Simulator
      console.log(`[SIMULATOR] ${method} ${path}`);
      return handleSimulatedRequest(path, method, options);
    }

    return nativeFetch(resource, options);
  };

  // Simulated Request Handler
  async function handleSimulatedRequest(path, method, options) {
    let body = {};
    if (options.body) {
      try {
        body = typeof options.body === "string" ? JSON.parse(options.body) : options.body;
      } catch (e) {
        body = {};
      }
    }

    // Delay simulation for realistic UX feel (30-80ms)
    await new Promise((r) => setTimeout(r, 45));

    // 1. Workflow Summary & KPIs
    if (path === "/api/workflows/summary") {
      const leads = getDB("orbit_leads");
      const tickets = getDB("orbit_tickets");
      const invoices = getDB("orbit_invoices");
      const projects = getDB("orbit_projects");
      const approvals = getDB("orbit_approvals").filter((a) => a.status === "PENDING");

      const qualifiedLeads = leads.filter((l) => l.qualification_status === "QUALIFIED").length;
      const urgentTickets = tickets.filter((t) => t.urgency === "CRITICAL" || t.urgency === "HIGH").length;
      const discrepancies = invoices.filter((i) => i.has_discrepancy).length;
      const verifiedRev = projects
        .filter((p) => p.payment_status === "PAID")
        .reduce((sum, p) => sum + (p.contract_value || 0), 0);

      return mockResponse({
        leads: { total: leads.length, qualified: qualifiedLeads, avg_latency_ms: 42 },
        support: { total: tickets.length, urgent_incidents: urgentTickets },
        invoices: { total: invoices.length, discrepancies_detected: discrepancies },
        orchestration: { active_projects: projects.length, verified_payments_amount: verifiedRev },
        system: { pending_approvals: approvals.length, mode: "GITHUB_PAGES_SIMULATOR" }
      });
    }

    // 2. Execution History
    if (path.startsWith("/api/workflows/history")) {
      const logs = getDB("orbit_logs");
      return mockResponse(logs.slice(0, 10));
    }

    // 3. Leads Ingestion & Submission
    if (path === "/api/leads" || path === "/api/leads/") {
      return mockResponse(getDB("orbit_leads"));
    }

    if (path === "/api/leads/submit") {
      const leads = getDB("orbit_leads");
      const budget = body.budget || 0;
      let score = 50;
      let priority = "MEDIUM";
      let status = "QUALIFIED";

      if (budget >= 25000) {
        score = 85;
        priority = "HIGH";
      } else if (budget < 5000) {
        score = 25;
        priority = "LOW";
        status = "DISQUALIFIED";
      }

      const newLead = {
        id: "lead_" + Date.now(),
        contact_name: body.contact_name || "Enterprise Lead",
        contact_email: body.contact_email || "lead@company.com",
        company_name: body.company_name || "Enterprise Corp",
        company_size: body.company_size || "50-100",
        budget: budget,
        timeline: body.timeline || "immediate",
        needs: body.needs || "Enterprise Automation",
        score: score,
        priority: priority,
        qualification_status: status,
        processing_time_ms: Math.floor(Math.random() * 20) + 35,
        rationale: `Validated business prospect with $${budget.toLocaleString()} stated budget. AI qualification confirms ${priority} tier routing.`,
        sales_talking_points: [
          `Highlight sub-second automated workflow routing and Airtable CRM synchronization.`,
          `Reference existing success metrics in high-volume eCommerce automation.`,
          `Demonstrate audit trails and SLA compliance (< 10.0s).`
        ],
        airtable_record_id: "rec_mock_" + Math.random().toString(36).substring(2, 9),
        slack_ts: Date.now() + ".000100",
        created_at: new Date().toISOString()
      };

      leads.unshift(newLead);
      setDB("orbit_leads", leads);

      // Add audit log
      const logs = getDB("orbit_logs");
      logs.unshift({
        id: "log_" + Date.now(),
        module: "leads",
        workflow_name: "Lead Intelligence Pipeline",
        trigger_type: "WEBHOOK",
        status: "SUCCESS",
        duration_ms: newLead.processing_time_ms,
        created_at: new Date().toISOString()
      });
      setDB("orbit_logs", logs);

      return mockResponse({ success: true, lead: newLead, duplicate: false, processing_time_ms: newLead.processing_time_ms });
    }

    // 4. Support Ingestion & Classification
    if (path === "/api/support/tickets" || path === "/api/support/tickets/") {
      return mockResponse(getDB("orbit_tickets"));
    }

    if (path === "/api/support/ingest") {
      const tickets = getDB("orbit_tickets");
      const subj = (body.subject || "").toLowerCase();
      const text = (body.body || "").toLowerCase();

      let intent = "product_inquiry";
      let urgency = "LOW";
      let escalated = false;
      let draft = "Thank you for contacting ORBIT Support. We have received your inquiry and our team is reviewing approved operational documentation to assist you.";

      if (subj.includes("500") || subj.includes("down") || subj.includes("critical") || text.includes("outage")) {
        intent = "urgent_incident";
        urgency = "CRITICAL";
        escalated = true;
        draft = "URGENT INCIDENT ESCALATION: We have detected a critical operational alert regarding your system access. On-call engineers have been paged. This ticket is prioritized as P0.";
      } else if (subj.includes("refund") || text.includes("cancel") || text.includes("billing")) {
        intent = "billing";
        urgency = "MEDIUM";
        escalated = true;
        draft = "Under approved company policy, subscriptions canceled within 30 days are eligible for refund review. This response is stored as DRAFT-ONLY pending human manager sign-off.";
      }

      const newTicket = {
        id: "tkt_" + Date.now(),
        sender: body.sender || "user@domain.com",
        subject: body.subject || "Support Request",
        body: body.body || "",
        intent: intent,
        urgency: urgency,
        sentiment: urgency === "CRITICAL" ? -0.8 : 0.0,
        draft_response: draft,
        escalated: escalated,
        status: escalated ? "ESCALATED" : "DRAFT_PENDING_REVIEW",
        created_at: new Date().toISOString()
      };

      tickets.unshift(newTicket);
      setDB("orbit_tickets", tickets);

      return mockResponse({ success: true, ticket: newTicket });
    }

    // 5. Invoices & Reconciliation
    if (path === "/api/invoices" || path === "/api/invoices/") {
      return mockResponse(getDB("orbit_invoices"));
    }

    if (path === "/api/invoices/upload") {
      const invoices = getDB("orbit_invoices");
      const isDiscrepant = Math.random() > 0.4;
      const subtotal = 3500.00;
      const tax = 350.00;
      const total = isDiscrepant ? 3960.00 : 3850.00;

      const newInvoice = {
        id: "inv_" + Date.now(),
        vendor: "Apex Cloud Services",
        invoice_number: "INV-2026-" + Math.floor(1000 + Math.random() * 9000),
        invoice_date: new Date().toISOString().split("T")[0],
        subtotal: subtotal,
        discount: 0.00,
        tax_amount: tax,
        total_amount: total,
        calculated_total: 3850.00,
        discrepancy_amount: isDiscrepant ? 110.00 : 0.00,
        has_discrepancy: isDiscrepant,
        is_duplicate: false,
        is_approved: !isDiscrepant,
        is_exported: false,
        status: isDiscrepant ? "FLAGGED_DISCREPANCY" : "RECONCILED",
        items: [
          { description: "Managed VPS Compute Nodes", quantity: 2, unit_price: 1750.00, amount: 3500.00 }
        ],
        created_at: new Date().toISOString()
      };

      invoices.unshift(newInvoice);
      setDB("orbit_invoices", invoices);

      if (isDiscrepant) {
        const approvals = getDB("orbit_approvals");
        approvals.unshift({
          id: "appr_" + Date.now(),
          module: "invoices",
          title: `Invoice #${newInvoice.invoice_number} Variance ($110.00)`,
          description: "Subtotal $3,500 + Tax $350 != Stated $3,960.00. Requires managerial override.",
          entity_id: newInvoice.id,
          status: "PENDING",
          requested_at: new Date().toISOString()
        });
        setDB("orbit_approvals", approvals);
      }

      return mockResponse({ success: true, invoice: newInvoice });
    }

    if (path.includes("/approve")) {
      const invoices = getDB("orbit_invoices");
      const id = path.split("/")[3];
      const inv = invoices.find((i) => i.id === id);
      if (inv) {
        inv.is_approved = true;
        inv.status = "APPROVED_FOR_EXPORT";
        setDB("orbit_invoices", invoices);
      }
      return mockResponse({ success: true, message: "Invoice approved." });
    }

    if (path.includes("/export")) {
      const invoices = getDB("orbit_invoices");
      const id = path.split("/")[3];
      const inv = invoices.find((i) => i.id === id);
      if (inv) {
        inv.is_exported = true;
        inv.status = "EXPORTED_TO_SHEETS";
        setDB("orbit_invoices", invoices);
      }
      return mockResponse({ success: true, message: "Invoice exported to Google Sheets ledger." });
    }

    // 6. Enterprise Orchestration & Projects
    if (path === "/api/orchestration/projects" || path === "/api/orchestration/projects/") {
      return mockResponse(getDB("orbit_projects"));
    }

    if (path === "/api/orchestration/intake") {
      const projects = getDB("orbit_projects");
      const nextCode = "PRJ-2026-00" + (projects.length + 1);
      const newProj = {
        id: "proj_" + Date.now(),
        project_code: nextCode,
        client_name: body.client_name || "Enterprise Client",
        client_email: body.client_email || "client@domain.com",
        company_name: body.company_name || "Client Corp",
        service_tier: body.service_tier || "ENTERPRISE",
        contract_value: body.contract_value || 50000,
        contract_status: "DRAFT",
        contract_template_version: "v3.2",
        payment_status: "PENDING_WEBHOOK",
        slack_channel_id: null,
        status: "CONTRACT_REVIEW",
        created_at: new Date().toISOString()
      };

      projects.unshift(newProj);
      setDB("orbit_projects", projects);

      return mockResponse({ success: true, project: newProj });
    }

    if (path.includes("/simulate-stripe-payment")) {
      const projects = getDB("orbit_projects");
      const projId = body.project_id;
      const proj = projects.find((p) => p.id === projId || p.project_code === projId);
      if (proj) {
        proj.payment_status = "PAID";
        proj.stripe_payment_intent = "pi_mock_" + Math.random().toString(36).substring(2, 9);
        proj.slack_channel_id = "C0" + Math.floor(10000000 + Math.random() * 90000000);
        proj.slack_channel_name = proj.project_code.toLowerCase() + "-collab";
        proj.status = "ACTIVE_ONBOARDED";
        setDB("orbit_projects", projects);
      }
      return mockResponse({ success: true, message: "Payment verified via Stripe HMAC-SHA256 signature.", project: proj });
    }

    if (path.includes("/digest")) {
      const leads = getDB("orbit_leads");
      const invoices = getDB("orbit_invoices");
      const projects = getDB("orbit_projects");
      return mockResponse({
        reporting_period: "Current Week (Trailing 7 Days)",
        verified_leads_count: leads.length,
        invoices_processed: invoices.length,
        verified_revenue: projects.filter((p) => p.payment_status === "PAID").reduce((s, p) => s + p.contract_value, 0),
        generated_at: new Date().toISOString()
      });
    }

    // 7. Approvals
    if (path === "/api/workflows/approvals" || path === "/api/workflows/approvals/") {
      return mockResponse(getDB("orbit_approvals"));
    }

    if (path.includes("/resolve")) {
      const approvals = getDB("orbit_approvals");
      const id = path.split("/")[4];
      const appr = approvals.find((a) => a.id === id);
      if (appr) {
        appr.status = "RESOLVED";
        setDB("orbit_approvals", approvals);
      }
      return mockResponse({ success: true, message: "Approval resolved." });
    }

    // 8. Agent Workforce Registry
    if (path === "/api/agents" || path === "/api/agents/") {
      return mockResponse([
        { id: "agt_01", name: "Intake Agent", role: "Validation & Normalization", status: "ACTIVE", icon: "📥" },
        { id: "agt_02", name: "Lead Intelligence Agent", role: "AI Scoring & Talking Points", status: "ACTIVE", icon: "🎯" },
        { id: "agt_03", name: "Support Triage Agent", role: "Intent & Urgency Classification", status: "ACTIVE", icon: "⚡" },
        { id: "agt_04", name: "Knowledge Agent (RAG)", role: "Policy-Grounded Retrieval", status: "ACTIVE", icon: "📚" },
        { id: "agt_05", name: "Invoice Agent", role: "PDF Extraction & Deduplication", status: "ACTIVE", icon: "🧾" },
        { id: "agt_06", name: "Contract Agent", role: "Template-Governed MSA Drafting", status: "ACTIVE", icon: "📑" },
        { id: "agt_07", name: "Payment Verification Service", role: "Stripe HMAC-SHA256 Check", status: "ACTIVE", icon: "🔒" },
        { id: "agt_08", name: "Collaboration Agent", role: "Slack Channel Provisioning", status: "ACTIVE", icon: "💬" },
        { id: "agt_09", name: "Executive Reporting Agent", role: "Database Metric Compilation", status: "ACTIVE", icon: "📊" },
        { id: "agt_10", name: "Workflow Supervisor", role: "DAG Tracking & Bounded Retries", status: "ACTIVE", icon: "🛡️" }
      ]);
    }

    // 9. Integrations Status
    if (path.includes("/integrations")) {
      return mockResponse({
        openai: { name: "OpenAI", status: "DEMO_MODE", circuit_breaker: "CLOSED" },
        airtable: { name: "Airtable CRM", status: "DEMO_MODE", circuit_breaker: "CLOSED" },
        slack: { name: "Slack Alerts", status: "DEMO_MODE", circuit_breaker: "CLOSED" },
        email: { name: "Email Ingestion", status: "DEMO_MODE", circuit_breaker: "CLOSED", draft_only: true },
        sheets: { name: "Google Sheets", status: "DEMO_MODE", circuit_breaker: "CLOSED" },
        stripe: { name: "Stripe Verifier", status: "VERIFIED_LIVE_HMAC", circuit_breaker: "CLOSED" }
      });
    }

    // Default mock response
    return mockResponse({ success: true, message: "Handled by ORBIT In-Browser Simulator." });
  }

  function mockResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
      status: status,
      headers: { "Content-Type": "application/json" }
    });
  }

  // Update navbar mode badge on GitHub Pages
  window.addEventListener("DOMContentLoaded", () => {
    const badge = document.getElementById("globalModeBadge");
    if (badge && isGitHubPages) {
      badge.textContent = "GITHUB PAGES DEMO";
      badge.title = "Running interactive in-browser simulator. Backend server optional.";
      badge.style.background = "linear-gradient(135deg, #4F46E5, #2563EB)";
      badge.style.color = "#FFFFFF";
    }
  });
})();
