Reading the prior version files first, then cross-referencing against the current v5 state.Now cross-reference against the current v5 implementations.I now have all the evidence needed from all four legacy files and current v5 state. Producing the spec.

---

# Hardware / Model-Selection / Provisioning Stack — Alignment Spec
**Date:** 2026-03-20  
**Scope:** v5 compatibility boundary with v3/v4 as prior-capability evidence  
**Method:** Direct code inspection of all four legacy files and current v5 state

---

## 1. Hardware Detection / Classification

### Current v5 State
`HardwareService` in `backend/models/hardware_profiler.py` is the most complete version across all four generations. Detection precedence: `GPU_CUDA → NPU_APPLE → NPU_INTEL → QUALCOMM_NPU → GPU_GENERAL → CPU_ONLY`. Each path uses layered probe strategies (torch, onnxruntime providers, openvino, GPUtil, platform heuristics), all fail-safe. `refresh_hardware_info()` is called at `__init__` and on demand.

### Legacy Evidence
- **v3** introduced the full six-type taxonomy and the layered probe pattern, including the onnxruntime provider fallback for GPU detection when GPUtil finds nothing. It also introduced `_has_npu()` as a cross-platform best-effort sweep.
- **v4** simplified — it dropped the OpenVINO/Qualcomm probes and the onnxruntime provider fallback GPU detection, reverting to a thinner implementation than v3. This was a regression, not an improvement.
- **v5** effectively reunifies both, restoring v3's detection depth with cleaner structure.

### Gap Analysis

| Capability | v3 | v4 | v5 | Assessment |
|-----------|-----|-----|-----|------------|
| Six-type `HardwareType` enum | ✅ | ✅ | ✅ | Aligned |
| CUDA probe via torch | ✅ | ✅ | ✅ | Aligned |
| Apple NPU via MPS + platform | ✅ | Partial | ✅ | v5 improved |
| Intel NPU via OpenVINO | ✅ | ❌ | ✅ | v5 restored |
| Qualcomm probe via `qaic` + heuristics | ✅ | ❌ | ✅ | v5 restored |
| onnxruntime provider fallback for GPU | ✅ | ❌ | ✅ | v5 restored |
| `ResourceManager` with degradation callbacks | ✅ | ✅ | Simplified | See §6 |
| `get_hardware_state()` as async | ✅ | ✅ | Sync dict | Different contract |
| CPU frequency in `_cpu_info` | ✅ | ✅ | ✅ | Aligned |

**One meaningful gap:** v3/v4 exposed `get_hardware_state()` as an async method returning a typed `HardwareState` Pydantic model. v5 returns a plain `dict` synchronously. The `DetailedHealthResponse` in the API layer reconstructs a similar shape, but the controller and any future voice/STT/TTS callers would need to adapt. This is not a blocker today but is the main integration seam for voice.

---

## 2. Hardware Capability Taxonomy

### `HardwareType` — Verdict: **Retain as-is with one normalization fix**

v5's enum uses SCREAMING_SNAKE_CASE values (`"CPU_ONLY"`, `"GPU_CUDA"` etc.) while the `ModelRegistry._normalize_hardware()` maps these to lowercase strings (`"cpu"`, `"gpu-cuda"`, `"npu"`, `"gpu"`). This intermediate normalization layer is the single point that bridges the enum values to the catalog's `supported_hardware` strings. It works but creates a three-way vocabulary: enum values → normalized strings → catalog strings.

**What should not be revived literally:** v3's `allocate_model_memory()` method on `HardwareService` that mixed hardware detection with memory allocation logic. v5 correctly separates these into `HardwareService` (detection only) and `ResourceManager` (allocation tracking).

**What should be formalized:** The `_normalize_hardware()` mapping is currently private to `ModelRegistry`. It should be elevated to a module-level function or a shared constant so that any new consumer (voice stack, STT/TTS provisioner) can use the same translation without re-implementing it.

### `HardwareProfile` — Verdict: **`light | medium | heavy | npu-optimized` should be retained**

v3 originated this taxonomy and tied it to memory thresholds (GPUs ≥8GB → heavy, ≥4GB → medium, etc.) plus onnxruntime provider presence. v5's `get_hardware_profile()` simplifies to RAM-only thresholds (≥32GB → heavy, ≥16GB → medium, else light) with an NPU shortcut. This is a deliberate simplification — correct for the current GGUF/llama.cpp inference stack where RAM is the primary constraint. The v3 GPU VRAM heuristic is not wrong but is harder to maintain and less portable.

**One gap to address:** v5's profile determination does not consider GPU VRAM at all. On a machine with 32GB RAM and a 4GB GPU, it returns `heavy`, but `heavy` models (7B+) may exceed VRAM. The VRAM heuristic from v3 is worth reviving as an optional narrowing gate — not replacing the RAM-primary approach, but capping the profile downward when VRAM is known and insufficient.

---

## 3. Model-Selection Policy and Consumers

### Current v5 State
`ModelRegistry` is a YAML-catalog-driven selector. `select_model(profile, hardware, role)` filters by: enabled → role → hardware compatibility (with fallback chain) → profile range → priority sort. The result is a dict from the catalog. `ensure_model_present()` is a separate provisioning step with `MODEL_FETCH=never|missing` policy.

### Legacy Evidence
- **v3** embedded model profiles as code-level dicts keyed by profile string (`light`, `medium`, `heavy`, `npu-optimized`, `stt-base`, `tts-medium`). Selection was: hardware profile → profile mapping → direct dict lookup. Checksum verification was listed per model (several as "placeholder"). Download used `huggingface_hub.hf_hub_download` with async fallback strategies (mirror, backup — both unimplemented stubs).
- **v4** narrowed further to STT/TTS provisioning only, removing LLM provisioning entirely. Used a minimal sync `ModelManager` with `huggingface_hub` download and threading locks.

### Gap Analysis

| Capability | v3 | v4 | v5 | Assessment |
|-----------|-----|-----|-----|------------|
| Hardware-driven model selection | ✅ | ❌ (STT/TTS only) | ✅ | v5 generalized correctly |
| YAML-externalised catalog | ❌ | ❌ | ✅ | v5 improvement |
| Checksum / integrity verification | Partial stubs | ❌ | ❌ | **Gap in all versions** |
| `huggingface_hub` download | ✅ | ✅ | ❌ (urllib) | **Regression in v5** |
| Multi-role catalog entries | ❌ | ❌ | ✅ | v5 improvement |
| Hardware fallback chain in selection | ❌ | ❌ | ✅ | v5 improvement |
| STT/TTS roles in catalog | ❌ catalog | ❌ code | Stub entries | **Partially present** |
| Voice model provisioning path | ❌ code-only | ✅ code-only | ❌ | **Absent in v5** |

**Critical gap:** v5 uses `urllib.request.urlretrieve` for downloads. This is synchronous, has no progress reporting, no retry, and no integrity check. v3 and v4 both used `huggingface_hub.hf_hub_download`, which handles redirects, authentication (for gated models), resumable downloads, and caching. `huggingface_hub` is already in the ecosystem (v3/v4 used it; it supports both sync and async). For voice model provisioning — where Whisper and Piper ONNX files come from Hugging Face — `urllib` is insufficient. An adapter from `urllib` → `huggingface_hub` is the correct migration path, not a rewrite of `ModelRegistry`.

**STT/TTS model entries in `models.yaml`:** `whisper-stt` and `piper-tts` catalog entries exist but are `enabled: false` and have placeholder paths (`models/whisper.gguf`, `models/piper.onnx`) that do not reflect the actual file structures used by whisper.cpp or Piper ONNX. The v3/v4 paths (`ggml-base.en.bin`, `en_US-lessac-medium.onnx` + `.onnx.json`) are the correct reference.

---

## 4. Backend Install / Provisioning Assumptions

### CUDA
- v3/v4/v5 all probe via `torch.cuda.is_available()`. v5 additionally checks onnxruntime `CUDAExecutionProvider`.
- `requirements.txt` includes `torch>=2.8.0` with CPU-only `faiss-cpu`. No explicit `torch+cu*` index. CUDA inference works only if the user installs the CUDA-capable torch wheel separately. This is an **undocumented runtime assumption** — the `Dockerfile` builds llama.cpp from source which handles CUDA at compile time, but the Python torch installation does not guarantee CUDA.
- **Verdict:** Not a code gap, but a documentation and Dockerfile configuration gap. The current approach is workable; it should be made explicit in `README.md` and `.env.example`.

### ONNX Runtime
- `onnxruntime>=1.19.0` is in `requirements.txt`. This is CPU-only onnxruntime. For Piper TTS (which uses ONNX), this is sufficient for CPU inference.
- For GPU-accelerated ONNX (DirectML on Windows, CUDA via onnxruntime-gpu), a different wheel is needed. v3 detected `DmlExecutionProvider` and `ROCMExecutionProvider` — these require `onnxruntime-directml` or `onnxruntime-gpu` respectively.
- **Verdict:** CPU ONNX is sufficient for Piper TTS at medium quality. If NPU-accelerated Piper is desired, an `onnxruntime-directml` or provider-specific package must be added. This is deferred until voice stack is built.

### Whisper
- v3 used `whisper.cpp` (C binary + `ggml-base.en.bin`). v4 referenced same. v5 catalog has a `whisper.gguf` path — this does not correspond to any real whisper.cpp model format. The actual format is `ggml-*.bin`. This is a **catalog error** that will cause voice provisioning to fail when voice is implemented.
- `requirements.txt` has no `openai-whisper`, `faster-whisper`, or whisper.cpp Python binding. The backend `voice/__init__.py` is empty.
- **Verdict:** The Whisper path has no implementation and a wrong catalog entry. Both must be corrected before voice work begins.

### `huggingface_hub`
- Present in v3/v4 as a direct dependency. Absent from v5 `requirements.txt`. Required for Piper and Whisper model downloads from gated or non-direct-URL sources.
- **Verdict:** Must be added to `requirements.txt` as part of the voice provisioning slice.

---

## 5. Downstream Coupling into Voice / STT / TTS Paths

### Current v5 State
`backend/voice/__init__.py` is empty. `models.yaml` has `whisper-stt` and `piper-tts` as disabled stubs. No `/voice` API routes exist. No voice workflow node exists. `ModelRegistry.select_model()` supports `role="stt"` and `role="tts"` via the `roles` field in the catalog — the selection logic works, but no consumer calls it for those roles.

### What the Legacy Versions Established
- **v3** defined the full voice provisioning chain: `ModelManager.download_recommended_model("stt"|"tts")` → `hf_hub_download` → path returned to caller. It also defined the correct model IDs (`ggerganov/whisper.cpp`, `rhasspy/piper-voices`) and filenames. SHA-256 checksums were listed for some entries.
- **v4** distilled this into a minimal, sync, lock-safe provisioner focused on STT/TTS only — the cleanest voice provisioning implementation across all versions. Its `ModelManager` is directly reusable conceptually.

### Integration Seam Analysis

The v5 architecture needs the following seams for voice:

```
HardwareService.detect_hardware_type()
    ↓
ModelRegistry.select_model(profile, hardware, role="stt"|"tts")
    ↓
ModelRegistry.ensure_model_present(model)   ← needs huggingface_hub adapter here
    ↓
backend/voice/stt_provider.py               ← does not exist
backend/voice/tts_provider.py               ← does not exist
    ↓
/voice/transcribe  /voice/speak             ← does not exist
```

The v4 `ModelManager` pattern (sync, lock-per-filename, `hf_hub_download`) is the correct adapter shape for `ensure_model_present()`. It should not replace `ModelRegistry`; it should be an alternative provisioning path for voice models where the download source is Hugging Face rather than a direct URL.

**ONNX coupling:** Piper TTS outputs audio via ONNX inference. `onnxruntime` is already installed. The Piper Python wrapper (`piper-tts` PyPI package) wraps onnxruntime and handles the `.onnx` + `.onnx.json` pair. It must be added to `requirements.txt` for the voice stack.

**Whisper coupling:** `faster-whisper` (wraps CTranslate2 and whisper.cpp-compatible models in GGUF/CTranslate2 format) is the most practical Python-callable STT backend. It is compatible with `ggml-*.bin` model files. `openai-whisper` is an alternative but heavier.

---

## 6. Gaps Not Worth Reviving

### `ResourceManager` dynamic allocation callbacks (v3/v4)
v3's `ResourceManager` had `allocate_memory()`, `deallocate_memory()`, and degradation callbacks. v5 has a simplified version with no threading or callbacks. The v3 version was premature optimization — in a local personal assistant with one model loaded at a time, dynamic memory tracking adds complexity without value. v5's simplification is correct. **Do not revive.**

### Async `get_hardware_state()` (v3/v4)
Both v3 and v4 defined this as `async`. v5 makes it sync. The async signature was inherited from an earlier FastAPI coupling and served no real concurrent purpose — hardware probes are blocking by nature. v5's sync version is correct. **Do not revive.**

### Multi-strategy download fallbacks (v3)
v3's `_download_from_mirror()` and `_download_from_backup()` were both unimplemented stubs. **Do not revive** — implement `huggingface_hub` properly instead.

### Global `model_manager` singleton (v3/v4)
Both versions had `model_manager = ModelManager()` at module level. v5's DI approach (constructed per-request in controller) is correct. **Do not revive.**

---

## 7. Target Compatibility Model

```
HardwareType (enum, str, 6 values)  ←→  profile string (4 values)
    GPU_CUDA        →  "heavy" (or "medium" if VRAM < 8GB)
    GPU_GENERAL     →  "medium" (or "light" if VRAM < 4GB)
    NPU_APPLE       →  "npu-optimized"
    NPU_INTEL       →  "npu-optimized"
    QUALCOMM_NPU    →  "npu-optimized"
    CPU_ONLY        →  "light" | "medium" depending on RAM

profile  →  ModelRegistry.select_model(profile, hardware_str, role)
    role="chat"|"code"   →  GGUF via llama.cpp     (current)
    role="stt"           →  Whisper model           (voice stack, deferred)
    role="tts"           →  Piper ONNX model        (voice stack, deferred)

ensure_model_present()
    MODEL_FETCH=never    →  fail if missing          (current)
    MODEL_FETCH=missing  →  urllib for direct URLs   (current, sufficient for GGUF)
                         →  huggingface_hub adapter  (needed for voice models)
```

The `_normalize_hardware()` vocabulary bridge in `ModelRegistry` should be promoted to a shared utility to prevent duplication when voice consumers need the same mapping.

---

## 8. Migration Slices in Safe Execution Order

| Slice | What | Risk |
|-------|------|------|
| **S1** | Fix `models.yaml` STT/TTS catalog entries: correct paths (`ggml-base.en.bin`, `.onnx`+`.onnx.json`), correct model IDs, disable until implemented | Zero — YAML only, no code |
| **S2** | Add VRAM-aware profile narrowing gate to `get_hardware_profile()` — cap profile downward when GPU VRAM is known and insufficient | Low — additive, all existing tests pass |
| **S3** | Promote `_normalize_hardware()` to a shared module-level function; export from `backend/models/__init__.py` | Low — additive, no behavior change |
| **S4** | Add `huggingface_hub>=0.x` to `requirements.txt`; add `ModelRegistry.ensure_model_present_hf()` as an alternative provisioner for HF-sourced models | Low — additive, no existing path changes |
| **S5** | Voice stack scaffolding: STT provider, TTS provider, controller voice path, `/voice` routes | High — new subsystem, scoped to M20 |

---

## 9. Key Risks and Regression Traps

**Risk 1 — `models.yaml` whisper path is wrong today.** If `MODEL_FETCH=missing` is set and a voice caller selects the `whisper-stt` entry, `urllib.request.urlretrieve` will attempt to fetch `models/whisper.gguf` (a nonexistent URL), not the correct `ggml-base.en.bin` from `ggerganov/whisper.cpp`. This will silently fail with a RuntimeError. Fix: S1 + S4.

**Risk 2 — Profile inflation on GPU-RAM-rich machines.** A machine with 32GB RAM and a 4GB integrated GPU returns `heavy`, but 7B GGUF models exceed 4GB VRAM. The model will load into system RAM (slower) or fail. Risk is UX, not crash. Fix: S2.

**Risk 3 — `_normalize_hardware()` duplication.** If voice or STT/TTS provisioning implements its own hardware→catalog string mapping, divergence will cause silent model selection mismatches. Fix: S3 before any voice work begins.

**Risk 4 — onnxruntime variant mismatch.** `onnxruntime` (CPU) is installed. If the user's machine has CUDA and they expect GPU-accelerated Piper TTS, `onnxruntime-gpu` is needed instead. Installing both causes conflicts. This is a Dockerfile and requirements management problem, not a code problem. Must be documented and gated by hardware detection before voice is enabled.

**Risk 5 — `ResourceManager` is a stub.** The v5 `ResourceManager` has no threading, no degradation callbacks, and allocations are not actually enforced. If multiple escalation providers or voice streams attempt concurrent model loading, there is no contention guard. Acceptable now; becomes relevant when voice runs concurrently with chat inference.

---

## 10. Recommended First Execution Slice: S1 — Catalog Correction

**Scope:** `models/models.yaml` only. No code changes.

**Corrections:**
1. `whisper-stt`: change `path` to `models/ggml-base.en.bin`, change `download_url` to `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin`, keep `enabled: false`.
2. `piper-tts`: change `path` to `models/en_US-lessac-medium.onnx`, add a companion entry `piper-tts-config` with `path: models/en_US-lessac-medium.onnx.json` and same HF URL from `rhasspy/piper-voices`, both `enabled: false`.
3. Add correct `model_id` fields to both entries (`ggerganov/whisper.cpp`, `rhasspy/piper-voices`) as metadata for future `huggingface_hub` provisioning.

**Why first:** It is zero-risk (YAML, no tests break), corrects a latent data error that would cause hard failures when voice work begins, and establishes the correct reference point for all subsequent voice and provisioning slices. Every later slice (S2–S5) depends on the catalog being accurate.