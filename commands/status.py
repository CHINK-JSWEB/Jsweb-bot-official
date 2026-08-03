import db


async def status(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /status <order_id>")
        return

    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Order ID must be a number.")
        return

    row = db.get_order(order_id)
    if not row or row["user_id"] != update.effective_user.id:
        await update.message.reply_text("Order not found.")
        return

    import smm_api
    try:
        panel_status = smm_api.get_order_status(row["panel_order_id"])
        db.update_order_status(order_id, panel_status.get("status", row["status"]))
        await update.message.reply_text(
            f"Order #{order_id}\n"
            f"Status: {panel_status.get('status')}\n"
            f"Start count: {panel_status.get('start_count')}\n"
            f"Remains: {panel_status.get('remains')}"
        )
    except smm_api.SMMApiError as e:
        await update.message.reply_text(
            f"Order #{order_id} — local status: {row['status']}\n"
            f"(Couldn't reach panel for live status: {e})"
        )