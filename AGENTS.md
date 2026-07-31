# Repository Guidelines

## Project Overview

A skill for [Claude Code](https://code.claude.com), Codex, and other AI coding agents that turns text descriptions into **multi-layered technical architecture diagrams as SVG**, validates their layout with a 13-dimension quality evaluator, and exports them to **editable PowerPoint** (PPTX) — every shape becomes a native, resizable PPT element.

Core value proposition: draw architecture diagrams in code via a fluent Python API, validate the rendered SVG (not just the API calls), and export to native editable shapes.

## Architecture & Data Flow

Three-layer pipeline:

1. **Build** — `svg_utils.SVGDrawer` emits SVG XML and maintains semantic `Node`/`Edge` registries plus an affine transform stack.
2. **Evaluate** — `evaluator.evaluate_svg()` parses **both** the registries and the rendered SVG string (regex-heavy) to apply ~13 quality checks (collision, boundary, coverage, connections, crossings, typography tiers, palette, text overflow, composition).
3. **Export** — `svg2pptx.svg_to_pptx()` walks the SVG tree and maps each element to a native `python-pptx` shape with EMU coordinate conversion.

> **Critical pattern**: The evaluator is *render-then-parse*. It does not trust the API registries alone; it re-parses the actual SVG output. When editing, changes must keep both the internal registries and the emitted XML consistent.

## Key Directories

| Path | Purpose |
|------|---------|
| `plugins/architecture-drawer/skills/architecture-drawer/scripts/` | Core source (`svg_utils.py`, `evaluator.py`, `svg2pptx.py`) |
| `plugins/architecture-drawer/skills/architecture-drawer/evals/` | 13 regression generators, each in its own `gen.py` |
| `plugins/architecture-drawer/skills/architecture-drawer/references/` | Preset color schemes (S1–S4) in `design_specs.md` |
| `tests/` | pytest suite: spec compliance + regression snapshots |
| `examples/` | Minimal demo of the generate-evaluate-export loop (`hello_arch.py`) |
| `.github/workflows/` | CI configuration |

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run all tests
pytest

# Regenerate golden SVG snapshots after an accepted visual change
pytest --regenerate-golden

# Run a single eval generator
python plugins/architecture-drawer/skills/architecture-drawer/evals/20260730_vllm_arch/gen.py

# Run the demo (generate-evaluate-export)
python examples/hello_arch.py
```

## Code Conventions & Common Patterns

### Module coupling
All three core modules are tightly coupled and share via `sys.path` insertion. Eval generators resolve `$SKILL` relative to themselves:

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
```

### Node & Edge semantics
For the evaluator to validate connections, drawing code must register connectable shapes as **nodes** and connections as **edges**:

```python
# Register a node (rect)
drawer.rect(100, 100, 120, 40, fill=..., stroke=..., node_id="api", node_kind="op")

# Register a junction (circle)
drawer.circle(200, 150, 6, fill=..., node_id="jn", node_kind="junction")

# Register an edge (auto-snaps to node borders)
drawer.connect("api", "right", "jn", "left", stroke=..., marker_end="arrow")
```

### Transform stack
`group(transform)` contexts accumulate an affine matrix. Nodes/edges drawn inside are registered in **absolute coordinates**:

```python
with drawer.group("translate(100,50) rotate(30)"):
    drawer.rect(...)   # registered in global space
```

### Semantic roles
Elements accept `role="node|edge|decoration|legend|background"`. `decoration`/`legend`/`background` are excluded from business checks (spacing, collision, palette).

### Design-system constraints (enforced by evaluator)
- **Font tiers**: 3–4 per diagram (e.g., 20 / 14 / 12 / 10), adjacent tiers ≥1.15× apart.
- **Palette**: ≤8 accent colors (≤12 with justification). Prefer preset schemes from `references/design_specs.md`.
- **Background**: defaults to white (`#FFFFFF`). Dark themes must declare explicitly.
- **Node spacing**: same-kind nodes ≥14 px apart.
- **Container gutter**: ≥20 px margin inside containers.

### Error handling
The evaluator returns `(score, report)` tuples rather than raising. `auto_refine(drawer, target_score=100, max_iter=3)` reads the report and iteratively fixes geometric issues (gutter nudges, spacing spreads). Complex issues (dangles, crossings, route-through) still need manual intervention.

### No async / no type checker
Code is synchronous Python. No `async`/`await`, no mypy configuration, no linting or formatting tools are set up.

## Important Files

| File | Role |
|------|------|
| `plugins/architecture-drawer/skills/architecture-drawer/scripts/svg_utils.py` | `SVGDrawer` DSL, primitives, collision helpers, affine math, rasterization via `rsvg-convert` |
| `plugins/architecture-drawer/skills/architecture-drawer/scripts/evaluator.py` | Quality engine: 13 checks, scoring, `auto_refine()` |
| `plugins/architecture-drawer/skills/architecture-drawer/scripts/svg2pptx.py` | PPTX exporter: native shapes + raster fallback, arrow rendering, XML transparency/dash injection |
| `SKILL.md` | Agent-consumable workflow spec with YAML frontmatter |
| `tests/conftest.py` | Shared fixtures, score-threshold map, `--regenerate-golden` / `--llm-replay` CLI options, `replay_gen()` |
| `tests/test_regression.py` | Two tests: deterministic quality+snapshot (frozen `gen.py`) and opt-in LLM replay (`input.md` → regenerate → score floor) |
| `tests/test_skill_spec.py` | Agent Skills spec compliance (frontmatter, naming, file references) |

## Runtime/Tooling Preferences

- **Runtime**: Python 3 (CI targets 3.13)
- **Package manager**: `pip`
- **Runtime dependency**: `python-pptx >= 1.0`
- **Test dependency**: `pytest >= 8`
- **System dependency**: `librsvg2-bin` (provides `rsvg-convert` for PNG rasterization)
- **No build step**: pure Python, no compilation
- **No configured linter/formatter/type-checker**

## Testing & QA

- **Framework**: pytest
- **Test files**: `tests/test_skill_spec.py` (spec compliance), `tests/test_regression.py` (end-to-end regression)
- **Regression approach**: each eval `gen.py` is run as a black-box subprocess; stdout is parsed for a quality score (regex-matching several label variants), which is asserted against a per-case threshold. The rendered SVG is diffed against a golden snapshot under `tests/golden/`.
- **LLM replay (opt-in, anti-leakage, multi-round)**: `pytest --llm-replay [--llm-iter N]` mirrors a real Claude Code session — generate `gen.py` from **only** `input.md` + `SKILL.md` (golden SVG excluded to prevent reverse-transcription), run it, and if below target or with `[FAIL]` items, feed the evaluator report back to the LLM for coordinate/layout fixes (what `auto_refine` cannot do), looping up to N rounds (default 3). Asserts best score clears `LLM_REPLAY_MIN_SCORE` (≥80). Generated code runs sandboxed. Local/nightly only; skipped by default.
 - **CI**: GitHub Actions on `ubuntu-latest`, Python 3.13, installs `librsvg2-bin`, runs `pytest -v`.
