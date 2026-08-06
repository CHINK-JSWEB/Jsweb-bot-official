import db
from commands.admin import is_admin


async def map_id(update, context):
    """Admin command: /map <panel_id_or_range> <local_id_or_range> [name...]"""
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/map 76 1506 FB Reacts\n"
            "/map 76-82 1506-1512 FB Reacts   (range, maps 1-to-1 in order)"
        )
        return

    panel_arg, local_arg = context.args[0], context.args[1]
    name = " ".join(context.args[2:]) if len(context.args) > 2 else ""

    # Single mapping (no dash)
    if "-" not in panel_arg and "-" not in local_arg:
        db.add_mapping(panel_arg, local_arg, name)
        await update.message.reply_text(f"✅ Mapped panel ID {panel_arg} → local ID {local_arg}")
        return

    # Range mapping, e.g. 76-82 -> 1506-1512
    try:
        p_start, p_end = [int(x) for x in panel_arg.split("-")]
        l_start, l_end = [int(x) for x in local_arg.split("-")]
    except ValueError:
        await update.message.reply_text("Range format dapat: 76-82 1506-1512")
        return

    if (p_end - p_start) != (l_end - l_start):
        await update.message.reply_text(
            f"⚠️ Hindi pantay ang bilang ng IDs sa dalawang range "
            f"({p_end - p_start + 1} vs {l_end - l_start + 1}). Paki-check."
        )
        return

    count = 0
    for offset in range(p_end - p_start + 1):
        db.add_mapping(str(p_start + offset), str(l_start + offset), name)
        count += 1

    await update.message.reply_text(
        f"✅ Na-map ang {count} services: {p_start}-{p_end} → {l_start}-{l_end}"
        + (f" ({name})" if name else "")
    )


async def find_id(update, context):
    """Anyone can use: /findid <panel_id> — returns the matching local/dashboard ID."""
    if not context.args:
        await update.message.reply_text("Usage: /findid <panel_id>")
        return

    panel_id = context.args[0]
    row = db.get_local_id(panel_id)
    if not row:
        await update.message.reply_text(
            f"Walang naka-mapa na local ID para sa panel ID {panel_id}.\n"
            f"(Admin: gamitin ang /map para idagdag.)"
        )
        return

    name_part = f" — {row['name']}" if row["name"] else ""
    await update.message.reply_text(
        f"🔎 Panel ID {panel_id} → Dashboard ID *{row['local_id']}*{name_part}",
        parse_mode="Markdown"
    )


async def list_map(update, context):
    """Admin command: /maplist — shows all saved mappings."""
    if not is_admin(update.effective_user.id):
        from commands.access import ADMIN_ONLY_NOTICE
        await update.message.reply_text(ADMIN_ONLY_NOTICE)
        return
    rows = db.list_mappings()
    if not rows:
        await update.message.reply_text("Wala pang naka-save na mappings.")
        return
    lines = [f"{r['panel_id']} → {r['local_id']}" + (f" ({r['name']})" if r["name"] else "")
              for r in rows]
    await update.message.reply_text("📋 Service ID Mappings:\n" + "\n".join(lines))