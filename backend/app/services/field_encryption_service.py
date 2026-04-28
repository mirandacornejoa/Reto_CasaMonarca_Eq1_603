"""
Cifrado simétrico de campos sensibles a nivel aplicación.

Usa Fernet (AES-128-CBC + HMAC-SHA256) de la librería cryptography.
La clave maestra se lee de FIELD_ENCRYPTION_KEY en el entorno.

Generación de clave:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Si FIELD_ENCRYPTION_KEY no está configurado, el servicio lanza un error
al intentar cifrar/descifrar para no operar en claro silenciosamente.
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _load_fernet() -> Fernet:
    key = os.getenv("FIELD_ENCRYPTION_KEY", "")
    if not key:
        raise EnvironmentError(
            "FIELD_ENCRYPTION_KEY no está configurado. "
            "Genera una clave con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode())


class FieldEncryptionService:
    """Cifra y descifra valores de texto para columnas sensibles en BD."""

    # Prefijo para distinguir valores cifrados de valores en claro (migración gradual)
    _PREFIX = "enc:"

    @staticmethod
    def encrypt(plaintext: str) -> str:
        """Retorna string cifrado con prefijo 'enc:'."""
        f = _load_fernet()
        token = f.encrypt(plaintext.encode("utf-8"))
        return FieldEncryptionService._PREFIX + base64.urlsafe_b64encode(token).decode()

    @staticmethod
    def decrypt(ciphertext: str) -> str:
        """Descifra un valor. Acepta valores con o sin prefijo (migración gradual)."""
        if not ciphertext:
            return ciphertext
        if not ciphertext.startswith(FieldEncryptionService._PREFIX):
            # Valor en claro heredado — lo devuelve sin descifrar
            return ciphertext
        f = _load_fernet()
        raw = base64.urlsafe_b64decode(ciphertext[len(FieldEncryptionService._PREFIX):])
        try:
            return f.decrypt(raw).decode("utf-8")
        except InvalidToken:
            raise ValueError("No se pudo descifrar el campo. Verifica FIELD_ENCRYPTION_KEY.")

    @staticmethod
    def decrypt_or_none(ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None:
            return None
        return FieldEncryptionService.decrypt(ciphertext)

    @staticmethod
    def is_encrypted(value: str) -> bool:
        return bool(value and value.startswith(FieldEncryptionService._PREFIX))
