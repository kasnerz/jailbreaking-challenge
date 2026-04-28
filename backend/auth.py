import hmac
import time

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from .config import settings

router = APIRouter()
# auto_error=False so we can return 401 (not 403) for missing credentials
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    password: str


@router.post("/auth/login")
async def login(request: Request, body: LoginRequest):
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(body.password.encode(), settings.APP_PASSWORD.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password"
        )

    payload = {
        "sub": "attendee",
        "exp": int(time.time()) + 8 * 3600,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"token": token}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = jwt.decode(
            credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"]
        )
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
