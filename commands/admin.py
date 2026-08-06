import db
import logging
from config import ADMIN_IDS, CURRENCY

logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def pending(update, context):
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return
    rows = db.get_pending_deposits()
    if not rows:
        await update.message.reply_text("No pending deposits.")
        return
    lines = [f"#{r['deposit_id']} — user {r['user_id']} — {CURRENCY}{r['amount']:,.2f}"
              for r in rows]
    await update.message.reply_text("Pending deposits:\n" + "\n".join(lines))


async def approve(update, context):
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return
    await _resolve_deposit(update, context, int(context.args[0]), "approved")


async def reject(update, context):
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return
    await _resolve_deposit(update, context, int(context.args[0]), "rejected")


async def _resolve_deposit(update, context, deposit_id: int, decision: str):
    row = db.get_deposit(deposit_id)
    if not row:
        await update.message.reply_text("Deposit not found.")
        return
    if row["status"] != "pending":
        await update.message.reply_text(f"Deposit #{deposit_id} already {row['status']}.")
        return

    db.resolve_deposit(deposit_id, decision, update.effective_user.id)
    if decision == "approved":
        db.adjust_balance(row["user_id"], row["amount"], "deposit",
                           f"Deposit #{deposit_id} approved")

    await update.message.reply_text(f"Deposit #{deposit_id} {decision}.")
    try:
        await context.bot.send_message(
            chat_id=row["user_id"],
            text=f"Your deposit #{deposit_id} of {CURRENCY}{row['amount']:,.2f} "
                 f"was {decision}."
        )
    except Exception:
        logger.exception("Failed to notify user %s", row["user_id"])


async def deposit_callback(update, context):
    """Handles the Approve/Reject inline buttons on deposit notifications."""
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("Admins only.", show_alert=True)
        return

    action, dep_id_str = query.data.split(":")
    deposit_id = int(dep_id_str)
    decision = "approved" if action == "dep_approve" else "rejected"

    row = db.get_deposit(deposit_id)
    if not row or row["status"] != "pending":
        await query.edit_message_caption(caption=f"Deposit #{deposit_id} already handled.")
        return

    db.resolve_deposit(deposit_id, decision, query.from_user.id)
    if decision == "approved":
        db.adjust_balance(row["user_id"], row["amount"], "deposit",
                           f"Deposit #{deposit_id} approved")

    await query.edit_message_caption(
        caption=f"Deposit #{deposit_id} — {decision} by @{query.from_user.username}"
    )
    try:
        await context.bot.send_message(
            chat_id=row["user_id"],
            text=f"Your deposit #{deposit_id} of {CURRENCY}{row['amount']:,.2f} "
                 f"was {decision}."
        )
    except Exception:
        logger.exception("Failed to notify user %s", row["user_id"])


async def broadcast(update, context):
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return

    message = " ".join(context.args)
    with db.get_conn() as conn:
        user_ids = [r["user_id"] for r in conn.execute("SELECT user_id FROM users")]

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {message}")
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"Broadcast sent: {sent} ok, {failed} failed.")