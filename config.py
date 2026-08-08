import os

# ── Telegram ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("JSWEB_BOT_TOKEN", "")
ADMIN_IDS = [int(x) for x in os.getenv("JSWEB_ADMIN_IDS", "").split(",") if x.strip()]

# ── SMM Panel API ─────────────────────────────────────────
SMM_API_URL = os.getenv("JSWEB_SMM_API_URL", "")
SMM_API_KEY = os.getenv("JSWEB_SMM_API_KEY", "")

# ── Database ──────────────────────────────────────────────
DB_PATH = os.getenv("JSWEB_DB_PATH", "jsweb.db")

# ── Misc ──────────────────────────────────────────────────
CURRENCY = "₱"

# ── Admin Panel ───────────────────────────────────────────
ADMIN_PANEL_URL = "https://jsweboosting.site/admin"
ADMIN_PANEL_USERNAME = os.getenv("JSWEB_PANEL_USER", "")
ADMIN_PANEL_PASSWORD = os.getenv("JSWEB_PANEL_PASS", "")
ADMIN_PANEL_PIN = os.getenv("JSWEB_PANEL_PIN", "")

# ── User/Booster Site Login ──────────────────────────────
USER_SITE_URL = "https://jsweboosting.site"

# ── Recommended Services Channel ─────────────────────────
RECO_CHANNEL_ID = int(os.getenv("JSWEB_RECO_CHANNEL_ID", "0"))

# ── Customer Service (Group button) ──────────────────────
CUSTOMER_SERVICE_LINK = os.getenv("JSWEB_CS_LINK", "https://t.me/")
# ── Import Secret (para sa Termux → Render dashboard sync) ──
IMPORT_SECRET = os.getenv("JSWEB_IMPORT_SECRET", "")
# ── Rules/FAQ (Group button) ─────────────────────────────
RULES_LINK = "https://t.me/+mICjKrlW9fliNTNl"
# ── OCR (GCash receipt verification) ─────────────────────
OCR_API_KEY = os.getenv("JSWEB_OCR_API_KEY", "")
# ── Auto-verify Safety Cap ────────────────────────────────
AUTO_APPROVE_MAX_AMOUNT = float(os.getenv("JSWEB_AUTO_APPROVE_MAX", "1000"))
# ── Add Funds — eksklusibong Owner IDs lang ─────────────
ADDFUNDS_OWNER_IDS = [8488933928, 7540290780]