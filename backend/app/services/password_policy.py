"""
Política de contraseñas — alineada con NIST 800-63b.

Reglas:
  - Longitud mínima: 12 caracteres
  - Longitud máxima: 128 caracteres (permitir passphrases)
  - Rechazar contraseñas en lista de las más comunes
  - Rechazar si la contraseña es igual al email del usuario
  - NO se fuerzan reglas arbitrarias de composición (1 mayúscula + 1 símbolo, etc.)
"""

import os
from typing import Optional, Tuple

MIN_LENGTH = 12
MAX_LENGTH = 128

# Cargar lista de contraseñas comunes (una vez al importar el módulo)
_COMMON_PASSWORDS: set = set()


def _load_common_passwords() -> set:
    """Carga la lista de contraseñas comunes desde archivo."""
    global _COMMON_PASSWORDS
    if _COMMON_PASSWORDS:
        return _COMMON_PASSWORDS

    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "common_passwords.txt")
    try:
        with open(data_path, encoding="utf-8") as f:
            _COMMON_PASSWORDS = {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        _COMMON_PASSWORDS = set()

    return _COMMON_PASSWORDS


class PasswordPolicy:
    """Valida contraseñas según política de seguridad."""

    @staticmethod
    def validate(password: str, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Valida una contraseña.

        Returns:
            (is_valid, error_message)  — error_message es "" si es válida.
        """
        if len(password) < MIN_LENGTH:
            return False, (
                f"La contraseña debe tener al menos {MIN_LENGTH} caracteres. "
                f"Tip: usa una frase memorable, por ejemplo: 'mi gato come tacos 42'"
            )

        if len(password) > MAX_LENGTH:
            return False, f"La contraseña no debe exceder {MAX_LENGTH} caracteres."

        # Rechazar si es igual al email
        if email and password.lower() == email.lower():
            return False, "La contraseña no puede ser igual a tu correo electrónico."

        # Rechazar si contiene el email como subcadena principal
        if email:
            email_local = email.split("@")[0].lower()
            if len(email_local) >= 4 and password.lower() == email_local:
                return False, "La contraseña no puede ser tu nombre de usuario del correo."

        # Rechazar contraseñas comunes
        common = _load_common_passwords()
        if common and password.lower() in common:
            return False, (
                "Esta contraseña es demasiado común y fácil de adivinar. "
                "Elige algo más único, como una frase personal."
            )

        return True, ""
