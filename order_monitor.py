"""
Background checker — tumatakbo paminsan-minsan (job queue), tinitignan ang
order status ng lahat ng naka-sign-in na accounts, at nag-a-alert sa user
kapag may nagbago (lalo na kapag naging 'Completed').
"""

import logging
import db
import user_site

logger = logging.getLogger(__name__)


async def check_all_orders(context):
    accounts = db.get_all_user_accounts()
    if not accounts:
        return

    for acc in accounts:
        telegram_id = acc["telegram_id"]
        try:
            session = user_site.login(acc["site_username"], acc["site_password"])
            orders = user_site.get_orders(session, limit=20)
        except Exception as e:
            logger.warning(f"Order check failed for user {telegram_id}: {e}")
            continue

        for o in orders:
            order_id = o["order_id"]
            new_status = o["status"]
            old_status = db.get_tracked_status(telegram_id, order_id)

            if old_status is None:
                # Unang beses natin nakikita 'to — i-store lang, walang notify
                # (para hindi mabomba ng notifications yung mga lumang orders)
                db.set_tracked_status(telegram_id, order_id, new_status)
                continue

            if old_status != new_status:
                db.set_tracked_status(telegram_id, order_id, new_status)
                try:
                    await context.bot.send_message(
                        chat_id=int(telegram_id),
                        text=(
                            f"🔔 Order Update!\n\n"
                            f"#{order_id} — {o['service_name'][:50]}\n"
                            f"Status: {old_status} → {new_status}"
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Couldn't notify user {telegram_id}: {e}")