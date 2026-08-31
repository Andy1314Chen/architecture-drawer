"""Evaluator palette-floor tests — the 无配色 (colorless-diagram) defect class.

Observed in the wild (2026-08-29 coarse-spec agent-replay pilot): an agent
"fixed" its text-contrast WARN by de-coloring the whole diagram — the final
100-score output carried only desaturated slate tones (#546E7A / #37474F /
#78909C), which pass the R==G==B neutral filter yet read as colorless. The
palette cap is meaningless without a floor, so ``check_palette`` now FAILs any
business diagram whose accents carry no readable hue (HSL saturation < 0.25).
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / (
    "plugins/architecture-drawer/skills/architecture-drawer/scripts")
sys.path.insert(0, str(SCRIPTS))

from svg_utils import SVGDrawer                    # noqa: E402
from evaluator import check_palette, _is_chromatic  # noqa: E402


def _wrap(svg_body, w=600, h=400):
    class D:
        pass
    d = D()
    d._s = svg_body
    d.width, d.height = w, h
    d.render = lambda: svg_body
    return d


def test_chromatic_classification():
    """Slate pseudo-accents are achromatic; pastel tints are chromatic."""
    assert not _is_chromatic("#546e7a")   # slate, S≈0.18 — the pilot's only "colors"
    assert not _is_chromatic("#37474f")
    assert not _is_chromatic("#999999")   # pure gray
    assert _is_chromatic("#dae8fc")       # pastel blue tint, S≈0.85
    assert _is_chromatic("#d47130")       # saturated orange
    assert _is_chromatic("#1b3a5c")       # dark navy accent


def test_decolored_diagram_fails_the_floor():
    """The exact pilot regression: slate-only 'accents' → no-chromatic FAIL."""
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="200" height="80" fill="#ffffff" '
           'stroke="#546e7a" stroke-width="2"/>'
           '<rect x="50" y="200" width="500" height="60" fill="#546e7a" '
           'stroke="#37474f" stroke-width="1"/>'
           '<rect x="300" y="50" width="200" height="80" fill="#f5f5f5" '
           'stroke="#78909c" stroke-width="1"/></svg>')
    issues = check_palette(_wrap(svg))
    assert any("no chromatic accent" in s for s in issues)


def test_neutral_only_diagram_fails_the_floor():
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="200" height="80" fill="#ffffff" '
           'stroke="#999999" stroke-width="1"/>'
           '<rect x="300" y="50" width="200" height="80" fill="#eeeeee" '
           'stroke="#cccccc" stroke-width="1"/></svg>')
    issues = check_palette(_wrap(svg))
    assert any("no chromatic accent" in s for s in issues)


def test_tinted_diagram_passes_the_floor():
    """Golden-style layering — light tint fills + dark accent stroke — is the
    sanctioned way to carry color (and the documented contrast fix)."""
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="500" height="120" fill="#dae8fc" '
           'stroke="#1b3a5c" stroke-width="1.5"/>'
           '<rect x="50" y="220" width="500" height="120" fill="#d5e1eb" '
           'stroke="#1b3a5c" stroke-width="1.5"/></svg>')
    issues = check_palette(_wrap(svg))
    assert not any("no chromatic accent" in s for s in issues)


def test_gray_dominant_structure_fails():
    """The agent_infra replay defect: color present but marginal — neutral
    bands/cards everywhere, chromatic color confined to two small chips.
    Low on BOTH axes (elements AND area) -> FAIL."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(6):  # the gray skeleton
        parts.append(f'<rect x="50" y="{40 + i * 140}" width="1000" height="100" '
                     f'fill="#f2f2f2" stroke="#b0b0b0" stroke-width="1"/>')
    for i in range(3):  # white cards on top
        parts.append(f'<rect x="80" y="{60 + i * 140}" width="200" height="60" '
                     f'fill="#ffffff" stroke="#bebebe" stroke-width="1"/>')
    # the only color: two tiny chips
    parts.append('<rect x="400" y="60" width="60" height="30" fill="#dbeafe" stroke="#2563eb"/>')
    parts.append('<rect x="400" y="200" width="60" height="30" fill="#fee2e2" stroke="#dc2626"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert any("gray-dominant" in s for s in issues)


def test_tinted_bands_are_not_gray_dominant():
    """Band-style scheme: tinted band fills ride the AREA axis."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(6):
        parts.append(f'<rect x="50" y="{40 + i * 140}" width="1000" height="100" '
                     f'fill="#dae8fc" stroke="#1b3a5c" stroke-width="1.5"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert not any("gray-dominant" in s for s in issues)


def test_node_style_colors_ride_the_element_axis():
    """Node-style scheme (constellation/flowchart): neutral bands are fine
    when the primary NODES carry the color."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(5):  # neutral layer bands
        parts.append(f'<rect x="100" y="{40 + i * 170}" width="1000" height="120" '
                     f'fill="#f7f7f7" stroke="none"/>')
    for i in range(20):  # colored constellation nodes
        parts.append(f'<circle cx="{150 + (i % 5) * 200}" cy="{100 + (i // 5) * 170}" '
                     f'r="15" fill="#dbeafe" stroke="#2563eb" stroke-width="1.4"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert not any("gray-dominant" in s for s in issues)

def test_floor_survives_the_real_drawer():
    """End-to-end through SVGDrawer: a colored diagram keeps its palette PASS,
    a slate-only one draws the FAIL inside the full evaluate_svg report."""
    d = SVGDrawer(600, 400)
    d.rect(50, 50, 500, 120, fill="#dae8fc", stroke="#1b3a5c", stroke_width=1.5)
    issues = check_palette(d)
    assert not any("no chromatic accent" in s for s in issues)

    d2 = SVGDrawer(600, 400)
    d2.rect(50, 50, 500, 120, fill="#ffffff", stroke="#546e7a", stroke_width=2)
    issues2 = check_palette(d2)
    assert any("no chromatic accent" in s for s in issues2)


def _refine_drawer():
    """Two INDEPENDENT violation scenarios on one canvas.

    Left: node 'a' (60x30) sits 5px off the left edge of its 200x120 layer
    band (gutter 5 < 20) — centering it clears the gutter without touching
    anything else. Right: nodes 'b'/'c' are 6px apart on x (spacing 6 < 14);
    pushing 'c' +9px clears it. The two zones are far apart so one fixer's
    output never creates the other's violation."""
    d = SVGDrawer(600, 400)
    d.rect(10, 10, 200, 120, fill="#eef2f7", stroke="#1b3a5c", role="layer",
           node_id="band", bbox=False)
    d.rect(15, 40, 60, 30, fill="white", stroke="#1b3a5c", node_id="a")
    d.rect(400, 40, 60, 30, fill="white", stroke="#1b3a5c", node_id="b")
    d.rect(466, 40, 60, 30, fill="white", stroke="#1b3a5c", node_id="c")
    return d


def test_issues_carry_codes_and_evidence():
    """The auto-fixable checks emit Issue objects: stable code + measured
    evidence, while rendering byte-identically to the legacy strings."""
    from evaluator import check_spacing, check_composition, Issue
    d = _refine_drawer()
    sp = [i for i in check_spacing(d) if isinstance(i, Issue)]
    assert any(i.code == "spacing/too-close" for i in sp)
    tgt = [i for i in sp if i.code == "spacing/too-close"][0]
    assert tgt.evidence["gap"] == 6.0
    assert tgt.evidence["min_gap"] == 14.0
    assert isinstance(tgt, str) and "[spacing]" in tgt  # legacy rendering intact

    _, warn = check_composition(d)
    gut = [i for i in warn if isinstance(i, Issue) and i.code == "composition/gutter"]
    assert gut, "expected a gutter Issue for node 'a'"
    assert gut[0].evidence["container"] == (10.0, 10.0, 200.0, 120.0)


def test_auto_refine_fixes_from_evidence():
    """Gutter fix centers 'a' in its band; spacing fix pushes 'c' clear of
    'b' by the exact deficit — both sized from the measured evidence, and
    the violations disappear from the follow-up report."""
    from evaluator import auto_refine, check_spacing, check_composition, Issue
    d = _refine_drawer()
    score, report, fixes = auto_refine(d, target_score=100, max_iter=3)
    assert any("centered 'a'" in f for f in fixes)
    assert any("'c'" in f and "along x" in f for f in fixes)
    # Violations are gone in the final report.
    assert not [i for i in check_spacing(d)
                if isinstance(i, Issue) and i.code == "spacing/too-close"]
    _, warn = check_composition(d)
    assert not [i for i in warn
                if isinstance(i, Issue) and i.code == "composition/gutter"]
    # And the rendered SVG carries the moved coordinates.
    svg = d.render()
    assert 'x="466.0"' not in svg      # b stays at 400; c moved off 466
    assert 'x="80.0"' in svg           # centered 'a': 10 + (200-60)/2


def test_check_spacing_exempts_containment_pairs():
    """A chip fully inside its card is a legal layout: its clearance is the
    gutter rule's job, not sibling spacing. Regression guard for the replay
    incident where slots inside server_context were flagged '0.0px apart',
    auto_refine then pushed them into a collision (score 81 -> 41)."""
    import sys
    sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None
    from svg_utils import SVGDrawer
    from evaluator import check_spacing, _fix_spacing, _issue

    d = SVGDrawer(width=1280, height=900)
    d.rect(408, 681, 500, 110, node_id="server_context", node_kind="op")
    for k in range(4):
        d.rect(432 + k * 120, 735, 96, 40, node_id=f"slot_{k}", node_kind="op")
    # container<->slot pairs exempt; slot<->slot kept 24px apart -> no issues
    assert check_spacing(d) == []

    # a fabricated pre-fix issue on a containment pair must be refused
    fake = _issue("[spacing] 'slot_0' and 'server_context' only 0.0px apart (< 14.0).",
                  code="spacing/too-close", subject="slot_0", a="server_context",
                  gap=0.0, min_gap=14.0, axis="y")
    fixes = []
    assert _fix_spacing(d, fake, 0, fixes) is False
    assert any("contains it" in f for f in fixes)


def test_fix_gutter_protects_grid_arrays():
    """An equal-pitch row/column is intentional alignment: centering one
    member scatters the array and collides neighbours (the satellite replay
    incident: ground stations moved into a broken column, new collisions, a
    full repair round burned). A lone non-grid node must still be centered."""
    import sys
    sys.path.insert(0, str(SCRIPTS)) if str(SCRIPTS) not in sys.path else None
    from svg_utils import SVGDrawer
    from evaluator import _fix_gutter, _issue

    d = SVGDrawer(width=1280, height=960)
    d.rect(88, 816, 1104, 142, node_id="band_ground", node_kind="layer", role="layer")
    for gx, nid in [(175, "s0"), (325, "s1"), (475, "s2"), (625, "s3"), (775, "s4"), (925, "s5")]:
        d.rect(gx, 842, 120, 40, node_id=nid, node_kind="op")
    fake = _issue("[composition] node 's0' gutter 12.0px < 20.0 in container.",
                  code="composition/gutter", subject="s0",
                  gutter=12.0, min_gutter=20.0, container=(88, 816, 1104, 142))
    fixes = []
    assert _fix_gutter(d, fake, 0, fixes) is False
    assert any("grid" in f for f in fixes)
    # array alignment preserved
    xs = [d.nodes[n].x for n in ("s0", "s1", "s2", "s3", "s4", "s5")]
    assert len(set(round(x) for x in ys)) if (ys := [d.nodes[n].y for n in ("s0","s1","s2")]) else False
    assert all(abs((xs[k+1]-xs[k]) - 150) <= 2 for k in range(5))

    d2 = SVGDrawer(width=800, height=400)
    d2.rect(50, 50, 400, 200, node_id="band2", node_kind="layer", role="layer")
    d2.rect(60, 150, 120, 40, node_id="lone", node_kind="op")
    fake2 = _issue("[composition] node 'lone' gutter 10.0px < 20.0 in container.",
                   code="composition/gutter", subject="lone",
                   gutter=10.0, min_gutter=20.0, container=(50, 50, 400, 200))
    fixes2 = []
    assert _fix_gutter(d2, fake2, 0, fixes2) is True
