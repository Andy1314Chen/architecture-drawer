# Experiment Summary

Running log of work on architecture-drawer. Append newest to the top. Mark
`BLOCKED` for external blockers; record outcomes (success **and** failure).

## 2026-08-29 — agent-replay unblocked (provider pinning + timeout banking); coarse-spec pilot PASSES

**BLOCKED → resolved.** `--agent-replay` died with an opaque upstream 403 HTML
page before the agent even started. Diagnosis: `PiAgentBackend` invoked a bare
`pi -p`, inheriting `~/.pi/agent/settings.json`'s `defaultProvider=deepseek`
while `auth.json` holds credentials only for **zai**. A bare `--model` is NOT a
fix (glm-4.7 exists under 4 configured providers → ambiguous), and `--provider`
alone still uses that provider's default model (also 403). Fix (72e9b7b): pin
**both** — `--agent-provider`/`--agent-model` options, constructor args, or
`PI_AGENT_PROVIDER`/`PI_AGENT_MODEL`. Working combo on this machine:
`--agent-provider zai --agent-model glm-4.7` (smoke: `pi -p` → PONG, exit 0).

**Second harness defect found by the first pilot:** round-0 ran 1802s, hit the
1800s subprocess timeout, and the case aborted as "agent run error" — although
the agent had already written a gen.py gating at **88** (0 FAIL, one contrast
WARN, semantic QA clean). The old timeout was calibrated for the detailed-spec
era (~912s worst); coarse-spec rounds legitimately take 45+ min of real design.
Fix (bc08332): `AgentBackend.timeout` 1800→3600, and `run()` converts
TimeoutExpired into a synthetic returncode-124 CompletedProcess so the harness
scores the on-disk gen.py and the refine loop repairs it (same contract as
`score_gen_script`). Verified in-process (1s timeout → 124 + message).

**Coarse-spec pilot result (vllm, zai/glm-4.7, --agent-keep):** PASSED in
1947s — final score **100** (0 FAIL / 0 WARN), semantic QA 100/clean, full
SVG/PNG/PPTX triplet; deterministic re-gate of the retained sandbox confirms.
Discriminative-power evidence vs the detailed-spec era: the killed round-0
took ~45 min of genuine self-design (own canvas 1400×1200 vs golden 1240×970,
own blue-family palette) landing at 88-with-contrast-WARN — then refine closed
it to 100. The replay now measures text→diagram capability, not transcription.

## 2026-08-29 — eval specs rewritten to coarse semantic form (de-specification)

**Problem (maintainer decision):** all 8 `evals/*/input.md` carried a
"Design Specification" half that was the golden `gen.py` transcribed into
prose — band/node y-coordinate tables (cicd listed all 13 spine y-centers),
per-node W×H token tables (vllm), the equal-gap formula `(730−n·cardW)/(n+1)`
(pi_agent), exact hex palettes, font tiers, rx/stroke-width specs. The golden
SVG is deliberately kept out of the agent-replay sandbox as an anti-leakage
measure, but a spec encoding the golden's geometry is the same information in
prose form — the replay measured "transcribe a complete layout recipe into
DSL", not the skill's text→diagram capability, and SKILL.md's completion mode
was never exercised (every spec hit faithful mode). Corroborating signal:
6-7/7 cases scored 100 on the first agent round — no discriminative power.

**Change:** each input.md now keeps only semantics (components, layers,
relations, flows, role-color vocabulary, bilingual conventions, real-vs-
decorative edge distinctions) and ends with an explicit hand-off: layout,
palette, typography and geometry are the skill's to design per its design
system. Deterministic layer untouched: frozen `gen.py`, SCORE_THRESHOLDS and
golden snapshots all unchanged.

**Side effect:** golden diagrams now cover 100% of each coarse spec's
bold/backtick entities — the former `spec-entities-partial` warns on
satellite/vllm/cicd/pi_agent came from design-token backticks the diagrams
rightly don't reproduce. Semantic-QA allow-list shrank to mlir's verified
true positives (unused `ag` marker + 6 empty texts).

**Verification:** `pytest -q` green (66 passed, 1 opt-in skip) before and
after; per-eval semantic codes printed directly to confirm the allow-list
matches reality. **Expected next `--agent-replay` run:** first-round scores
drop, refine rounds become meaningful, wall time per case rises — that is
the test regaining signal, not a regression.

## 2026-08-29 — removed the LLM-replay layer (former "Protocol A")

**Decision (maintainer):** drop `pytest --llm-replay` / `--llm-iter` entirely.
Rationale: the layer replayed the skill as *pasted documentation* inside a
single headless `claude -p` call — no skill installation, no native discovery,
no agent tooling — so it measured SKILL.md doc sufficiency, not real
regression behavior. `--agent-replay` (real install + Pi-native discovery +
self-authored gen.py) covers the same anti-leakage contract one layer closer
to real usage; the headless layer was a weaker duplicate.

**Removed:** `replay_gen` / `_llm_generate` / `_run_and_score` /
`_build_replay_prompt` / `_build_refine_prompt` / `_extract_code` in
`tests/conftest.py` (+ the `--llm-replay`/`--llm-iter` options, `llm_replay`
marker, now-unused `os`/`shutil`/`tempfile` imports), `test_llm_replay_quality`
in `tests/test_regression.py`, the stale `replay_out/` .gitignore entry, and
all doc references (both READMEs, CHANGELOG Unreleased, AGENTS.md,
`agent_backends.py` docstring cross-ref). **Renamed** the shared floor
constant `LLM_REPLAY_MIN_SCORE` → `AGENT_REPLAY_MIN_SCORE` (value unchanged,
80) so no symbol names a deleted feature.

**Verification:** `pytest -q` → 66 passed, 1 opt-in skip (agent-replay only;
the llm-replay skip is gone). `pytest --llm-replay` now fails with
"unrecognized arguments". Grep confirms zero remaining code/doc references —
only this log and the CHANGELOG Removed entry mention the old names.


## 2026-08-29 — semantic-QA layer + pi_agent spine fix

**Semantic-QA layer** (`scripts/semantic_qa.py`, 940 lines): meaning-level
smoke-check on the rendered SVG after the geometry score. Five check families:
dangling marker refs (FAIL — the `connect()` default-`arrowhead` trap where
every arrowhead silently vanishes), unused markers (WARN), canvas size drift,
label/host mismatch, rails slicing filled containers / connectors through
cards, text semantics vs spec (placeholder FAIL; entity coverage <40% FAIL /
<85% WARN). Parses the raw SVG incl. grouped shapes and composite arcs; the
registry evaluator is structurally blind to all five (rails are never
registered as edges; `role='layer'` containers never registered as nodes).
Wired into `--agent-replay` (FAILs gate; WARNs feed refine) and SKILL.md §3b.
21 tests in `tests/test_semantic_qa.py` incl. the exact production trap and a
clean-pass guarantee over every golden eval SVG (allow-list: mlir's verified
unused `ag` marker; spec-entities-partial on 4 evals where the diagram
reasonably paraphrases the spec wording).

**pi_agent spine fix**: the right AgentEvent spine's first segment started
24px inside the LLM API box and crossed band fills; segments now live in the
inter-band gutters (first segment still kisses 8px into the LLM box — known
residual, see below).

**Known residuals (deliberately not fixed yet):** (1) gen.py's comment claims
"kisses the LLM box's TOP edge (LLMY+8)" but LLMY+8 is 8px *inside* the box,
and input.md says "NEVER cross into the LLM box interior" — comment/spec
wording vs geometry disagree by 8px (under the checker's 24px threshold);
(2) semantic FAILs are not fed into the agent-replay refine prompt — only
WARNs are — so a round-0 semantic FAIL on a geometrically-perfect diagram
fails the case without the agent getting a repair chance.

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
