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
