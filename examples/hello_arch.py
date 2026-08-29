"""Minimal standalone example for architecture-drawer (no Claude required).

Run:
    python examples/hello_arch.py

Produces examples/hello_arch/hello_arch.svg next to this script. Demonstrates
the core generate-evaluate-export loop in ~20 lines.
"""
import os
import sys
from pathlib import Path

# Resolve the skill scripts dir relative to this example file.
_HERE = Path(__file__).resolve().parent
_SKILL = (_HERE / ".." / "plugins" / "architecture-drawer" / "skills"
          / "architecture-drawer" / "scripts").resolve()
sys.path.insert(0, str(_SKILL))

from svg_utils import SVGDrawer, save_svg  # noqa: E402
from evaluator import evaluate_svg  # noqa: E402
from svg2pptx import svg_to_pptx  # noqa: E402
from design_brief import DesignBrief, ColorSpec  # noqa: E402
from semantic_qa import run_semantic_qa  # noqa: E402

OUT = _HERE / "hello_arch"
OUT.mkdir(parents=True, exist_ok=True)

d = SVGDrawer(900, 320, bg="#FFFFFF")
d.arrow_head("arrow", "#1B3A5C")

# Scheme S1 Monochrome Blue — see references/design_specs.md.
d.rect(80, 140, 140, 44, rx=6, fill="#D5E1EB", stroke="#1B3A5C", node_id="api")
d.rect(380, 140, 140, 44, rx=6, fill="#BBCEDF", stroke="#1B3A5C", node_id="logic")
d.rect(680, 140, 140, 44, rx=6, fill="#9BB9D1", stroke="#1B3A5C", node_id="store")

d.text(150, 162, "API Layer", font_size=14, weight="bold", bbox=False)
d.text(450, 162, "Business Logic", font_size=14, weight="bold", bbox=False)
d.text(750, 162, "Data Store", font_size=14, weight="bold", bbox=False)

d.connect("api", "right", "logic", "left", stroke="#1B3A5C", marker_end="arrow")
d.connect("logic", "right", "store", "left", stroke="#1B3A5C", marker_end="arrow")

# Design Brief (Step 1) — three primary nodes, no containers; the API →
# Logic → Store arrows run left-to-right, so no chain stages are declared.
BRIEF = DesignBrief(
    scheme="S1",
    layout="node",
    flow="left-right",
    palette_role={
        "api":   ColorSpec("#D5E1EB", "#1B3A5C"),
        "logic": ColorSpec("#BBCEDF", "#1B3A5C"),
        "store": ColorSpec("#9BB9D1", "#1B3A5C"),
    },
    flow_chain=(),
)

score, report = evaluate_svg(d)
print(f"Quality Score: {score}")
qa = run_semantic_qa(d, expected_size=(900, 320), brief=BRIEF)
print("Semantic QA:")
for line in qa.report():
    print(line)


save_svg(d.render(), str(OUT / "hello_arch.svg"))
svg_to_pptx(d.render(), str(OUT / "hello_arch.pptx"))
BRIEF.write(str(OUT / "brief.json"))
print(f"Wrote {OUT}")
