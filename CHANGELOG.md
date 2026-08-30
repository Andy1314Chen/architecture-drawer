# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Ad-hoc agent-replay cases (`--agent-case <dir>`)** — replaying a case outside the frozen `evals/` set previously required adding a `gen.py` (which silently pulled it into the deterministic regression set — the two concerns were coupled by `_eval_dirs`). New `--agent-case` option: point it at any directory containing an `input.md` spec; the case runs through the full replay gate (agent authors `gen.py` in the sandbox, score ≥80 floor, quartet artifacts incl. `brief.json`) while never entering the regression set. Name collisions with frozen evals fail explicitly.

- **Design-brief contract** — `scripts/design_brief.py` + `check_design_brief` in `semantic_qa.py` + `tests/test_design_brief.py`: the Step-1 design brief is now machine-readable data (`DesignBrief`: scheme, layout `band|node`, flow `top-down|left-right|none`, `palette_role {data-node-id: (fill, stroke)}`, `flow_chain` = ordered pipeline stages, side bands excluded) and the **rendered SVG is asserted against it** — declared tint gone white FAIL, wrong/undeclared paint WARN, empty declared band FAIL (text-only bands count as content), side-band-as-chain chain-broken FAIL, ≥70% inter-layer flow dominance (real return edges tolerated), chain degree rules (first out≥1 / middle both≥1 / last in≥1), declared order vs geometry, absent brief → visible WARN (anti-freerider). `svg_utils` emits `data-node-id` on all 7 node-registering primitives (goldens regenerated: verified pure attribute insertions). `run_semantic_qa(..., brief=)`; evals write `brief.json` next to the artifact triplet (now a quartet); `--agent-replay` gates on brief.json. Capability boundary documented: verifies rendering ↔ self-declared contract, not contract ↔ user intent. Post-migration hardening: misdeclared flow axis now FAILs (`brief-flow-axis` — >=70% of inter-layer edges travel farther along the cross axis than the declared one; catches wrong-axis declarations on full-width bands where the directional-dominance ratio is skipped by design), and `layer_of` attribution expands containers by 4px so connect()'s marker-tip retraction (~1.5px into the gutter) no longer loses border-spine endpoints.
- **Agent replay** — `tests/test_agent_replay.py` + `tests/agent_backends.py`: an opt-in regression layer (`pytest --agent-replay`) that installs the skill into a leak-free sandbox (the golden `evals/` generators are never copied), lets the **Pi coding agent** (pi.dev) discover it via its native skill mechanism and self-author `gen.py` from `input.md`, then uses the harness as the deterministic gate — re-running the produced `gen.py` and asserting score ≥ `AGENT_REPLAY_MIN_SCORE` plus a full SVG/PPTX/PNG artifact triplet. Refine rounds are stateless. New CLI options `--agent-iter` (default 3), `--agent-eval <name>`, and `--agent-keep` (retain each case's sandbox under `output/agent_replay/<name>/`).
- **Semantic QA layer** — `scripts/semantic_qa.py` + `tests/test_semantic_qa.py`: a meaning-level smoke-check on the *rendered SVG* after the geometry score, for the defect classes a bounding-box evaluator structurally cannot see — dangling `marker-end` references (the `connect()` default-`arrowhead` trap, FAIL), defined-but-unused markers (WARN), declared-vs-actual canvas drift, label/host mismatch, raw rails slicing filled containers / connectors through card interiors, and text semantics vs the spec (placeholder/garbled/empty FAIL; spec-entity coverage <40% FAIL, <85% WARN). Wired into `--agent-replay` (FAILs gate the run; WARNs feed the refine prompt) and documented in `SKILL.md` §3b + capability ㉒. Also fixes the pi_agent eval's right spine, which started 24px inside the LLM API box (segments now live in the inter-band gutters).
- **Chromatic palette floor (无配色 detection, evaluator dimension ⑯)** — observed in the coarse-spec agent-replay pilot: an agent "fixed" its text-contrast WARN by de-coloring the whole diagram; the final 100-score output carried only desaturated slate tones (#546E7A/#37474F/#78909C), which pass the R==G==B neutral filter yet read as colorless. `check_palette` now FAILs any business diagram whose accents carry no readable hue (HSL saturation ≥0.25 — pastel tints count, slate/pure grays do not). SKILL.md's troubleshooting no longer suggests "revert op fills to neutral white" as a palette remedy and explicitly prohibits de-coloring as a contrast fix. Contract tests in `tests/test_evaluator.py`; all 8 goldens unaffected (7 clean, cicd keeps only its documented >8-accent WARN).
- **Step 1 — Design Brief (开工前完整设计)** in `SKILL.md`: after Step 0 classifies the requirement and before any code, the agent must produce a five-section design proposal combining the user's spec with the skill's design system — canvas & layout skeleton (relative formulas, not hard-coded coordinates), palette (one S1–S4 preset + role→tint/stroke mapping table), typography tiers, edge routing (spines outside content, solid/dashed semantics), and a risk checklist (contrast pairings, spacing/gutter budgets, the marker trap). Landing rule: the brief's tokens must land as a constants block atop `gen.py`, making the code the brief's executable form. Interactive sessions may seek a veto; headless runs print-and-proceed. Completes the coarse-spec era's contract: the skill owns design decisions, so it now states them explicitly before drawing instead of discovering them through evaluator iteration.
- **Gray-dominance detection (灰色主导, extends evaluator dimension ⑯)** — user-reported on the agent_infra replay artifact: multiple colors present but the diagram reads gray-family overall — every band/container/card neutral, chromatic color confined to a few small chips (11% of business elements, 2.3% of painted area). `check_palette` now measures chromatic coverage on two axes — element share (node-style schemes: color lives in many colored nodes) and painted-area share (band-style schemes: color lives in tinted containers) — and FAILs when BOTH are low (<35% elements AND <15% area). One strong axis is always legitimate; calibrated against all 8 goldens (each clears an axis with ≥2× margin) and the accepted vllm/satellite artifacts. Three contract tests added; suite green with thresholds untouched.
- **Doc ↔ API drift guard** — `tests/test_doc_api.py`: a deterministic, always-on test that scans fenced code blocks in `SKILL.md` + `references/*.md` for `drawer.<m>(` and asserts each exists on `SVGDrawer`, plus a curated public-module-function importability check. Catches doc ↔ API drift in the default CI gate.
- **`score_gen_script()`** in `tests/conftest.py`: shared deterministic gate for agent-produced generators (injects no `PYTHONPATH` so broken skill-path resolution surfaces as a fixable failure).
- **`--agent-keep` artifact retention** for `--agent-replay`: copies each case's sandbox (agent-written `gen.py` + SVG/PNG/PPTX + installed skill + `score_report.txt`) to `output/agent_replay/<eval_name>/`. Default off (leak-free). `output/` is gitignored.
- **First non-architecture eval case** — `evals/20260802_100000_cicd_pipeline_flow/`: a CI/CD deployment **flowchart** (process diagram). Exercises the flowchart primitives and role palette no other case touches — green `circle()` terminators, yellow `decision()` diamonds (first usage in `evals/`), orange `hexagon()` I/O, blue process `rect()`, and a purple double-border subprocess (inset `rect()`). Branches converge on a single failure terminator. Scores 96 (the only deduction is the documented, justified >8-accent role-palette WARN; hard cap is 12). Threshold locked at 96; golden SVG seeded.

### Changed
- Documented the layered test matrix in `AGENTS.md` and `README.md` (deterministic regression · spec · doc-API · agent replay).

### Removed
- **Coarse semantic eval specs** — all 8 `evals/*/input.md` rewritten to keep only the semantic content (components, layers, relations, flows, role-color vocabulary, bilingual conventions) and drop the former "Design Specification" sections (canvas size, band/node coordinate tables, equal-gap formulas, per-node W×H tokens, exact palette hex, font-tier values, stroke/marker specs). The detailed specs were the golden layouts transcribed into prose — a laundered leak that turned `--agent-replay` into a transcription test instead of a measure of the skill's text→diagram capability, and left SKILL.md's completion mode unexercised. The frozen `gen.py`/thresholds/golden snapshots are untouched (deterministic regression unaffected); side effect: every golden now covers 100% of its spec's entities, so the semantic-QA allow-list shrank to mlir's verified true positives.
- **LLM replay layer (former "Protocol A")** — `pytest --llm-replay` / `--llm-iter`, the `claude`-CLI headless generate/fix loop (`replay_gen`, `_llm_generate`, `_run_and_score`, prompt builders) in `tests/conftest.py`, and `test_llm_replay_quality`. Rationale: it replayed the skill as *pasted documentation* inside a single headless model call — no skill installation, no native discovery — so it measured doc sufficiency, not real regression behavior, and duplicated a weaker subset of `--agent-replay`. The score floor constant was renamed `LLM_REPLAY_MIN_SCORE` → `AGENT_REPLAY_MIN_SCORE` (value unchanged, 80).

### Fixed
- **Brief-contract dedup identity drop** — `_dedup_rects` in `semantic_qa.py` discarded the `data-node-id` of an identical-geometry twin (frame/body rect pair where only the second carries `node_id=`), producing a false `brief-shape-missing` FAIL + `brief-layer-undeclared` WARN + `brief-chain-broken` FAIL cascade on honest diagrams. The kept entry now ADOPTS the twin's aligned identity when it lacks one. Regression test: `test_dup_geometry_adopts_dropped_identity`.
- **Brief/render color normalization asymmetry** — `ColorSpec` normalized through `design_brief.norm_hex` (which leaves named colors as-is) while the checker normalized rendered fills through `svg_utils.normalize_color` (which resolves them): declaring `ColorSpec("gray", ...)` against a honestly rendered `fill="gray"` produced a spurious `brief-fill-mismatch` WARN. `ColorSpec` now canonicalizes via `canon_hex` (svg_utils as the single normalization source); `norm_hex` remains for pass-through tokens (`none`/`''`) that `is_plain` must recognize.
- **Brief tint predicate asymmetry** — check A decided "declared tint" with `svg_utils.is_neutral` (R==G==B hex) while the schema derives tints with `design_brief.is_plain` (white/none/empty = plain): a declared `ColorSpec("none", ...)` rendered transparent FAILed `brief-tint-lost` on an honest diagram, and a declared gray tint rendered white passed silently. The predicate is now `is_plain` (schema-consistent): `none`/white declarations are plain, gray tints count as structure color in both directions.
- **SKILL.md regression** — commit `a725445` (design-brief docs) accidentally deleted the `4. **Auto-Correction**` section header and its first ten remedy bullets (connect-for-`dangles`, `phantom`, `routes through node`, `cross`, `too close`, arrow-position/`marker_tip_depth`, font-tier convergence, palette remedies, layout), leaving the remaining six bullets orphaned under the semantic-QA code block. The section is restored byte-identical from `620c373` — it is the refine-round playbook the agent consumes.
- **Agent-replay robustness pass** on the opt-in `--agent-replay` layer:
  - The refine loop now **early-exits** when a score already past `AGENT_REPLAY_MIN_SCORE` with no `[FAIL]` items plateaus (no gain over the previous round), instead of burning every refine round — each a full agent call — chasing a 100 it isn't reaching.
  - `score_gen_script()` **timeouts** (180 s) now return a score-less `"timed out"` report so the refine loop can repair a slow/looping script, instead of aborting the whole case as an "agent run error".
  - `--agent-eval <name>` matching **no** eval case now **fails loudly** (listing the available names) instead of silently `skip`-ping green.
  - `--agent-keep` **persist failures** no longer mask the case result or leak the sandbox — the `rmtree` cleanup always runs.
  - The leak-free sandbox no longer copies `scripts/__pycache__` / `*.pyc` (`shutil.copytree` now ignores `__pycache__`).
  - Synced the agent-replay CLI flags (`--agent-iter`, `--agent-eval`, `--agent-keep`) in both READMEs.

- **`--agent-replay` opaque 403 when pi's interactive default provider lacks credentials** — `PiAgentBackend` invoked a bare `pi -p`, inheriting `~/.pi/agent/settings.json`'s default provider; with credentials present only for another provider (e.g. zai), every run failed with an upstream 403 HTML page before the agent started. The backend now pins **both** provider and model (constructor args, new `--agent-provider`/`--agent-model` pytest options, or `PI_AGENT_PROVIDER`/`PI_AGENT_MODEL` env). A bare `--model` is not enough: the same model id can exist under several configured providers (ambiguous), and `--provider` alone still uses that provider's default model. Verified end-to-end: sandbox + pinned argv → `pi -p` exits 0.

## [1.0.0] — 2026-07-30

First public release. Extracted from an internal `ppt-agent` workspace and
restructured as an installable Claude Code plugin marketplace and an Agent
Skills spec-compliant skill.

### Added
- **Claude Code marketplace packaging** — `.claude-plugin/marketplace.json` and
  `plugins/architecture-drawer/.claude-plugin/plugin.json`; install via
  `/plugin marketplace add Andy1314Chen/architecture-drawer`.
- **Agent Skills spec compliance** — `SKILL.md` frontmatter (`name` matches the
  directory, bounded `description`), relative file references only.
- **Regression test suite** (`tests/`) — runs every `evals/` generator as a
  subprocess, asserts each printed quality score meets a per-case threshold, and
  diffs the rendered SVG against a golden snapshot (`--regenerate-golden` to
  refresh). 7 cases, 7 golden SVGs.
- **Skill-spec test** — validates frontmatter, name↔directory, description
  bounds, relative references, core-script presence, and absence of hardcoded
  absolute paths.
- **README**, **MIT LICENSE**, **requirements.txt** / **requirements-dev.txt**,
  and a GitHub Actions CI workflow (`test.yml`).

### Changed
- **`SKILL.md`** rewritten to be path-agnostic: the skill's `scripts/` dir is
  resolved relative to `__file__` (never a hard-coded `/home/...` path). All
  examples and the `$SKILL` definition updated accordingly.
- **Removed `validate_output_path` / `OutputPathError`** from `svg_utils.py`.
  `save_svg`, `rasterize_svg`, and `svg2pptx.svg_to_pptx` now write wherever
  the caller asks (creating parent dirs as needed) instead of enforcing an
  `output/<task>/` directory. The prior constraint refused legitimate
  cross-project and temporary paths.
- **Removed `allow_anywhere` parameters** throughout (`svg_to_pptx`,
  `save_pptx`) since the layout gate they bypassed no longer exists.
- **All 7 generators** (`evals/*/gen.py`) ported to portable `__file__`-relative
  skill paths and de-score-gated so they always emit their SVG/PNG/PPTX triplet
  (regardless of score), making them usable as deterministic regression cases.
- The legacy lower-scoring case (`mlir_pipeline` 76) is retained at its current
  threshold — the suite records existing quality rather than retroactively
  raising the bar.

### Removed
- Debug/scratch scripts (`gen_debug.py`, `_diag.py`) — not regression material.
- Hardcoded absolute `/home/conne/git/ppt-agent/...` path references everywhere.
