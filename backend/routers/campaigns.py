import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.deps import get_current_tenant, require_role
from core import db as dbmod
from core.ai import generate_campaign_ideas
from core.events import log_action

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_campaigns(ctx=Depends(get_current_tenant)):
    tid = ctx["tenant"]["id"]
    return await dbmod.campaigns.find({"tenant_id": tid}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/generate")
async def generate(ctx=Depends(require_role("owner", "admin"))):
    tid = ctx["tenant"]["id"]
    tenant = ctx["tenant"]
    kb = await dbmod.kb.find({"tenant_id": tid}, {"_id": 0}).to_list(50)
    kb_summary = "\n".join([f"- {e['title']}: {e['content'][:160]}" for e in kb]) or "(empty)"
    # Recent comment themes (top categories)
    pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 5},
    ]
    themes = [d["_id"] async for d in dbmod.comments.aggregate(pipeline) if d["_id"]]
    brand = {"name": tenant.get("business_name", ""), "industry": tenant.get("industry", ""), "tone": tenant.get("brand_tone", "")}
    try:
        result = await generate_campaign_ideas(brand, kb_summary, themes)
    except Exception as e:
        raise HTTPException(502, f"AI error: {e}")
    items = result.get("campaigns", []) if isinstance(result, dict) else []
    if not items:
        raise HTTPException(502, "AI returned no campaigns")
    docs = []
    for c in items:
        docs.append({
            "id": str(uuid.uuid4()), "tenant_id": tid, "created_at": _now(),
            "created_by": ctx["user"]["id"], "status": "draft", **c,
        })
    await dbmod.campaigns.insert_many([dict(d) for d in docs])
    await log_action(tid, ctx["user"]["id"], "campaigns.generated", "campaigns", {"count": len(docs)})
    return docs


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str, ctx=Depends(require_role("owner", "admin"))):
    tid = ctx["tenant"]["id"]
    res = await dbmod.campaigns.delete_one({"tenant_id": tid, "id": campaign_id})
    if not res.deleted_count:
        raise HTTPException(404, "Not found")
    return {"ok": True}
