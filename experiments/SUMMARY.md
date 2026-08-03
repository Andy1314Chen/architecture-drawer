# Experiment Summary

Running log of work on architecture-drawer. Append newest to the top. Mark
`BLOCKED` for external blockers; record outcomes (success **and** failure).

## 2026-08-02 — agent-replay regression layer (Protocol B, Pi backend)

**Goal:** add a regression path that installs the skill into a real coding
agent and gates its self-authored `gen.py` deterministically — closest to real
editor usage.

**Decision: switched backend from opencode → Pi coding agent (pi.dev).**
opencode's `.claude/skills` discovery is disputed (issue #6266) and versioned
flags drifted across sources. Pi's contract is authoritative and stable:
- print mode `pi -p "<prompt>"` (verified end-to-end: exit 0, clean stdout);
- `--skill <path>` loads the skill additively and **bypasses the project-trust
  gate** (`-a`), so the load works in a fresh untrusted sandbox;
- `.pi/skills/<name>/SKILL.md` project discovery + `AGENTS.md` context file;
- default tools read/write/edit/bash/grep/find/ls, no permission pop-ups.

**Delivered:**
- `tests/agent_backends.py` — `AgentBackend` ABC + `PiAgentBackend` +
  `prepare_sandbox()` (leak-free: copies `SKILL.md`+scripts/references/assets
  only, never `evals/`; drops target `input.md` + `AGENTS.md` hint at root;
  `git init`s the sandbox).
- `tests/test_agent_replay.py` — opt-in `--agent-replay`, stateless refine
  loop, asserts score ≥80 + SVG parseable + PPTX opens with shapes + PNG
  non-empty (per-case rsvg tolerance).
- `tests/test_doc_api.py` — deterministic doc↔API drift guard (always on).
- `conftest.py`: `--agent-replay`/`--agent-iter`/`--agent-eval`, `agent_replay`
  marker, `score_gen_script()` (no PYTHONPATH injection).
- Docs: AGENTS.md, README.md, CHANGELOG.md updated; test matrix documented.

**Anti-leakage invariant preserved:** golden `gen.py`/SVG never enter the
sandbox (matches Protocol A's `_build_replay_prompt` rationale). Verified by
smoke test: `evals/` absent, `gen.py` absent from skill, only target
`input.md` present.
**Verification (this machine):**
- `pytest -q`: all green, 2 opt-in skips (llm/agent replay).
- `pytest tests/test_doc_api.py -v`: 2 passed.
- Sandbox shape smoke test: leak-free, layout correct.
- `pi -p --no-session "..."`: exit 0.
- **End-to-end agent run:** PASSED — `pytest --agent-replay --agent-eval 20260728_153000_agent_infra_architecture --agent-iter 1` (534s): Pi discovered the installed skill, authored `gen.py`, scored ≥80, and the harness verified SVG XML-parseable + PPTX opens with shapes + PNG non-empty.
- **Full 7-case regression (iter=1, zai/glm-5.2, parallel):** PASSED — all 7 evals ≥80 + artifact triplet verified. Per-case wall time: llm_inference_arch 465s, satellite_arch 567s, llama_cpp_arch 684s, mlir_pipeline 688s, agent_infra_architecture 641s, pi_agent_architecture 912s, vllm_arch 912s. Total parallel wall time 864s (7 cases run concurrently as separate `--agent-eval` jobs). Confirms the post-fix chain (per-case try/except isolation, mtime artifact selection, missing-gen.py-aware refine prompt).

**Followup — `--agent-keep` artifact retention:** original design deleted every
sandbox after gating (leak-free but unrecoverable). Added an opt-in
`--agent-keep` that persists each case's sandbox (agent-written `gen.py` +
SVG/PNG/PPTX + `score_report.txt`) under `output/agent_replay/<name>/`
(gitignored). Default behavior unchanged. Verified live: single-case run →
`output/agent_replay/20260728_153000_agent_infra_architecture/` populated,
score 100, all artifacts present.

**Full 7-case + keep run (iter=1, zai/glm-5.2, parallel, 1200s wall):** 6/7
score 100 first try; `pi_agent_architecture` flaked — round-0 pi process
exceeded the 1200s `PiAgentBackend.timeout` and was killed before writing
`gen.py`. try/except isolation worked: only that case failed, 6 others passed.
`--agent-keep` retained the empty failed sandbox for diagnosis. **Raised
`PiAgentBackend.timeout` 1200s → 1800s** (covers ~912s worst observed + model
variance). **Retry of the failed case alone: score 100, 900s** — confirmed
flake (model/Provider latency variance), not a stable failure. All 7 cases now
score 100 with artifacts retained under `output/agent_replay/<name>/`.

## 2026-08-02 — agent/LLM-replay hardening pass (issues 1–6)

Reviewed 6 reported issues against the opt-in `--agent-replay`/`--llm-replay`
layers; all confirmed. Fixed in one pass:

- **Plateau early-exit** (Protocol A `replay_gen` + B loop): stop refining once
  a score past `LLM_REPLAY_MIN_SCORE` has no `[FAIL]` and no gain over the prior
  round — a stable ~95 no longer burns every refine call. Verified in-process:
  fake backend stuck at 95 → 2 calls (1 initial + 1 refine) instead of 4;
  monotonic 88→94→99→100 still consumes all rounds.
- **Timeout → refine feedback** (`score_gen_script`/`_run_and_score`, 180 s):
  `TimeoutExpired` now returns `(None, "timed out…")` so a slow/looping script
  is repairable instead of aborting the whole case as "agent run error".
- **`_persist_sandbox` finally-leak**: persist failure no longer skips the
  `rmtree` (try/except around persist; cleanup always runs).
- **`--agent-eval` typo → fail**: an unmatched name now fails loudly (listing
  candidates) instead of silently `skip`-ping green.
- **Sandbox `__pycache__` leak**: `copytree` now `ignore`s `__pycache__`.
- **Doc drift**: `--agent-iter`/`--agent-keep` synced in both READMEs.

Verification: `pytest -q` green (2 opt-in skips); in-process functional checks
of the timeout branch + plateau early-exit pass.

## 2026-08-02 — first flowchart eval case (cicd_pipeline_flow)

Added `evals/20260802_100000_cicd_pipeline_flow/` — the first non-architecture
diagram in the suite. All 7 prior cases are system/cloud architecture; none
used `decision()` (diamond) or the flowchart role palette.

- **Coverage gained**: green `circle()` terminators, yellow `decision()`
  diamonds (zero prior usages), orange `hexagon()` as I/O, blue process
  `rect()`, purple double-border subprocess (decorative inset `rect()` with
  `role="decoration"`). Two decision diamonds branch "No" left and converge on
  one shared failure terminator.
- **Score: 96.** Every check PASS except the palette WARN (-4): the 5-role
  flowchart palette = 10 accent hex values > `max_colors=8`. This is the
  documented, justified >8 scheme (hard cap 12, no FAIL) — the case locks in
  that the WARN path is non-fatal and the role palette is evaluator-clean.
- **Two layout traps hit & fixed** (score 48 → 96 in one pass):
  1. Terminator labels drawn INSIDE the circles tripped the text-overlap check
     (text-on-own-shape) → labels now placed OFF the circle (right of spine /
     left of failure column).
  2. 是/否 branch flags sat ON the edge lines → both text-overlap AND
     edge-through-text. Fixed by auto-detecting edge axis and offsetting
     perpendicular (vertical edge → label right; horizontal edge → label above).
- **Determinism**: gen.py output is byte-identical across runs (gen==golden).
Threshold locked at 96; golden seeded; `pytest -q` green.

## Conventions
- Dates ISO. Newest first.
- BLOCKED items: state the external blocker + what unblocks it.
- Per `~/.claude/CLAUDE.md`: failures are as valuable as successes — record them.
