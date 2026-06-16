from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from core.deps import get_current_tenant, require_role
from core import db as dbmod

router = APIRouter(prefix="/leads", tags=["leads"])


def _now(): return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_leads(ctx=Depends(get_current_tenant)):
    tid = ctx["tenant"]["id"]
    items = await dbmod.leads.find({"tenant_id": tid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return items


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, status: str, ctx=Depends(require_role("owner", "admin"))):
    tid = ctx["tenant"]["id"]
    res = await dbmod.leads.update_one({"tenant_id": tid, "comment_id": lead_id}, {"$set": {"status": status, "updated_at": _now()}})
    if not res.matched_count:
        raise HTTPException(404, "Lead not found")
    return {"ok": True}
