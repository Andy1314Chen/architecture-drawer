# gen.py Skeleton — copy this shape, fill in your architecture

The fixed parts (path resolution, brief, evaluation, export) never change;
only the constants block and the drawing section are yours. Following this
shape avoids re-deriving the boilerplate and the known first-run failures
(missing brief, wrong save order, deep-literal bracket slips).

```python
#!/usr/bin/env python3
"""<Arch name> — <one-line summary of the design>."""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, ".pi/skills/architecture-drawer/scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)

from svg_utils import SVGDrawer, save_svg, rasterize_svg, layout_grid, layout_row, layout_band
from design_brief import DesignBrief
from evaluator import evaluate_svg, auto_refine
from semantic_qa import run_semantic_qa
from svg2pptx import svg_to_pptx

# ---- Step 1: design brief tokens (named constants, never deep literals) ----
W, H = 1280, 860
TITLE = "<Arch name>"
NODE_IDS = ["src", "queue", "engine", "sink"]      # primary nodes
BANDS = [("layer_a", "Layer A", 120), ("layer_b", "Layer B", 300)]  # (id, label, y)
FLOW = ("src", "queue", "engine", "sink")           # flow_chain stages
PALETTE_ROLE = {                                    # data-node-id -> (fill, stroke)
    "layer_a": ("#D5E1EB", "#1B3A5C"),
}
BRIEF = DesignBrief(scheme="S1 monochrome", layout="band", flow="left-right",
                    palette_role=PALETTE_ROLE, flow_chain=FLOW)

d = SVGDrawer(width=W, height=H)
# title
d.text(W / 2, 36, TITLE, font_size=20, weight="bold")

# ---- Step 2: draw (state the array; helpers do the arithmetic) ----
for bid, label, by in BANDS:
    d.rect(60, by, W - 120, 160, fill="#F5F7FA", stroke="#1B3A5C",
           node_id=bid, node_kind="layer", role="layer")
    d.text(76, by + 24, label, font_size=14, weight="bold")
    bx, byy, bw, bh = layout_band(label, 60, by, W - 120, 160)
    for (x, y), nid in zip(layout_grid(4, bx, byy, 4, 120, 40, 24, 0), NODE_IDS):
        d.rect(x, y, 120, 40, fill="white", stroke="#1B3A5C", node_id=nid)

for a, b in zip(FLOW, FLOW[1:]):
    d.connect(a, "right", b, "left", stroke="#1B3A5C", marker_end="arrowhead")

# ---- Step 3: evaluate -> bounded repair -> export (fixed shape) ----
score, report = evaluate_svg(d)
print(f"Score: {score}")
if score < 100:
    score2, report2, fixes = auto_refine(d)
    print(f"After auto_refine: {score2}  (fixes: {fixes})")

qa = run_semantic_qa(d, expected_size=(W, H), brief=BRIEF)
save_svg(d.render(), "diagram.svg")
rasterize_svg("diagram.svg", "diagram.png", W)
svg_to_pptx("diagram.svg", "diagram.pptx")
BRIEF.write("brief.json")
```

Notes:
- The `BANDS` / `NODE_IDS` / `FLOW` constants pattern replaces inline nested
  literals — bracket mismatches in 5-deep tuples cost real repair rounds.
- Run `python3 gen.py` after every drawing change; read the report lines and
  fix exactly what they name (see `checks_cheatsheet.md`).
- Canvas/positions are approximate at first write — the evaluator is the
  oracle; do not hand-verify all 16 checks before the first run.
