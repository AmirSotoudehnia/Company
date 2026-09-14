from __future__ import annotations

import hashlib
import secrets
import re

from app.db import db


class TenantError(ValueError):
    pass


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "tenant"


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_tenant(name: str, slug: str | None = None) -> tuple[dict, str]:
    slug = _slugify(slug or name)
    raw_key = "ac_" + secrets.token_urlsafe(32)
    with db() as conn:
        cur = conn.execute("INSERT INTO tenants(name,slug) VALUES(?,?)", (name.strip(), slug))
        tenant_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO tenant_keys(tenant_id,key_hash,label) VALUES(?,?,?)",
            (tenant_id, hash_api_key(raw_key), "bootstrap"),
        )
        tenant = dict(conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone())
    return tenant, raw_key


def issue_api_key(tenant_id: int, label: str = "operator") -> tuple[dict, str]:
    raw_key = "ac_" + secrets.token_urlsafe(32)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO tenant_keys(tenant_id,key_hash,label) VALUES(?,?,?)",
            (tenant_id, hash_api_key(raw_key), label.strip()),
        )
        row = conn.execute("SELECT id,tenant_id,label,revoked,created_at FROM tenant_keys WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row), raw_key


def list_api_keys(tenant_id: int) -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT id,tenant_id,label,revoked,created_at FROM tenant_keys WHERE tenant_id=? ORDER BY id DESC", (tenant_id,)
        )]


def revoke_api_key(tenant_id: int, key_id: int) -> dict:
    with db() as conn:
        row = conn.execute("SELECT id FROM tenant_keys WHERE id=? AND tenant_id=?", (key_id, tenant_id)).fetchone()
        if not row:
            raise TenantError("API key not found")
        active = conn.execute("SELECT COUNT(*) FROM tenant_keys WHERE tenant_id=? AND revoked=0", (tenant_id,)).fetchone()[0]
        if active <= 1:
            raise TenantError("Cannot revoke the final active API key")
        conn.execute("UPDATE tenant_keys SET revoked=1 WHERE id=?", (key_id,))
        return dict(conn.execute("SELECT id,tenant_id,label,revoked,created_at FROM tenant_keys WHERE id=?", (key_id,)).fetchone())


def tenant_from_api_key(raw: str) -> dict | None:
    if not raw:
        return None
    with db() as conn:
        row = conn.execute(
            """SELECT t.* FROM tenant_keys k JOIN tenants t ON t.id=k.tenant_id
               WHERE k.key_hash=? AND k.revoked=0 AND t.status='active'""",
            (hash_api_key(raw),),
        ).fetchone()
        return dict(row) if row else None


def register_installation(tenant_id: int, installation_id: int, account_login: str, account_type: str = "User") -> dict:
    with db() as conn:
        existing = conn.execute("SELECT tenant_id FROM github_installations WHERE installation_id=?", (installation_id,)).fetchone()
        if existing and int(existing["tenant_id"]) != tenant_id:
            raise TenantError("GitHub installation is already assigned to another tenant")
        conn.execute(
            """INSERT INTO github_installations(installation_id,tenant_id,account_login,account_type,status)
               VALUES(?,?,?,?, 'active')
               ON CONFLICT(installation_id) DO UPDATE SET account_login=excluded.account_login, account_type=excluded.account_type, status='active'""",
            (installation_id, tenant_id, account_login, account_type),
        )
        return dict(conn.execute("SELECT * FROM github_installations WHERE installation_id=?", (installation_id,)).fetchone())


def register_repository(tenant_id: int, installation_id: int, owner: str, name: str, default_branch: str = "main", policy_json: str = "{}") -> dict:
    with db() as conn:
        inst = conn.execute(
            "SELECT 1 FROM github_installations WHERE installation_id=? AND tenant_id=? AND status='active'",
            (installation_id, tenant_id),
        ).fetchone()
        if not inst:
            raise TenantError("Installation does not belong to this tenant")
        full_name = f"{owner}/{name}"
        conn.execute(
            """INSERT INTO repositories(tenant_id,installation_id,owner,name,full_name,default_branch,policy_json)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(tenant_id,full_name) DO UPDATE SET installation_id=excluded.installation_id, default_branch=excluded.default_branch, policy_json=excluded.policy_json, enabled=1""",
            (tenant_id, installation_id, owner, name, full_name, default_branch, policy_json),
        )
        row = conn.execute("SELECT * FROM repositories WHERE tenant_id=? AND full_name=?", (tenant_id, full_name)).fetchone()
        return dict(row)


def get_repository(tenant_id: int, repository_id: int) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM repositories WHERE id=? AND tenant_id=? AND enabled=1",
            (repository_id, tenant_id),
        ).fetchone()
        if not row:
            raise TenantError("Repository not found for tenant")
        return dict(row)
