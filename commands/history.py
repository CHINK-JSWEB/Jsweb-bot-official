import db
from telegram.constants import ParseMode
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE


async def history(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return

    user_id = update.effective_user.id
    orders = db.get_orders(user_id, limit=5)
    txs = db.get_transactions(user_id, limit=5)

    lines = ["📜 *Recent Orders*"]
    if orders:
        for o in orders:
            lines.append(
                f"#{o['order_id']} — {o['service_id']} x{o['quantity']} "
                f"— {CURRENCY}{o['charge']:,.2f} — {o['status']}"
            )
    else:
        lines.append("No orders yet.")

    lines.append("\n💳 *Recent Transactions*")
    if txs:
        for t in txs:
            sign = "+" if t["amount"] >= 0 else ""
            lines.append(f"{t['type']}: {sign}{CURRENCY}{t['amount']:,.2f} — {t['note']}")
    else:
        lines.append("No transactions yet.")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)