import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

key_str = os.getenv("ENCRYPTION_KEY")
if not key_str:
    # Fallback to a generated key for local dev if not found
    key_str = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = key_str

_cipher_suite = Fernet(key_str.encode('utf-8'))

def encrypt_data(data: bytes | str) -> bytes:
    if isinstance(data, str):
        data = data.encode('utf-8')
    return _cipher_suite.encrypt(data)

def decrypt_data(token: bytes | str) -> bytes:
    if isinstance(token, str):
        token = token.encode('utf-8')
    return _cipher_suite.decrypt(token)

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
