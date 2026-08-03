import db
from commands.menu import show_main_menu


async def start(update, context):
    user = update.effective_user
    db.ensure_user(user.id, user.username)
    await show_main_menu(update, context)