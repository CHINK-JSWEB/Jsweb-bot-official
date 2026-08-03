import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import db
from config import BOT_TOKEN

from commands.start import start
from commands.balance import balance
from commands.services import services
from commands.order import order
from commands.status import status
from commands.history import history
from commands.deposit import deposit, handle_photo
from commands.admin import pending, approve, reject, broadcast, deposit_callback
from commands.menu import menu_callback, handle_menu_text
from commands.mapping import map_id, find_id, list_map
from commands.dashboard import sync_dashboard, find_dash, search_dash
from commands.keyword_reply import handle_site_keyword, handle_addfunds_keyword, handle_reco_keyword
from commands.signin import signin_start
from commands.reco import reco_start
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"JSWEB bot is running.")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands (typing still works kung gusto)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("services", services))
    app.add_handler(CommandHandler("order", order))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Admin commands
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("map", map_id))
    app.add_handler(CommandHandler("maplist", list_map))
    app.add_handler(CommandHandler("findid", find_id))
    app.add_handler(CommandHandler("syncdash", sync_dashboard))
    app.add_handler(CommandHandler("finddash", find_dash))
    app.add_handler(CommandHandler("searchdash", search_dash))
    app.add_handler(CommandHandler("reco", reco_start))
    app.add_handler(CommandHandler("signin", signin_start))
    app.add_handler(CallbackQueryHandler(deposit_callback, pattern=r"^dep_(approve|reject):"))
    
    # Menu buttons
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^m:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_site_keyword), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_addfunds_keyword), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reco_keyword), group=3)
    threading.Thread(target=run_health_server, daemon=True).start()

    logger.info("JSWEB bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()