import db
import user_site
from commands.access import is_private, PRIVATE_ONLY_NOTICE

signin_flow = {}  # user_id -> "awaiting_username" o {"step": "password", "username": ...}


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

        await update.message.reply_text("🔄 Verifying your account...")

        try:
            session = user_site.login(username, password)
        except user_site.UserLoginError:
            await update.message.reply_text(
                "❌ Invalid username or password. Please try /signin again."
            )
            return True
        except Exception as e:
            await update.message.reply_text(f"⚠️ Couldn't reach the site: {e}")
            return True

        db.save_user_account(user_id, username, password)

        try:
            balance = user_site.get_balance(session)
            balance_line = f"\n💰 Balance: ₱{balance:,.2f}"
        except Exception:
            balance_line = ""

        await update.message.reply_text(
            f"🎉 Welcome back, Booster *{username}*!{balance_line}",
            parse_mode="Markdown"
        )
        return True

    return False