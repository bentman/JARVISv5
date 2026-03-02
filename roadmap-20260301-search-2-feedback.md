## Brief summary of `roadmap-20260301-search-2.md`

This updated roadmap is a **planned M8 implementation outline** (not completion evidence) for adding web search + policy-bound escalation. It addresses prior review issues by explicitly:
- using current privacy wrapper contract (`evaluate_and_prepare_external_call`),
- adding an `EXTERNAL` tool permission tier with executor enforcement,
- wiring search tools through existing `ToolCallNode`/dispatch patterns,
- adding budget governance, provider ladder (SearXNG → DuckDuckGo → Tavily),
- using Trafilatura-first extraction with BeautifulSoup fallback,
- defining tests and validation commands.

## Current repo assessment against this roadmap

### Present in repo now (good foundation)
- M5-style privacy/audit plumbing exists (`privacy_wrapper`, `redactor`, `audit_logger`).
- Tool runtime patterns exist (`ToolRegistry`, `execute_tool_call`, `ToolCallNode`, file-tool dispatch).
- Retrieval/context infrastructure exists (`HybridRetriever`, context builder integration).
- `ddgs` and `requests` already exist in `backend/requirements.txt`.

### Not present yet (M8 still unimplemented)
- No `backend/search/` package (`budget.py`, `providers.py`, etc.).
- No search tools (`search_web`, `fetch_url`) in backend tools.
- No `EXTERNAL` permission in `PermissionTier`.
- No executor branch enforcing EXTERNAL semantics.
- No search config fields in `backend/config/settings.py`.
- No SearXNG service in `docker-compose.yml`.
- No `trafilatura` / `beautifulsoup4` in requirements.
- No M8-specific unit/integration tests.

## Validation of approach for this repo

**Overall:** The updated roadmap is directionally sound and aligned with `Project.md` (local-first, explicit external policy, auditability, deterministic flow). It is implementable with existing patterns.

### Strengths
- Correctly aligns to current privacy-wrapper API shape.
- Correctly anchors runtime wiring in `ToolCallNode`/dispatch pattern.
- Adds explicit policy gates (feature flag + budget + permission checks).
- Provider ladder and SearXNG health check are practical for reliability.

### Gaps/risks to tighten before implementation
1. **Tool permission caching interaction:** current executor caches only `READ_ONLY`; EXTERNAL tools should remain non-cacheable unless explicitly designed.
2. **Double privacy scanning behavior:** executor already performs external-call privacy evaluation; search tool internals should avoid redundant/conflicting policy checks unless intentionally layered.
3. **ToolCallNode sandbox requirement:** current node hard-fails without non-empty `sandbox_roots`; search tools must account for this invocation contract.
4. **Roadmap count mismatch:** “Modified Files (6)” section lists 7 files.
5. **Network-dependent tests:** provider tests should mock network to remain deterministic and CI-stable.

## Bottom line

`roadmap-20260301-search-2.md` is a strong improvement over the prior version and is mostly repo-compatible. The main implementation success factor will be keeping all M8 additions strictly on existing executor/node contracts and ensuring deterministic tests (especially for provider/network paths).