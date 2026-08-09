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
            session = user_site.get_authenticated_session(
                telegram_id, acc["site_username"], acc["site_password"]
            )
            orders = user_site.get_orders(session, limit=20)
        except Exception as e:
            logger.warning(f"Order check failed for user {telegram_id}: {e}")
            continue

        # Kung wala pang kahit isang naka-track na order sa account na 'to,
        # ibig sabihin unang beses natin siya na-scan — i-store lahat bilang
        # baseline nang tahimik (para hindi mabomba ng notifications yung mga
        # dati nang order).
        is_first_scan = not db.has_tracked_orders(telegram_id)

        for o in orders:
            order_id = o["order_id"]
            new_status = o["status"]
            old_status = db.get_tracked_status(telegram_id, order_id)

            if old_status is None:
                db.set_tracked_status(telegram_id, order_id, new_status)
                if is_first_scan:
                    continue  # tahimik lang, baseline import
                # Bagong order na lumitaw pagkatapos ng unang scan — i-notify!
                try:
                    await context.bot.send_message(
                        chat_id=int(telegram_id),
                        text=(
                            f"🔔 New Order Detected!\n\n"
                            f"#{order_id} — {o['service_name'][:50]}\n"
                            f"Status: {new_status}"
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Couldn't notify user {telegram_id}: {e}")
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