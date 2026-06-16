import os
import json
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from datetime import datetime, timezone
from core import db as dbmod
from core import meta

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = logging.getLogger("webhooks")

VERIFY_TOKEN = os.environ['FB_WEBHOOK_VERIFY_TOKEN']


def _now(): return datetime.now(timezone.utc).isoformat()


@router.get("/meta")
async def meta_verify(request: Request):
    qs = request.query_params
    if qs.get("hub.mode") == "subscribe" and qs.get("hub.verify_token") == VERIFY_TOKEN:
        challenge = qs.get("hub.challenge", "")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(403, "Verification failed")


@router.post("/meta")
async def meta_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("x-hub-signature-256")
    if not meta.verify_signature(body, sig):
        raise HTTPException(401, "Invalid signature")
    payload = json.loads(body)
    await dbmod.webhook_events.insert_one({"received_at": _now(), "payload": payload})

    # Best-effort processing of feed/comments events
    try:
        for entry in payload.get("entry", []):
            page_id_or_ig = str(entry.get("id"))
            for change in entry.get("changes", []):
                field = change.get("field")
                value = change.get("value", {})
                if field in ("feed", "comments"):
                    await _process_change(page_id_or_ig, field, value)
    except Exception as e:
        log.exception("webhook processing failed: %s", e)
    return {"ok": True}


async def _process_change(source_id: str, field: str, value: dict):
    from core.ai import classify_comment, generate_reply, should_auto_reply
    from core.security import decrypt_token

    # Find tenant via connected page or IG account
    page = await dbmod.pages.find_one({"page_id": source_id})
    ig = None
    if not page:
        ig = await dbmod.ig_accounts.find_one({"ig_id": source_id})
    if not page and not ig:
        return
    tenant_id = (page or ig)["tenant_id"]
    token = decrypt_token((page or ig)["access_token_enc"])
    page_id_for_post = page["page_id"] if page else ig["page_id"]
    platform = "facebook" if page else "instagram"

    # Only handle "add" verbs with comment data
    if value.get("item") != "comment" and field != "comments":
        return
    if value.get("verb") and value["verb"] != "add":
        return

    comment_id = value.get("comment_id") or value.get("id")
    message = value.get("message", "")
    post_id = value.get("post_id", "")
    from_obj = value.get("from", {})

    if not comment_id or not message:
        return
    existing = await dbmod.comments.find_one({"tenant_id": tenant_id, "comment_id": comment_id})
    if existing:
        return

    tenant = await dbmod.tenants.find_one({"id": tenant_id})
    kb_entries = await dbmod.kb.find({"tenant_id": tenant_id}).to_list(50)
    kb_ctx = "\n".join([f"- [{e['kind']}] {e['title']}: {e['content']}" for e in kb_entries])
    brand = {"name": tenant.get("business_name", ""), "tone": tenant.get("brand_tone", ""), "industry": tenant.get("industry", "")}

    cls = await classify_comment(message)
    doc = {
        "tenant_id": tenant_id, "comment_id": comment_id, "post_id": post_id, "page_id": page_id_for_post,
        "platform": platform, "from_name": from_obj.get("name", "Unknown"), "from_id": from_obj.get("id", ""),
        "message": message, "created_time": value.get("created_time", _now()),
        "like_count": 0, "classification": cls, "category": cls.get("category"),
        "sentiment": cls.get("sentiment"), "confidence": cls.get("confidence"),
        "status": "pending", "created_at": _now(),
    }
    await dbmod.comments.insert_one(doc)

    if cls.get("lead_score", 0) >= 60 or cls.get("category") == "lead_intent":
        await dbmod.leads.insert_one({
            "tenant_id": tenant_id, "comment_id": comment_id, "from_name": doc["from_name"],
            "from_id": doc["from_id"], "page_id": page_id_for_post, "message": message,
            "score": cls.get("lead_score", 0), "category": cls.get("category"),
            "status": "new", "created_at": _now(),
        })
        from core.events import notify
        await notify(tenant_id, "new_lead", f"New lead from {doc['from_name']} (score {cls.get('lead_score', 0)})", {"comment_id": comment_id})

    if doc.get("sentiment") == "negative":
        from core.events import notify as _notify
        await _notify(tenant_id, "negative_comment", f"Negative comment from {doc['from_name']}", {"comment_id": comment_id})

    try:
        reply_text = await generate_reply(message, cls, kb_ctx, brand)
    except Exception:
        reply_text = ""

    if should_auto_reply(cls) and reply_text and tenant.get("auto_reply_enabled", True):
        try:
            res = await meta.reply_to_comment(comment_id, reply_text, token)
            await dbmod.replies.insert_one({
                "tenant_id": tenant_id, "comment_id": comment_id, "reply_id": res.get("id"),
                "text": reply_text, "auto": True, "approved_by": None, "posted_at": _now(),
            })
            await dbmod.comments.update_one({"tenant_id": tenant_id, "comment_id": comment_id}, {"$set": {"status": "replied"}})
            return
        except Exception:
            pass

    await dbmod.approvals.insert_one({
        "tenant_id": tenant_id, "comment_id": comment_id, "suggested_reply": reply_text,
        "reason": "requires human approval", "status": "pending", "created_at": _now(),
    })
    await dbmod.comments.update_one({"tenant_id": tenant_id, "comment_id": comment_id}, {"$set": {"status": "pending_approval"}})
