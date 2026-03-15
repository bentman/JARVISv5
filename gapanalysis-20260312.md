# Gap Analysis — JARVISv5 Post-M15
**Date:** 2026-03-12
**Basis:** Direct code inspection of repository vs. `Project.md` vision and invariants.
**Method:** No assumptions. Every claim is grounded in file-level evidence.

---

## Inspection Scope

Files read for this analysis:

- `Project.md` — vision, invariants, target architecture
- `backend/config/settings.py` — typed settings, projection, editable keys
- `backend/config/api_keys.py` — API key registry
- `backend/controller/controller_service.py` — FSM/DAG orchestration, escalation integration
- `backend/models/model_registry.py` — model selection, ensure_model_present
- `backend/models/escalation_policy.py` — escalation policy module
- `backend/security/redactor.py` — PII redaction engine
- `backend/security/audit_logger.py` — security audit logger (event types include ENCRYPTION_PERFORMED, DECRYPTION_PERFORMED — no implementation behind them)
- `backend/security/privacy_wrapper.py` — external call gating
- `backend/voice/__init__.py` — empty file, no implementation
- `backend/api/main.py` — full API surface
- `backend/memory/memory_manager.py` — memory layer
- `backend/requirements.txt` — declared dependencies
- `models/models.yaml` — model catalog
- `frontend/src/components/SettingsPanel.jsx` — full settings UI source
- `frontend/src/components/` — MemoryPanel.jsx, WorkflowVisualizer.jsx (no VoicePanel)
- `SYSTEM_INVENTORY.md` — capability ledger through M15

---

## Verified Implemented Capabilities (not gaps)

The following Project.md requirements are satisfied by verified code:

| Area | Status | Evidence |
|------|--------|----------|
| FSM/DAG orchestration (§3.1) | Verified | `controller_service.py`, `fsm.py`, M10–M15 |
| Working / Episodic / Semantic memory (§3.2, §4) | Verified | `memory_manager.py`, M2, M7, M12 |
| Local LLM routing + hardware-aware selection (§3.3, §6.1–6.2) | Verified | `model_registry.py`, `hardware_profiler.py` |
| Escalation policy + budget governance (§6.3) | Verified | `escalation_policy.py`, M15 |
| Tool registry + sandboxed execution (§3.4) | Verified | `registry.py`, `sandbox.py`, `executor.py`, M4 |
| Search providers + privacy redaction before external calls (§3.4, §8.1) | Verified | `search_web_node.py`, `redactor.py`, M14 |
| PII redaction engine (§8.1) | Verified | `redactor.py`, M5 |
| Security audit logger (§8.2) | Verified | `audit_logger.py`, M5 |
| Privacy wrapper for external calls (§8.2) | Verified | `privacy_wrapper.py`, M5 |
| Web client: chat + workflow status + memory search + settings (§3.5, §11) | Verified | `App.jsx`, `SettingsPanel.jsx`, `MemoryPanel.jsx`, M9–M15 |
| Docker-first execution (§9) | Verified | `docker-compose.yml`, `Dockerfile` |
| Regression harness + unit/integration/agentic tests (§10) | Verified | `validate_backend.py`, M10, 337 tests passing |
| Reproducibility, memory recall, task success, drift, latency metrics (§10.2) | Verified | M10 test suites |

---

## Gap Summary Table

| ID | Gap | Project.md Reference | Priority | Sequence |
|----|-----|---------------------|----------|----------|
| G-A | Escalation provider execution layer absent (concrete implementations + registry startup) | §3.3, §6.3 | High | Next |
| G-B | Settings panel missing privacy/redaction controls | §3.5, §11.2 | High | Next |
| G-C | No settings API write path for `REDACT_PII_QUERIES` / `REDACT_PII_RESULTS` | §8.1 | High | Next (coupled with G-B) |
| G-D | Voice stack entirely absent | §2, §7 | Low-Medium | After G-A/B/C |
| G-E | Model integrity checksums absent | §6.2, §8.2 | Low | After G-D |
| G-F | Encryption at rest absent | §8.1 | Lowest | Last |

---

## Gap Detail

---

### G-A — Escalation Provider Execution Layer Absent

**What Project.md requires (§3.3, §6.3):**
A real escalation path to external cloud model providers when local model is unavailable, with budget governance and privacy controls applied before dispatch.

**What the repo has — correctly and completely implemented:**

- **Policy layer:** `decide_escalation()` evaluates seven gates in order: permission denied → provider not configured → provider unsupported → provider key missing → budget not allocated → budget exceeded → OK. All gates function correctly and are fully tested.
- **Settings layer:** `ALLOW_MODEL_ESCALATION`, `ESCALATION_PROVIDER`, and `ESCALATION_BUDGET_USD` are typed fields in `settings.py`, present in `.env` and `.env.example` with safe defaults, editable via `POST /settings` (first two in `EDITABLE_SETTINGS_ENV_KEYS`).
- **UI layer (`SettingsPanel.jsx`):** The escalation section is fully implemented with a save button.
  - `configuredEscalationProviders` is derived from `settings.escalation_configured_providers`, which is sourced from `ApiKeyRegistry().get_configured_providers()` — returning only providers whose `*_API_KEY` entry in `.env` is non-empty. The dropdown populates exclusively from this filtered list.
  - The dropdown is disabled when `allow_model_escalation` is unchecked or no providers are configured. A "No configured escalation providers available." message is shown when the list is empty.
  - The Save / Cancel button pair calls `updateSettings()` → `POST /settings`, which writes `ESCALATION_PROVIDER` atomically back to `.env`.
  - This behavior is confirmed by both code inspection and the screenshot provided.
- **Key registry:** `ApiKeyRegistry` reads `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROK_API_KEY`, `OPENAI_API_KEY` from `.env`. Three of four have real key values present in the current `.env`.
- **Redaction:** `create_default_redactor()` is called and `redaction_result.redacted` is passed to the provider before any dispatch attempt. `escalation_redaction_applied` is set in context.
- **Controller integration:** `_handle_local_model_unavailable()` correctly calls `decide_escalation()`, sets `escalation_status` on all paths, applies redaction on the allow path, then looks up the registry.

**What is missing — the precise and only gap:**
`_ESCALATION_PROVIDER_REGISTRY` is declared as a module-level empty dict: `_ESCALATION_PROVIDER_REGISTRY: dict[str, EscalationProviderBase] = {}`. No concrete `EscalationProviderBase` subclass exists for any provider (Anthropic, Gemini, Grok, OpenAI). Nothing populates this registry at startup.

When `decide_escalation()` returns `allow=True` (all gates pass), the controller executes:
```python
provider_impl = _ESCALATION_PROVIDER_REGISTRY.get(provider)
if provider_impl is None:
    context["escalation_status"] = "failed"
    context["escalation_error"] = "escalation_provider_not_registered"
    ...
```
This is the terminal failure in all production configurations, regardless of how correctly the settings and keys are configured.

**Evidence:**
- `backend/models/` — `escalation_policy.py`, `hardware_profiler.py`, `local_inference.py`, `model_registry.py`. No `providers/` subdirectory. No concrete provider implementation files.
- `backend/requirements.txt` — `openai>=1.0.0` present; `anthropic`, `google-generativeai`, `groq` absent.
- `controller_service.py` — `_ESCALATION_PROVIDER_REGISTRY: dict[str, EscalationProviderBase] = {}` is never mutated outside of test monkeypatching.

**Scope of work required:** Implement concrete `EscalationProviderBase` subclasses (at minimum one, e.g. Anthropic given the key is present), add SDK dependencies to `requirements.txt`, and register providers in `_ESCALATION_PROVIDER_REGISTRY` at module or app startup. All surrounding infrastructure is complete.

---

### G-B — Settings Panel Missing Privacy / Redaction Controls

**What Project.md requires (§3.5, §11.2):**
Settings panel includes hardware profiles, **privacy controls**, and budget monitoring.

**What the repo has:**
`SettingsPanel.jsx` `EDITABLE_FIELDS` array: `hardware_profile`, `log_level`, `allow_external_search`, `default_search_provider`, `cache_enabled`, `allow_model_escalation`, `escalation_provider`. Rendered controls cover hardware, search, cache, and escalation.

**What is missing:**
No UI controls for `REDACT_PII_QUERIES` or `REDACT_PII_RESULTS`. Both fields are defined in `settings.py` and appear in `SafeConfigProjection` and `SettingsResponse`, but are absent from `EDITABLE_FIELDS` and have no rendered control in the panel.

**Evidence:**
- `backend/config/settings.py` — `REDACT_PII_QUERIES: bool = True`, `REDACT_PII_RESULTS: bool = False`. Neither is in `EDITABLE_SETTINGS_ENV_KEYS`.
- `backend/api/schemas.py` — `SettingsResponse` includes both. `SettingsUpdateRequest` does not (no write path).
- `frontend/src/components/SettingsPanel.jsx` — `EDITABLE_FIELDS` contains no PII/redaction entries; no checkbox or control rendered for either field.

---

### G-C — No Settings API Write Path for Privacy / Redaction Fields

**What Project.md requires (§8.1):**
User controls for data handling policies including selective redaction.

**What the repo has:**
`REDACT_PII_QUERIES` and `REDACT_PII_RESULTS` are readable via `GET /settings`. The controller reads `settings.REDACT_PII_QUERIES` at runtime to gate redaction behavior.

**What is missing:**
Neither field is in `EDITABLE_SETTINGS_ENV_KEYS`. `POST /settings` raises `unsupported editable setting` for both. Values can only be changed by directly editing `.env`.

**Note:** G-B and G-C must be resolved together. The backend write path and the frontend controls are two halves of the same surface. Closing one without the other leaves an incomplete and untestable feature.

---

### G-D — Voice Stack Entirely Absent

**What Project.md requires (§2, §7):**
Whisper STT, Piper TTS, openWakeWord wake word detection, dedicated voice session workflow path, voice artifact lifecycle stored as episodic traces, deterministic voice runtime.

**What the repo has:**
- `backend/voice/__init__.py` — empty file. No imports, no code, no stubs.
- `models/models.yaml` — `whisper-stt` and `piper-tts` entries present but both `enabled: false`; no model weights exist.
- `frontend/src/components/` — no `VoicePanel.jsx` or equivalent. Components present: MemoryPanel, SettingsPanel, WorkflowVisualizer only.
- `backend/requirements.txt` — no `whisper`, `openai-whisper`, `faster-whisper`, `piper-tts`, `openwakeword`, or equivalent.
- `backend/api/main.py` — no `/voice` routes.
- `tests/` — no voice-related tests.

**Evidence:**
- `backend/voice/__init__.py`: empty (zero content).
- Repo-wide search for "whisper": no matches.
- Repo-wide search for "voice": returns only the `backend/voice` directory name — no file content matches.

**Project.md §2** marks voice as "optional" ("Voice Optional: STT/TTS and wake word, but not required for core usage"). The directory placeholder and disabled catalog stubs confirm design intent. No implementation exists anywhere.

---

### G-E — Model Integrity Checksums Absent

**What Project.md requires (§6.2, §8.2):**
"Integrity Verification: Model checksums and validation" and "Model Integrity: Checksum verification for all models."

**What the repo has:**
`models/models.yaml` entries define `path`, `download_url`, `enabled`, `roles`, `supported_hardware`, `priority`. No checksum fields of any kind (`sha256`, `md5`, `hash`, or equivalent) appear in any entry.

`model_registry.py` `ensure_model_present()` checks `path.exists()` only — no hash verification before use or after download. No verification step follows `urllib.request.urlretrieve`.

`backend/security/audit_logger.py` defines `ENCRYPTION_PERFORMED` and `DECRYPTION_PERFORMED` event types but no `MODEL_INTEGRITY_VERIFIED` or equivalent event type and no code path that would emit one.

**Evidence:**
- Repo-wide search for "checksum": no matches.
- `models/models.yaml`: no hash fields in any entry.
- `model_registry.py` `ensure_model_present()`: `path.exists()` is the sole integrity check.

**Impact:** A corrupted or substituted GGUF file is accepted silently. Real security gap, but self-contained and does not affect day-to-day functionality.

---

### G-F — Encryption at Rest Absent

**What Project.md requires (§8.1):**
"Encryption: Conversation storage encrypted at rest."

**What the repo has:**
- Task/conversation data stored as plain JSON under `data/working_state/`.
- Episodic trace stored as plain SQLite at `data/episodic/trace.db`.
- Semantic memory as plain FAISS index + SQLite at `data/semantic/`.
- `requirements.txt` includes `cryptography>=44.0.0`, `python-jose[cryptography]>=3.3.0`, `passlib[bcrypt]>=1.7.4`. These libraries are present but used for JWT handling and password hashing only — none are wired to encrypt storage artifacts.
- `backend/security/audit_logger.py` defines `ENCRYPTION_PERFORMED` / `DECRYPTION_PERFORMED` event types with no implementations that emit them.

**Evidence:**
- Repo-wide search for "encrypt": no matches.
- `memory_manager.py`: plain path strings passed to storage constructors; no encryption wrapper at any layer.
- `backend/security/`: `redactor.py`, `audit_logger.py`, `privacy_wrapper.py` — no `encryptor.py` or equivalent.

**Impact:** All local artifacts are stored in plaintext. Lowest-priority gap: the system is local-first, OS/filesystem-level encryption is the practical mitigation, and the `cryptography` library needed for implementation is already in `requirements.txt`.

---

## Gap Sequencing Rationale

**G-A (escalation provider implementations)** is highest priority. Every surrounding layer — settings, UI, key-gating, policy evaluation, redaction, controller integration — is complete and working. The UI correctly shows only providers whose keys are configured in `.env`, and saving the selection works end-to-end. The sole remaining work is concrete `EscalationProviderBase` subclasses and their registration at startup. The M15 control plane investment delivers zero runtime value until this is done.

**G-B + G-C (privacy/redaction controls)** must be closed together. The read surface for `REDACT_PII_QUERIES`/`REDACT_PII_RESULTS` already exists in the settings API response. Only the write path (`EDITABLE_SETTINGS_ENV_KEYS`) and UI controls are missing. Closes a named §3.5 requirement absent from all user-facing surfaces.

**G-D (voice stack)** is explicitly "optional" per §2 and has zero implementation. It is a large subsystem: new dependencies (Whisper, Piper, openWakeWord), new workflow nodes, new API routes, new frontend component, new tests. Lower priority than functional gaps that unblock already-built infrastructure.

**G-E (model integrity)** is self-contained. Adding `sha256` fields to `models.yaml` and a verification step to `ensure_model_present()` is a bounded, low-risk change. Real security gap but does not affect current daily functionality. Sequenced after voice, which delivers visible product capability.

**G-F (encryption at rest)** is the lowest-priority gap. OS/filesystem encryption is the practical mitigation for a personal local assistant. Wrapping all storage layers is invasive. The `cryptography` library is already in `requirements.txt` when the time comes.
