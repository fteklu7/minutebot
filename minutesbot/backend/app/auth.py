import hmac

from fastapi import Header, HTTPException

from app.config import settings


def require_key(x_access_key: str | None = Header(default=None)):
    # single private key. Keeps a deployed copy from being used by strangers.
    if not settings.access_key:
        return
    if not x_access_key or not hmac.compare_digest(x_access_key, settings.access_key):
        raise HTTPException(status_code=401, detail="missing or wrong access key")
