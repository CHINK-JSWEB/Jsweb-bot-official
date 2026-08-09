from datetime import datetime
import db
import user_site
from commands.access import is_private, PRIVATE_ONLY_NOTICE

signin_flow = {}  # user_id -> "awaiting_username" o {"step": "password", "username": ..., "username_msg_id": ...}


async def signin_start(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return
    user_id = update.effective_user.id
    signin_flow[user_id] = "awaiting_username"
    await update.message.reply_text(
        "🔑 Sign in to your existing JSWEBOOSTING.SITE account.\n\n"
        "Please type your *username*:",
        parse_mode="Markdown"
    )


async def handle_signin_text(update, context) -> bool:
    user_id = update.effective_user.id
    if user_id not in signin_flow:
        return False

    text = update.message.text.strip()
    state = signin_flow[user_id]

    if state == "awaiting_username":
        signin_flow[user_id] = {"step": "password", "username": text}
        await update.message.reply_text("Now please type your *password*:", parse_mode="Markdown")
        return True

    if isinstance(state, dict) and state["step"] == "password":
        username = state["username"]
        password = text
        signin_flow.pop(user_id, None)

        # I-bura agad ang message na may password (security) — anuman ang mangyari
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except Exception:
            pass  # baka wala lang permission mag-delete (bihira sa DM, pero safe-guard)

        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id, text="🔄 Verifying your account..."
        )

        try:
            session = user_site.login(username, password)
            user_site.cache_session(user_id, session)
        except user_site.UserLoginError:
            await status_msg.edit_text("❌ Invalid username or password. Please try /signin again.")
            return True
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Couldn't reach the site: {e}")
            return True

        db.save_user_account(user_id, username, password)

        # Kunin ang lahat ng detalye para sa mas kumpletong welcome message
        try:
            balance = user_site.get_balance(session)
        except Exception:
            balance = None

        try:
            orders = user_site.get_orders(session, limit=100)
            total_orders = len(orders)
        except Exception:
            total_orders = None

        try:
            total_spend = user_site.get_total_spend(session)
        except Exception:
            total_spend = None

        timestamp = datetime.now().strftime("%B %d, %Y • %I:%M %p")

        lines = [f"🎉 Welcome back, Booster *{username}*!", ""]
        if balance is not None:
            lines.append(f"💰 Balance: ₱{balance:,.2f}")
        if total_orders is not None:
            lines.append(f"📦 Total Orders: {total_orders}")
        if total_spend is not None:
            lines.append(f"💵 Total Spend: ₱{total_spend:,.2f}")
        lines.append(f"🕐 Signed in: {timestamp}")

        await status_msg.edit_text("\n".join(lines), parse_mode="Markdown")
        return True

    return False