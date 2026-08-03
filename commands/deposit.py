import db
from config import CURRENCY, ADMIN_IDS
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from commands.access import is_private, PRIVATE_ONLY_NOTICE

# Tracks kung sino ang nasa gitna ng deposit flow (naghihintay ng screenshot)
pending_deposit_amount = {}


async def deposit(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return

    user_id = update.effective_user.id
    db.ensure_user(user_id, update.effective_user.username)

    if not context.args:
        await update.message.reply_text("Usage: /deposit <amount>")
        return

    try:
        amount = float(context.args[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Enter a valid amount, e.g. /deposit 500")
        return

    pending_deposit_amount[user_id] = amount
    await update.message.reply_text(
        f"Got it — depositing {CURRENCY}{amount:,.2f}.\n"
        f"Please send a screenshot of your payment now as a photo."
    )


async def handle_photo(update, context):
    """Catches a screenshot after /deposit <amount> was called."""
    user_id = update.effective_user.id
    if user_id not in pending_deposit_amount:
        return  # not in a deposit flow, ignore

    amount = pending_deposit_amount.pop(user_id)
    file_id = update.message.photo[-1].file_id
    deposit_id = db.create_deposit(user_id, amount, file_id)

    await update.message.reply_text(
        f"📤 Deposit request #{deposit_id} for {CURRENCY}{amount:,.2f} submitted.\n"
        f"Waiting for admin approval."
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve", callback_data=f"dep_approve:{deposit_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"dep_reject:{deposit_id}"),
    ]])
    caption = (
        f"💵 New deposit request #{deposit_id}\n"
        f"User: @{update.effective_user.username or user_id} (id {user_id})\n"
        f"Amount: {CURRENCY}{amount:,.2f}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id, photo=file_id, caption=caption, reply_markup=keyboard
            )
        except Exception:
            pass