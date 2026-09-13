from __future__ import annotations

import hmac
from fastapi import Header, HTTPException, Request
from app.core.settings import settings

def require_operator(request: Request, x_control_token: str = Header(default="", alias="X-Control-Token")) -> bool:
    host = request.client.host if request.client else ""
    if settings.control_allow_local_unauth and host in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return True
    expected = settings.control_token
    if not expected or not x_control_token or not hmac.compare_digest(x_control_token, expected):
        raise HTTPException(status_code=401, detail="Operator authentication required")
    return True
