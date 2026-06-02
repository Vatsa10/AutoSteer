"""Simple Fernet encryption for workspace integration tokens."""

import base64
import hashlib

from cryptography.fernet import Fernet


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from any secret string."""
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plaintext: str, secret: str) -> str:
    if not secret:
        raise ValueError("INTEGRATION_ENCRYPTION_KEY is required to store tokens")
    f = Fernet(_derive_key(secret))
    return f.encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, secret: str) -> str:
    if not secret:
        raise ValueError("INTEGRATION_ENCRYPTION_KEY is required to read tokens")
    f = Fernet(_derive_key(secret))
    return f.decrypt(ciphertext.encode()).decode()
