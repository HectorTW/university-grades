import hashlib
import hmac
import secrets


def generate_digit_code(length: int = 6) -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def hash_otp(secret_key: str, code: str) -> str:
    return hmac.new(secret_key.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp(secret_key: str, code: str, digest: str) -> bool:
    return hmac.compare_digest(hash_otp(secret_key, code), digest)
