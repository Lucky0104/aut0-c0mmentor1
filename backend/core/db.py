import os
from motor.motor_asyncio import AsyncIOMotorClient

_client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = _client[os.environ['DB_NAME']]

# Collections (all keyed by tenant_id where applicable)
users = db.users
tenants = db.tenants
members = db.tenant_members
pages = db.facebook_pages
ig_accounts = db.instagram_accounts
posts = db.posts
comments = db.comments
replies = db.replies
approvals = db.approval_queue
leads = db.leads
kb = db.knowledge_base
campaigns = db.campaigns
notifications = db.notifications
audit_logs = db.audit_logs
webhook_events = db.webhook_events
invites = db.team_invites
settings_col = db.tenant_settings


async def ensure_indexes():
    await users.create_index("fb_user_id", unique=True, sparse=True)
    await users.create_index("email")
    await members.create_index([("user_id", 1), ("tenant_id", 1)], unique=True)
    await pages.create_index([("tenant_id", 1), ("page_id", 1)], unique=True)
    await ig_accounts.create_index([("tenant_id", 1), ("ig_id", 1)], unique=True)
    await comments.create_index([("tenant_id", 1), ("comment_id", 1)], unique=True)
    await comments.create_index([("tenant_id", 1), ("created_at", -1)])
    await leads.create_index([("tenant_id", 1), ("created_at", -1)])
    await approvals.create_index([("tenant_id", 1), ("status", 1)])
    await kb.create_index([("tenant_id", 1), ("kind", 1)])
    await invites.create_index("token", unique=True)
