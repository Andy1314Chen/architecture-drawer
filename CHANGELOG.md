# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-30

First public release. Extracted from an internal `ppt-agent` workspace and
restructured as an installable Claude Code plugin marketplace and an Agent
Skills spec-compliant skill.

### Added
- **Claude Code marketplace packaging** — `.claude-plugin/marketplace.json` and
  `plugins/architecture-drawer/.claude-plugin/plugin.json`; install via
  `/plugin marketplace add conne/architecture-drawer`.
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
