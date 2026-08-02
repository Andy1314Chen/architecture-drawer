"""Unit tests for SVGDrawer primitives that the black-box regression suite
(``test_regression.py``) does not exercise directly: post-emit relocation
(``relocate_node``) and the pure-geometry layout helpers.

``relocate_node`` must keep the rendered SVG, the Node registry, AND the Edge
registry in sync — the evaluator's connection/crossing checks read
``drawer.edges[*].start/.end/.path_d``, not the re-parsed SVG, so a re-emit that
left those stale would report phantom dangles and undermine auto_refine.
"""
from __future__ import annotations

import math
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(
    os.path.join(_HERE, "..", "plugins", "architecture-drawer",
                 "skills", "architecture-drawer", "scripts")
)
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)

from svg_utils import SVGDrawer, layout_radial, _angle_to_side  # noqa: E402


# --------------------------------------------------------------------------
# relocate_node — registry / SVG sync (the B1 contract)
# --------------------------------------------------------------------------
def test_relocate_syncs_edge_registry_straight_edge():
    """A straight edge's start/end must track its endpoint node's new border."""
    d = SVGDrawer(600, 400)
    d.rect(100, 100, 80, 40, node_id="a")
    d.rect(300, 100, 80, 40, node_id="b")
    d.connect("a", "right", "b", "left")
    edge = d.edges[0]
    old_end = edge.end

    assert d.relocate_node("b", 350, 100) is True

    # Registry follows the move ...
    assert edge.end != old_end
    assert edge.end == (350.0, 120.0)  # b's new left-border midpoint
    # ... and so does the rendered SVG (b's rect + the re-routed line).
    svg = d.render()
    assert 'x="350"' in svg
    assert edge.end[0] == 350.0


def test_relocate_syncs_curve_edge_path_d():
    """A curved edge's path_d AND endpoints must refresh on relocate."""
    d = SVGDrawer(600, 400)
    d.rect(50, 50, 60, 30, node_id="p")
    d.rect(400, 50, 60, 30, node_id="q")
    d.connect("p", "right", "q", "left", as_curve=True, curve_dir="h")
    edge = d.edges[0]
    old_path_d = edge.path_d

    assert d.relocate_node("q", 450, 50) is True

    assert edge.path_d != old_path_d          # curve geometry regenerated
    assert edge.end == (450.0, 65.0)          # q's new left-border midpoint


def test_relocate_no_false_dangle_in_evaluator():
    """End-to-end: after relocating a connected node, the evaluator's
    connection check must NOT report a phantom dangle (the bug B1 fixed).

    Before B1, the re-routed edge XML moved but edge.end stayed ~20px stale,
    exceeding conn_tolerance (12px) and producing a false [FAIL] dangle.
    """
    d = SVGDrawer(600, 400)
    d.rect(100, 100, 80, 40, node_id="a")
    d.rect(300, 100, 80, 40, node_id="b")
    d.connect("a", "right", "b", "left")
    d.relocate_node("b", d.nodes["b"].x + 50, d.nodes["b"].y)

    # evaluator imports from svg_utils via the same sys.path entry.
    from evaluator import check_connections
    issues = check_connections(d, tolerance=12.0)
    assert issues == [], f"phantom dangle after relocate: {issues}"


# --------------------------------------------------------------------------
# relocate_node — shapes / contexts that must refuse
# --------------------------------------------------------------------------
@pytest.mark.parametrize("shape", ["database", "decision", "hexagon", "cloud"])
def test_non_rect_circle_shapes_not_relocatable(shape):
    """Shapes without _record_rebuild return False (reported by auto_refine,
    never silently relocating to stale XML)."""
    d = SVGDrawer(600, 400)
    fn = getattr(d, shape)
    fn(100, 100, 80, 60, node_id="x")
    assert d.relocate_node("x", 200, 200) is False


def test_node_drawn_in_group_not_relocatable():
    """Nodes inside a group() are local-coord; relocation is meaningless."""
    d = SVGDrawer(600, 400)
    with d.group("translate(100,50)"):
        d.rect(0, 0, 60, 30, node_id="g")
    assert d.relocate_node("g", 500, 500) is False


def test_relocate_unknown_node_returns_false():
    d = SVGDrawer(600, 400)
    assert d.relocate_node("nope", 10, 10) is False


# --------------------------------------------------------------------------
# layout_radial / _angle_to_side — pure geometry
# --------------------------------------------------------------------------
def test_layout_radial_places_hub_center_neighbors_on_circle():
    pos, sides = layout_radial(
        hub=("hub", 60, 30),
        neighbors=[("n0", 40, 20), ("n1", 40, 20), ("n2", 40, 20)],
        center=(300, 200),
        radius=120,
        start_angle=-90.0,
    )
    # Hub centered.
    assert pos["hub"] == (270.0, 185.0, 60, 30)
    # Neighbors at exact radius from center.
    for nid in ("n0", "n1", "n2"):
        x, y, w, h = pos[nid]
        ncx, ncy = x + w / 2, y + h / 2
        assert math.hypot(ncx - 300, ncy - 200) == pytest.approx(120, abs=1e-6)
    # Every neighbor has connect() sides assigned.
    assert set(sides) == {"n0", "n1", "n2"}
    # First neighbor straight up -> neighbor is above hub.
    assert sides["n0"] == ("bottom", "top")


def test_angle_to_side_quadrants():
    assert _angle_to_side(0) == ("left", "right")       # neighbor right of hub
    assert _angle_to_side(90) == ("top", "bottom")      # neighbor below hub
    assert _angle_to_side(180) == ("right", "left")     # neighbor left of hub
    assert _angle_to_side(-90) == ("bottom", "top")     # neighbor above hub


def test_layout_radial_zero_neighbors():
    pos, sides = layout_radial(("h", 10, 10), [], (50, 50), 30)
    assert pos == {"h": (45.0, 45.0, 10, 10)}
    assert sides == {}


# ==========================================================================
# Round 2: evaluator correctness (claims 1/2/4/5) + svg_utils robustness (3/6)
# ==========================================================================
from evaluator import (  # noqa: E402
    check_composition, _estimate_text_width, _text_bboxes,
)


# ---- claim 1: reorder_barycenter was dead code crashing on Edge.start_id ----
def test_reorder_barycenter_removed():
    """The function referenced Edge.start_id/end_id (which don't exist; only
    from_id/to_id do) and had zero callers. Deleting it is safer than shipping
    a crash-on-first-use exported helper."""
    import evaluator
    assert not hasattr(evaluator, "reorder_barycenter"), (
        "reorder_barycenter should be deleted (crashed on Edge.start_id, "
        "zero callers)")


# ---- claim 2: curve edges must not report false bends / short segments ----
def test_curve_edge_no_false_bend_or_short_segment():
    """A connect(as_curve=True) edge between differently-y endpoints samples
    into a polyline whose every micro-segment is non-collinear. The old
    `cross != 0` exact test counted all of them as bends (reported '15 bends
    (limit 2)'); the tessellation artifacts also tripped shortest-segment.
    Curves are continuous-curvature by design and must be exempt."""
    d = SVGDrawer(600, 400)
    d.rect(50, 50, 80, 40, node_id="a")
    d.rect(400, 200, 80, 40, node_id="b")
    d.connect("a", "right", "b", "left", as_curve=True, curve_dir="h")
    _, warn = check_composition(d)
    edge_warns = [w for w in warn if "edge" in w
                  and ("bend" in w or "segment" in w)]
    assert edge_warns == [], f"curve edge falsely flagged: {edge_warns}"


def test_straight_polyline_still_counts_bends():
    """Bend detection must still fire for genuine orthogonal polyline routing
    (a path_d of only M/L commands). This guards against over-exemption: only
    curves (C/S/Q/T/A) are skipped, not all path_d edges."""
    d = SVGDrawer(800, 400)
    d.path("M50,50 L200,50 L200,150 L400,150 L400,250 L600,250",
           edge_id="zig", register_edge=True, start=(50, 50), end=(600, 250))
    _, warn = check_composition(d)
    assert any("zig" in w and "bend" in w for w in warn), (
        "orthogonal 4-bend polyline must be flagged")


def test_straight_two_bend_not_flagged():
    """Two bends is at the limit (max_bends=2) and must NOT warn."""
    d = SVGDrawer(800, 400)
    d.path("M50,50 L200,50 L200,150 L600,150",
           edge_id="L2", register_edge=True, start=(50, 50), end=(600, 150))
    _, warn = check_composition(d)
    assert not any("L2" in w and "bend" in w for w in warn)


# ---- claim 4: text metric model unified to center (dominant-baseline=central) ----
def test_text_bbox_uses_center_model():
    """SVGDrawer emits dominant-baseline='central', so (x,y) is the vertical
    CENTER of the glyphs. _text_bboxes and check_text_overflow must use the
    center model (ty +/- fs/2), not the baseline model (ty-0.8fs .. ty+0.2fs)
    which was off by 0.3fs."""
    d = SVGDrawer(200, 100)
    d.rect(40, 30, 120, 40, node_id="box")  # container
    d.text(100, 50, "hi", font_size=14)      # centered in box
    svg = d.render()
    bboxes = _text_bboxes(svg)
    assert len(bboxes) == 1
    lx, ty, rx, by = bboxes[0]
    # center model: top = 50 - 14/2 = 43, bottom = 50 + 14/2 = 57
    assert ty == pytest.approx(43, abs=0.5)
    assert by == pytest.approx(57, abs=0.5)


# ---- claim 5: HTML entities must not inflate text width ----
def test_estimate_text_width_unescapes_entities():
    """svg_utils.text() html.escape()s content before emitting, so the
    evaluator parses 'a&amp;b' from the rendered SVG. _estimate_text_width
    must html.unescape it back to 'a&b' (3 glyphs), not count 5 chars."""
    assert _estimate_text_width("a&amp;b", 14, False) == _estimate_text_width("a&b", 14, False)
    # sanity: the unescaped width is for 3 glyphs, not 5
    raw = _estimate_text_width("a&b", 14, False)
    five = _estimate_text_width("abcde", 14, False)
    assert raw < five


# ---- claim 3: relocate_node guards survive python -O ----
def test_relocate_node_raises_not_asserts():
    """The element-count invariant must raise RuntimeError (not assert, which
    `python -O` strips) so a malformed rebuild can never silently corrupt the
    element list and shift every downstream _emit_range index."""
    d = SVGDrawer(200, 100)
    d.rect(50, 50, 60, 30, node_id="n")
    # Force a rebuild that emits the wrong number of elements.
    d.nodes["n"]._emit_range = (0, 1)
    d.nodes["n"]._rebuild_xml = lambda nx, ny: ["x", "y", "z"]
    with pytest.raises(RuntimeError, match="node rebuild emitted"):
        d.relocate_node("n", 100, 100)


# ---- claim 6: component bbox must include the left-protruding tabs ----
def test_component_bbox_includes_tabs():
    """component() draws two tabs at x='-8' inside a translate group, so they
    protrude 8px LEFT of the box. The collision bbox must cover them or a
    left-side neighbor collision is missed."""
    d = SVGDrawer(300, 200)
    d.component(100, 80, 80, 50, node_id="c", bbox=True)
    b = d.bboxes[-1]
    assert b.x == 92 and b.w == 88, (b.x, b.w)  # x-8, w+8
