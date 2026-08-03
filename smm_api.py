import requests

from config import SMM_API_URL, SMM_API_KEY


class SMMApiError(Exception):
    pass


def _call(payload: dict) -> dict:
    payload = {"key": SMM_API_KEY, **payload}
    try:
        resp = requests.post(SMM_API_URL, data=payload, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise SMMApiError(f"Network error calling SMM panel: {e}") from e
    except ValueError as e:
        raise SMMApiError(f"Invalid JSON from SMM panel: {e}") from e


def get_services() -> list[dict]:
    """Returns list of {service, name, type, rate, min, max, category}."""
    data = _call({"action": "services"})
    if isinstance(data, dict) and "error" in data:
        raise SMMApiError(data["error"])
    return data


def place_order(service_id: str, link: str, quantity: int) -> str:
    """Places an order on the panel. Returns the panel's order id."""
    data = _call({
        "action": "add",
        "service": service_id,
        "link": link,
        "quantity": quantity,
    })
    if "error" in data:
        raise SMMApiError(data["error"])
    return str(data["order"])


def get_order_status(panel_order_id: str) -> dict:
    """Returns {charge, start_count, status, remains, currency}."""
    data = _call({"action": "status", "order": panel_order_id})
    if "error" in data:
        raise SMMApiError(data["error"])
    return data


def get_panel_balance() -> dict:
    """Returns {balance, currency} — panel's own balance (yours as reseller)."""
    data = _call({"action": "balance"})
    if "error" in data:
        raise SMMApiError(data["error"])
    return data