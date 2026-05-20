# TODO — Document Analyst

## v1 — Bugs & Polish
- [ ] Restore chat messages on page refresh (needs `/api/history` endpoint that reads from checkpointer)
- [ ] Visual indicator when backend is unreachable (health check polling)
- [ ] Handle upload errors with toast notifications (sonner)
- [ ] Agent activity indicator not updating in sidebar (stream annotations not wired)

## v1 — Missing
- [ ] Tests: pytest for backend packages, vitest for frontend
- [ ] CI/CD pipeline (GitHub Actions): lint, type-check, test, build
- [ ] `GET /api/history?session_id=` endpoint — return past messages from checkpointer for UI restore
- [ ] Error boundary component for graceful React error handling

## v2 — DSPy Prompt Optimization
- [ ] Collect Q&A pairs from v1 usage (Langfuse datasets)
- [ ] Define DSPy signatures for each agent
- [ ] Define quality metrics (LLM-as-judge, recall, coherence)
- [ ] Run BootstrapFewShot / MIPROv2 optimizers
- [ ] Evaluate v1 vs v2 on held-out test set

## v2 — Enhancements
- [ ] PostgreSQL checkpointer (`USE_POSTGRES_CHECKPOINTER=true`) for persistent memory
- [ ] Langfuse integration (callback handler for LLM tracing)
- [ ] Conversation summarization for long chats (sliding window / summary)
- [ ] Multiple chat sessions sidebar (list past conversations)

## v3 — Production Hardening
- [ ] OpenTelemetry (structlog + Langfuse already OTel-ready)
- [ ] Authentication (NextAuth.js / JWT)
- [ ] Rate limiting per session
- [ ] Docker production builds (multi-stage)
- [ ] Terraform/Pulumi for cloud deployment
- [ ] Secrets management (Azure Key Vault)
