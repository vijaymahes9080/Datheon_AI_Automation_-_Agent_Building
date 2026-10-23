import os
from PIL import Image, ImageDraw, ImageFont

def get_font(name, size):
    font_paths = {
        "bold": "C:/Windows/Fonts/segoeuib.ttf",
        "semibold": "C:/Windows/Fonts/seguisb.ttf",
        "regular": "C:/Windows/Fonts/segoeui.ttf",
    }
    path = font_paths.get(name, font_paths["regular"])
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_rounded_rect(draw, bbox, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def generate_linkedin_image():
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), color="#F8FAFC")
    draw = ImageDraw.Draw(img)

    # Top brand strip
    for x in range(W):
        # gradient from #4F46E5 (79, 70, 229) to #2563EB (37, 99, 235)
        ratio = x / W
        r = int(79 * (1 - ratio) + 37 * ratio)
        g = int(70 * (1 - ratio) + 99 * ratio)
        b = int(229 * (1 - ratio) + 235 * ratio)
        draw.line([(x, 0), (x, 7)], fill=(r, g, b))

    f_badge = get_font("semibold", 13)
    f_title = get_font("bold", 36)
    f_sub = get_font("regular", 16)
    f_card_title = get_font("bold", 15)
    f_card_sub = get_font("regular", 11)
    f_card_text = get_font("regular", 12)
    f_bold_label = get_font("bold", 12)
    f_big_metric = get_font("bold", 26)
    f_metric_lbl = get_font("bold", 11)
    f_metric_sub = get_font("regular", 11)

    # Category Pill
    draw_rounded_rect(draw, (60, 36, 310, 64), radius=14, fill="#EEF2FF", outline="#C7D2FE", width=1)
    draw.ellipse((74, 46, 84, 56), fill="#4F46E5")
    draw.text((92, 42), "AUTONOMOUS AI WORKFORCE", font=f_badge, fill="#4338CA")

    # Title & Subtitle
    draw.text((60, 78), "ORBIT AI Operations Studio", font=f_title, fill="#0F172A")
    draw.text((60, 126), "Bridging Autonomous Multi-Agent AI with Deterministic Enterprise Safety", font=f_sub, fill="#475569")

    # 4 Cards Grid
    card_w = 255
    card_h = 275
    y_cards = 165
    gap = 20
    x_start = 60

    modules = [
        {
            "title": "Lead Intelligence",
            "subtitle": "Revenue Routing Pipeline",
            "color": "#4F46E5",
            "badge_bg": "#EEF2FF",
            "badge_txt": "#4338CA",
            "stat_lbl": "SCORE",
            "stat_val": "85/100 (HIGH)",
            "bullets": [
                "• Web Form & Webhook Ingestion",
                "• AI Sales Talking Points",
                "• Airtable & Slack CRM Sync",
                "• SLA: 42ms (< 10s req.)"
            ],
            "footer": "✓ Project 1 Complete"
        },
        {
            "title": "Support Intelligence",
            "subtitle": "Email & Grounded RAG",
            "color": "#2563EB",
            "badge_bg": "#FEF3C7",
            "badge_txt": "#92400E",
            "stat_lbl": "SAFETY POLICY",
            "stat_val": "DRAFT-ONLY LOCKED",
            "bullets": [
                "• 8 Business Intent Classes",
                "• 100% Policy-Grounded RAG",
                "• Prompt Injection Defense",
                "• Escalation Gatekeeper"
            ],
            "footer": "✓ Project 2 Complete"
        },
        {
            "title": "Invoice Intelligence",
            "subtitle": "Financial Ops & Reconcile",
            "color": "#059669",
            "badge_bg": "#ECFDF5",
            "badge_txt": "#065F46",
            "stat_lbl": "ARITHMETIC AUDIT",
            "stat_val": "STRICT ±$0.05 CHECK",
            "bullets": [
                "• Secure PDF Text Extraction",
                "• Variance Flag & Export Lock",
                "• SHA-256 Duplicate Check",
                "• Google Sheets Staging"
            ],
            "footer": "✓ Project 3 Complete"
        },
        {
            "title": "Multi-Agent Ops",
            "subtitle": "Enterprise Orchestration",
            "color": "#7C3AED",
            "badge_bg": "#FAF5FF",
            "badge_txt": "#6B21A8",
            "stat_lbl": "STRIPE HMAC VERIFIER",
            "stat_val": "SHA-256 LIVE",
            "bullets": [
                "• Project ID Allocator",
                "• Template-Governed MSA",
                "• Slack Channel Provisioning",
                "• Weekly Executive Digest"
            ],
            "footer": "✓ Project 4 Complete"
        }
    ]

    for i, mod in enumerate(modules):
        cx = x_start + i * (card_w + gap)
        # Card Background
        draw_rounded_rect(draw, (cx, y_cards, cx + card_w, y_cards + card_h), radius=12, fill="#FFFFFF", outline="#E2E8F0", width=1)
        # Top color accent
        draw_rounded_rect(draw, (cx, y_cards, cx + card_w, y_cards + 5), radius=2, fill=mod["color"])

        # Title & Subtitle
        draw.text((cx + 18, y_cards + 18), mod["title"], font=f_card_title, fill="#0F172A")
        draw.text((cx + 18, y_cards + 38), mod["subtitle"], font=f_card_sub, fill="#64748B")

        # Metric box inside card
        draw_rounded_rect(draw, (cx + 18, y_cards + 56, cx + card_w - 18, y_cards + 98), radius=6, fill="#F8FAFC", outline="#F1F5F9", width=1)
        draw.text((cx + 26, y_cards + 62), mod["stat_lbl"], font=f_metric_lbl, fill="#64748B")
        draw.text((cx + 26, y_cards + 76), mod["stat_val"], font=f_bold_label, fill=mod["color"])

        # Bullets
        by = y_cards + 112
        for b in mod["bullets"]:
            draw.text((cx + 18, by), b, font=f_card_text, fill="#334155")
            by += 22

        # Card Footer Pill
        draw_rounded_rect(draw, (cx + 18, y_cards + card_h - 38, cx + card_w - 18, y_cards + card_h - 14), radius=6, fill=mod["badge_bg"], outline=None)
        draw.text((cx + 28, y_cards + card_h - 32), mod["footer"], font=f_bold_label, fill=mod["badge_txt"])

    # Bottom Metrics Bar
    bar_y = 470
    bar_h = 135
    draw_rounded_rect(draw, (60, bar_y, W - 60, bar_y + bar_h), radius=12, fill="#FFFFFF", outline="#E2E8F0", width=1)

    stats = [
        {"val": "19 / 19 Pass", "val_color": "#059669", "lbl": "AUTOMATED TEST SUITE", "sub": "100% Comprehensive Coverage"},
        {"val": "30 Commits", "val_color": "#4F46E5", "lbl": "CONVENTIONAL COMMITS", "sub": "Pushed to GitHub Branch main"},
        {"val": "10 Agents", "val_color": "#0F172A", "lbl": "WORKFORCE REGISTRY", "sub": "Explicit Roles & Zero Bypass"},
        {"val": "Python 3.12", "val_color": "#2563EB", "lbl": "FASTAPI ASYNC STACK", "sub": "SQLite WAL + Pydantic V2"}
    ]

    col_w = (W - 120) // 4
    for idx, st in enumerate(stats):
        bx = 60 + idx * col_w + 30
        draw.text((bx, bar_y + 22), st["lbl"], font=f_metric_lbl, fill="#64748B")
        draw.text((bx, bar_y + 44), st["val"], font=f_big_metric, fill=st["val_color"])
        draw.text((bx, bar_y + 82), st["sub"], font=f_metric_sub, fill="#64748B")

        if idx < 3:
            sep_x = 60 + (idx + 1) * col_w
            draw.line([(sep_x, bar_y + 20), (sep_x, bar_y + bar_h - 20)], fill="#F1F5F9", width=2)

    # Save to image.png and assets
    os.makedirs("assets", exist_ok=True)
    img.save("image.png", "PNG")
    img.save("assets/image.png", "PNG")
    img.save("assets/linkedin_banner.png", "PNG")
    print("Saved image.png, assets/image.png, and assets/linkedin_banner.png")

def generate_hero_image():
    W, H = 1200, 520
    img = Image.new("RGB", (W, H), color="#F8FAFC")
    draw = ImageDraw.Draw(img)

    f_badge = get_font("semibold", 12)
    f_title = get_font("bold", 42)
    f_sub = get_font("regular", 17)
    f_pill = get_font("semibold", 12)
    f_card_title = get_font("bold", 15)
    f_card_sub = get_font("regular", 11)
    f_card_text = get_font("regular", 11)
    f_bold_label = get_font("bold", 11)
    f_metric = get_font("bold", 16)

    # Category Pill
    draw_rounded_rect(draw, (60, 42, 330, 72), radius=15, fill="#EEF2FF", outline="#C7D2FE", width=1)
    draw.ellipse((76, 52, 86, 62), fill="#4F46E5")
    draw.text((94, 49), "ENTERPRISE AUTOMATION SUITE", font=f_badge, fill="#4338CA")

    # Title & Subtitle
    draw.text((60, 88), "ORBIT AI Operations Studio", font=f_title, fill="#0F172A")
    draw.text((60, 142), "Autonomous Workforce & Multi-System Business Automation for Agencies and eCommerce", font=f_sub, fill="#475569")

    # Feature Pill Tags
    pills = [
        ("• 4 Core Business Systems", "#10B981", 185),
        ("• 10 Agent Personas", "#6366F1", 160),
        ("• Draft-Only Email Shield", "#0284C7", 185),
        ("• Stripe HMAC Verified", "#F59E0B", 175)
    ]
    px = 60
    for txt, col, pw in pills:
        draw_rounded_rect(draw, (px, 178, px + pw, 208), radius=15, fill="#FFFFFF", outline="#E2E8F0", width=1)
        draw.text((px + 14, 185), txt, font=f_pill, fill="#334155")
        px += pw + 14

    # 4 Cards Row
    cards = [
        {
            "title": "Lead Intelligence",
            "sub": "Revenue Routing",
            "score_lbl": "SCORE: 85/100",
            "extra": "HIGH PRIORITY",
            "bullets": ["• Web Ingestion Form", "• AI Sales Talking Points", "• Airtable & Slack Sync", "• SLA: 42ms (< 10s SLA)"]
        },
        {
            "title": "Support Intelligence",
            "sub": "Email & Policy RAG",
            "score_lbl": "DRAFT-ONLY",
            "extra": "100% POLICY RAG",
            "bullets": ["• 8 Intent Classes", "• Prompt Injection Defense", "• Human Escalation Gate", "• Never Auto-Sends"]
        },
        {
            "title": "Invoice Intelligence",
            "sub": "Financial Ops & Audit",
            "score_lbl": "MATH CHECK",
            "extra": "STRICT ±$0.05",
            "bullets": ["• Secure PDF Text Parser", "• Arithmetic Audit Gate", "• SHA-256 Deduplication", "• Google Sheets Export"]
        },
        {
            "title": "Multi-Agent Ops",
            "sub": "Enterprise Orchestration",
            "score_lbl": "STRIPE HMAC",
            "extra": "SHA-256 VERIFIED",
            "bullets": ["• Project ID: PRJ-2026-001", "• Template-Governed MSA", "• Slack Channel Provision", "• Executive Reporting"]
        }
    ]

    card_w = 255
    card_h = 245
    y_cards = 235
    for i, c in enumerate(cards):
        cx = 60 + i * (card_w + 20)
        draw_rounded_rect(draw, (cx, y_cards, cx + card_w, y_cards + card_h), radius=12, fill="#FFFFFF", outline="#E2E8F0", width=1)
        draw.text((cx + 18, y_cards + 18), c["title"], font=f_card_title, fill="#0F172A")
        draw.text((cx + 18, y_cards + 36), c["sub"], font=f_card_sub, fill="#64748B")

        draw_rounded_rect(draw, (cx + 18, y_cards + 54, cx + card_w - 18, y_cards + 92), radius=6, fill="#F8FAFC", outline="#F1F5F9", width=1)
        draw.text((cx + 26, y_cards + 60), c["score_lbl"], font=f_bold_label, fill="#4F46E5")
        draw.text((cx + 26, y_cards + 74), c["extra"], font=f_metric, fill="#059669")

        by = y_cards + 104
        for b in c["bullets"]:
            draw.text((cx + 18, by), b, font=f_card_text, fill="#334155")
            by += 20

        draw_rounded_rect(draw, (cx + 18, y_cards + card_h - 34, cx + card_w - 18, y_cards + card_h - 12), radius=6, fill="#F1F5F9")
        draw.text((cx + 28, y_cards + card_h - 28), "Verified & Tested", font=f_bold_label, fill="#475569")

    img.save("assets/hero_light.png", "PNG")
    print("Saved assets/hero_light.png")

if __name__ == "__main__":
    generate_linkedin_image()
    generate_hero_image()
