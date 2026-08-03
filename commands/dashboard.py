import db
import dashboard_scraper
from commands.admin import is_admin
from config import CURRENCY


async def sync_dashboard(update, context):
    """Admin command: /syncdash — nagpapaalala na lang, hindi na direktang nag-s-scrape
    dito (dahil na-block ang Render IP ng site). Gamitin ang push_dashboard.py sa Termux."""
    if not is_admin(update.effective_user.id):
        return

    last_sync = db.dashboard_last_sync()
    count = db.dashboard_services_count()

    if last_sync:
        import datetime
        dt = datetime.datetime.fromtimestamp(last_sync).strftime("%B %d, %Y • %I:%M %p")
        status = f"📊 Current data: {count} services (last synced: {dt})"
    else:
        status = "📊 No data synced yet."

    await update.message.reply_text(
        f"{status}\n\n"
        f"⚠️ Please run this from Termux instead:\n"
        f"`python push_dashboard.py`\n\n"
        f"(Direct sync from here doesn't work reliably due to hosting IP restrictions.)",
        parse_mode="Markdown"
    )


async def find_dash(update, context):
    """Kahit sino: /finddash <panel_id> — hahanapin ang katumbas na local ID."""
    if not context.args:
        await update.message.reply_text("Usage: /finddash <panel_id>\nHal: /finddash 76")
        return

    panel_id = context.args[0]
    row = db.find_dashboard_by_panel_id(panel_id)

    if not row:
        count = db.dashboard_services_count()
        if count == 0:
            await update.message.reply_text(
                "Wala pang na-sync na data. Paki-run muna ng admin ang /syncdash."
            )
        else:
            await update.message.reply_text(
                f"Walang nakitang local ID para sa panel ID {panel_id}.\n"
                f"(Baka bago siya — pa-run mo sa admin ang /syncdash para ma-refresh.)"
            )
        return

    await update.message.reply_text(
        f"🔎 Panel ID `{panel_id}` → Local ID *{row['local_id']}*\n"
        f"📌 {row['name']}\n"
        f"💰 {CURRENCY}{row['price']:,.2f}",
        parse_mode="Markdown"
    )


async def search_dash(update, context):
    """Kahit sino: /searchdash <keyword> — maghanap by pangalan."""
    if not context.args:
        await update.message.reply_text("Usage: /searchdash <keyword>\nHal: /searchdash reaction")
        return

    keyword = " ".join(context.args)
    rows = db.search_dashboard_services(keyword)

    if not rows:
        await update.message.reply_text(f"Walang nakitang tugma para sa '{keyword}'.")
        return

    lines = [f"🔎 Resulta para sa '{keyword}':\n"]
    for r in rows:
        lines.append(
            f"Local ID {r['local_id']} (Panel ID {r['panel_id']}) — {r['name'][:50]}\n"
            f"   {CURRENCY}{r['price']:,.2f}"
        )
    await update.message.reply_text("\n".join(lines))