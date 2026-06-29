import os
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

key_str = os.getenv("ENCRYPTION_KEY")
if not key_str:
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    raise RuntimeError(f"ENCRYPTION_KEY not found in environment or {env_path}. Aborting to prevent data loss.")

_cipher_suite = Fernet(key_str.encode('utf-8'))


def get_cipher_suite() -> Fernet:
    """Get the cipher suite, allowing key reload if needed."""
    global _cipher_suite
    return _cipher_suite


def reload_cipher_suite() -> None:
    """Reload the cipher suite from environment (for key rotation)."""
    global _cipher_suite
    key_str = os.getenv("ENCRYPTION_KEY")
    if not key_str:
        raise RuntimeError("ENCRYPTION_KEY not found in environment")
    _cipher_suite = Fernet(key_str.encode('utf-8'))


def encrypt_data(data: bytes | str) -> bytes:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return get_cipher_suite().encrypt(data)


def decrypt_data(token: bytes | str) -> bytes:
    if isinstance(token, str):
        token = token.encode('utf-8')
    return get_cipher_suite().decrypt(token)


def encrypt_string(text: str) -> str:
    if not text:
        return text
    return encrypt_data(text).decode('utf-8')


def decrypt_string(token: str) -> str:
    if not token:
        return token
    try:
        return decrypt_data(token).decode('utf-8')
    except Exception:
        # Value was stored before encryption was active — return as-is
        return token