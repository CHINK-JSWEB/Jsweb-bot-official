"""
GCash screenshot verification: OCR (kunin ang amount/reference number)
at tamper detection (Error Level Analysis — palatandaan ng pag-edit).
"""

import re
import io
import requests
from PIL import Image, ImageChops

from config import OCR_API_KEY


class VerifyResult:
    def __init__(self):
        self.amount = None
        self.ref_no = None
        self.raw_text = ""
        self.tamper_suspected = False
        self.tamper_reason = ""
        self.ocr_success = False


def _ocr_image(image_bytes: bytes) -> str:
    resp = requests.post(
        "https://api.ocr.space/parse/image",
        files={"file": ("receipt.jpg", image_bytes)},
        data={"apikey": OCR_API_KEY, "language": "eng", "OCREngine": 2},
        timeout=30,
    )
    data = resp.json()
    if data.get("IsErroredOnProcessing"):
        return ""
    results = data.get("ParsedResults") or []
    if not results:
        return ""
    return results[0].get("ParsedText", "")


def _extract_amount(text: str):
    # Hahanapin natin ang "Total Amount Sent" o "Amount" na sinundan ng numero
    patterns = [
        r"Total Amount Sent[^\d]*([\d,]+\.\d{2})",
        r"Amount[^\d]*([\d,]+\.\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def _extract_ref(text: str):
    # GCash ref numbers: karaniwang 13 digits, minsan may spaces sa pagitan
    m = re.search(r"Ref\.?\s*No\.?\s*:?\s*([\d\s]{10,20})", text, re.IGNORECASE)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) >= 10:
            return digits
    # Fallback: hanapin lang ng kahit anong 13-digit na number
    m = re.search(r"\b(\d{13})\b", re.sub(r"\s", "", text))
    if m:
        return m.group(1)
    return None


def _check_tamper(image_bytes: bytes) -> tuple[bool, str]:
    """Simpleng Error Level Analysis (ELA) — hinahanap ang mga parte ng litrato
    na may kakaibang antas ng compression kumpara sa buong larawan (madalas
    palatandaan ito ng pag-edit/paste ng ibang elemento)."""
    try:
        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buffer = io.BytesIO()
        original.save(buffer, "JPEG", quality=90)
        buffer.seek(0)
        resaved = Image.open(buffer)

        diff = ImageChops.difference(original, resaved)
        extrema = diff.getextrema()
        max_diff = max(e[1] for e in extrema)

        # Mataas na max_diff = maraming pagkakaiba sa re-compression = posibleng
        # na-edit na parte. (Threshold na ito ay approximation lang, hindi 100%.)
        if max_diff > 60:
            return True, f"High compression inconsistency detected (score: {max_diff})"
        return False, ""
    except Exception as e:
        return False, ""  # kung nag-fail ang check, huwag nang i-flag (avoid false positives)


def verify_receipt(image_bytes: bytes) -> VerifyResult:
    result = VerifyResult()

    text = _ocr_image(image_bytes)
    result.raw_text = text

    if not text:
        return result

    result.amount = _extract_amount(text)
    result.ref_no = _extract_ref(text)
    result.ocr_success = result.amount is not None and result.ref_no is not None

    tamper, reason = _check_tamper(image_bytes)
    result.tamper_suspected = tamper
    result.tamper_reason = reason

    return result