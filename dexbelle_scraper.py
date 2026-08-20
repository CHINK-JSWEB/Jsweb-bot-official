"""
Auto-scraper para sa dexbellesmm.com Recommended Services — kinukuha
diretso mula sa "Dexbelle AI" chat widget nila (bot.php endpoint).
"""

import re
import time
import requests

from config import DEXBELLE_URL, DEXBELLE_USERNAME, DEXBELLE_PASSWORD

PLATFORMS = ["Facebook", "Instagram", "TikTok", "YouTube", "Telegram"]

_ITEM_PATTERN = re.compile(
    r"ID\s+(\d+)\s*-\s*(.*?)\s*</b>.*?₱([\d,.]+)</span>",
    re.DOTALL,
)


class DexbelleError(Exception):
    pass


def _login() -> requests.Session:
    session = requests.Session()
    session.get(DEXBELLE_URL, timeout=20)
    resp = session.post(DEXBELLE_URL + "/", data={
        "username": DEXBELLE_USERNAME,
        "password": DEXBELLE_PASSWORD,
        "remember": "1",
    }, timeout=20)
    if "password" in resp.text.lower() and "balance" not in resp.text.lower():
        raise DexbelleError("Invalid DexBelle login credentials.")
    return session


def _reset_reco_menu(session: requests.Session):
    """Kinukuha muna yung platform selector — parang 'pagsisimula ulit' ng usapan,
    para hindi ma-stuck sa parehong platform state sa server."""
    session.post(
        DEXBELLE_URL + "/bot.php",
        json={"message": {"text": "Recommended"}, "action": "get_reco"},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


def _get_platform_items(session: requests.Session, platform: str) -> list[dict]:
    resp = session.post(
        DEXBELLE_URL + "/bot.php",
        json={"action": "reco_plat", "platform": platform},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    data = resp.json()
    html = data.get("html", "")

    items = []
    for m in _ITEM_PATTERN.finditer(html):
        panel_id, name, price = m.groups()
        items.append({
            "panel_id": panel_id,
            "name": name.strip(),
            "dexbelle_price": float(price.replace(",", "")),
        })
    return items


def get_all_recommended() -> dict:
    """Returns {platform_name: [items]} for lahat ng platforms."""
    session = _login()
    result = {}
    for platform in PLATFORMS:
        try:
            result[platform] = _get_platform_items(session, platform)
        except Exception:
            result[platform] = []
        time.sleep(1.5)
    return result