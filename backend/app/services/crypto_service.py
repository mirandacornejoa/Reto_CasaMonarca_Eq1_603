class CryptoService:
    """Placeholder de criptografía para sprint 2."""

    @staticmethod
    def build_sha256(content: bytes) -> str:
        import hashlib

        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def sign_document(*args, **kwargs):
        raise NotImplementedError("Firma digital será implementada en sprint 2")
