import hashlib
import hmac


def signature_message(timestamp: int, raw_body: bytes) -> bytes:
    return str(timestamp).encode() + b"." + raw_body


def sign_payload(secret: str, timestamp: int, raw_body: bytes) -> str:
    digest = hmac.new(
        key=secret.encode(),
        msg=signature_message(timestamp, raw_body),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def signatures_match(expected: str, received: str) -> bool:
    return hmac.compare_digest(expected, received)
