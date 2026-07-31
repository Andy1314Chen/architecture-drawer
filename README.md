# architecture-drawer

English · [简体中文](README.zh_CN.md)

A [Claude Code](https://code.claude.com) skill (and standalone Python library) that generates **multi-layered technical architecture diagrams as SVG**, validates their layout with a 13-dimension quality evaluator, and exports them to **editable PowerPoint** (`pptx`) — every shape becomes a native, resizable PPT element, not a flattened image.

> Draw architecture diagrams in SVG. Export to editable PowerPoint.

[![Tests](https://github.com/conne/architecture-drawer/actions/workflows/test.yml/badge.svg)](https://github.com/conne/architecture-drawer/actions/workflows/test.yml)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## What it does

- **Author diagrams in code** — a fluent Python API (`SVGDrawer`) places rects, circles, shapes, text, and connectors with semantic node/edge registration.
- **Validate, don't assert** — a 13-check `evaluate_svg` parses the *rendered* SVG (not the API calls) to score collision, boundary, coverage, connection landing, phantom anchors, edge-through-node, crossings, spacing, font tiers, palette, text overflow, composition budget, and text-vs-shape overlaps.
- **Export to editable PPTX** — `svg_to_pptx` maps each SVG element to a native PowerPoint shape (rect→rectangle, circle→oval, line→connector, path→freeform, text→textbox), with arrow rendering, Bezier flattening, and transparency/dash injection. An image-rasterization fallback mode is included.
- **Generate → Evaluate → Correct** workflow with `auto_refine` for iterative geometric cleanup.

## Showcase

All diagrams below were generated entirely from text descriptions by the skill, then scored by the 13-dimension evaluator (each scored ≥76/100). They double as the regression suite under `evals/`.

### vLLM — High-Throughput LLM Serving with PagedAttention

![](docs/showcase/vllm_arch.png)

Six-layer request pipeline (client → API server → engine → paged KV cache → execution → optimizations). Solid edges = data flow; dashed = cache/block management. *Scheme S1 Monochrome Blue.*

### MLIR AI Compiler — Multi-Stream Execution Pipeline

![](docs/showcase/mlir_pipeline.png)

A 4-layer × multi-column matrix (graph optimization → transformation → lowering → codegen) with vertical-fusion grouping and a concurrent multi-stream overlap timeline. *8-accent categorical palette.*

### Agent Infrastructure — Layered Architecture

![](docs/showcase/agent_infra_architecture.png)

Five horizontal layers (application → orchestration → core capabilities → execution → infrastructure) with a cross-cutting security/observability band. Bilingual CN/EN labels. *Neutral grays + 5 colored core modules.*

## Install (Claude Code)

This repo is a [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces). Add it and install the plugin:

```
/plugin marketplace add conne/architecture-drawer
/plugin install architecture-drawer@architecture-drawer
```

Or from the CLI:

```bash
claude plugin marketplace add conne/architecture-drawer
claude plugin install architecture-drawer@architecture-drawer
```

Scope with `--scope project` (shared via VCS) or `--scope local` (gitignored). Default is `user`.

### Codex CLI

> Codex CLI fully supports the [Agent Skills](https://agentskills.io) directory structure.

Copy the skill directory into Codex's skills folder (usually `~/.codex/skills/`):

```bash
cp -r plugins/architecture-drawer/skills/architecture-drawer ~/.codex/skills/architecture-drawer
```

Or install project-scoped (recommended):

```bash
mkdir -p .codex/skills
cp -r plugins/architecture-drawer/skills/architecture-drawer .codex/skills/
```

Once installed, ask Codex naturally — the workflow in `SKILL.md` is consumed automatically:

```
> Draw the architecture of vLLM and export to PPTX
```

### Other agent platforms (Gemini CLI, Cursor, Copilot)

Each skill is a standalone [Agent Skills spec](https://agentskills.io) directory. Copy it into your platform's skills location (typically `.agents/skills/`):

| Platform | Default skills path |
|---|---|
| Gemini CLI | `~/.gemini/skills/` |
| Cursor (@rules) | `.cursorrules` or `cursor/skills/` |
| Copilot CLI | Per-platform instructions |

```bash
cp -r plugins/architecture-drawer/skills/architecture-drawer .agents/skills/architecture-drawer
```

## Use as a Python library (no Claude required)

The three modules under `.../skills/architecture-drawer/scripts/` (`svg_utils.py`, `evaluator.py`, `svg2pptx.py`) are plain Python — drop them on `sys.path` and import directly:

```python
import sys
sys.path.insert(0, "path/to/architecture-drawer/plugins/architecture-drawer/skills/architecture-drawer/scripts")

from svg_utils import SVGDrawer, save_svg, rasterize_svg
from evaluator import evaluate_svg
from svg2pptx import svg_to_pptx

d = SVGDrawer(1200, 800, bg="#FFFFFF")
d.arrow_head("arrow", "#333")
d.rect(100, 100, 120, 40, fill="#D5E1EB", stroke="#1B3A5C", node_id="a")
d.rect(300, 100, 120, 40, fill="#D5E1EB", stroke="#1B3A5C", node_id="b")
d.connect("a", "right", "b", "left", stroke="#1B3A5C", marker_end="arrow")

score, report = evaluate_svg(d)
print(f"Quality Score: {score}")

save_svg(d.render(), "diagram.svg")
rasterize_svg("diagram.svg", "diagram.png", width=1200)
svg_to_pptx(d.render(), "diagram.pptx")   # editable native shapes
```

### Dependencies

| Dependency | Required by | Install |
|---|---|---|
| `python-pptx >= 1.0` | PPTX export (`svg2pptx.py`) | `pip install python-pptx` |
| `rsvg-convert` | PNG rasterization (`rasterize_svg`) | `apt install librsvg2-bin` / `brew install librsvg` |
| `pytest >= 8` | Running the test suite | `pip install pytest` |

## Repository layout

```
architecture-drawer/
├── .claude-plugin/marketplace.json              # Claude Code marketplace registry
├── plugins/architecture-drawer/
│   ├── .claude-plugin/plugin.json               # plugin manifest
│   └── skills/architecture-drawer/
│       ├── SKILL.md                             # agent-consumable workflow (spec-compliant)
│       ├── scripts/                             # svg_utils.py · evaluator.py · svg2pptx.py
│       ├── references/design_specs.md           # 4 preset color schemes (S1–S4)
│       ├── evals/                               # 7 regression cases (gen.py each)
│       └── assets/
├── tests/                                       # pytest: score thresholds + SVG golden snapshots
│   ├── conftest.py
│   ├── test_regression.py
│   ├── test_skill_spec.py                       # Agent Skills spec compliance
│   └── golden/*.svg                             # snapshot baselines
└── examples/                                    # minimal standalone usage examples
```

## Regression test suite

The 7 diagrams under `evals/` double as a regression suite. Each `gen.py` is run as a subprocess; its printed quality score must meet a per-case threshold, and its rendered SVG must match a golden snapshot under `tests/golden/`.

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest                      # 7 tests, all green
pytest --regenerate-golden  # refresh snapshots after an accepted change
```

The suite **locks in current quality** — it catches degradation, it does not retro-raise the bar on legacy generators written before later-added checks (e.g. text-overlap). Bump a threshold only after intentionally improving that generator.

### LLM replay (opt-in, non-deterministic)

The default suite tests the **engine** (SVGDrawer + evaluator + svg2pptx) against frozen `gen.py` scripts. To also test the skill's core promise — *turn a text description into a compliant diagram* — each eval ships an `input.md` spec. Run the LLM replay gate:

```bash
pytest --llm-replay                 # multi-round: generate -> evaluate -> correct
pytest --llm-replay --llm-iter 5    # allow more correction rounds (default 3)
```

This mirrors a real Claude Code session using the skill: an LLM generates an initial `gen.py` from **only** `input.md` + `SKILL.md` (anti-leakage — the golden SVG is never provided), runs it, and if the score is below target or there are `[FAIL]` items, feeds the evaluator report back to the LLM for a fix (coordinates/layout adjustments — exactly what `auto_refine` cannot do), looping until target or max rounds. Asserts the best score clears a flat floor (≥80). Requires the `claude` CLI. Run locally or nightly, **not** in the PR gate.

## References & acknowledgments

The geometry/connection detection draws on several open-source projects (their reference docs and validators were studied): [ink-graph](https://github.com/qaz1230sp/ink-graph), [fireworks-tech-graph](https://github.com/yizhiyanhua-ai/fireworks-tech-graph), [svg-animations](https://github.com/supermemoryai/skills), [svg-design](https://github.com/tryopendata/skills), and [svg2pptx](https://github.com/benouinirachid/svg2pptx) (the architectural blueprint for the PPTX export module). See the full credits in [`SKILL.md`](plugins/architecture-drawer/skills/architecture-drawer/SKILL.md).

## License

MIT — see [LICENSE](LICENSE).
