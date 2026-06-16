# DashAI — Multi-Tenant FB/IG AI Comment Manager

## Original Problem Statement (verbatim summary)
Build a production-ready multi-tenant SaaS that lets businesses connect Facebook Pages + Instagram Business Accounts, monitor comments in real time, classify intent + sentiment using Claude, auto-reply when safe, route negative/low-confidence to a human approval queue, detect leads, manage RBAC teams, view analytics, and maintain a knowledge base for grounded replies.

## User Choices
- Tech stack: React + FastAPI + MongoDB (adapted from Next.js/Postgres spec)
- Auth: Real Facebook OAuth only — no demo/mock
- AI: Claude Sonnet 4.5 via Emergent Universal LLM Key
- Scope: MVP excludes subscriptions / Stripe billing / Sentry / Docker / CI

## Architecture
- Backend FastAPI (`/api` prefix), motor MongoDB, JWT auth, Fernet-encrypted FB tokens
- Frontend React + Tailwind + Shadcn UI, Swiss/High-Contrast design (Klein Blue #002FA7, Chivo / IBM Plex)
- Claude pipeline: classify (14 categories + sentiment + lead_score + confidence) → conditional reply → auto-post to Meta or queue for approval
- Multi-tenant: every collection keyed by `tenant_id`; `X-Tenant-Id` header + JWT enforce isolation; RBAC roles owner / admin / moderator / viewer

## Implemented (Feb 2026)
- Facebook OAuth (login URL with MongoDB-TTL state, callback exchange, long-lived token, /me discovery, httpOnly cookie issuance)
- Page + IG Business Account discovery + connect (real Meta Graph v22.0)
- Meta Webhook GET verify + POST signature verification (HMAC-SHA256) + async comment ingestion
- Comment classification (14 categories), sentiment, lead score via Claude Sonnet 4.5
- Auto-reply gate: only positive/neutral + confidence > 90% + safe categories
- Approval Queue with approve / edit / reject → posts back to Meta
- Lead Detection (score ≥ 60 or category=lead_intent) with status pipeline
- **Auto-DM generator (NEW)** — per-lead button calls Claude for a personalized opener; copy to clipboard
- Knowledge Base CRUD (products / services / FAQs / policies) used as RAG context
- Team Management: invite link, accept, RBAC enforcement
- Workspace switcher + multi-tenant membership
- Analytics: KPI overview, sentiment trend (7/14d), category distribution, top pages
- Settings: brand tone, reply style, auto-reply toggle
- **Audit Logs (NEW)** — page connect, approval action events logged; UI page
- **Campaigns (NEW)** — Claude-generated campaign ideas with audience/budget/copy/hashtags
- **Notifications (NEW)** — in-app bell with unread badge; auto-created on new lead + negative comment
- **Security: httpOnly cookie auth, CSRF double-submit middleware, MongoDB-TTL OAuth state, CORS-pinned origin**
- 49/49 backend tests passing (100%)

## Deferred — P1 / P2 Backlog
- P1: Subscription plans + Stripe billing + plan-limit enforcement
- P1: Audit logs page (collection already exists, no UI)
- P1: Campaign Suggestions UI (backend helper in `core/ai.py:generate_campaign_ideas` exists, no route/page yet)
- P1: Notifications (in-app + email)
- P2: WebSocket real-time updates
- P2: Move OAuth state cache from in-memory to Redis/Mongo TTL
- P2: Move webhook processing to BullMQ-style queue (Celery + Redis)
- P2: Sentry monitoring, Docker, CI/CD, load tests
- P2: Invite expiry; full Audit Log UI; advanced lead scoring with ML

## Files
- Backend: `/app/backend/server.py` + `/app/backend/core/*` + `/app/backend/routers/*`
- Frontend: `/app/frontend/src/App.js` + `/app/frontend/src/pages/*` + `/app/frontend/src/components/*` + `/app/frontend/src/lib/*`
- Design: `/app/design_guidelines.json`
- Tests: `/app/backend/tests/backend_test.py` (created by testing agent)
