import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

_demo_activation_links: list[dict] = []


class NotificationService:
    @staticmethod
    def send_activation_link(full_name: str, email: str, activation_link: str) -> bool:
        if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
            msg = EmailMessage()
            msg["Subject"] = "Activación de cuenta"
            msg["From"] = settings.SMTP_FROM_EMAIL
            msg["To"] = email
            msg.set_content(
                (
                    f"Hola {full_name},\n\n"
                    f"Tu cuenta fue registrada. Actívala aquí:\n{activation_link}\n\n"
                    "Si no solicitaste esta cuenta, ignora este mensaje."
                )
            )

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                if settings.SMTP_USE_TLS:
                    smtp.starttls()
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                smtp.send_message(msg)
            return True

        logger.info("[DEMO] Enlace activación %s => %s", email, activation_link)
        _demo_activation_links.append(
            {
                "full_name": full_name,
                "email": email,
                "activation_link": activation_link,
            }
        )
        return False

    @staticmethod
    def get_demo_activation_links() -> list[dict]:
        return _demo_activation_links[-50:]
