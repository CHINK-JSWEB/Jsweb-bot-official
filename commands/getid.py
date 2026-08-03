from telegram.ext import MessageHandler, filters


async def handle_forward_check(update, context):
    """Debug/utility: kahit anong message sa DM ng bot, susubukang hanapin
    kung may forward info (galing sa channel/group) at ibabalik ang Chat ID."""
    if not update.message or update.effective_chat.type != "private":
        return

    msg = update.message
    chat = None

    # Bagong Bot API (7.0+): forward_origin
    origin = getattr(msg, "forward_origin", None)
    if origin is not None:
        chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)

    # Lumang Bot API: forward_from_chat
    if chat is None:
        chat = getattr(msg, "forward_from_chat", None)

    if chat:
        await msg.reply_text(
            f"📌 Channel/Group ID: `{chat.id}`\nName: {getattr(chat, 'title', 'N/A')}",
            parse_mode="Markdown"
        )
    else:
        # Debug fallback — para makita natin kung ano talaga ang natanggap
        await msg.reply_text(
            f"🔍 Debug: walang forward info na nakita.\n"
            f"forward_origin: {getattr(msg, 'forward_origin', 'wala')}\n"
            f"forward_from_chat: {getattr(msg, 'forward_from_chat', 'wala')}\n"
            f"forward_sender_name: {getattr(msg, 'forward_sender_name', 'wala')}"
        )