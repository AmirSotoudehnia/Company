from fastapi import Header, HTTPException

from app.platform.tenancy import tenant_from_api_key


def require_tenant(x_tenant_key: str = Header(default="", alias="X-Tenant-Key")) -> dict:
    tenant = tenant_from_api_key(x_tenant_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid tenant key")
    return tenant
