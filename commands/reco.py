import re
import unicodedata
from datetime import datetime
import db
from commands.admin import is_admin
from config import RECO_CHANNEL_ID

reco_flow = set()  # user_ids na naghihintay mag-paste ng listahan

PLATFORM_ALIASES = {
    "facebook": "Facebook", "fb": "Facebook",
    "instagram": "Instagram", "ig": "Instagram",
    "tiktok": "Tiktok", "tt": "Tiktok",
    "telegram": "Telegram", "tg": "Telegram",
}
SUBCAT_KEYWORDS = ["followers", "views", "react", "shares", "share", "comments", "comment",
                    "group members", "members", "saves", "save", "likes", "like"]
SKIP_LINE_MARKERS = [
    "recommended services", "as of", "note:", "important reminder",
    "please note", "services may be busy", "try low", "bonus", "will not match"
]

PLATFORM_EMOJI = {"Facebook": "🔷", "Tiktok": "🎬", "Instagram": "🌈", "Telegram": "🚀"}

SUBCAT_EMOJI = [
    ("follower", "⭐"),
    ("view", "👁"),
    ("react", "❤️"),
    ("share", "🔄"),
    ("comment", "💬"),
    ("group member", "👥"),
    ("member", "👥"),
    ("save", "💾"),
    ("like", "🔥"),
]

# ── Font styles ──────────────────────────────────────────────
_BOLD_SANS = {}
for _i in range(26):
    _BOLD_SANS[chr(ord('A') + _i)] = chr(0x1D5D4 + _i)
    _BOLD_SANS[chr(ord('a') + _i)] = chr(0x1D5EE + _i)
for _i in range(10):
    _BOLD_SANS[chr(ord('0') + _i)] = chr(0x1D7EC + _i)

_ITALIC_BOLD = {}
for _i in range(26):
    _ITALIC_BOLD[chr(ord('A') + _i)] = chr(0x1D468 + _i)
    _ITALIC_BOLD[chr(ord('a') + _i)] = chr(0x1D482 + _i)


def bold_sans(text: str) -> str:
    """Bold Sans-Serif — para sa platform names (FACEBOOK, TIKTOK, atbp)."""
    return "".join(_BOLD_SANS.get(ch, ch) for ch in text)


def italic_bold(text: str) -> str:
    """Bold Italic — para sa sub-labels (Followers, Views, atbp), iba ang porma
    kaysa sa platform names para may contrast."""
    return "".join(_ITALIC_BOLD.get(ch, ch) for ch in text)


def _subcat_emoji(label: str) -> str:
    low = label.lower()
    for kw, emoji in SUBCAT_EMOJI:
        if kw in low:
            return emoji
    return "▫️"


def _is_noise(line: str) -> bool:
    low = line.lower()
    return any(m in low for m in SKIP_LINE_MARKERS)


def _strip_symbols(text: str) -> str:
    return re.sub(r'[^\w\s\-\(\)]', ' ', text).strip()


def _looks_like_platform_header(line: str):
    if any(ch.isdigit() for ch in line):
        return None
    clean = re.sub(r'[^\w\s]', ' ', line.lower()).strip()
    words = clean.split()
    if len(words) > 3:
        return None  # malamang hindi header kung mahaba masyado ang linya
    for word in words:
        if word in PLATFORM_ALIASES:
            return PLATFORM_ALIASES[word]
    return None


def _looks_like_subcat_header(line: str):
    if any(ch.isdigit() for ch in line):
        return None
    clean = line.lower()
    for kw in SUBCAT_KEYWORDS:
        if kw in clean:
            label = _strip_symbols(line)
            return label if label else kw.capitalize()
    return None


def _extract_ids(line: str):
    tokens = []
    working = line
    for m in re.finditer(r'\b(\d{1,7})\s*[-–]\s*(\d{1,7})\b', working):
        tokens.append(("range", int(m.group(1)), int(m.group(2))))
    working = re.sub(r'\b\d{1,7}\s*[-–]\s*\d{1,7}\b', ' ', working)
    for m in re.finditer(r'\b\d{1,6}\b', working):
        tokens.append(("single", int(m.group(0))))
    working = re.sub(r'\b\d{1,6}\b', ' ', working)
    note = re.sub(r'[•,\-–—]', ' ', working)
    note = re.sub(r'\s+', ' ', note).strip(' ()')
    return tokens, note


def _collapse_ids(ids: list[str]) -> str:
    nums = []
    for i in ids:
        try:
            nums.append(int(i))
        except ValueError:
            nums.append(None)
    parts = []
    i = 0
    while i < len(nums):
        if nums[i] is None:
            parts.append(ids[i])
            i += 1
            continue
        j = i
        while j + 1 < len(nums) and nums[j + 1] is not None and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(f"{nums[i]}–{nums[j]}" if j > i else str(nums[i]))
        i = j + 1
    return " • ".join(parts)


def _resolve_tokens(tokens):
    resolved = []
    missing = []
    for t in tokens:
        if t[0] == "single":
            panel_id = str(t[1])
            row = db.find_dashboard_by_panel_id(panel_id)
            if row:
                resolved.append(row["local_id"])
            else:
                missing.append(panel_id)
        else:
            _, s, e = t
            for pid in range(s, e + 1):
                row = db.find_dashboard_by_panel_id(str(pid))
                if row:
                    resolved.append(row["local_id"])
                else:
                    missing.append(str(pid))
    return resolved, missing


def parse_and_resolve(text: str) -> str:
    lines = [l.rstrip() for l in text.splitlines()]
    categories = {}
    order = []
    current_cat = None
    current_sub = None
    all_missing = []

    for raw_line in lines:
        line = unicodedata.normalize("NFKC", raw_line.strip())
        if not line or _is_noise(line):
            continue

        cat = _looks_like_platform_header(line)
        if cat:
            current_cat = cat
            current_sub = None
            if cat not in categories:
                categories[cat] = []
                order.append(cat)
            continue

        sub = _looks_like_subcat_header(line)
        if sub:
            current_sub = sub
            continue

        if not any(ch.isdigit() for ch in line) or current_cat is None:
            continue

        tokens, note = _extract_ids(line)
        if not tokens:
            continue

        resolved, missing = _resolve_tokens(tokens)
        all_missing.extend(missing)

        if resolved:
            display = _collapse_ids(resolved)
            if note:
                display += f" ({note})"
            categories[current_cat].append((current_sub or "", display))

    if not categories:
        return "⚠️ No IDs detected. Make sure the list includes platform headers (FACEBOOK/TIKTOK/etc.) and ID numbers."

    preferred_order = ["Facebook", "Instagram", "Tiktok", "Telegram"]
    order_sorted = [c for c in preferred_order if c in categories]
    order_sorted += [c for c in order if c not in order_sorted]

    timestamp = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    out = []
    out.append(f"✨🎀 {bold_sans('RECOMMENDED SERVICES')} 🎀✨")
    out.append(f"🕐「 {timestamp} 」")
    out.append("━━━━━━━━━━━━━━")
    out.append("")

    for cat in order_sorted:
        items = categories[cat]
        if not items:
            continue
        emoji = PLATFORM_EMOJI.get(cat, "🔹")
        out.append(f"{emoji} {bold_sans(cat.upper())}")
        for sub, display in items:
            sub_emoji = _subcat_emoji(sub) if sub else "▫️"
            sub_label = italic_bold(sub.title()) if sub else italic_bold("Services")
            out.append(f"{sub_emoji} {sub_label} → {display}")
        out.append("")
        out.append("━━━━━━━━━━━━━━")
        out.append("")

    while out and out[-1] in ("", "━━━━━━━━━━━━━━"):
        out.pop()

    if all_missing:
        uniq = sorted(set(all_missing), key=lambda x: int(x))
        out.append("")
        out.append(f"⚠️ Not yet added to the dashboard ({len(uniq)}): " + ", ".join(uniq[:30]))
        if len(uniq) > 30:
            out.append(f"...and {len(uniq) - 30} more")

    return "\n".join(out)


async def reco_start(update, context):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only. You are not the admin.")
        return
    reco_flow.add(update.effective_user.id)
    await update.message.reply_text(
        "📋 Please paste the full recommendation list now (send it in one message)."
    )


async def handle_reco_text(update, context) -> bool:
    user_id = update.effective_user.id
    if user_id not in reco_flow:
        return False
    if not is_admin(user_id):
        reco_flow.discard(user_id)
        return False
    reco_flow.discard(user_id)
    result = parse_and_resolve(update.message.text)

    for i in range(0, len(result), 3800):
        await update.message.reply_text(result[i:i + 3800])

    # I-bura muna ang mga lumang reco messages sa Channel (kung meron)
    old_ids_raw = db.get_meta("last_reco_channel_messages")
    if old_ids_raw:
        for old_id in old_ids_raw.split(","):
            try:
                await context.bot.delete_message(chat_id=RECO_CHANNEL_ID, message_id=int(old_id))
            except Exception:
                pass  # baka nabura na dati, o wala nang access — okay lang, tuloy pa rin

    new_ids = []
    try:
        for i in range(0, len(result), 3800):
            sent = await context.bot.send_message(
                chat_id=RECO_CHANNEL_ID, text=result[i:i + 3800]
            )
            new_ids.append(str(sent.message_id))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Couldn't post to channel: {e}")
        return True

    db.set_meta("last_reco_channel_messages", ",".join(new_ids))

    return True