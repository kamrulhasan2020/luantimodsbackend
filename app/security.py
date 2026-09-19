import hashlib
import secrets

API_KEY_PREFIX = "lmb_"


def generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    # Keys are 256 bits of randomness, so a fast unsalted hash is fine and allows lookup by hash.
    return hashlib.sha256(api_key.encode()).hexdigest()
