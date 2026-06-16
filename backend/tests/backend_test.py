"""DashAI backend API tests - tenant/auth/kb/team/leads/comments/approvals/analytics/webhooks."""
import os
import sys
import json
import hmac
import hashlib
import uuid
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import pytest
import requests

sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from core import db as dbmod  # noqa
from core.security import create_jwt, encrypt_token  # noqa

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback to frontend .env
    with open("/app/frontend/.env") as f:
        for ln in f:
            if ln.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = ln.split("=", 1)[1].strip().rstrip("/")

FB_APP_SECRET = os.environ["FB_APP_SECRET"]
VERIFY_TOKEN = os.environ["FB_WEBHOOK_VERIFY_TOKEN"]

NOW = datetime.now(timezone.utc).isoformat()


def _seed_user_tenant(role="owner", business="TEST_Co"):
    uid = "TEST_u_" + uuid.uuid4().hex[:8]
    tid = "TEST_t_" + uuid.uuid4().hex[:8]

    async def _ins():
        await dbmod.users.insert_one({
            "id": uid, "fb_user_id": uid, "name": "T", "email": f"{uid}@t.com",
            "picture": "", "fb_access_token": encrypt_token("fake_fb_token"),
            "created_at": NOW,
        })
        await dbmod.tenants.insert_one({
            "id": tid, "business_name": business, "owner_user_id": uid,
            "onboarded": False, "auto_reply_enabled": True, "industry": "E-com",
            "website": "", "description": "", "brand_tone": "friendly",
            "reply_style": "concise", "support_email": "", "support_phone": "",
            "timezone": "UTC", "created_at": NOW,
        })
        await dbmod.members.insert_one({
            "user_id": uid, "tenant_id": tid, "role": role, "created_at": NOW,
        })
    asyncio.get_event_loop().run_until_complete(_ins())
    return uid, tid, create_jwt(uid, tid)


@pytest.fixture(scope="session")
def seeded_owner():
    uid, tid, jwt = _seed_user_tenant("owner")
    yield {"uid": uid, "tid": tid, "jwt": jwt}


@pytest.fixture(scope="session")
def seeded_viewer():
    uid, tid, jwt = _seed_user_tenant("viewer", "TEST_Viewer_Co")
    yield {"uid": uid, "tid": tid, "jwt": jwt}


@pytest.fixture(scope="session")
def seeded_second_user():
    uid, tid, jwt = _seed_user_tenant("owner", "TEST_Second_Co")
    yield {"uid": uid, "tid": tid, "jwt": jwt}


def H(jwt, tid=None):
    h = {"Authorization": f"Bearer {jwt}"}
    if tid:
        h["X-Tenant-Id"] = tid
    return h


# ---------- Public / health ----------
def test_health():
    r = requests.get(f"{BASE_URL}/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json() == {"ok": True}


# ---------- Facebook OAuth URL builder ----------
def test_fb_login_url():
    r = requests.get(f"{BASE_URL}/api/auth/facebook/login", timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert "url" in j and "state" in j and j["state"]
    parsed = urlparse(j["url"])
    assert "facebook.com" in parsed.netloc
    q = parse_qs(parsed.query)
    scope = q.get("scope", [""])[0]
    for s in ("pages_show_list", "pages_manage_engagement", "instagram_basic",
              "instagram_manage_comments", "business_management"):
        assert s in scope, f"missing scope {s}"
    assert q.get("state", [""])[0] == j["state"]


# ---------- Webhooks ----------
def test_webhook_verify_ok():
    r = requests.get(f"{BASE_URL}/api/webhooks/meta",
                     params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "challenge_xyz"},
                     timeout=10)
    assert r.status_code == 200
    assert r.text == "challenge_xyz"


def test_webhook_verify_wrong_token():
    r = requests.get(f"{BASE_URL}/api/webhooks/meta",
                     params={"hub.mode": "subscribe", "hub.verify_token": "WRONG", "hub.challenge": "x"},
                     timeout=10)
    assert r.status_code == 403


def test_webhook_post_missing_signature():
    r = requests.post(f"{BASE_URL}/api/webhooks/meta", data=b"{}", headers={"Content-Type": "application/json"}, timeout=10)
    assert r.status_code == 401


def test_webhook_post_valid_signature():
    body = json.dumps({"object": "page", "entry": []}).encode()
    sig = "sha256=" + hmac.new(FB_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    r = requests.post(f"{BASE_URL}/api/webhooks/meta", data=body,
                      headers={"Content-Type": "application/json", "x-hub-signature-256": sig}, timeout=10)
    assert r.status_code == 200


# ---------- Auth on protected endpoints ----------
@pytest.mark.parametrize("path", [
    "/api/tenant", "/api/pages", "/api/comments", "/api/approvals",
    "/api/leads", "/api/kb", "/api/team/members", "/api/analytics/overview",
])
def test_protected_endpoints_401_without_jwt(path):
    r = requests.get(f"{BASE_URL}{path}", timeout=10)
    assert r.status_code == 401, f"{path} -> {r.status_code}"


# ---------- /me ----------
def test_me_returns_user_and_tenants(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=H(seeded_owner["jwt"]), timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert j["user"]["id"] == seeded_owner["uid"]
    assert any(t["id"] == seeded_owner["tid"] and t["role"] == "owner" for t in j["tenants"])


# ---------- Tenant ----------
def test_get_and_patch_tenant(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/tenant", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert r.json()["id"] == seeded_owner["tid"]
    new_name = "TEST_Renamed_" + uuid.uuid4().hex[:4]
    r2 = requests.patch(f"{BASE_URL}/api/tenant", headers={**H(seeded_owner["jwt"], seeded_owner["tid"]), "Content-Type": "application/json"},
                        data=json.dumps({"business_name": new_name}), timeout=10)
    assert r2.status_code == 200
    assert r2.json()["business_name"] == new_name
    r3 = requests.get(f"{BASE_URL}/api/tenant", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r3.json()["business_name"] == new_name


def test_tenant_onboard_owner_only(seeded_owner, seeded_viewer):
    payload = {"business_name": "TEST_Onboard", "industry": "SaaS", "website": "https://x",
               "description": "d", "brand_tone": "friendly", "reply_style": "concise",
               "support_email": "s@x.com", "support_phone": "", "timezone": "UTC"}
    r = requests.post(f"{BASE_URL}/api/tenant/onboard", headers=H(seeded_owner["jwt"], seeded_owner["tid"]),
                      json=payload, timeout=10)
    assert r.status_code == 200
    assert r.json()["onboarded"] is True
    r2 = requests.post(f"{BASE_URL}/api/tenant/onboard", headers=H(seeded_viewer["jwt"], seeded_viewer["tid"]),
                       json=payload, timeout=10)
    assert r2.status_code == 403


# ---------- KB ----------
def test_kb_crud_and_rbac(seeded_owner, seeded_viewer):
    # viewer cannot POST
    r = requests.post(f"{BASE_URL}/api/kb", headers=H(seeded_viewer["jwt"], seeded_viewer["tid"]),
                      json={"kind": "faq", "title": "Q", "content": "A"}, timeout=10)
    assert r.status_code == 403

    r = requests.post(f"{BASE_URL}/api/kb", headers=H(seeded_owner["jwt"], seeded_owner["tid"]),
                      json={"kind": "faq", "title": "TEST_Q", "content": "TEST_A"}, timeout=10)
    assert r.status_code == 200
    entry = r.json()
    assert entry["title"] == "TEST_Q" and "id" in entry

    r = requests.get(f"{BASE_URL}/api/kb", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert any(e["id"] == entry["id"] for e in r.json())

    r = requests.delete(f"{BASE_URL}/api/kb/{entry['id']}", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200


# ---------- Tenant isolation ----------
def test_tenant_isolation(seeded_owner, seeded_second_user):
    # owner of tenant A trying to access tenant B
    r = requests.get(f"{BASE_URL}/api/kb", headers=H(seeded_owner["jwt"], seeded_second_user["tid"]), timeout=10)
    assert r.status_code == 403


# ---------- Team invites/accept ----------
def test_team_invite_accept_flow(seeded_owner, seeded_second_user):
    r = requests.post(f"{BASE_URL}/api/team/invite", headers=H(seeded_owner["jwt"], seeded_owner["tid"]),
                      json={"email": "second@example.com", "role": "moderator"}, timeout=10)
    assert r.status_code == 200, r.text
    inv = r.json()
    assert inv["token"] and inv["role"] == "moderator"

    r = requests.get(f"{BASE_URL}/api/team/invites", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert any(i["token"] == inv["token"] for i in r.json())

    # Second user accepts (no X-Tenant-Id needed since accept uses get_current_user)
    r = requests.post(f"{BASE_URL}/api/team/accept/{inv['token']}",
                      headers=H(seeded_second_user["jwt"]), timeout=10)
    assert r.status_code == 200
    assert r.json()["tenant_id"] == seeded_owner["tid"]

    r = requests.get(f"{BASE_URL}/api/team/members", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    members = r.json()
    assert len(members) >= 2


# ---------- Leads ----------
def test_leads_list_and_patch_404(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/leads", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    r2 = requests.patch(f"{BASE_URL}/api/leads/nonexistent_id?status=qualified",
                        headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r2.status_code == 404


# ---------- Comments ----------
def test_comments_filter_no_crash(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/comments?sentiment=positive",
                     headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Approvals ----------
def test_approvals_list_and_404(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/approvals", headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    r2 = requests.post(f"{BASE_URL}/api/approvals/nonexistent/action",
                       headers=H(seeded_owner["jwt"], seeded_owner["tid"]),
                       json={"action": "approve"}, timeout=10)
    assert r2.status_code == 404


# ---------- Analytics ----------
def test_analytics_overview_keys(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/analytics/overview",
                     headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    j = r.json()
    for k in ("total_comments_today", "ai_replies_today", "pending_approvals",
              "negative_comments", "total_leads", "pages_connected", "instagram_connected"):
        assert k in j, f"missing key {k}"
        assert isinstance(j[k], int)


def test_analytics_sentiment_trend(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/analytics/sentiment-trend?days=7",
                     headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    j = r.json()
    assert isinstance(j, list) and len(j) == 7
    for d in j:
        assert {"date", "positive", "neutral", "negative"}.issubset(d.keys())


def test_analytics_categories(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/analytics/categories",
                     headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=10)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Pages discover (graceful Meta error) ----------
def test_pages_discover_meta_error_502(seeded_owner):
    r = requests.get(f"{BASE_URL}/api/pages/discover",
                     headers=H(seeded_owner["jwt"], seeded_owner["tid"]), timeout=30)
    # Expected: 502 because the fake FB token will fail at Meta. Should not be 500.
    assert r.status_code == 502, f"got {r.status_code}: {r.text}"
