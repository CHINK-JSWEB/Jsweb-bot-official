"""
Login at pagkuha ng balance/orders ng regular users/boosters sa jsweboosting.site
(hindi admin panel — ito yung totoong dashboard login ng mga customer).
"""

import re
import requests
from bs4 import BeautifulSoup

from config import USER_SITE_URL


class UserLoginError(Exception):
    pass


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    session.get(USER_SITE_URL, timeout=20)
    resp = session.post(USER_SITE_URL + "/", data={
        "username": username,
        "password": password,
        "remember": "1",
    }, timeout=20)

    if "Login To" in resp.text and "balance" not in resp.text.lower():
        raise UserLoginError("Invalid username or password.")

    return session


def get_balance(session: requests.Session) -> float:
    resp = session.get(USER_SITE_URL + "/", timeout=20)
    soup = BeautifulSoup(resp.text, "lxml")
    bal_el = soup.find(class_="balance")
    if not bal_el:
        return 0.0
    match = re.search(r"[\d,]+\.?\d*", bal_el.get_text())
    return float(match.group().replace(",", "")) if match else 0.0


def get_orders(session: requests.Session, limit: int = 15) -> list[dict]:
    resp = session.get(USER_SITE_URL + "/orders", timeout=20)
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table")
    if not table:
        return []

    orders = []
    rows = table.find_all("tr")[1:]  # skip header row

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue

        span_id = cells[0].find("span", id=True)
        order_id = span_id.get_text(strip=True) if span_id else cells[0].get_text(strip=True)

        date = cells[1].get_text(strip=True)

        charge_text = cells[3].get_text(strip=True)
        charge_match = re.search(r"[\d,]+\.?\d*", charge_text)
        charge = float(charge_match.group().replace(",", "")) if charge_match else 0.0

        quantity = cells[5].get_text(strip=True)
        service_name = cells[6].get_text(strip=True).lstrip("-").strip()

        status_span = cells[7].find("span")
        status = status_span.get_text(strip=True) if status_span else cells[7].get_text(strip=True)

        orders.append({
            "order_id": order_id,
            "date": date,
            "charge": charge,
            "quantity": quantity,
            "service_name": service_name,
            "status": status,
        })

        if len(orders) >= limit:
            break

    return orders


def get_total_spend(session: requests.Session) -> float:
    resp = session.get(USER_SITE_URL + "/orders", timeout=20)
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table")
    if not table:
        return 0.0

    total = 0.0
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        match = re.search(r"[\d,]+\.?\d*", cells[3].get_text(strip=True))
        if match:
            total += float(match.group().replace(",", ""))

    return round(total, 2)