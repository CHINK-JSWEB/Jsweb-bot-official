from datetime import datetime
import db
import dexbelle_scraper
from config import CURRENCY, RECO_CHANNEL_ID
from commands.admin import is_admin

_BOLD_SANS = {}
for _i in range(26):
    _BOLD_SANS[chr(ord('A') + _i)] = chr(0x1D5D4 + _i)
    _BOLD_SANS[chr(ord('a') + _i)] = chr(0x1D5EE + _i)
for _i in range(10):
    _BOLD_SANS[chr(ord('0') + _i)] = chr(0x1D7EC + _i)


def bold_sans(text: str) -> str:
    return "".join(_BOLD_SANS.get(ch, ch) for ch in text)


PLATFORM_EMOJI = {"Facebook": "🔷", "Instagram": "🌈", "TikTok": "🎬", "YouTube": "▶️", "Telegram": "🚀"}


def _build_dexreco_text() -> str:
    data = dexbelle_scraper.get_all_recommended()
    timestamp = datetime.now().strftime("%B %d, %Y • %I:%M %p")

    out = []
    out.append(f"✨🎀 {bold_sans('DEXBELLE RECOMMENDED')} 🎀✨")
    out.append(f"🕐「 {timestamp} 」")
    out.append("━━━━━━━━━━━━━━")
    out.append("")

    missing = []

    for platform, items in data.items():
        if not items:
            continue
        emoji = PLATFORM_EMOJI.get(platform, "🔹")
        out.append(f"{emoji} {bold_sans(platform.upper())}")

        for item in items:
            row = db.find_dashboard_by_panel_id(item["panel_id"], provider_contains="dexbelle")
            if row:
                out.append(f"▫️ {row['local_id']} — {item['name'][:60]} ({CURRENCY}{row['price']:,.2f})")
            else:
                missing.append(item["panel_id"])

        out.append("")
        out.append("━━━━━━━━━━━━━━")
        out.append("")

    while out and out[-1] in ("", "━━━━━━━━━━━━━━"):
        out.pop()

    if missing:
        uniq = sorted(set(missing), key=lambda x: int(x))
        out.append("")
        out.append(f"⚠️ Not yet added to the dashboard ({len(uniq)}): " + ", ".join(uniq[:30]))

    return "\n".join(out)


async def dexreco_command(update, context):
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return

    msg = await update.message.reply_text("🔄 Fetching recommended services from DexBelleSMM...")

    try:
        result = _build_dexreco_text()
    except dexbelle_scraper.DexbelleError as e:
        await msg.edit_text(f"⚠️ {e}")
        return
    except Exception as e:
        await msg.edit_text(f"⚠️ Error: {e}")
        return

    for i in range(0, len(result), 3800):
        await update.message.reply_text(result[i:i + 3800])

    old_ids_raw = db.get_meta("last_dexreco_channel_messages")
    if old_ids_raw:
        for old_id in old_ids_raw.split(","):
            try:
                await context.bot.delete_message(chat_id=RECO_CHANNEL_ID, message_id=int(old_id))
            except Exception:
                pass

    new_ids = []
    try:
        for i in range(0, len(result), 3800):
            sent = await context.bot.send_message(chat_id=RECO_CHANNEL_ID, text=result[i:i + 3800])
            new_ids.append(str(sent.message_id))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Couldn't post to channel: {e}")
        return

    db.set_meta("last_dexreco_channel_messages", ",".join(new_ids))