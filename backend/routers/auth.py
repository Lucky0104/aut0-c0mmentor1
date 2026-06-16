import os
import uuid
import secrets
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from datetime import datetime, timezone
from core import db as dbmod
from core import meta
from core.security import create_jwt, encrypt_token
from core.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

FRONTEND_URL = os.environ['FRONTEND_URL']

# in-memory state store (short-lived); ok for MVP
_state_cache: dict[str, dict] = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("/facebook/login")
async def fb_login():
    state = secrets.token_urlsafe(24)
    _state_cache[state] = {"created": _now()}
    return {"url": meta.login_dialog_url(state), "state": state}


@router.get("/facebook/callback")
async def fb_callback(code: str = Query(...), state: str = Query("")):
    # Exchange code
    try:
        tok = await meta.exchange_code_for_token(code)
        short_token = tok["access_token"]
        long_tok = await meta.get_long_lived_user_token(short_token)
        user_token = long_tok.get("access_token", short_token)
        me = await meta.get_me(user_token)
    except Exception as e:
        return RedirectResponse(f"{FRONTEND_URL}/login?error={str(e)[:120]}")

    fb_user_id = me["id"]
    name = me.get("name", "User")
    email = me.get("email", "")
    picture = (me.get("picture") or {}).get("data", {}).get("url", "")

    user = await dbmod.users.find_one({"fb_user_id": fb_user_id}, {"_id": 0})
    if not user:
        user = {
            "id": str(uuid.uuid4()),
            "fb_user_id": fb_user_id,
            "name": name,
            "email": email,
            "picture": picture,
            "fb_access_token": encrypt_token(user_token),
            "created_at": _now(),
        }
        await dbmod.users.insert_one(dict(user))
        # Create default tenant
        tenant_id = str(uuid.uuid4())
        await dbmod.tenants.insert_one({
            "id": tenant_id,
            "business_name": f"{name}'s Workspace",
            "owner_user_id": user["id"],
            "onboarded": False,
            "auto_reply_enabled": True,
            "industry": "",
            "website": "",
            "description": "",
            "brand_tone": "friendly professional",
            "reply_style": "concise",
            "support_email": email,
            "support_phone": "",
            "timezone": "UTC",
            "created_at": _now(),
        })
        await dbmod.members.insert_one({
            "user_id": user["id"], "tenant_id": tenant_id, "role": "owner", "created_at": _now()
        })
        active_tid = tenant_id
    else:
        # Update token
        await dbmod.users.update_one({"id": user["id"]}, {"$set": {
            "fb_access_token": encrypt_token(user_token),
            "name": name, "picture": picture,
        }})
        m = await dbmod.members.find_one({"user_id": user["id"]}, {"_id": 0})
        active_tid = m["tenant_id"] if m else None

    jwt_token = create_jwt(user["id"], active_tid)
    resp = RedirectResponse(f"{FRONTEND_URL}/oauth/success")
    resp.set_cookie(
        key="dashai_token", value=jwt_token, max_age=7 * 24 * 3600,
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp


@router.post("/logout")
async def logout():
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("dashai_token", path="/")
    return resp


@router.get("/me")
async def me(user=Depends(get_current_user)):
    m_list = await dbmod.members.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    tenants_out = []
    for m in m_list:
        t = await dbmod.tenants.find_one({"id": m["tenant_id"]}, {"_id": 0})
        if t:
            tenants_out.append({**t, "role": m["role"]})
    return {
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "picture": user.get("picture", "")},
        "tenants": tenants_out,
        "active_tenant_id": user.get("_tid"),
    }


@router.post("/switch/{tenant_id}")
async def switch_tenant(tenant_id: str, user=Depends(get_current_user)):
    from fastapi.responses import JSONResponse
    m = await dbmod.members.find_one({"user_id": user["id"], "tenant_id": tenant_id})
    if not m:
        raise HTTPException(403, "Not a member")
    new_token = create_jwt(user["id"], tenant_id)
    resp = JSONResponse({"ok": True, "tenant_id": tenant_id})
    resp.set_cookie(
        key="dashai_token", value=new_token, max_age=7 * 24 * 3600,
        httponly=True, secure=True, samesite="lax", path="/",
    )
    return resp
