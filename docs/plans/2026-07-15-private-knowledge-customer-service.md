# Private Knowledge Customer Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Build a local-first knowledge base, cited Q&A, web console, and Feishu customer-service system with strict public/sensitive access boundaries.

**Architecture:** A FastAPI backend owns ingestion, retrieval, privacy, model, identity, and handoff rules. A React + TypeScript frontend provides the admin console and standalone chat, while Feishu is implemented as a channel adapter. PostgreSQL + pgvector persists metadata, vectors, identities, conversations, tickets, and audits; source documents remain in the authorized local folder.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL + pgvector, pytest, React, TypeScript, Vite, Vitest, Playwright, local embedding/reranking libraries, DeepSeek OpenAI-compatible API, Ollama API, Feishu Open Platform.

---

## Delivery rules

- Implement tasks in order and keep each task on a dedicated branch or worktree.
- For every behavior: write a failing test, run it, add the smallest implementation, rerun the focused test, then run the relevant suite.
- Do not add OCR, enterprise WeChat, voice, file upload, or unrestricted general chat in this plan.
- Never place API keys, app secrets, document contents, or production paths in fixtures or commits.
- Do not call a cloud model from automated tests; use a request-capturing fake provider.

### Task 1: Backend foundation and health endpoint

**Files:**
- Create: `advanced_llm_apps/private_knowledge_customer_service/backend/pyproject.toml`
- Create: `advanced_llm_apps/private_knowledge_customer_service/backend/app/main.py`
- Create: `advanced_llm_apps/private_knowledge_customer_service/backend/app/config.py`
- Create: `advanced_llm_apps/private_knowledge_customer_service/backend/tests/test_health.py`

**Steps:**

1. Write a failing API test asserting `GET /health` returns service, database, scheduler, embedding, model, and Feishu statuses without secrets.
2. Run `uv run pytest tests/test_health.py -v` from `backend`; expect import or route failure.
3. Add the minimal application factory, typed settings, and health response.
4. Rerun the focused test; expect PASS.
5. Run `uv run pytest -v`; expect all backend tests PASS.
6. Commit: `chore: bootstrap private knowledge service backend`.

### Task 2: Database schema and migrations

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/domain/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_initial_schema.py`
- Create: `backend/tests/test_schema.py`

**Steps:**

1. Write schema tests for knowledge sources, chunks, scan runs, whitelist identities, conversations, messages, tickets, model configs, and audit events.
2. Run `uv run pytest tests/test_schema.py -v`; expect failure because models and migration do not exist.
3. Implement the minimum typed models, constraints, enums, indexes, and pgvector column.
4. Apply migrations to the test database with `uv run alembic upgrade head`.
5. Rerun schema tests; expect PASS.
6. Commit: `feat: add private knowledge service schema`.

### Task 3: Authorized directory and file inventory

**Files:**
- Create: `backend/app/ingestion/inventory.py`
- Create: `backend/app/ingestion/fingerprint.py`
- Create: `backend/tests/ingestion/test_inventory.py`

**Steps:**

1. Write failing tests for missing `public/` or `sensitive/`, symlink escape, unsupported files, deterministic fingerprints, and partition assignment.
2. Run `uv run pytest tests/ingestion/test_inventory.py -v`; expect failure.
3. Implement root validation, safe path resolution, extension allowlist, and path/mtime/size/hash fingerprinting.
4. Rerun focused tests; expect PASS.
5. Commit: `feat: inventory authorized knowledge folders`.

### Task 4: Six document parsers and canonical chunks

**Files:**
- Create: `backend/app/ingestion/parsers/base.py`
- Create: `backend/app/ingestion/parsers/pdf.py`
- Create: `backend/app/ingestion/parsers/docx.py`
- Create: `backend/app/ingestion/parsers/text.py`
- Create: `backend/app/ingestion/parsers/xlsx.py`
- Create: `backend/app/ingestion/parsers/pptx.py`
- Create: `backend/app/ingestion/chunking.py`
- Create: `backend/tests/fixtures/documents/README.md`
- Create: `backend/tests/ingestion/test_parsers.py`

**Steps:**

1. Add minimal synthetic fixtures for PDF, DOCX, MD, TXT, XLSX, and PPTX with known anchors and locations.
2. Write failing parameterized tests asserting normalized text and page/sheet/slide metadata.
3. Run `uv run pytest tests/ingestion/test_parsers.py -v`; expect failure.
4. Implement the parser protocol, six parsers, and metadata-preserving chunker.
5. Rerun focused tests; expect PASS for every format.
6. Commit: `feat: parse supported knowledge documents`.

### Task 5: Transactional incremental scanning

**Files:**
- Create: `backend/app/ingestion/service.py`
- Create: `backend/app/api/scans.py`
- Create: `backend/tests/ingestion/test_scan_service.py`

**Steps:**

1. Write failing tests for initial scan, unchanged skip, content update, deletion, one-file failure, and preservation of the previous index on replacement failure.
2. Run `uv run pytest tests/ingestion/test_scan_service.py -v`; expect failure.
3. Implement inventory diffing and transactional source/chunk replacement.
4. Add `POST /admin/scans` and `GET /admin/scans/{id}` with counts and errors.
5. Rerun focused and backend tests; expect PASS.
6. Commit: `feat: add incremental knowledge scanning`.

### Task 6: Adapt the existing RAGLite hybrid retrieval and citation contract

**Files:**
- Create: `backend/app/retrieval/raglite_adapter.py`
- Create: `backend/app/retrieval/evidence.py`
- Create: `backend/tests/retrieval/test_search.py`

**Steps:**

1. Read and cite the reuse sources `rag_tutorials/local_hybrid_search_rag/local_main.py` and `rag_tutorials/multimodal_agentic_rag/backend/rag_store.py` in the adapter module.
2. Write failing contract tests for RAGLite hybrid search, retrieve, rerank, partition routing, deterministic evidence ordering, and source locations.
3. Run `uv run pytest tests/retrieval/test_search.py -v`; expect failure.
4. Adapt RAGLite `hybrid_search`, `retrieve_chunks`, and `rerank_chunks`; do not implement replacement fusion or reranking algorithms.
5. Map results to the existing multimodal template's `citation/source/similarity/evidence` contract, extended with source locator metadata.
6. Rerun tests and verify an external identity can never route to the sensitive RAGLite store.
7. Commit: `feat: adapt existing hybrid retrieval template`.

### Task 7: Pluggable models and privacy gateway

**Files:**
- Create: `backend/app/model_providers/base.py`
- Create: `backend/app/model_providers/deepseek.py`
- Create: `backend/app/model_providers/ollama.py`
- Create: `backend/app/privacy/policy.py`
- Create: `backend/tests/privacy/test_policy.py`
- Create: `backend/tests/model_providers/test_providers.py`

**Steps:**

1. Write failing policy-table tests for public/sensitive evidence, internal/external identity, local/cloud provider, and sensitive-cloud checkbox states.
2. Add a capturing fake cloud provider and assert forbidden sensitive text never enters its request.
3. Run focused tests; expect failure.
4. Adapt the DeepSeek `OpenAI(base_url="https://api.deepseek.com")` pattern from `ai_system_architect_r1` and the Agno Ollama pattern from `agentic_rag_embedding_gemma`; do not write replacement HTTP clients.
5. Implement only the provider selection boundary and privacy decisions `GENERATE`, `EXCERPT_ONLY`, `HANDOFF`.
6. Rerun privacy and provider tests; expect PASS without real network calls.
7. Commit: `feat: enforce pluggable model privacy policy`.

### Task 8: Authentication and employee whitelist

**Files:**
- Create: `backend/app/auth/local.py`
- Create: `backend/app/auth/feishu_oauth.py`
- Create: `backend/app/permissions/identities.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/identities.py`
- Create: `backend/tests/auth/test_identity_resolution.py`

**Steps:**

1. Write failing tests for local admin login, Feishu OAuth mapping, whitelist add/remove, unknown identity, and failed identity lookup.
2. Assert unknown and failed identities resolve to external customer.
3. Implement password hashing, session/token issuance, OAuth callback boundary, and audited whitelist operations.
4. Run focused and backend suites; expect PASS.
5. Commit: `feat: add dual login and employee whitelist`.

### Task 9: Conversation, answer, and handoff state machine

**Files:**
- Create: `backend/app/customer_service/conversations.py`
- Create: `backend/app/customer_service/risk.py`
- Create: `backend/app/customer_service/handoff.py`
- Create: `backend/app/api/chat.py`
- Create: `backend/tests/customer_service/test_handoff.py`

**Steps:**

1. Write failing tests for explicit handoff, low evidence, high-risk categories, bot pause, human reply, and bot resume.
2. Run `uv run pytest tests/customer_service/test_handoff.py -v`; expect failure.
3. Implement the minimal conversation states and ticket lifecycle.
4. Add cited streaming answer and excerpt-only response contracts.
5. Rerun focused and backend tests; expect PASS.
6. Commit: `feat: add customer service handoff workflow`.

### Task 10: Feishu channel adapter

**Files:**
- Create: `backend/app/channels/feishu/verification.py`
- Create: `backend/app/channels/feishu/events.py`
- Create: `backend/app/channels/feishu/cards.py`
- Create: `backend/app/api/feishu.py`
- Create: `backend/tests/channels/test_feishu.py`

**Steps:**

1. Write failing fixture-based tests for URL verification, signed callbacks, duplicate event IDs, private chat, group mention, answer card, ticket card, and callback retry.
2. Run focused tests; expect failure.
3. Implement signature verification, event normalization, idempotency storage, fast acknowledgement, and asynchronous dispatch.
4. Ensure group messages without `@机器人` are ignored.
5. Rerun focused and backend tests; expect PASS.
6. Commit: `feat: connect Feishu customer service channel`.

### Task 11: Scheduler and auditing

**Files:**
- Create: `backend/app/scheduler/scans.py`
- Create: `backend/app/audit/service.py`
- Create: `backend/tests/scheduler/test_daily_scan.py`
- Create: `backend/tests/audit/test_audit.py`

**Steps:**

1. Write failing clock-controlled tests for an every-other-day scan, missed-run recovery, concurrent-run exclusion, and failure notification.
2. Write tests that sensitive setting, whitelist, scan, answer, and handoff operations create redacted audit events.
3. Implement the scheduler lock, run policy, audit writer, and administrator notification boundary.
4. Rerun focused and backend tests; expect PASS.
5. Commit: `feat: schedule and audit knowledge operations`.

### Task 12: Frontend foundation, login, and role routing

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/router.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/auth/AuthProvider.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/tests/auth.test.tsx`

**Steps:**

1. Copy `rag_tutorials/multimodal_agentic_rag/frontend` as the frontend baseline, preserving its Vite/React setup, workspace layout, Q&A panel, status feedback, and citation list.
2. Write failing Vitest tests for local login, Feishu login action, protected routes, and administrator-only routes.
3. Run `npm test -- auth.test.tsx`; expect failure.
4. Adapt the existing source panel to local-folder scan status and adapt `/ask` without rebuilding the page shell.
5. Implement only the missing typed API client, auth state, login page, and route guards.
6. Rerun focused tests and `npm test`; expect PASS.
7. Commit: `feat: adapt multimodal RAG web shell`.

### Task 13: Admin console

**Files:**
- Create: `frontend/src/layouts/AdminLayout.tsx`
- Create: `frontend/src/pages/admin/DashboardPage.tsx`
- Create: `frontend/src/pages/admin/KnowledgePage.tsx`
- Create: `frontend/src/pages/admin/RetrievalLabPage.tsx`
- Create: `frontend/src/pages/admin/SupportPage.tsx`
- Create: `frontend/src/pages/admin/IdentitiesPage.tsx`
- Create: `frontend/src/pages/admin/ModelsPage.tsx`
- Create: `frontend/src/pages/admin/FeishuPage.tsx`
- Create: `frontend/src/pages/admin/AuditPage.tsx`
- Create: `frontend/tests/admin.test.tsx`

**Steps:**

1. Write failing page tests for loading, empty, error, and success states.
2. Add a dedicated test proving the sensitive-cloud checkbox defaults off, requires confirmation, and displays an audit result.
3. Implement the smallest accessible responsive pages backed by typed API calls.
4. Run `npm test`; expect PASS.
5. Commit: `feat: build knowledge service admin console`.

### Task 14: Standalone web Q&A

**Files:**
- Create: `frontend/src/layouts/ChatLayout.tsx`
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/components/chat/MessageList.tsx`
- Create: `frontend/src/components/chat/Composer.tsx`
- Create: `frontend/src/components/chat/CitationDrawer.tsx`
- Create: `frontend/src/components/chat/HandoffAction.tsx`
- Create: `frontend/tests/chat.test.tsx`

**Steps:**

1. Write failing tests for conversations, streaming, stop, citations, excerpt-only mode, feedback, regenerate, and handoff.
2. Write a role test proving external users never see sensitive labels or citations.
3. Implement the responsive chat experience and administrator-only retrieval debug drawer.
4. Run unit tests; expect PASS.
5. Add Playwright journeys for employee, external customer, and administrator.
6. Commit: `feat: add standalone cited knowledge chat`.

### Task 15: Local deployment and end-to-end acceptance

**Files:**
- Create: `deploy/docker-compose.yml`
- Create: `deploy/env.example`
- Create: `deploy/start-local.sh`
- Create: `deploy/stop-local.sh`
- Create: `backend/tests/e2e/test_privacy_acceptance.py`
- Create: `advanced_llm_apps/private_knowledge_customer_service/README.md` updates
- Modify: `advanced_llm_apps/private_knowledge_customer_service/docs/project-status.md`

**Steps:**

1. Add local PostgreSQL + pgvector configuration, migrations, backend, frontend, and scheduler processes without secrets.
2. Add a smoke test that indexes fixtures, asks as employee/customer, exercises cloud/local provider fakes, and completes a handoff.
3. Run backend tests, frontend tests, Playwright, migration checks, and secret scanning; expect all PASS.
4. Run the real local stack and verify health, manual scan, cited web answer, and Feishu sandbox callback.
5. Update README and the visible project status with exact commands and verified limitations.
6. Commit: `test: verify private knowledge customer service mvp`.

## Final acceptance checklist

- [ ] All six document types produce traceable citations.
- [ ] Manual and every-other-day scans handle add/update/delete/failure.
- [ ] External users cannot retrieve sensitive chunks through any channel.
- [ ] Sensitive chunks never reach the fake cloud provider when the checkbox is off.
- [ ] DeepSeek-compatible and Ollama providers pass contract tests.
- [ ] Web local login and Feishu OAuth both work.
- [ ] Admin console, standalone Q&A, and Feishu interactions pass end-to-end journeys.
- [ ] Explicit, low-confidence, and high-risk handoff paths all pause the bot.
- [ ] Logs and Git contain no secrets or sensitive fixture content.
