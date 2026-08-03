import db
import smm_api
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE


async def order(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return

    user_id = update.effective_user.id
    db.ensure_user(user_id, update.effective_user.username)

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /order <service_id> <link> <quantity>"
        )
        return

    service_id, link, qty_str = context.args[0], context.args[1], context.args[2]
    try:
        quantity = int(qty_str)
    except ValueError:
        await update.message.reply_text("Quantity must be a number.")
        return

    # Look up the service to compute the charge before placing the order
    try:
        all_services = smm_api.get_services()
        svc = next((s for s in all_services if str(s.get("service")) == service_id), None)
    except smm_api.SMMApiError as e:
        await update.message.reply_text(f"⚠️ Couldn't verify service: {e}")
        return

    if not svc:
        await update.message.reply_text("Service ID not found. Check /services.")
        return

    rate = float(svc.get("rate", 0))
    charge = round((rate * quantity) / 1000, 2)

    bal = db.get_balance(user_id)
    if bal < charge:
        await update.message.reply_text(
            f"Insufficient balance. Need {CURRENCY}{charge:,.2f}, "
            f"you have {CURRENCY}{bal:,.2f}. Use /deposit to top up."
        )
        return

    try:
        panel_order_id = smm_api.place_order(service_id, link, quantity)
    except smm_api.SMMApiError as e:
        await update.message.reply_text(f"⚠️ Order failed: {e}")
        return

    db.adjust_balance(user_id, -charge, "order", f"Order for service {service_id}")
    order_id = db.create_order(
        user_id, service_id, link, quantity, charge, panel_order_id, status="processing"
    )

    await update.message.reply_text(
        f"✅ Order placed!\n"
        f"Order ID: {order_id}\n"
        f"Panel Order ID: {panel_order_id}\n"
        f"Charged: {CURRENCY}{charge:,.2f}\n"
        f"Check progress with: /status {order_id}"
    )