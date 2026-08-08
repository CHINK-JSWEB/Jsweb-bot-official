"""
Scraper para sa jsweboosting.site admin panel.

Naglo-login gamit ang requests session, tapos kinukuha lahat ng service rows
mula sa Services page — LAHAT NG PAGES (naka-paginate ang listahan).
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup

from config import ADMIN_PANEL_URL, ADMIN_PANEL_USERNAME, ADMIN_PANEL_PASSWORD, ADMIN_PANEL_PIN

logger = logging.getLogger(__name__)


class DashboardScrapeError(Exception):
    pass


def _login() -> requests.Session:
    session = requests.Session()
    session.get(ADMIN_PANEL_URL, timeout=30)
    resp = session.post(ADMIN_PANEL_URL, data={
        "username": ADMIN_PANEL_USERNAME,
        "password": ADMIN_PANEL_PASSWORD,
        "admin_pin": ADMIN_PANEL_PIN,
        "remember": "1",
    }, timeout=30)

    if "Services" not in resp.text and "Admin Dashboard" not in resp.text:
        raise DashboardScrapeError("Hindi successful ang login sa admin panel.")

    return session


def _parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.find_all("tr", attrs={"data-id": True})
    results = []

    for row in rows:
        data_id = row.get("data-id", "")
        if not data_id.startswith("service-"):
            continue

        local_id = data_id.replace("service-", "")
        panel_id = row.get("data-api-service", "")
        name = row.get("data-service", "")
        provider = row.get("data-provider-name", "")

        price = 0.0
        rate_td = row.find("td", class_="service-block__rate")
        if rate_td:
            match = re.search(r"[\d,]+\.?\d*", rate_td.get_text())
            if match:
                price = float(match.group().replace(",", ""))

        results.append({
            "local_id": local_id,
            "panel_id": panel_id,
            "name": name,
            "provider": provider,
            "price": price,
        })

    return results


def _fetch_page(session: requests.Session, url: str, retries: int = 3) -> str:
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code == 200:
                return resp.text
            last_error = f"HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)
        logger.warning(f"Retry {attempt}/{retries} for {url} — {last_error}")
        time.sleep(2)
    raise DashboardScrapeError(f"Failed to fetch {url} after {retries} tries: {last_error}")


def scrape_services(max_pages: int = 30) -> list[dict]:
    """Returns list of {local_id, panel_id, name, provider, price} — LAHAT ng pages."""
    session = _login()
    all_results = []
    seen_local_ids = set()

    for page in range(1, max_pages + 1):
        url = ADMIN_PANEL_URL + "/services" if page == 1 else ADMIN_PANEL_URL + f"/services/{page}"

        html = _fetch_page(session, url)
        page_rows = _parse_rows(html)

        new_ids = {r["local_id"] for r in page_rows} - seen_local_ids
        first_id = page_rows[0]["local_id"] if page_rows else "N/A"
        last_id = page_rows[-1]["local_id"] if page_rows else "N/A"
        logger.info(
            f"Page {page}: {len(page_rows)} rows, {len(new_ids)} new, "
            f"first_id={first_id} last_id={last_id}, total so far: {len(all_results)}"
        )

        if not page_rows:
            logger.info(f"Page {page} was empty — stopping (reached the end).")
            break

        if not new_ids:
            logger.warning(f"Page {page} had no NEW ids (possibly stale/cached) — skipping but continuing.")
            time.sleep(3.5)
            continue

        for r in page_rows:
            if r["local_id"] not in seen_local_ids:
                all_results.append(r)
                seen_local_ids.add(r["local_id"])

        time.sleep(0.7)  # konting delay para hindi ma-flag bilang bot

    logger.info(f"Scraping done. Total services: {len(all_results)}")
    return all_results
    
def add_balance(username: str, amount: float, note: str = "Auto-verified deposit") -> dict:
    """Nagdadagdag ng balance sa isang totoong user account sa site, gamit
    ang parehong admin login. Ginagamit ito ng auto-verify deposit feature."""
    session = _login()
    resp = session.post(
        "https://jsweboosting.site/admin/payments/new-online",
        data={
            "username": username,
            "amount": str(amount),
            "add-remove": "add",
            "method": "1",
            "note": note,
        },
        timeout=30,
    )
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:500]}