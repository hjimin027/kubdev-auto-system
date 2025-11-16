from fastapi import Header, HTTPException
from typing import Optional

DEV_API_KEYS = {
    "admin-key-123": {"role": "admin", "user": {"id": 1, "name": "admin"}},
    "dev-key-456": {"role": "dev", "user": {"id": 2, "name": "dev"}},
    "test-key-789": {"role": "test", "user": {"id": 3, "name": "test"}},
}


async def get_current_user(authorization: Optional[str] = Header(None)):
    # Development convenience: if no Authorization, act as dev user
    if not authorization:
        return {"id": 2, "name": "dev", "role": "dev"}

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid auth scheme")

    info = DEV_API_KEYS.get(token)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = info["user"].copy()
    user["role"] = info["role"]
    return user

