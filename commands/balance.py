import db
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE


async def balance(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return
    user_id = update.effective_user.id
    db.ensure_user(user_id, update.effective_user.username)
    bal = db.get_balance(user_id)
    await update.message.reply_text(f"💰 Balance: {CURRENCY}{bal:,.2f}")