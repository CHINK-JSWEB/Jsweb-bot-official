import db
import user_site
from config import CURRENCY


async def _build_leaderboard_text() -> str:
    accounts = db.get_all_user_accounts()
    if not accounts:
        return "📊 No linked accounts yet. Users need to /signin first."

    results = []
    for acc in accounts:
        try:
            session = user_site.login(acc["site_username"], acc["site_password"])
            total = user_site.get_total_spend(session)
            results.append((acc["site_username"], total))
        except Exception:
            continue  # skip accounts na hindi ma-login (baka nagpalit ng password)

    if not results:
        return "📊 Couldn't fetch leaderboard data right now. Please try again later."

    results.sort(key=lambda x: x[1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 Top Spenders Leaderboard\n"]
    for i, (username, total) in enumerate(results[:10]):
        rank = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{rank} {username} — {CURRENCY}{total:,.2f}")

    return "\n".join(lines)


async def leaderboard_command(update, context):
    msg = await update.message.reply_text("🔄 Calculating leaderboard, please wait...")
    text = await _build_leaderboard_text()
    await msg.edit_text(text)


async def leaderboard_callback(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Calculating leaderboard, please wait...")
    text = await _build_leaderboard_text()

    from commands.menu import back_button
    await query.edit_message_text(text, reply_markup=back_button())