"""
Patakbuhin ito sa TERMUX lang (hindi ito deployed sa Render).
Nag-s-scrape ito ng dashboard services gamit ang totoong IP ng Termux mo
(hindi na-block, di gaya ng Render), tapos ipinapadala ang resulta papunta
sa live bot mo sa Render.
"""

import requests
import dashboard_scraper
from config import IMPORT_SECRET

RENDER_URL = "https://jsweb-bot-official.onrender.com/import_dashboard"

print("Scraping mula sa admin panel gamit ang Termux IP...")
rows = dashboard_scraper.scrape_services()
print(f"Nakuha: {len(rows)} services. Ipinapadala papunta sa Render...")

resp = requests.post(RENDER_URL, json={"secret": IMPORT_SECRET, "rows": rows}, timeout=60)
print("Status:", resp.status_code)
print("Response:", resp.text)