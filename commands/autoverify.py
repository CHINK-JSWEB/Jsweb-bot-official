import db
import gcash_verify
import dashboard_scraper
from config import CURRENCY, ADMIN_IDS


async def handle_gcash_screenshot(update, context):
    """Kapag may na-DM na screenshot sa bot, susubukan itong i-verify at
    i-auto-credit kung malinis lahat ng checks."""
    user_id = update.effective_user.id

    account = db.get_user_account(user_id)
    if not account:
        await update.message.reply_text(
            "🔒 Please /signin first so I know which account to credit."
        )
        return

    processing_msg = await update.message.reply_text("🔍 Verifying your receipt, please wait...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    result = gcash_verify.verify_receipt(bytes(image_bytes))

    # Hindi nabasa ng OCR — ipasa sa admin
    if not result.ocr_success:
        await processing_msg.edit_text(
            "⚠️ I couldn't clearly read the amount/reference number from this "
            "screenshot. Forwarding to admin for manual review."
        )
        await _notify_admin_manual(context, user_id, account["site_username"], result, image_bytes)
        return

    # Duplicate reference number — tanggihan agad
    if db.is_ref_used(result.ref_no):
        await processing_msg.edit_text(
            "❌ This receipt's reference number has already been used before. "
            "If you believe this is a mistake, please contact Customer Service."
        )
        return

    # May palatandaan ng pag-edit — ipasa sa admin
    if result.tamper_suspected:
        await processing_msg.edit_text(
            "⚠️ This screenshot needs manual verification. "
            "Forwarding to admin for review."
        )
        await _notify_admin_manual(context, user_id, account["site_username"], result, image_bytes)
        return

    # Malinis lahat — auto-credit!
    try:
        dashboard_scraper.add_balance(
            account["site_username"], result.amount,
            note=f"Auto-verified GCash deposit (Ref: {result.ref_no})"
        )
    except Exception as e:
        await processing_msg.edit_text(
            f"⚠️ Verification passed, but crediting failed: {e}\nForwarding to admin."
        )
        await _notify_admin_manual(context, user_id, account["site_username"], result, image_bytes)
        return

    db.mark_ref_used(result.ref_no, user_id, result.amount)

    await processing_msg.edit_text(
        f"✅ Verified & Credited!\n\n"
        f"💰 Amount: {CURRENCY}{result.amount:,.2f}\n"
        f"🧾 Ref No: {result.ref_no}\n\n"
        f"Your balance has been updated automatically."
    )


async def _notify_admin_manual(context, user_id, site_username, result, image_bytes):
    caption = (
        f"⚠️ Manual review needed\n"
        f"User: {site_username} (Telegram ID: {user_id})\n"
        f"Detected amount: {result.amount}\n"
        f"Detected ref: {result.ref_no}\n"
        f"Tamper flag: {result.tamper_suspected} {result.tamper_reason}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(chat_id=admin_id, photo=bytes(image_bytes), caption=caption)
        except Exception:
            pass