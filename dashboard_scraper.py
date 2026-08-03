"""
Scraper para sa jsweboosting.site admin panel.

Naglo-login gamit ang requests session, tapos kinukuha lahat ng service rows
mula sa Services page — LAHAT NG PAGES (naka-paginate ang listahan).
Bawat <tr> doon ay may data-id (local ID) at data-api-service (z-smm.com
panel ID) na magkatabi — kaya direkta na nating nakukuha ang tugma nila.
"""

import re
import requests
from bs4 import BeautifulSoup

from config import ADMIN_PANEL_URL, ADMIN_PANEL_USERNAME, ADMIN_PANEL_PASSWORD, ADMIN_PANEL_PIN


class DashboardScrapeError(Exception):
    pass


def _login() -> requests.Session:
    session = requests.Session()
    session.get(ADMIN_PANEL_URL, timeout=20)
    resp = session.post(ADMIN_PANEL_URL, data={
        "username": ADMIN_PANEL_USERNAME,
        "password": ADMIN_PANEL_PASSWORD,
        "admin_pin": ADMIN_PANEL_PIN,
        "remember": "1",
    }, timeout=20)

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


def scrape_services(max_pages: int = 30) -> list[dict]:
    """Returns list of {local_id, panel_id, name, provider, price} — LAHAT ng pages."""
    session = _login()
    all_results = []
    seen_local_ids = set()

    for page in range(1, max_pages + 1):
        if page == 1:
            url = ADMIN_PANEL_URL + "/services"
        else:
            url = ADMIN_PANEL_URL + f"/services/{page}"

        resp = session.get(url, timeout=30)
        page_rows = _parse_rows(resp.text)

        if not page_rows:
            # Walang laman ang page na ito — tapos na tayo
            break

        # Kung parehong laman ng nakaraang page (paulit-ulit), tigil na rin
        new_ids = {r["local_id"] for r in page_rows} - seen_local_ids
        if not new_ids:
            break

        for r in page_rows:
            if r["local_id"] not in seen_local_ids:
                all_results.append(r)
                seen_local_ids.add(r["local_id"])

    return all_results