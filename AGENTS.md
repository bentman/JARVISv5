# AGENTS.md: Agent Operating Contract for JARVISv5

This file is the authoritative operating contract for all AI (and Human) Agents in this repository.

## 1. Highest Priority Rule: Python Environment Isolation

- All Python commands must use `backend/.venv`.
- Never use global Python packages for this project.
- Never install Python dependencies globally.

Dependency source of truth:

- `backend/requirements.txt` is the single source of truth for backend Python dependencies.
- Any backend dependency add, remove, or version change must update `backend/requirements.txt` in the same task.
- `backend/requirements.txt` entries must be grouped with clear category headers by backend area (for example: `# backend/core`, `# backend/main`, `# backend/memory`).
- Default version operator is `>=`.
- Use `==` only when there is a strong, explicit reason and it is documented in the task evidence.

Required command pattern:

- Windows PowerShell:
  - `backend/.venv/Scripts/python <command>`

If the virtual environment is missing:

- Create: `python -m venv backend/.venv`
- After creating the virtual environment, always upgrade pip in that environment:
  - `backend/.venv/Scripts/python -m pip install --upgrade pip`
- Then install dependencies:
  - `backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`

If `backend/.venv` is broken or inconsistent, stop and report minimal repair steps before continuing.

## 2. Core Operating Constraints

- Do not guess. If something cannot be verified from repository evidence, state what was checked and stop.
- Do not claim completion without reproducible evidence.
- Do not expand scope beyond the explicit request.
- Do not create new repo artifacts unless explicitly requested.
- Do not introduce parallel architectures, shadow systems, or alternate workflows.
- Prefer existing repository patterns and minimal diffs.
- Keep output concise and evidence-focused.

Programming principles (non-negotiable):

- Reinforce existing patterns: before adding new structure, reuse existing repository patterns for file placement, naming, command flow, and validation approach. If no pattern exists, propose the smallest consistent extension.
- Test-Configure-Install: for dependency or runtime setup, test if present, configure if exists, install if missing. For updates, always reconfigure and re-validate.
- KISS: keep implementations simple, direct, and easy to follow.
- Idempotency: commands and changes must be safe to re-run without unintended side effects.
- DRY: reuse shared logic and existing utilities; avoid duplicating logic.
- YAGNI: add only what is required for the current approved scope.
- Separation of concerns: each module or change addresses one responsibility.
- Deterministic operations: prioritize efficient, repeatable, and deterministic command sequences and outcomes.

## 3. Deterministic Execution Rules

- Execution must be deterministic and approval-gated.
- Use explicit, reproducible command sequences.
- Prefer non-interactive command flags and explicit paths to keep runs reproducible.
- Use smallest viable validation first, then broaden only when required.
- If repeated attempts do not change failure mode, stop and report.
- Do not silently iterate after failed validation.

## 4. Approval-Gated Change Control

Before editing, provide a short proposal and wait for explicit approval when work touches any of the following:

- Multiple files
- Core backend systems
- Tests or validation harnesses
- Docker/compose surfaces
- Dependency changes
- Environment repair steps

Proposal format:

- Files to modify
- Commands to run
- Expected evidence

Then stop until approved.

## 5. Authoritative Truth Sources

Use this precedence order:

1. `AGENTS.md`
2. `Project.md`
3. `SYSTEM_INVENTORY.md`
4. `CHANGE_LOG.md`

If a conflict is observed between files and runtime behavior, report the conflict and propose the smallest correction.

## 6. Task Execution Workflow

Apply Section 2 programming principles at each step.

For each task:

1. Discover: identify smallest relevant file set and validation path.
2. Confirm scope and constraints.
3. Propose when required by Section 4.
4. Implement only approved changes.
5. Validate with explicit commands.
6. Report exact outcomes with minimal proof.
7. Stop when objective is complete.

Python test expectation:

- Add or maintain a standard `pytest` test for almost every backend `*.py` module.
- Place tests under `tests/unit`, `tests/integration`, or `tests/agentic` as appropriate.
- For scoped tasks, required tests apply to changed/affected modules; broad repository backfill is separate scope unless explicitly requested.
- Minimum bar: import/structure validation for the module.
- Preferred bar: behavior/function validation for the module.

Do not add follow-up work unless explicitly requested.

## 7. Validation Requirements

General:

- Validation must test observable behavior.
- Include exact command(s) and outcome (`PASS`, `FAIL`, `SKIPPED`, or equivalent).
- Include a minimal output excerpt needed to prove the claim.
- Validation evidence should confirm repeatability for deterministic operations (same command path, same expected result class).
- If command output is inherently non-deterministic, validate using stable assertions and expected outcome class.

Backend:

- Run Python validation via `backend/.venv/Scripts/python`.
- Primary harness: `scripts/validate_backend.py`.
- Tests are under `tests/unit`, `tests/integration`, and `tests/agentic`.
- Standard test command pattern:
  - Targeted first: `backend/.venv/Scripts/python -m pytest tests/unit -q` (or matching integration/agentic path for scope)
  - Full suite when required by scope: `backend/.venv/Scripts/python -m pytest tests/`
- Coverage expectation: maintain pytest coverage for almost every backend `*.py` file; minimum import/structure test, preferably function/behavior test.

Frontend:

- Use existing project-defined commands and runtime surfaces.
- Do not invent alternate tooling paths.

Warnings:

- Treat warnings as backlog unless they break correctness, safety, or required behavior.

## 8. File and Artifact Boundaries

- Keep runtime artifacts out of repository root.
- Use existing project locations for generated data (for example, `data/` and project-defined paths).
- Do not introduce new storage locations without explicit approval.
- Ensure ignore rules cover generated artifacts when changes require it.

## 9. CHANGE_LOG.md Requirements

`CHANGE_LOG.md` is append-only and records completed, verified work.

Rules:

- Never rewrite or delete prior entries.
- Maintain entries in descending chronological order (newest first).
- Add new entries directly under `## Entries`.
- Log only after validation evidence exists.
- Use factual, past-tense statements.
- If prior record is inaccurate, append a corrective entry; do not edit history.

Minimum entry content:

- Timestamp
- Short summary of what changed
- Scope (files/areas)
- Evidence (exact command(s) run + minimal excerpt pointer or excerpt)

## 10. SYSTEM_INVENTORY.md Requirements

`SYSTEM_INVENTORY.md` is the capability truth ledger.

Rules:

- Record only observable repository artifacts (files, directories, executable code, configuration, scripts, explicit UI text).
- Do not include intent, plans, or inferred behavior.
- One component entry equals one observed capability/feature.
- New capabilities must be added at the top under `## Inventory` and above `## Observed Initial Inventory`.
- Corrections and clarifications must be added only below `## Appendix`.
- Required entry fields:
  - Capability: brief descriptive component name with date/time
  - State: `Planned`, `Implemented`, `Verified`, `Deferred`
  - Location: relative file path(s)
  - Validation: method and/or relative script path(s)
  - Notes: optional, one line max
- Do not promote state without validation evidence.

## 11. Git Safety Rules

Never run destructive git operations without explicit approval, including:

- `git restore`
- `git reset`
- `git clean`
- `git rebase`
- history rewrites

If rollback is requested, propose the safest approach based on whether changes are committed or uncommitted.

## 12. Reporting Format for Agent Responses

When reporting completion or progress, use:

- Summary
- Files inspected and changed
- Commands executed and outcomes
- Minimal evidence excerpt
- Stop (unless next action is explicitly requested)

Do not state or imply verification without corresponding command evidence.
