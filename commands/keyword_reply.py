import re

SITE_URL = "https://jsweboosting.site"
SITE_CAPTION = f"🌐 Visit our official site:\n{SITE_URL}"

FUNDS_CAPTION = (
    "🪷 for adding funds !\n"
    "━━━━━━━━━━━━━━\n\n"
    "gcash : 09555504904\n"
    "initials : J.S\n\n"
    "🍵 screen record\n"
    "transaction history\n"
    "and tg profile only !"
)

# ⚠️ Palitan mo ito ng totoong link ng channel mo pag ready na
RECO_CHANNEL_LINK = "https://t.me/+mmctZ7gyzaRkNDZl"
RECO_CAPTION = f"📢 Recommended services: [click here]({RECO_CHANNEL_LINK})"

_SITE_PATTERN = re.compile(r"\bsite\b", re.IGNORECASE)
_FUNDS_PATTERN = re.compile(r"\badd\s*funds?\b", re.IGNORECASE)
_RECO_PATTERN = re.compile(r"\breco\b", re.IGNORECASE)


async def handle_site_keyword(update, context):
    """Auto-replies with the site link kapag na-detect ang salitang 'site'."""
    if not update.message or not update.message.text:
        return
    if _SITE_PATTERN.search(update.message.text):
        await update.message.reply_text(
            SITE_CAPTION,
            reply_to_message_id=update.message.message_id,
        )


async def handle_addfunds_keyword(update, context):
    """Auto-replies with GCash details kapag na-detect ang 'add funds' (o 'add fund')."""
    if not update.message or not update.message.text:
        return
    if _FUNDS_PATTERN.search(update.message.text):
        await update.message.reply_text(
            FUNDS_CAPTION,
            reply_to_message_id=update.message.message_id,
        )


async def handle_reco_keyword(update, context):
    """Auto-replies with a clickable link papunta sa recommended services channel."""
    if not update.message or not update.message.text:
        return
    if _RECO_PATTERN.search(update.message.text):
        await update.message.reply_text(
            RECO_CAPTION,
            reply_to_message_id=update.message.message_id,
            parse_mode="Markdown",
        )