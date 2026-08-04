import db
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE

calc_flow = {}  # user_id -> "awaiting_id" o {"step": "qty", "local_id": ...}


async def calc_start(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return
    user_id = update.effective_user.id
    calc_flow[user_id] = "awaiting_id"
    await update.message.reply_text(
        "🧮 Price Calculator\n\nPlease type the Local Service ID (e.g. 1506):"
    )


async def handle_calc_text(update, context) -> bool:
    user_id = update.effective_user.id
    if user_id not in calc_flow:
        return False

    text = update.message.text.strip()
    state = calc_flow[user_id]

    if state == "awaiting_id":
        service = db.get_dashboard_service(text)
        if not service:
            await update.message.reply_text(
                f"❌ Local ID {text} not found. Please check the ID and try again, or /calc to restart."
            )
            calc_flow.pop(user_id, None)
            return True

        calc_flow[user_id] = {"step": "qty", "local_id": text, "name": service["name"], "price": service["price"]}
        await update.message.reply_text(
            f"📌 {service['name']}\n💰 Rate: {CURRENCY}{service['price']:,.2f} / 1000\n\n"
            f"Now type the quantity:"
        )
        return True

    if isinstance(state, dict) and state["step"] == "qty":
        try:
            quantity = int(text)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please type a valid number.")
            return True

        charge = round((state["price"] * quantity) / 1000, 2)
        calc_flow.pop(user_id, None)

        await update.message.reply_text(
            f"🧮 Price Calculation\n\n"
            f"📌 {state['name']}\n"
            f"🔢 Quantity: {quantity:,}\n"
            f"💰 Estimated Price: {CURRENCY}{charge:,.2f}\n\n"
            f"Type /calc to calculate again."
        )
        return True

    return False