import json
import time
import db
from config import CURRENCY


async def check_scheduled_orders(context):
    now_ts = int(time.time())
    due = db.get_due_scheduled_orders(now_ts)

    for row in due:
        items = json.loads(row["items_json"])
        lines = ["⏰ It's time for your scheduled order(s)!\n"]
        total = 0.0
        for i in items:
            lines.append(
                f"📌 Local ID: {i['local_id']}\n"
                f"   {i['name'][:50]}\n"
                f"   Link: {i['link']}\n"
                f"   Quantity: {i['quantity']}\n"
                f"   Est. Charge: {CURRENCY}{i['charge']:,.2f}\n"
            )
            total += i['charge']
        lines.append(f"💰 Estimated Total: {CURRENCY}{total:,.2f}")
        lines.append("\n👉 Copy the details above and place the order(s) on the site.")

        try:
            await context.bot.send_message(chat_id=int(row["telegram_id"]), text="\n".join(lines))
        except Exception:
            pass

        db.mark_scheduled_order_sent(row["id"])