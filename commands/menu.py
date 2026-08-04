from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db
import user_site
from commands.access import PRIVATE_ONLY_NOTICE
from config import CUSTOMER_SERVICE_LINK


def private_menu_keyboard(is_admin_user=False):
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="m:mybalance"),
         InlineKeyboardButton("📦 Orders", callback_data="m:myorders")],
        [InlineKeyboardButton("💵 Total Spend", callback_data="m:totalspend")],
    ]
    if is_admin_user:
        keyboard.append([InlineKeyboardButton("📌 Reco Parser (Admin)", callback_data="m:reco")])
    return InlineKeyboardMarkup(keyboard)


def group_menu_keyboard():
    from commands.keyword_reply import RECO_CHANNEL_LINK
    from config import RULES_LINK
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Sign-in", callback_data="m:signin"),
         InlineKeyboardButton("📌 Reco", url=RECO_CHANNEL_LINK)],
        [InlineKeyboardButton("💵 Add Funds", callback_data="m:addfunds"),
         InlineKeyboardButton("🎧 Customer Service", url=CUSTOMER_SERVICE_LINK)],
        [InlineKeyboardButton("📜 Rules/FAQ", url=RULES_LINK)],
    ])


def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="m:main")]])


async def show_main_menu(update, context, edit=False):
    from commands.admin import is_admin

    if edit:
        chat = update.callback_query.message.chat
        user_id = update.callback_query.from_user.id
    else:
        chat = update.effective_chat
        user_id = update.effective_user.id

    if chat.type == "private":
        text = "🏠 *JSWEB Boosting Service*\n\nChoose an option below:"
        markup = private_menu_keyboard(is_admin(user_id))
    else:
        text = "🏠 *JSWEB Boosting Service*\n\nTap an option below:"
        markup = group_menu_keyboard()

    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def menu_callback(update, context):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    chat_type = update.effective_chat.type

    if data == "m:signin":
        await query.answer(PRIVATE_ONLY_NOTICE, show_alert=True)
        return

    personal_prefixes = ("m:mybalance", "m:myorders", "m:totalspend")
    if chat_type != "private" and any(data == p for p in personal_prefixes):
        await query.answer(PRIVATE_ONLY_NOTICE, show_alert=True)
        return

    await query.answer()
    db.ensure_user(user_id, query.from_user.username)

    if data == "m:main":
        from commands.reco import reco_flow
        reco_flow.discard(user_id)
        await show_main_menu(update, context, edit=True)
        return

    if data == "m:reco":
        from commands.admin import is_admin
        from commands.reco import reco_flow
        if not is_admin(user_id):
            await query.answer("Admins only.", show_alert=True)
            return
        reco_flow.add(user_id)
        await query.edit_message_text(
            "📋 Please paste the full recommendation list now (send it in one message).",
            reply_markup=back_button()
        )
        return

    if data == "m:addfunds":
        from commands.keyword_reply import FUNDS_CAPTION
        await context.bot.send_message(chat_id=update.effective_chat.id, text=FUNDS_CAPTION)
        return

    if data == "m:mybalance":
        account = db.get_user_account(user_id)
        if not account:
            await query.edit_message_text(
                "🔒 You haven't signed in yet. Use /signin to link your account.",
                reply_markup=back_button()
            )
            return
        try:
            session = user_site.login(account["site_username"], account["site_password"])
            balance = user_site.get_balance(session)
            await query.edit_message_text(f"💰 Balance: ₱{balance:,.2f}", reply_markup=back_button())
        except Exception as e:
            await query.edit_message_text(f"⚠️ Couldn't fetch balance: {e}", reply_markup=back_button())
        return

    if data == "m:myorders":
        account = db.get_user_account(user_id)
        if not account:
            await query.edit_message_text(
                "🔒 You haven't signed in yet. Use /signin to link your account.",
                reply_markup=back_button()
            )
            return
        try:
            session = user_site.login(account["site_username"], account["site_password"])
            orders = user_site.get_orders(session, limit=10)
        except Exception as e:
            await query.edit_message_text(f"⚠️ Couldn't fetch orders: {e}", reply_markup=back_button())
            return
        if not orders:
            await query.edit_message_text("No orders found.", reply_markup=back_button())
            return
        lines = ["📦 *Recent Orders*\n"]
        for o in orders[:10]:
            lines.append(f"#{o['order_id']} — {o['service_name'][:40]}\n   ₱{o['charge']:,.2f} — {o['status']}")
        await query.edit_message_text("\n".join(lines), reply_markup=back_button(), parse_mode="Markdown")
        return

    if data == "m:totalspend":
        account = db.get_user_account(user_id)
        if not account:
            await query.edit_message_text(
                "🔒 You haven't signed in yet. Use /signin to link your account.",
                reply_markup=back_button()
            )
            return
        try:
            session = user_site.login(account["site_username"], account["site_password"])
            total = user_site.get_total_spend(session)
            await query.edit_message_text(f"💵 Total Spend: ₱{total:,.2f}", reply_markup=back_button())
        except Exception as e:
            await query.edit_message_text(f"⚠️ Couldn't compute total spend: {e}", reply_markup=back_button())
        return


async def handle_menu_text(update, context):
    from commands.signin import handle_signin_text
    if await handle_signin_text(update, context):
        return

    from commands.reco import handle_reco_text
    if await handle_reco_text(update, context):
        return