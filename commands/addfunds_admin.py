from datetime import datetime
import db
import dashboard_scraper
from config import CURRENCY, ADDFUNDS_OWNER_IDS
from commands.access import ADMIN_ONLY_NOTICE


async def addfunds_command(update, context):
    if update.effective_user.id not in ADDFUNDS_OWNER_IDS:
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /addfunds <username> <amount>\nExample: /addfunds JSWEB 100"
        )
        return

    username = context.args[0]
    try:
        amount = float(context.args[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Amount must be a valid positive number.")
        return

    processing_msg = await update.message.reply_text("🔄 Processing...")

    admin_name = update.effective_user.first_name or update.effective_user.username or "Admin"

    try:
        dashboard_scraper.add_balance(
            username, amount,
            note=f"Manual admin credit via bot ({update.effective_user.id})"
        )
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ Failed to add funds: {e}")
        return

    new_balance = dashboard_scraper.get_latest_balance(username)
    previous_balance = (new_balance - amount) if new_balance is not None else None
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = ["✅ SUCCESS!", ""]
    lines.append(f"💳 Added: {CURRENCY}{amount:,.2f}")
    lines.append(f"💳 Total Credited: {CURRENCY}{amount:,.2f}")
    lines.append(f"👤 User: {username}")
    if previous_balance is not None:
        lines.append(f"💰 Previous Balance: {CURRENCY}{previous_balance:,.2f}")
    if new_balance is not None:
        lines.append(f"💵 New Balance: {CURRENCY}{new_balance:,.2f}")
    lines.append(f"🧑‍💼 Processed by: {admin_name}")
    lines.append(f"🕐 Time: {timestamp}")

    await processing_msg.edit_text("\n".join(lines))

    # Kung may naka-sign-in na Telegram user na gumagamit ng username na ito,
    # i-DM din natin siya para malaman niya
    for acc in db.get_all_user_accounts():
        if acc["site_username"].lower() == username.lower():
            try:
                await context.bot.send_message(
                    chat_id=int(acc["telegram_id"]),
                    text=f"💰 Your balance has been credited with {CURRENCY}{amount:,.2f} by an admin.\n"
                         f"New balance: {CURRENCY}{new_balance:,.2f}" if new_balance is not None else
                         f"💰 Your balance has been credited with {CURRENCY}{amount:,.2f} by an admin."
                )
            except Exception:
                pass
            break