---
name: architecture-drawer
description: Generates complex, multi-layered technical architecture SVGs from text descriptions. Features intelligent layout constraints, overlap detection, connection/arrow validation, and quality evaluation to ensure professional, polished output.
---

# SVG Architecture Drawer (Smart Version)

This Skill converts complex technical descriptions into structured SVG architecture diagrams. It integrates layout constraints, collision detection, **connection/arrow connectivity validation**, and quality evaluation, automatically identifying and guiding the correction of layout errors.
The script directory (referred to as `$SKILL` below) is this skill's own
`scripts/` folder. From a generator script that lives next to its artifacts,
resolve it relative to the script's own location (never hard-code an absolute
path, which breaks on other machines):

```python
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
# From evals/<name>/gen.py -> ../../scripts ; adjust depth for your layout.
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
```

## Core Workflow: Generate-Evaluate-Correct

1. **Content Parsing & Planning**:
   - Identify layers, components, and flow direction.
   - Determine canvas dimensions (default 1200x800).

2. **Coding & Layout**:
   - Write a Python script calling `$SKILL/svg_utils.py`.
   - **Required**: use `drawer.check_collisions()` to check overlaps; use the semantic API (below) to register nodes and edges so connections can be auto-validated.

3. **Quality Evaluation**:
   - Call `evaluate_svg(drawer)` from `$SKILL/evaluator.py`.
   - Evaluation dimensions: ① **Containment-aware** element overlap detection (parent-child nesting does not count as a collision); ② boundary checks; ③ canvas coverage; ④ **connection/arrow connectivity** (endpoints must land on registered node borders, 12px tolerance; also detects degenerate zero-length edges and duplicate edges); ⑤ **phantom anchor detection** (nodes referenced by edges but invisible); ⑥ **edge-routes-through-node** (edges must not pass through the interior of a non-endpoint node, 3px inset); ⑦ **edge crossing** (two edge segments intersecting internally); ⑧ **same-kind node minimum spacing** (Euclidean distance between op/junction nodes ≥ 14px); ⑨ **font-size tier detection** (parse SVG to extract all `font-size` values, deduplicate to ≤4 tiers, adjacent tiers must be ≥1.15× apart — prevents accidental micro-steps like 11/12/13/14); ⑩ **palette detection** (accent colors ≤8 warning, ≤12 hard limit; coexistence of very dark L<0.2 and very light L>0.8 accents is flagged as a conflict; background defaults to light); ⑪ **text overflow detection** (parse all `<text>` elements' true geometry, estimate text width by font metrics: overflowing the canvas = FAIL, text wider than its container [smallest rectangle containing the text center] = WARN — closes the blind spot of text drawn via `add_element` that doesn't enter `bboxes` and is invisible to collision/boundary checks); ⑫ **composition quality budget** (ported from fireworks `assess_composition`: ≤2 bends per edge, path stretch ratio ≤1.35, container gutter ≥20px, shortest path segment ≥16px; **text as a measurable obstacle** — edge segments passing through a `<text>` bbox = FAIL, systematically eliminating "text crossed/covered by edges"; gutter is only checked for nodes fully contained within a container, cross-band nodes are not false-flagged). ⑨⑩⑪⑫ **parse the actual SVG** rather than relying on API calls, so they work equally well for raw `add_element` drawing.
   - ⑬ **text-vs-shape & text-vs-text overlap detection** (`check_text_overlaps`): parses every `<text>` bbox (center model, `dominant-baseline="central"`) against all visible circles/rects/polygons/lines/paths AND against other `<text>` — closes the registry blind spot where `bbox=False` text/shapes and `add_element` shapes are invisible to `check_collisions`. Legend/background shapes, the full-canvas bg rect, and rects fully containing the text (intentional in-box labels) are exempt. Like ⑨⑩⑪⑫, this **parses the actual SVG** rather than trusting the API.

4. **Auto-Correction**:
   - If the evaluation score is below **80**, analyze the `[FAIL]` items in the report.
   - Connection issues (`dangles` / `Degenerate edge` / `overlaps`): use `drawer.connect(...)` to let endpoints auto-snap to node borders; avoid manually computing offset coordinates.
   - `phantom` (phantom anchors): the node referenced by an edge is invisible → give it a real fill/stroke, or use the distinct-port pattern to connect to a visible junction.
   - `routes through node`: an edge cuts through an intermediate node → reroute via orthogonal bypass channels, or relay through a junction (see distinct-port pattern), keeping a ≥20px gap from the intermediate node.
   - `cross` (edge crossings): adjust node layout or routing channels so edges don't intersect (reference fireworks' zero-crossing budget).
   - `too close`: same-kind nodes are clustered → increase spacing or enlarge the canvas.
   - Arrow position: `connect()` auto-retracts by `marker_tip_depth` — retraction = `(markerWidth − refX) × stroke_width`, derived from the marker dimensions registered by `arrow_head()`, so the arrow tip lands exactly on the target border (neither poking in nor leaving a gap). For custom markers, pass the real dimensions via `arrow_head(id, color, marker_width=, ref_x=)` — no manual tweaking needed.
   - `font` (font sizes): more than 4 distinct tiers after dedup → converge to 3-4 tiers (title/body/note); near-overlapping tiers (ratio <1.15, e.g. 11/12) → merge into one tier. Recommended modular scale: 20 / 14 / 12 / 10 (all steps ≥1.15). This matches the tier count measured in each ink-graph style.
   - `palette`: accent count >8 → revert op fills to neutral white, or switch to a single-hue scheme (S1 Monochrome Blue, only 5 accents) so layer fills + one unified border carry the palette; >12 → trim to a preset scheme. Luminance conflict (very dark + very light coexist) → unify into one brightness family. Non-light background → apply white by default; dark themes must declare `set_background()`/`bg=`. See `references/design_specs.md` for the 4 preset schemes (S1–S4) and when to use each.
   - Layout issues: adjust component coordinates, spacing, or scale ratio, then regenerate.
   - `text` overflow: text exceeds the canvas → shorten the copy or shift the start point left; text wider than its card/container → shorten, auto-wrap by container width (greedy word-wrap), or widen the container. Note that `<text>` does not enter `bboxes` by default, so collision/boundary checks can't see it — this detection fills that gap.
   - `text overlap` (text on a shape or another text): a label sits on top of a circle/triangle/arc/line or collides with a neighboring label → move the label clear of the shape (place it above/below the icon, not on it) or shorten it. `auto_refine` cannot fix this (no geometry handle for raw `add_element` text) — adjust coordinates manually. This catches overlaps `check_collisions` misses because `bbox=False` text/shapes and `add_element` shapes bypass the collision registry.
   - `composition` gutter (insufficient container margin): node too close to the container edge → push the node toward the container center; or call **`auto_refine(drawer)`** (below) to iteratively auto-correct.
   - **`auto_refine(drawer, target_score=100, max_iter=3)`**: reads the `evaluate_svg` report and auto-corrects programmable issue categories (gutter → nudge node toward container center; too close → spread along the primary axis), looping until the target is met or iterations are exhausted. Returns `(score, report, fixes)`. Complex fixes (dangles/cross/route-through) still need manual intervention — auto_refine only handles geometric micro-adjustments.

## Node & Edge Semantics

For the evaluator to "see" connections, drawing code must register connectable rectangles as **nodes** and connections as **edges**:

- **Register nodes**: `drawer.rect(..., node_id="op1", node_kind="op")` — draws a rectangle and registers a node simultaneously. `node_kind` can be `"op" | "layer" | "block" | "region"`; used for provenance only, not for validation.
- **Circle nodes (junctions/markers)**: `drawer.circle(cx, cy, r, ..., node_id="jn", node_kind="junction")` — draws a visible circle and registers a square Node of side 2r as a snap anchor; endpoints landing at the center register distance 0. Ideal for bus junctions and port markers.
- **Register edges**: prefer `drawer.connect(from_id, from_side, to_id, to_side, ...)` — endpoints are taken from node border midpoints (`"top"|"bottom"|"left"|"right"`), so arrows always land precisely on the node edge. Options: `dashed=True` (dashed, e.g. lowering/bypass flows), `as_curve=True` + `curve_dir="left"|"right"` (curve), `edge_label=` (annotation).
- **Low-level entry**: `drawer.line(..., register_edge=True)` / `drawer.path(..., register_edge=True, start=..., end=...)` can also manually register edges (for curves, `start/end` are the semantic endpoints; `d` can be any path).
- **`group(transform)` context**: nodes/edges/bboxes drawn inside `with drawer.group("translate(100,50) rotate(30)"):` are registered in **absolute coordinates** via the accumulated affine matrix, so local coordinates inside a group are also validated. Supports chained `matrix()/translate()/scale()/rotate()/skewX()/skewY()`.
- **Advanced shapes** (ported from ink-graph `shapes.md`, local coordinates via `<g transform>`): `drawer.database(x,y,w,h,...)` (cylinder, top ellipse depth=min(8,h*0.12)), `drawer.decision(...)` (diamond, four points around center), `drawer.hexagon(...)` (gateway, 25% corner insets), `drawer.component(...)` (with left-edge double tabs), `drawer.cloud(...)` (multi-lobe cubic curves). All accept `node_id/role/label`, register nodes consistently with `rect()`/`circle()`, and support connection snapping. Text centering uses `dominant-baseline="central"` (exact, replacing the old y+0.35*fs approximation).
- **Semantic role `role=`** (optional): `rect/circle/connect/line/path` all accept `role="node|edge|decoration|legend|background"`. Elements set to `decoration`/`legend`/`background` emit a `data-graph-role` attribute and are **excluded from business checks** (spacing, collision, palette count) — used for decorative layers (rail casings, background textures, legends). Default `node`/`edge` means business elements.
- **Math formulas with sub/superscripts**: `drawer.formula(x, y, markup, font_size=, fill=, anchor=, weight=)` renders genuine `<tspan>` baseline shifts — unlike `text()` (which HTML-escapes content and can only show literal underscores/carets). Markup: `_{...}` → subscript, `^{...}` → superscript; baseline auto-resets between tokens so multiple indices align (e.g. `"F_{k} = MS^{↑}_{k} + g_{k}"`). Default monospace family + bold for an equation look; pass `weight="normal"` for inline annotations. The sub/superscript glyph sizes (~0.72×) are derivative of the parent text size and are **excluded from the font-tier count** (see `check_font_scale`), so formulas do not inflate the 3–4-tier typography budget. (Note: `svg2pptx` concatenates `<tspan>` text flat — use image mode if you need exact subscript fidelity in PowerPoint.)

> **"Invisible anchor" anti-pattern (now forcefully blocked)**: it used to be possible to create `fill="none" stroke="none"` invisible rectangles to cheat the connection validation — the evaluator would pass, but the human eye would see dangling lines. Now `check_phantom_anchors()` detects any node referenced by an edge that is invisible (`fill=none ∧ stroke=none`/opacity=0/zero-size) and flags it as FAIL. When you need a "bus rail" or cross-layer channel, use the distinct-port pattern below to connect to a visible junction.

> **Distinct-port / junction pattern** (cross-layer aggregation, side channels): place visible circular junction nodes at the channel position, connect each real component to the junction with a short solid line `connect(layer, "left", junction, "right")`, then chain them into a rail with dashed lines `connect(junction, "bottom", junction2, "top", dashed=True)`. This way each rail segment lands between real visible nodes — passing validation while remaining clear to humans.

> Tip: container-type large rectangles (Module/Layer) enter bbox collision and coverage stats by default; for interior small elements (text, operation nodes), pass `bbox=False` to avoid false overlap reports or inflated coverage.

## Design Specifications
- **Font-size tiers**: use only 3-4 tiers per diagram (title 20 / section header 14 / body 12 / note 10), adjacent tiers ≥1.15× apart (modular type scale). Exceeding this triggers an evaluator warning.
- **Palette**: pick one of the 4 preset schemes in `references/design_specs.md` by diagram type — S1 Monochrome Blue (default, ≥4 modules), S2 Categorical (classification), S3 Semantic (cloud/system), S4 Duotone (focal highlight). All pre-verified (accent ≤12, no luminance clash). Op cards stay `fill="white"`; color lives in layer fills + borders only. Background defaults to white (`SVGDrawer(bg="#FFFFFF")`); only use `set_background()` for dark themes.
- **Color & typography**: see `references/design_specs.md`.
- **Stability**: prefer relative layout logic (i.e. compute new component positions based on known component coordinates).
- **Entity escaping**: SVG is strict XML — never use HTML entities in text (`&middot;`/`&mdash;` etc. are rejected by the parser). Use Unicode characters (`·` `—`) or `html.escape` instead.

## Example: Generation with Evaluation

```python
import sys
# Resolve the skill scripts dir relative to this file (see $SKILL note above).
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from svg_utils import SVGDrawer, save_svg
from evaluator import evaluate_svg
from pathlib import Path
# Write outputs next to this script (see "Output Layout Convention" below).
OUT = Path(__file__).resolve().parent

drawer = SVGDrawer(1200, 800, bg="#FFFFFF")   # white background is the default; change only for dark themes
drawer.arrow_head("arrowhead", "#333")

# Nodes (Scheme S1 Monochrome Blue — L1 tier; see design_specs.md for the full library)
drawer.rect(100, 100, 90, 34, fill="#D5E1EB", stroke="#1B3A5C",
            node_id="a", node_kind="op", bbox=False)
drawer.rect(300, 100, 90, 34, fill="#D5E1EB", stroke="#1B3A5C",
            node_id="b", node_kind="op", bbox=False)

# Edges: endpoints auto-snap to node borders, arrows land precisely on the edge
drawer.connect("a", "right", "b", "left",
               stroke="#1B3A5C", marker_end="arrowhead", edge_label="value")

# Evaluation (includes connection/arrow validation)
score, report = evaluate_svg(drawer)
print(f"Quality Score: {score}")
for line in report:
    print(line)

if score >= 80:
    save_svg(drawer.render(), str(OUT / "diagram.svg"))
else:
    print("Score too low, need adjustment.")
```

## Output Layout Convention

Every diagram generation is **self-contained in its own subdirectory** under `output/`. One diagram = one directory; the generator script and its SVG/PNG/PPTX triplet live together.

```
output/<timestamp>_<name>/
- gen_<name>.py        # generator script (version-controlled source)
- <name>.svg           # -
- <name>.png           #  |- triplet, regenerated in place on each run
- <name>.pptx          # -
```

**Rules:**
- **Script and outputs are co-located.** The `gen_*.py` lives *inside* its `output/<ts>_<name>/` directory — never in the repo root, never scattered away from its artifacts. Deleting the directory removes script + outputs together.
- **Write to the script's own directory, not a fresh timestamped dir per run** — re-running refreshes the triplet in place rather than accumulating duplicate directories:
  ```python
  from pathlib import Path
  OUT = Path(__file__).resolve().parent   # this script's own directory
  NAME = "<name>"
  ```
- **The `<timestamp>_<name>` directory name is frozen at creation** (a born-on date); it is not regenerated on each run.
- **Always emit the full triplet** — SVG (`save_svg`), PNG (`rasterize_svg`, wraps `rsvg-convert`), and PPTX (`svg2pptx.svg_to_pptx`) — so the directory is self-describing.
- **Artifacts are gitignored by extension** (`**/*.svg`, `**/*.png`, `**/*.pptx`); the `gen_*.py` scripts stay version-controlled. Never gitignore the whole output directory — that hides the scripts.

### The save/rasterize helpers

`save_svg()`, `rasterize_svg()`, and `svg2pptx.svg_to_pptx()` write wherever you ask — they create parent directories as needed and impose no layout constraint. A prior version enforced an `output/<task>/` directory at the library boundary (`validate_output_path` / `OutputPathError`); that was removed for the public release because it refused legitimate cross-project and temporary paths.

```python
from svg_utils import save_svg, rasterize_svg

save_svg(content, OUT / "diagram.svg")      # writes, mkdir -p the parent
rasterize_svg(OUT / "diagram.svg", OUT / "diagram.png", width=1200)
```

- `save_svg(content, filename)` — writes SVG *content* to *filename*, creating parents; returns the resolved path.
- `rasterize_svg(svg_path, png_path, width)` — runs `rsvg-convert -w <width>`; creates parents; returns the PNG path.
- `svg2pptx.svg_to_pptx(svg, pptx_path, config=None)` — converts to PPTX; creates parents.

> Prefer these wrappers over a raw `subprocess.run(["rsvg-convert", ...])` so path handling stays uniform.

## SVG to PPTX Export (svg2pptx)

After generating an SVG, you can export it to an **editable PowerPoint file** with one call. The module `$SKILL/svg2pptx.py` parses SVG elements into native PowerPoint shapes (rectangles, ovals, connectors, text boxes, freeforms) rather than embedding an image — so each element can be individually resized, recolored, and edited in PowerPoint/Keynote/LibreOffice. Inspired by the [svg2pptx](https://github.com/benouinirachid/svg2pptx) project.

### Two Export Modes

| Mode | Parameter | Effect | Use Case |
|---|---|---|---|
| **shapes** (default) | `mode="shapes"` | Each element → an independent editable shape | Architecture diagrams you want to fine-tune in PPT |
| **image** | `mode="image"` | Rasterize to PNG and embed (100% visual fidelity) | Complex SVGs for display only, no editing needed |

### API

```python
# sys.path was set above in the Example section ($SKILL = scripts directory)
from svg2pptx import svg_to_pptx, PptxConfig, save_pptx

# Option 1: SVG string → PPTX (most common, takes drawer.render())
svg_to_pptx(drawer.render(), OUT / "diagram.pptx")

# Option 2: SVG file → PPTX (file must end with .svg, otherwise parsed as an SVG string)
svg_to_pptx(OUT / "diagram.svg", OUT / "diagram.pptx")

# Option 3: Export directly from an SVGDrawer (equivalent to Option 1)
save_pptx(drawer, OUT / "diagram.pptx")

# Custom config: 16:9 slide, 2x scale, shapes mode
svg_to_pptx(OUT / "diagram.svg", OUT / "diagram.pptx",
            config=PptxConfig(slide_w=13.333, slide_h=7.5, scale=2.0))

# Image mode (rasterized embed, requires rsvg-convert)
svg_to_pptx(OUT / "diagram.svg", OUT / "diagram.pptx", config=PptxConfig(mode="image"))

# Add to an existing presentation's slide (no new file created)
# Note: add_svg_to_slide only supports shapes mode, not image rasterization
from svg2pptx import add_svg_to_slide
add_svg_to_slide(drawer.render(), slide, x=1.0, y=0.5, scale=0.8)
```

### SVG → PPTX Element Mapping

| SVG Element | PPTX Shape | Notes |
|---|---|---|
| `<rect rx=0>` | Rectangle | Auto shape; **rotates correctly** inside a rotated `<g>` |
| `<rect rx>0>` | Rounded Rectangle | Corner radius auto-mapped; **rotation** also handled |
| `<circle>` / `<ellipse>` | Oval | Ellipse/circle; **rotation** handled correctly |
| `<line>` | Connector (Straight) | Straight-line connector |
| `<polygon>` | Freeform (closed) | Polygon → freeform |
| `<polyline>` | Freeform (open) | Polyline → freeform |
| `<path>` | Freeform | **Bezier/Arc auto-flattened** to line segments (`curve_tolerance` controls precision) |
| `<text>` / `<tspan>` | Text Box | Preserves font/size/color/alignment, CJK works; `<tspan>` child text is auto-concatenated |
| `<g transform>` | Coordinate transform | **Accumulated affine matrix** (translate/scale/rotate) applied to all child shapes |
| `marker-end` | Freeform triangle | **Arrow auto-rendered**: draws a triangle at the segment endpoint based on marker geometry |
| `fill-opacity` | Transparency | Implemented via `<a:alpha>` XML injection (python-pptx does not support this natively) |
| `stroke-dasharray` | Dashed line | `prstDash` or `custDash` XML injection |

### Limitations
- **Gradients** are not supported (the first color is used).
- **Filters/effects** (blur, shadow) are not supported (shape shadows are disabled by default).
- **Bezier curves** are flattened to line segments (lower `curve_tolerance` = smoother, default 1.0px).
- **Font scaling**: font size scales proportionally with the fit-to-slide `scale` (`Pt(fs * scale * 72/96)`) — i.e. a large canvas mapped to a small slide shrinks text, and vice versa. The text-to-box ratio always stays consistent. To fix the font size, set `scale=1.0` and adjust `slide_w/slide_h` yourself.
- **`add_svg_to_slide`** only supports shapes mode (no image rasterization); for image mode use `svg_to_pptx`.
- **Image mode** requires `rsvg-convert` (installed on this system); shapes mode only requires `python-pptx`.

## Capabilities

All detection/export capabilities parse the actually-rendered SVG (`evaluate, don't assert`), so they work equally well for raw `add_element` drawing.

| # | Capability | Description |
|---|---|---|
| ① | Containment-aware collision | Parent-child nesting does not count as a collision |
| ② | Phantom anchor detection | Nodes referenced by edges but invisible → FAIL |
| ③ | Edge × edge crossing | Two edge segments intersecting internally |
| ④ | Marker depth auto-derivation | `(markerWidth−refX)×stroke` |
| ⑤ | Font-size tier detection | Parses SVG, ≤4 tiers, adjacent tiers ≥1.15× apart |
| ⑥ | Palette detection | Accent ≤8/12, background defaults to light |
| ⑦ | Curve bezier/arc sampling | Ported from fireworks `path_routes` |
| ⑧ | Luminance conflict by channel | Fill/stroke checked separately for dark+light coexistence |
| ⑨ | Transform matrix accumulation | `group()` context |
| ⑩ | `data-graph-role` semantic roles | decoration/legend/background skip business checks |
| ⑪ | Coverage bbox union | Sweep-line algorithm |
| ⑫ | Text overflow detection | Parses `<text>` geometry |
| ⑬ | Composition quality budget | bend≤2/stretch≤1.35/gutter≥20/segment≥16 + text as obstacle |
| ⑭ | Node shape library | database/decision/hexagon/component/cloud |
| ⑮ | Barycenter crossing minimization | Ported from DiagramForge: reorder by barycenter within layers |
| ⑯ | `auto_refine` auto-correction | Reads eval report, iteratively fixes gutter/spacing by issue code |
| ⑰ | SVG→PPTX export | Native editable shapes + rasterized image dual modes, arrow rendering, Bezier/Arc flattening, transparency/dash injection |
| ⑱ | Text-vs-shape & text-vs-text overlap | Parses rendered SVG: `<text>` bbox vs visible circles/rects/polygons/lines/paths + text vs text; closes the bbox-registry blind spot (`bbox=False`/`add_element`) |
| ⑲ | Formula rendering (sub/superscript) | `drawer.formula()` emits real `<tspan>` baseline shifts for `_{}`/`^{}` markup; evaluator strips markup in width estimates and counts only `<text>`-tier font sizes so subscripts don't inflate the tier budget |

## References & Acknowledgments

This Skill's geometry/connection detection draws on the following open-source projects (their references and validator implementations were actually studied):

- **ink-graph** (`qaz1230sp/ink-graph`): its references/pitfalls.md #2 (arrow occluded by node → retract endpoint 8px), #3/#10 (edge crossing through node → 20px gap bypass), #17 (fan-out alignment), #26 (marker size proportional to stroke), #29 (fan-out/fan-in + junction dot); its references/shapes.md `dominant-baseline="central"` centering, its references/layout-rules.md grid/spacing rules. **Measured each of its `style-*.md` at exactly 3-4 font tiers, 4-13 palette colors** — empirical basis for the font-tier/palette thresholds. *(These files live in the ink-graph repo, not this skill.)*
- **fireworks-tech-graph** (`yizhiyanhua-ai/fireworks-tech-graph`): its references/composition-quality-contract.md (executable budget: zero crossings/≤2 bends/≥40px node spacing/≥20px container gutter); its scripts/validate_svg.py `find_collisions` + `segment_hits_bounds` (path sampling vs node bbox), `data-graph-role` semantic roles, transform matrix accumulation, "evaluate, don't assert" (parse actual SVG rather than trusting API calls). *(Files live in the fireworks repo, not this skill.)*
- **svg-animations** (`supermemoryai/skills`): SMIL/CSS animation basics and `stroke-dasharray` stroke animation recipes (this Skill does not enable animation yet, reserved for later).
- **svg-design** (`tryopendata/skills`): primitive-first (circles use `<circle>`), `stroke-linecap="round"`, strict XML with no HTML entities, and other hygiene conventions.
- **svg2pptx** (`benouinirachid/svg2pptx`): architectural blueprint for the PPTX export module. Its "SVG element → PowerPoint native editable shape" philosophy (rect→rectangle, circle→oval, line→connector, path→freeform, text→textbox), Config dataclass design, `build_freeform` + `add_line_segments` usage, and Bezier flattening tolerance parameter were all adapted into the self-contained `scripts/svg2pptx.py` module (which adds arrow marker rendering, `fill-opacity` transparency injection, `stroke-dasharray` dash injection, and an image rasterization fallback mode).
