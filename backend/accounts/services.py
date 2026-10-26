import secrets
import string

import pyotp
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import AuditLog


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["name"] = user.full_name
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def generate_totp_secret():
    return pyotp.random_base32()


def totp_uri(user):
    return pyotp.TOTP(user.totp_secret).provisioning_uri(
        name=user.phone, issuer_name="Konaté-Service-Gym"
    )


def verify_totp(user, code):
    if not user.totp_secret or not code:
        return False
    return pyotp.TOTP(user.totp_secret).verify(str(code).strip(), valid_window=1)


def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def log_action(user, action, target_type="", target_id="", detail=""):
    AuditLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        detail=detail[:400],
    )


def send_password_reset_code(user):
    """Le propriétaire réinitialise le mot de passe depuis l'administration.

    Aucun e-mail/SMS automatique : la demande est traitée via WhatsApp, comme
    prévu au cahier des charges. On renvoie donc un lien de contact.
    """
    from core.models import ShopSetting
    from core.whatsapp import whatsapp_link

    shop = ShopSetting.load()
    message = (
        f"Bonjour, je souhaite réinitialiser le mot de passe de mon compte "
        f"Konaté-Service-Gym ({user.phone_display})."
    )
    return whatsapp_link(shop.whatsapp_phone, message)
