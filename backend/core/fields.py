from django.conf import settings
from django.db import models


def _get_fernet():
    key = getattr(settings, 'ENCRYPTION_KEY', '')
    if not key:
        return None
    from cryptography.fernet import Fernet
    return Fernet(key.encode() if isinstance(key, str) else key)


class EncryptedCharField(models.CharField):
    """CharField that transparently encrypts at rest using Fernet symmetric encryption.

    Falls back to plaintext when ENCRYPTION_KEY is not set (dev/test environments).
    Encrypted values are longer than the originals — use max_length=500 or higher.
    """

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        f = _get_fernet()
        if f is None:
            return value
        try:
            return f.decrypt(value.encode()).decode()
        except Exception:
            return value

    def get_prep_value(self, value):
        if not value:
            return value
        f = _get_fernet()
        if f is None:
            return value
        return f.encrypt(value.encode()).decode()
