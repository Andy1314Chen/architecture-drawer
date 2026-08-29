"""Semantic QA tests — the meaning-level checks layered on the geometry evaluator.

Covers the three defect classes the geometric evaluator structurally cannot
see (marker 缺省陷阱 / FIGS 尺寸漂移 / 标签错位), plus the clean-pass guarantee:
every golden eval SVG in the repo must pass semantic QA without warnings,
otherwise the checker itself has regressed into noise.
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / (
    "plugins/architecture-drawer/skills/architecture-drawer/scripts")
sys.path.insert(0, str(SCRIPTS))

from svg_utils import SVGDrawer                    # noqa: E402
from semantic_qa import run_semantic_qa            # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _codes(res):
    return [i.code for i in res.issues]


GOOD_BOX_SVG = """<svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5">
<polygon points="0 0, 10 3.5, 0 7" fill="#333"/></marker></defs>
<rect x="50" y="100" width="200" height="60" fill="white" stroke="#333"/>
<text x="150" y="130" font-size="14" text-anchor="middle">centered</text>
</svg>"""


# ---------------------------------------------------------------------------
# 1. marker 缺省陷阱
# ---------------------------------------------------------------------------
def test_marker_dangling_ref_fails():
    svg = GOOD_BOX_SVG.replace(
        '</defs>',
        '</defs><line x1="50" y1="200" x2="300" y2="200" stroke="#333" '
        'marker-end="url(#arrowhead)"/>')
    res = run_semantic_qa(svg)
    assert not res.ok
    assert "marker-dangling" in _codes(res)


def test_marker_defined_ref_passes():
    svg = GOOD_BOX_SVG.replace(
        '</defs>',
        '</defs><line x1="50" y1="200" x2="300" y2="200" stroke="#333" '
        'marker-end="url(#arrow)"/>')
    res = run_semantic_qa(svg)
    assert "marker-dangling" not in _codes(res)


def test_connect_default_marker_trap_integration():
    """The exact production trap: arrow_head('arrow', ...) registered, then a
    connect() call that omits marker_end defaults to 'arrowhead' — every
    arrowhead silently vanishes. Geometry passes; semantic QA must FAIL it."""
    d = SVGDrawer(400, 300)
    d.arrow_head("arrow", "#333")
    d.rect(50, 100, 120, 40, node_id="a", bbox=False)
    d.rect(230, 100, 120, 40, node_id="b", bbox=False)
    d.connect("a", "right", "b", "left")          # default marker_end='arrowhead'
    res = run_semantic_qa(d)
    assert not res.ok
    assert "marker-dangling" in _codes(res)

    # ...and the fix: explicit marker_end matching the registered id
    d2 = SVGDrawer(400, 300)
    d2.arrow_head("arrow", "#333")
    d2.rect(50, 100, 120, 40, node_id="a", bbox=False)
    d2.rect(230, 100, 120, 40, node_id="b", bbox=False)
    d2.connect("a", "right", "b", "left", marker_end="arrow")
    res2 = run_semantic_qa(d2)
    assert "marker-dangling" not in _codes(res2)


def test_marker_unused_warns():
    svg = GOOD_BOX_SVG.replace(
        '<polygon points="0 0, 10 3.5, 0 7" fill="#333"/></marker></defs>',
        '<polygon points="0 0, 10 3.5, 0 7" fill="#333"/></marker>'
        '<marker id="spare"><polygon points="0 0, 1 0.5, 0 1"/></marker></defs>')
    res = run_semantic_qa(svg)
    assert "marker-unused" in _codes(res)


# ---------------------------------------------------------------------------
# 2. FIGS 尺寸漂移
# ---------------------------------------------------------------------------
def test_size_drift_content_far_smaller_than_canvas():
    svg = ('<svg width="1200" height="800">'
           '<rect x="560" y="380" width="40" height="30" fill="white"/></svg>')
    res = run_semantic_qa(svg)
    assert "size-drift" in _codes(res)


def test_size_overflow_content_outside_canvas():
    svg = ('<svg width="300" height="200">'
           '<rect x="250" y="150" width="120" height="90" fill="white"/></svg>')
    res = run_semantic_qa(svg)
    assert "size-overflow" in _codes(res)
    assert not res.ok


def test_expected_size_mismatch_warns():
    svg = GOOD_BOX_SVG
    res = run_semantic_qa(svg, expected_size=(1240, 970))
    assert "size-declared-vs-spec" in _codes(res)
    res2 = run_semantic_qa(svg, expected_size=(400, 300))
    assert "size-declared-vs-spec" not in _codes(res2)


# ---------------------------------------------------------------------------
# 3. 标签错位
# ---------------------------------------------------------------------------
def test_label_offcenter_warns():
    svg = GOOD_BOX_SVG.replace('x="150" y="130"', 'x="110" y="130"')
    res = run_semantic_qa(svg)
    assert "label-offcenter" in _codes(res)


def test_centered_label_passes():
    res = run_semantic_qa(GOOD_BOX_SVG)
    assert "label-offcenter" not in _codes(res)
    assert "label-orphan" not in _codes(res)


def test_orphan_label_warns():
    svg = GOOD_BOX_SVG.replace(
        '</svg>',
        '<text x="350" y="250" font-size="12" text-anchor="middle">floating</text></svg>')
    res = run_semantic_qa(svg)
    assert "label-orphan" in _codes(res)


# ---------------------------------------------------------------------------
# 4. connector route vs filled shapes（箭头线盖在组件上）
# ---------------------------------------------------------------------------
def _band_svg(spine_x="776", extra=""):
    """Two filled bands + business cards; a right spine at spine_x."""
    return f'''<svg width="900" height="400">
<rect x="60" y="52" width="730" height="136" fill="#D5E1EB" stroke="#333"/>
<rect x="86" y="107" width="150" height="62" fill="white" stroke="#333"/>
<text x="161" y="138" font-size="12" text-anchor="middle">card a</text>
<rect x="60" y="206" width="730" height="136" fill="#BBCEDF" stroke="#333"/>
<rect x="86" y="261" width="150" height="62" fill="white" stroke="#333"/>
<text x="161" y="292" font-size="12" text-anchor="middle">card b</text>
{extra}
<line x1="{spine_x}" y1="190" x2="{spine_x}" y2="204" stroke="#D47130"
      stroke-width="2.8" marker-end="url(#up)"/>
</svg>'''


def test_rail_slicing_container_warns():
    """A full-height spine INSIDE the band x-range slices both bands."""
    svg = _band_svg().replace(
        'y1="190" x2="776" y2="204"', 'y1="60" x2="776" y2="340"')
    res = run_semantic_qa(svg)
    assert "rail-slices-container" in _codes(res)


def test_gutter_spine_passes():
    """The same spine confined to the inter-band gutter is clean."""
    res = run_semantic_qa(_band_svg())
    assert "rail-slices-container" not in _codes(res)
    assert "connector-through-card" not in _codes(res)


def test_hairline_divider_not_a_rail():
    """A 0.6px band-header underline must not be flagged as a rail."""
    svg = _band_svg().replace(
        'y1="190" x2="776" y2="204"',
        'y1="88" x2="72" y2="88"').replace(
        '<line x1="776"', '<line x1="72"').replace(
        'stroke-width="2.8"', 'stroke-width="0.6"')
    res = run_semantic_qa(svg)
    assert "rail-slices-container" not in _codes(res)


def test_anchored_edge_crossing_band_is_fine():
    """A card→card edge crossing a band fill is anchored — not a rail."""
    svg = _band_svg().replace(
        '<line x1="776" y1="190" x2="776" y2="204"',
        '<line x1="161" y1="169" x2="400" y2="261"')
    res = run_semantic_qa(svg)
    assert "rail-slices-container" not in _codes(res)


# ---------------------------------------------------------------------------
# 5. text semantics vs spec
# ---------------------------------------------------------------------------
def test_placeholder_text_fails():
    svg = GOOD_BOX_SVG.replace('>centered<', '>TODO: fill in<')
    res = run_semantic_qa(svg)
    assert "text-placeholder" in _codes(res)
    assert not res.ok


def test_empty_text_fails():
    svg = GOOD_BOX_SVG.replace(
        '</svg>', '<text x="350" y="250" font-size="12" text-anchor="middle">  </text></svg>')
    res = run_semantic_qa(svg)
    assert "text-empty" in _codes(res)


def test_spec_entity_loss_fails():
    """Dropping a spec's component identifiers gates the run (FAIL)."""
    spec = "Draw **AgentEvent** bus, `server_queue`, `server_routes`, and a UI layer."
    res = run_semantic_qa(GOOD_BOX_SVG, spec_text=spec)
    assert "spec-entities-missing" in _codes(res)
    assert not res.ok


def test_spec_entities_present_passes():
    spec = "Draw **AgentEvent** bus and a `server_queue`."
    svg = GOOD_BOX_SVG.replace(">centered<", ">AgentEvent / server_queue<")
    res = run_semantic_qa(svg, spec_text=spec)
    assert not any(c.startswith("spec-entities") for c in _codes(res))


def test_spec_design_jargon_not_entities():
    """Design directives (colors, '8 accents', 'anchor=middle') aren't entities."""
    spec = "Use **#1B3A5C**, **8 accents**, `anchor=middle`, bold **All edges are solid**."
    res = run_semantic_qa(GOOD_BOX_SVG, spec_text=spec)
    assert not any(c.startswith("spec-entities") for c in _codes(res))


def test_top_band_titles_are_exempt():
    """Centered title/subtitle above the grid are meant to float — never orphans."""
    svg = GOOD_BOX_SVG.replace(
        '</defs>',
        '</defs><text x="200" y="20" font-size="20" text-anchor="middle">Title</text>')
    res = run_semantic_qa(svg)
    assert "label-orphan" not in _codes(res)


# ---------------------------------------------------------------------------
# 4. clean-pass guarantee over every golden eval SVG
# ---------------------------------------------------------------------------
def _eval_svgs():
    evals = SCRIPTS.parent / "evals"
    return sorted(evals.glob("*/[!g][!e][!n]*.svg"))


def test_all_eval_svgs_pass_semantic_qa():
    """No unexpected flags on the golden outputs.

    Allow-listed true positives (verified by hand):
      - mlir: unused 'ag' marker + 6 genuinely empty <text> elements.
    Since the eval specs were rewritten to coarse semantic form (2026-08-29),
    every other golden covers 100% of its spec's bold/backtick entities —
    the former spec-entities-partial warns came from design-token backticks
    in the over-detailed specs, which the diagrams rightly don't reproduce.

    Each eval's brief.json (written by its gen.py next to the artifacts) is
    loaded and passed as the contract — the golden must not only pass the
    generic checks but honor its own declared design (brief-* codes). A
    missing brief.json shows up as brief-absent here, so evals cannot silently
    drop the contract.
    """
    allowed = {
        "mlir_pipeline.svg": {"marker-unused", "text-empty"},
    }
    for svg_path in _eval_svgs():
        spec = svg_path.parent / "input.md"
        brief_path = svg_path.parent / "brief.json"
        brief = None
        if brief_path.is_file():
            from design_brief import DesignBrief
            brief = DesignBrief.load(str(brief_path))
        res = run_semantic_qa(
            svg_path.read_text(encoding="utf-8"),
            spec_text=spec.read_text(encoding="utf-8") if spec.is_file() else None,
            brief=brief)
        unexpected = set(_codes(res)) - allowed.get(svg_path.name, set())
        assert not unexpected, (
            f"{svg_path.name}: semantic QA flagged {sorted(unexpected)} "
            f"(false positives on a golden diagram)")
