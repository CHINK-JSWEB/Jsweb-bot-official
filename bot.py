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
from commands.calculator import calc_start
from commands.leaderboard import leaderboard_command
from order_monitor import check_all_orders
from commands.help import help_command
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

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path != "/import_dashboard":
            self.send_response(404)
            self.end_headers()
            return

        import json
        import db
        from config import IMPORT_SECRET

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        if not IMPORT_SECRET or data.get("secret") != IMPORT_SECRET:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden")
            return

        rows = data.get("rows", [])
        db.sync_dashboard_services(rows)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"Imported {len(rows)} rows".encode())

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
    app.add_handler(CommandHandler("help", help_command))
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
    app.add_handler(CommandHandler("calc", calc_start))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CallbackQueryHandler(deposit_callback, pattern=r"^dep_(approve|reject):"))
    
    # Menu buttons
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^m:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_site_keyword), group=1)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_addfunds_keyword), group=2)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reco_keyword), group=3)
    threading.Thread(target=run_health_server, daemon=True).start()

    app.job_queue.run_repeating(check_all_orders, interval=600, first=60)

    logger.info("JSWEB bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()