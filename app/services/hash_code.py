import hmac
import hashlib
from app.config import settings

def hash_secret(secret: str) -> str:
    return hmac.new(settings.SECRET_BOT_POST_GENERATOR_KEY.encode(), secret.encode(), hashlib.sha256).hexdigest()

def check_secret(secret: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_secret(secret), hashed)
