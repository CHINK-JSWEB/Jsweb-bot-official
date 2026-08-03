import smm_api
from telegram.constants import ParseMode


async def services(update, context):
    try:
        items = smm_api.get_services()
    except smm_api.SMMApiError as e:
        await update.message.reply_text(f"⚠️ Couldn't fetch services: {e}")
        return

    if not items:
        await update.message.reply_text("No services found.")
        return

    lines = ["📋 *Available Services* (showing first 20)\n"]
    for s in items[:20]:
        lines.append(
            f"`{s.get('service')}` — {s.get('name')}\n"
            f"   Rate: ₱{s.get('rate')} / 1000 | "
            f"Min: {s.get('min')} Max: {s.get('max')}"
        )
    lines.append("\nOrder with: `/order <service_id> <link> <quantity>`")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN
    )