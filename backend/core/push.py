"""Notifications : enregistrement in-app + envoi FCM best-effort.

Les jetons FCM sont fournis par l'application mobile. Sans clé serveur
configurée (FCM_LEGACY_KEY), la notification reste consultable dans l'API
(me/notifications), ce qui garantit le fonctionnement hors ligne.
"""
import json
import logging
import os
import urllib.error
import urllib.request

from core.models import Notification

logger = logging.getLogger(__name__)


def send_push(user, title, body, order=None):
    if user is None:
        return None
    notification = Notification.objects.create(user=user, title=title[:120], body=body[:400], order=order)
    key = os.environ.get("FCM_LEGACY_KEY", "")
    if not key:
        return notification
    tokens = list(user.device_tokens.values_list("token", flat=True))
    for token in tokens:
        payload = json.dumps(
            {"to": token, "notification": {"title": title, "body": body}, "priority": "high"}
        ).encode()
        request = urllib.request.Request(
            "https://fcm.googleapis.com/fcm/send",
            data=payload,
            headers={
                "Authorization": f"key={key}",
                "Content-Type": "application/json",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=5).read()
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.warning("Échec de l'envoi FCM : %s", exc)
    return notification


def notify_order_status(order, message=None):
    if not order.user_id:
        return None
    body = message or f"Votre commande {order.number} est maintenant : {order.get_status_display()}."
    return send_push(order.user, "Mise à jour de votre commande", body, order=order)
