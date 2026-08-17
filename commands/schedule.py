import json
import time
from datetime import datetime, timedelta

import db
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE

schedule_flow = {}  # user_id -> {"step": ..., "items": [...], "current": {...}}


async def schedule_start(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return

    user_id = update.effective_user.id
    account = db.get_user_account(user_id)
    if not account:
        await update.message.reply_text("🔒 Please /signin first so I know which account this is for.")
        return

    schedule_flow[user_id] = {"step": "service_id", "items": [], "current": {}}
    await update.message.reply_text(
        "📅 Schedule an Order\n\n"
        "Type the Local Service ID (e.g. 1507):"
    )


async def handle_schedule_text(update, context) -> bool:
    user_id = update.effective_user.id
    if user_id not in schedule_flow:
        return False

    state = schedule_flow[user_id]
    text = update.message.text.strip()
    step = state["step"]

    if step == "service_id":
        service = db.get_dashboard_service(text)
        if not service:
            await update.message.reply_text(f"❌ Local ID {text} not found. Try again, or /schedule to restart.")
            schedule_flow.pop(user_id, None)
            return True
        state["current"] = {"local_id": text, "name": service["name"], "price": service["price"]}
        state["step"] = "link"
        await update.message.reply_text(f"📌 {service['name']}\n\nNow type the link:")
        return True

    if step == "link":
        state["current"]["link"] = text
        state["step"] = "quantity"
        await update.message.reply_text("Now type the quantity:")
        return True

    if step == "quantity":
        try:
            qty = int(text)
            if qty <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please type a valid number.")
            return True

        state["current"]["quantity"] = qty
        charge = round((state["current"]["price"] * qty) / 1000, 2)
        state["current"]["charge"] = charge
        state["items"].append(state["current"])
        state["current"] = {}
        state["step"] = "add_more"

        total_so_far = sum(i["charge"] for i in state["items"])
        await update.message.reply_text(
            f"✅ Added to schedule. Est. charge: {CURRENCY}{charge:,.2f}\n"
            f"Running total: {CURRENCY}{total_so_far:,.2f}\n\n"
            f"Type another Local Service ID to add more (bulk), or type *done* to continue:",
            parse_mode="Markdown"
        )
        return True

    if step == "add_more":
        if text.lower() == "done":
            state["step"] = "time"
            await update.message.reply_text(
                "🕐 What time should I send this? (24-hour format, e.g. 14:30 for 2:30 PM)\n"
                "If that time already passed today, I'll schedule it for tomorrow."
            )
            return True

        service = db.get_dashboard_service(text)
        if not service:
            await update.message.reply_text(f"❌ Local ID {text} not found. Try again, or type 'done'.")
            return True
        state["current"] = {"local_id": text, "name": service["name"], "price": service["price"]}
        state["step"] = "link"
        await update.message.reply_text(f"📌 {service['name']}\n\nNow type the link:")
        return True

    if step == "time":
        try:
            hour, minute = map(int, text.split(":"))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please use 24-hour format, e.g. 14:30")
            return True

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        items = state["items"]
        schedule_flow.pop(user_id, None)

        db.create_scheduled_order(user_id, json.dumps(items), int(target.timestamp()))

        total = sum(i["charge"] for i in items)
        lines = [f"✅ Scheduled for {target.strftime('%B %d, %Y • %I:%M %p')}\n"]
        for i in items:
            lines.append(f"• {i['name'][:40]} x{i['quantity']} — {CURRENCY}{i['charge']:,.2f}")
        lines.append(f"\nEstimated total: {CURRENCY}{total:,.2f}")
        lines.append("\nI'll DM you the order details at that time so you can place them quickly.")

        await update.message.reply_text("\n".join(lines))
        return True

    return False