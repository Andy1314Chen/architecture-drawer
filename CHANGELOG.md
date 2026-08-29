# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Agent replay** — `tests/test_agent_replay.py` + `tests/agent_backends.py`: an opt-in regression layer (`pytest --agent-replay`) that installs the skill into a leak-free sandbox (the golden `evals/` generators are never copied), lets the **Pi coding agent** (pi.dev) discover it via its native skill mechanism and self-author `gen.py` from `input.md`, then uses the harness as the deterministic gate — re-running the produced `gen.py` and asserting score ≥ `AGENT_REPLAY_MIN_SCORE` plus a full SVG/PPTX/PNG artifact triplet. Refine rounds are stateless. New CLI options `--agent-iter` (default 3), `--agent-eval <name>`, and `--agent-keep` (retain each case's sandbox under `output/agent_replay/<name>/`).
- **Semantic QA layer** — `scripts/semantic_qa.py` + `tests/test_semantic_qa.py`: a meaning-level smoke-check on the *rendered SVG* after the geometry score, for the defect classes a bounding-box evaluator structurally cannot see — dangling `marker-end` references (the `connect()` default-`arrowhead` trap, FAIL), defined-but-unused markers (WARN), declared-vs-actual canvas drift, label/host mismatch, raw rails slicing filled containers / connectors through card interiors, and text semantics vs the spec (placeholder/garbled/empty FAIL; spec-entity coverage <40% FAIL, <85% WARN). Wired into `--agent-replay` (FAILs gate the run; WARNs feed the refine prompt) and documented in `SKILL.md` §3b + capability ㉒. Also fixes the pi_agent eval's right spine, which started 24px inside the LLM API box (segments now live in the inter-band gutters).
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
