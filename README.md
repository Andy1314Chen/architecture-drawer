# architecture-drawer

English · [简体中文](README.zh_CN.md)

A skill for [Claude Code](https://code.claude.com), Codex, Open Code, Pi Agent, and other AI coding agents: turn a text description of your system architecture into an **editable PowerPoint architecture diagram**.

![License](https://img.shields.io/badge/license-MIT-blue)

---


## What it is

Turn **text descriptions** of an architecture into **editable PPT diagrams**: the agent generates an SVG from your description, auto-validates the layout, then exports to native PowerPoint shapes.

### vs. direct image generation

| | This project | Nano Banana / GPT-Image etc. |
|---|---|---|
| Output | **Editable PPT** (every shape draggable, recolorable, retextable) | Flattened image |
| Control | High (code-generated, precisely adjustable) | Low (prompt-driven, hard to reproduce) |
| Iteration | Fine-tune directly in PPT | Regenerate from scratch |
| Cost | Low | High (per-image billing) |

## Showcase


All diagrams below were generated entirely from text descriptions by the skill, then scored by the 13-dimension evaluator (each scored ≥76/100). They double as the regression suite under `evals/`.

### vLLM — High-Throughput LLM Inference Serving (PagedAttention)

![](docs/showcase/vllm_arch.png)

Six-layer request pipeline (client → API server → engine → paged KV cache → execution → optimizations). Solid edges = data flow; dashed = cache/block management. *Scheme S1 Monochrome Blue.*

### MLIR AI Compiler — Multi-Stream Execution Pipeline

![](docs/showcase/mlir_pipeline.png)

A 4-layer × multi-column matrix (graph optimization → transformation → lowering → codegen) with vertical-fusion grouping and a concurrent multi-stream overlap timeline. *8-accent categorical palette.*

### Agent Infrastructure — Layered Architecture

![](docs/showcase/agent_infra_architecture.png)

Five horizontal layers (application → orchestration → core capabilities → execution → infrastructure) with a cross-cutting security/observability band. Bilingual CN/EN labels. *Neutral grays + 5 colored core modules.*

## Best Practices

1. **Start with a clear text description.** Before coding, describe the architecture in prose—how many layers, what components each layer has, how they connect, and any special annotations. A crisp text spec (like the specs in `evals/*/input.md`) is the single biggest predictor of a quality diagram. For open-source projects, you can use the system architecture description from [DeepWiki](https://deepwiki.com).
2. **Let the skill generate.** Submit the text description to the skill and let it generate the initial `gen.py` and SVG. The evaluator automatically catches overlaps, dangles, and crossings.
3. **The skill auto-reviews the score.** If the score is ≥80, the diagram is structurally sound. If <80, the agent can automatically fix layout issues via `auto_refine` or multi-round LLM correction (`--llm-iter`).
4. **Export to PPTX for final polish.** Run `svg_to_pptx()` to get an editable PowerPoint file. Tweak colors, fonts, arrows, and layout there to match your brand or publication style—these belong in the presentation layer, not the generator code.

Suggested workflow: first discuss with DeepWiki or your agent to produce a clear text description of the system architecture, then use this skill to quickly generate a PPTX diagram, and finally fine-tune colors, labels, and other details directly in PPT.

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

Scope with `--scope project` (shared via version control) or `--scope local` (gitignored). Default is `user`.

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

## Dependencies

The agent generates a `gen.py` that imports three pure-Python modules (`svg_utils.py`, `evaluator.py`, `svg2pptx.py`) co-located in the skill. You don't write this code — the agent does. Install these once so generated diagrams can render and export:

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
└── examples/                                    # minimal demo of the generate-evaluate-export loop
```

## References & acknowledgments

The geometry/connection detection draws on several open-source projects (their reference docs and validators were studied): [ink-graph](https://github.com/qaz1230sp/ink-graph), [fireworks-tech-graph](https://github.com/yizhiyanhua-ai/fireworks-tech-graph), [svg-animations](https://github.com/supermemoryai/skills), [svg-design](https://github.com/tryopendata/skills), and [svg2pptx](https://github.com/benouinirachid/svg2pptx) (the architectural blueprint for the PPTX export module). See the full credits in [`SKILL.md`](plugins/architecture-drawer/skills/architecture-drawer/SKILL.md).

## License

MIT — see [LICENSE](LICENSE).
