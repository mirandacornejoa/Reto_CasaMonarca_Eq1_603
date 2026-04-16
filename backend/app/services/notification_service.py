"""Servicio de notificaciones — correo electrónico y modo demo."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

_demo_activation_links: list[dict] = []
_demo_otp_codes: list[dict] = []


class NotificationService:
    # ------------------------------------------------------------------ #
    #  Enlace de activación                                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def send_activation_link(full_name: str, email: str, activation_link: str) -> bool:
        """Envía enlace de activación por email. Retorna True si se envió por SMTP."""
        if settings.smtp_configured:
            try:
                msg = EmailMessage()
                msg["Subject"] = "Activación de cuenta — Casa Monarca"
                msg["From"] = settings.SMTP_FROM_EMAIL
                msg["To"] = email
                msg.set_content(
                    f"Hola {full_name},\n\n"
                    f"Tu cuenta fue registrada en el gestor de identidades de Casa Monarca.\n"
                    f"Actívala aquí:\n{activation_link}\n\n"
                    f"Este enlace expira en {settings.ACTIVATION_TOKEN_EXPIRE_HOURS} horas.\n\n"
                    "Si no solicitaste esta cuenta, ignora este mensaje."
                )

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                    if settings.SMTP_USE_TLS:
                        smtp.starttls()
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    smtp.send_message(msg)

                logger.info("Correo de activación enviado a %s", email)
                return True

            except smtplib.SMTPAuthenticationError:
                logger.error(
                    "SMTP: Fallo de autenticación con %s. Verifique SMTP_USER y SMTP_PASSWORD.",
                    settings.SMTP_HOST,
                )
            except smtplib.SMTPConnectError:
                logger.error(
                    "SMTP: No fue posible conectar a %s:%s. Verifique SMTP_HOST y SMTP_PORT.",
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                )
            except smtplib.SMTPException as exc:
                logger.error("SMTP: Error al enviar correo de activación a %s: %s", email, exc)
            except OSError as exc:
                logger.error("SMTP: Error de red al conectar a %s:%s: %s", settings.SMTP_HOST, settings.SMTP_PORT, exc)

        # Modo demo: correo NO enviado
        logger.warning(
            "[MODO DEMO] Correo de activación NO enviado. "
            "SMTP no configurado o falló. Enlace guardado en memoria para demo. "
            "Destino: %s | Enlace: %s",
            email,
            activation_link,
        )
        _demo_activation_links.append(
            {
                "full_name": full_name,
                "email": email,
                "activation_link": activation_link,
            }
        )
        return False

    # ------------------------------------------------------------------ #
    #  Código OTP para 2FA                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def send_otp_code(full_name: str, email: str, otp_code: str) -> bool:
        """Envía código OTP de verificación por email. Retorna True si se envió por SMTP."""
        if settings.smtp_configured:
            try:
                msg = EmailMessage()
                msg["Subject"] = "Código de verificación — Casa Monarca"
                msg["From"] = settings.SMTP_FROM_EMAIL
                msg["To"] = email
                msg.set_content(
                    f"Hola {full_name},\n\n"
                    f"Tu código de verificación es:\n\n"
                    f"    {otp_code}\n\n"
                    f"Este código expira en {settings.OTP_EXPIRE_MINUTES} minutos.\n\n"
                    "Si no intentaste iniciar sesión, ignora este mensaje y "
                    "considera cambiar tu contraseña."
                )

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                    if settings.SMTP_USE_TLS:
                        smtp.starttls()
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    smtp.send_message(msg)

                logger.info("Código OTP enviado a %s", email)
                return True

            except smtplib.SMTPAuthenticationError:
                logger.error("SMTP: Fallo de autenticación al enviar OTP.")
            except smtplib.SMTPConnectError:
                logger.error("SMTP: No fue posible conectar para enviar OTP.")
            except smtplib.SMTPException as exc:
                logger.error("SMTP: Error al enviar OTP a %s: %s", email, exc)
            except OSError as exc:
                logger.error("SMTP: Error de red al enviar OTP: %s", exc)

        # Modo demo
        logger.warning(
            "[MODO DEMO] OTP NO enviado por correo. Código: %s | Destino: %s",
            otp_code,
            email,
        )
        _demo_otp_codes.append(
            {
                "full_name": full_name,
                "email": email,
                "otp_code": otp_code,
            }
        )
        return False

    # ------------------------------------------------------------------ #
    #  Endpoints de demo                                                   #
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_demo_activation_links() -> list[dict]:
        return _demo_activation_links[-50:]

    @staticmethod
    def get_demo_otp_codes() -> list[dict]:
        return _demo_otp_codes[-50:]
