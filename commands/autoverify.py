import hashlib
import db
import dashboard_scraper
from config import CURRENCY
from commands.access import is_private, PRIVATE_ONLY_NOTICE

addfunds_flow = {}  # user_id -> "awaiting_amount" o {"step": "video", "amount": ...}


async def addfunds_start(update, context):
    if not is_private(update):
        await update.message.reply_text(PRIVATE_ONLY_NOTICE)
        return

    user_id = update.effective_user.id
    account = db.get_user_account(user_id)
    if not account:
        await update.message.reply_text("🔒 Please /signin first so I know which account to credit.")
        return

    addfunds_flow[user_id] = "awaiting_amount"
    await update.message.reply_text(
        "💵 Auto Add Funds\n\nHow much did you send? Type the amount (numbers only):"
    )


async def handle_addfunds_text(update, context) -> bool:
    user_id = update.effective_user.id
    if user_id not in addfunds_flow:
        return False

    state = addfunds_flow[user_id]
    text = update.message.text.strip()

    if state == "awaiting_amount":
        try:
            amount = float(text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Please type a valid number, e.g. 350")
            return True

        addfunds_flow[user_id] = {"step": "video", "amount": amount}
        await update.message.reply_text(
            f"Got it — {CURRENCY}{amount:,.2f}.\n\n"
            f"📹 Now please send a screen recording of the GCash transaction "
            f"(video, not a photo)."
        )
        return True

    return True  # nasa "video" step na, hinihintay yung video mismo


async def handle_addfunds_video(update, context):
    user_id = update.effective_user.id
    state = addfunds_flow.get(user_id)

    if not isinstance(state, dict) or state.get("step") != "video":
        return  # walang naka-hintay na amount, ignore

    account = db.get_user_account(user_id)
    if not account:
        await update.message.reply_text("🔒 Please /signin first.")
        addfunds_flow.pop(user_id, None)
        return

    amount = state["amount"]
    addfunds_flow.pop(user_id, None)

    processing_msg = await update.message.reply_text("🔄 Processing your video, please wait...")

    video = update.message.video or update.message.video_note
    file = await context.bot.get_file(video.file_id)
    video_bytes = await file.download_as_bytearray()

    video_hash = hashlib.sha256(bytes(video_bytes)).hexdigest()

    if db.is_video_used(video_hash):
        await processing_msg.edit_text(
            "❌ This video has already been used before. "
            "If you believe this is a mistake, please contact Customer Service."
        )
        return

    try:
        dashboard_scraper.add_balance(
            account["site_username"], amount,
            note="Auto-verified deposit (video)"
        )
    except Exception as e:
        await processing_msg.edit_text(f"⚠️ Crediting failed: {e}\nPlease contact Customer Service.")
        return

    db.mark_video_used(video_hash, user_id, amount)

    await processing_msg.edit_text(
        f"✅ Verified & Credited!\n\n"
        f"💰 Amount: {CURRENCY}{amount:,.2f}\n\n"
        f"Your balance has been updated automatically."
    )