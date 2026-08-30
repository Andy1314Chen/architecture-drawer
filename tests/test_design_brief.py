"""Design Brief contract tests (schema + check_design_brief A/B/C).

Covers the migration-critical behaviors:
  - schema: single-source derivation, flow_chain subset validation, enum
    guards, color normalization, json round-trip;
  - A palette: missing declared key FAIL, tint->white FAIL, wrong tint WARN,
    stroke mismatch WARN, undeclared chromatic paint WARN;
  - B layout: empty declared band FAIL, undeclared layer container WARN,
    node-style + rendered container FAIL, text-only band non-empty PASS;
  - C flow: direction dominance FAIL (inverted routing), legit back-edge
    tolerance PASS, chain degree rules, declared-order vs geometry,
    flow=none / no-chain short-circuits;
  - run_semantic_qa: absent brief -> visible WARN (anti-freerider).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugins"
                        / "architecture-drawer" / "skills"
                        / "architecture-drawer" / "scripts"))

from design_brief import ColorSpec, DesignBrief, is_plain, norm_hex  # noqa: E402
from semantic_qa import run_semantic_qa  # noqa: E402
from svg_utils import SVGDrawer  # noqa: E402


def _codes(res):
    return [i.code for i in res.issues]


# ---------------------------------------------------------------------------
# 1. schema
# ---------------------------------------------------------------------------
def test_norm_hex_and_is_plain():
    assert norm_hex("White") == "#ffffff"
    assert norm_hex("#FFF") == "#ffffff"
    assert norm_hex("#DAE8FC") == "#dae8fc"
    assert is_plain("white") and is_plain("#FFFFFF") and is_plain("none")
    assert not is_plain("#dae8fc")


def test_tint_plain_derived_not_declared():
    b = DesignBrief(palette_role={
        "a": ColorSpec("#dae8fc", "#1b3a5c"),
        "b": ColorSpec("white", "#1b3a5c")})
    assert b.tint_keys == ("a",)
    assert b.plain_keys == ("b",)


def test_flow_chain_must_be_palette_subset():
    with pytest.raises(ValueError, match="not declared in palette_role"):
        DesignBrief(palette_role={"a": ColorSpec("#dae8fc", "#1b3a5c")},
                    flow_chain=("a", "ghost"))


def test_invalid_enums_rejected():
    with pytest.raises(ValueError, match="layout"):
        DesignBrief(layout="hub-spoke")
    with pytest.raises(ValueError, match="flow"):
        DesignBrief(flow="radial")


def test_json_round_trip_and_write(tmp_path):
    b = DesignBrief(scheme="S2", layout="band", flow="top-down",
                    palette_role={"x": ColorSpec("#dae8fc", "#1b3a5c")},
                    flow_chain=("x",))
    b.write(tmp_path / "brief.json")
    b2 = DesignBrief.load(str(tmp_path / "brief.json"))
    assert b2 == b


# ---------------------------------------------------------------------------
# fixtures: a clean two-band diagram and its brief
# ---------------------------------------------------------------------------
BRIEF = DesignBrief(layout="band", flow="top-down", palette_role={
    "api":    ColorSpec("#dae8fc", "#1b3a5c"),
    "engine": ColorSpec("#d5e8d4", "#1b3a5c"),
}, flow_chain=("api", "engine"))


def _band_drawer(tint_api="#dae8fc", *, api_empty=False, flow_up=False):
    d = SVGDrawer(600, 420)
    d.arrow_head("ar", "#1b3a5c")
    d.rect(20, 20, 560, 160, fill=tint_api, stroke="#1b3a5c",
           node_id="api", role="layer")
    d.rect(20, 230, 560, 160, fill="#d5e8d4", stroke="#1b3a5c",
           node_id="engine", role="layer")
    if not api_empty:
        d.rect(60, 60, 100, 40, fill="white", stroke="#1b3a5c", node_id="t1")
    d.rect(60, 270, 100, 40, fill="white", stroke="#1b3a5c", node_id="b1")
    if api_empty:
        return d          # no cross edge exists — that is the point
    if flow_up:
        d.connect("b1", "top", "t1", "bottom",
                  stroke="#1b3a5c", marker_end="ar")
    else:
        d.connect("t1", "bottom", "b1", "top",
                  stroke="#1b3a5c", marker_end="ar")
    return d


# ---------------------------------------------------------------------------
# 2. assertion A — palette contract
# ---------------------------------------------------------------------------
def test_honest_band_diagram_is_clean():
    res = run_semantic_qa(_band_drawer(), brief=BRIEF)
    assert not [c for c in _codes(res) if c.startswith("brief-")]


def test_declared_key_missing_fails():
    brief = DesignBrief(palette_role={
        "api": ColorSpec("#dae8fc", "#1b3a5c"),
        "kv":  ColorSpec("#ffe6cc", "#d79b00")}, flow_chain=("api",))
    res = run_semantic_qa(_band_drawer(), brief=brief)
    assert "brief-shape-missing" in _codes(res)


def test_declared_tint_rendered_white_fails():
    d = SVGDrawer(600, 420)
    d.arrow_head("ar", "#1b3a5c")
    d.rect(20, 20, 560, 160, fill="white", stroke="#1b3a5c",
           node_id="api", role="layer")
    d.rect(20, 230, 560, 160, fill="#d5e8d4", stroke="#1b3a5c",
           node_id="engine", role="layer")
    d.rect(60, 60, 100, 40, fill="white", stroke="#1b3a5c", node_id="t1")
    d.rect(60, 270, 100, 40, fill="white", stroke="#1b3a5c", node_id="b1")
    d.connect("t1", "bottom", "b1", "top", stroke="#1b3a5c", marker_end="ar")
    res = run_semantic_qa(d, brief=BRIEF)
    assert "brief-tint-lost" in _codes(res)


def test_wrong_tint_and_stroke_warn():
    wrong = DesignBrief(palette_role={
        "api":    ColorSpec("#ffe6cc", "#d79b00"),
        "engine": ColorSpec("#d5e8d4", "#1b3a5c")}, flow_chain=("api", "engine"))
    res = run_semantic_qa(_band_drawer(), brief=wrong)
    codes = _codes(res)
    assert "brief-fill-mismatch" in codes
    assert "brief-stroke-mismatch" in codes
    assert "brief-tint-lost" not in codes   # still colored, only wrong tint


def test_undeclared_chromatic_paint_warns():
    d = _band_drawer()
    d.rect(300, 300, 90, 40, fill="#e1d5e7", stroke="#9673a6", node_id="odd")
    res = run_semantic_qa(d, brief=BRIEF)
    codes = _codes(res)
    assert "brief-fill-undeclared" in codes
    assert "brief-stroke-undeclared" in codes


# ---------------------------------------------------------------------------
# 3. assertion B — layout contract
# ---------------------------------------------------------------------------
def test_empty_declared_band_fails():
    res = run_semantic_qa(_band_drawer(api_empty=True), brief=BRIEF)
    assert "brief-layer-empty" in _codes(res)


def test_text_only_band_is_not_empty():
    d = SVGDrawer(600, 420)
    d.arrow_head("ar", "#1b3a5c")
    d.rect(20, 20, 560, 160, fill="#dae8fc", stroke="#1b3a5c",
           node_id="api", role="layer")
    d.rect(20, 230, 560, 160, fill="#d5e8d4", stroke="#1b3a5c",
           node_id="engine", role="layer")
    d.rect(60, 60, 100, 40, fill="white", stroke="#1b3a5c", node_id="t1")
    d.text(300, 300, "bullets band", font_size=12, bbox=False)
    d.text(300, 320, "second line", font_size=12, bbox=False)
    d.rect(300, 340, 90, 40, fill="white", stroke="#1b3a5c", node_id="b1")
    d.connect("t1", "bottom", "b1", "top", stroke="#1b3a5c", marker_end="ar")
    res = run_semantic_qa(d, brief=BRIEF)
    assert "brief-layer-empty" not in _codes(res)


def test_undeclared_layer_container_warns():
    d = _band_drawer()
    d.rect(20, 400, 200, 15, fill="#d5e8d4", stroke="#1b3a5c",
           role="layer")     # no data-node-id, not in palette
    res = run_semantic_qa(d, brief=BRIEF)
    assert "brief-layer-undeclared" in _codes(res)


def test_node_style_with_container_fails():
    node_brief = DesignBrief(layout="node", palette_role={
        "t1": ColorSpec("white", "#1b3a5c")})
    res = run_semantic_qa(_band_drawer(), brief=node_brief)
    assert "brief-layout-contradicted" in _codes(res)


# ---------------------------------------------------------------------------
# 4. assertion C — flow contract
# ---------------------------------------------------------------------------
def _grid_drawer(up_count, down_count):
    """Two bands with N up-edges and M down-edges between them."""
    d = SVGDrawer(1200, 420)
    d.arrow_head("ar", "#1b3a5c")
    d.rect(10, 10, 1180, 160, fill="#dae8fc", stroke="#1b3a5c",
           node_id="api", role="layer")
    d.rect(10, 230, 1180, 160, fill="#d5e8d4", stroke="#1b3a5c",
           node_id="engine", role="layer")
    n = up_count + down_count
    for i in range(n):
        x = 30 + i * (1140 // max(n, 1))
        d.rect(x, 60, 90, 40, fill="white", stroke="#1b3a5c", node_id=f"t{i}")
        d.rect(x, 270, 90, 40, fill="white", stroke="#1b3a5c", node_id=f"b{i}")
    for i in range(down_count):
        d.connect(f"t{i}", "bottom", f"b{i}", "top",
                  stroke="#1b3a5c", marker_end="ar")
    for i in range(up_count):
        j = down_count + i
        d.connect(f"b{j}", "top", f"t{j}", "bottom",
                  stroke="#1b3a5c", marker_end="ar")
    return d


def test_inverted_flow_dominance_fails():
    # 4 edges, 3 inverted: 25% follow top-down < 70%
    res = run_semantic_qa(_grid_drawer(up_count=3, down_count=1), brief=BRIEF)
    assert "brief-flow-dominance" in _codes(res)

def test_misdeclared_flow_axis_fails():
    # vertical spine declared as "left-right": every inter-layer edge
    # travels farther along the cross axis — must FAIL even though the
    # sample is too small for the directional-dominance ratio.
    lr = DesignBrief(layout="band", flow="left-right",
                     palette_role=BRIEF.palette_role,
                     flow_chain=BRIEF.flow_chain)
    codes = _codes(run_semantic_qa(_grid_drawer(up_count=1, down_count=4),
                                   brief=lr))
    assert "brief-flow-axis" in codes


def test_true_flow_axis_clean():
    codes = _codes(run_semantic_qa(_grid_drawer(up_count=1, down_count=4),
                                   brief=BRIEF))
    assert "brief-flow-axis" not in codes


def test_legit_back_edges_tolerated():
    # 5 edges, 1 return: 80% follow top-down >= 70% — must PASS
    res = run_semantic_qa(_grid_drawer(up_count=1, down_count=4), brief=BRIEF)
    codes = _codes(res)
    assert "brief-flow-dominance" not in codes
    assert "brief-chain-broken" not in codes


def test_broken_chain_degree_fails():
    # edges only INSIDE each band's own nodes... construct: single down edge
    # api->engine plus an isolated extra pair with no cross edge is fine;
    # break the chain by removing the only cross edge entirely
    d = SVGDrawer(600, 420)
    d.rect(20, 20, 560, 160, fill="#dae8fc", stroke="#1b3a5c",
           node_id="api", role="layer")
    d.rect(20, 230, 560, 160, fill="#d5e8d4", stroke="#1b3a5c",
           node_id="engine", role="layer")
    d.rect(60, 60, 100, 40, fill="white", stroke="#1b3a5c", node_id="t1")
    d.rect(300, 60, 100, 40, fill="white", stroke="#1b3a5c", node_id="t2")
    d.rect(60, 270, 100, 40, fill="white", stroke="#1b3a5c", node_id="b1")
    d.connect("t1", "right", "t2", "left", stroke="#333")  # intra-band only
    res = run_semantic_qa(d, brief=BRIEF)
    codes = _codes(res)
    assert "brief-chain-broken" in codes


def test_flow_none_skips_c():
    res = run_semantic_qa(_grid_drawer(up_count=3, down_count=1),
                          brief=DesignBrief(
                              layout="band", flow="none",
                              palette_role=BRIEF.palette_role,
                              flow_chain=("api", "engine")))
    assert not [c for c in _codes(res)
                if c in ("brief-flow-dominance", "brief-chain-broken")]


def test_no_chain_short_circuits_c():
    res = run_semantic_qa(_grid_drawer(up_count=3, down_count=1),
                          brief=DesignBrief(palette_role=BRIEF.palette_role))
    assert not [c for c in _codes(res)
                if c in ("brief-flow-dominance", "brief-chain-broken")]


def test_declared_order_vs_geometry():
    # declare engine ABOVE api while geometry disagrees
    flipped = DesignBrief(layout="band", flow="top-down", palette_role={
        "api":    ColorSpec("#dae8fc", "#1b3a5c"),
        "engine": ColorSpec("#d5e8d4", "#1b3a5c")}, flow_chain=("engine", "api"))
    res = run_semantic_qa(_band_drawer(), brief=flipped)
    assert "brief-layer-order" in _codes(res)


# ---------------------------------------------------------------------------
# 5. orchestration — absent brief is visible
# ---------------------------------------------------------------------------
def test_absent_brief_warns():
    res = run_semantic_qa(_band_drawer())
    assert "brief-absent" in _codes(res)


def test_brief_dict_coercion():
    res = run_semantic_qa(_band_drawer(), brief=BRIEF.to_dict())
    assert not [c for c in _codes(res) if c.startswith("brief-")]
