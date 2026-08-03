#!/usr/bin/env python3
"""CI/CD deployment pipeline — a process FLOWCHART (role palette, all roles).

The first eval case that is not an architecture diagram. Exercises primitives
and the documented flowchart role palette that no other case touches:
  - circle()  as green start/end terminators
  - decision()  as yellow branch diamonds (zero usages elsewhere in evals/)
  - hexagon()  as orange I/O (parallelogram substitute)
  - rect()     as blue process steps
  - rect() + inset rect() as purple double-border subprocess
Branches merge onto a single failure terminator so every edge is well-formed.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)

from svg_utils import SVGDrawer, save_svg, rasterize_svg
from svg2pptx import svg_to_pptx, PptxConfig
from evaluator import evaluate_svg

from pathlib import Path

OUT = Path(__file__).resolve().parent
NAME = "cicd_pipeline_flow"

W, H = 1000, 1240
CX = 500                       # center spine x
BX = 210                       # left failure-column x

# --- flowchart role palette (color = role) -------------------------------
GRN_F, GRN_S = "#D5E8D4", "#82B366"   # start / end terminator
BLU_F, BLU_S = "#DAE8FC", "#6C8EBF"   # process
YEL_F, YEL_S = "#FFF2CC", "#D6B656"   # decision
ORG_F, ORG_S = "#FFE6CC", "#D79B00"   # I/O (hexagon)
PUR_F, PUR_S = "#E1D5E7", "#9673A6"   # subprocess (double border)
EDGE = "#4D4D4D"                      # all edges gray
INK = "#1A1A1A"
SUB = "#555555"

F = [20, 14, 12, 10]          # title / label / sub / branch flag (>=1.15x apart)
BB = False                    # text stays out of the collision registry

d = SVGDrawer(W, H, bg="#FFFFFF")
d.arrow_head("ah", EDGE)

# --- title ----------------------------------------------------------------
d.text(CX, 44, "CI/CD 部署流水线  ·  Deployment Pipeline", font_size=F[0],
       weight="bold", fill=INK, anchor="middle", bbox=BB)

# --- geometry helpers -----------------------------------------------------
# decision(x,y,w,h) & rect/hexagon are corner-anchored; circle is centered.
DW, DH = 170, 84             # decision diamond
RW, RH = 200, 54             # process rect
HW, HH = 240, 56             # I/O hexagon
RR = 30                      # terminator radius


def term(cx, cy, nid):
    """Green terminator circle. Label is placed separately, OFF the circle,
    so the text-overlap check never flags text sitting on its own shape."""
    d.circle(cx, cy, RR, fill=GRN_F, stroke=GRN_S, stroke_width=1.8,
             node_id=nid, node_kind="op", bbox=True)


def io_hex(cx, cy, nid, title, sub=""):
    d.hexagon(cx - HW / 2, cy - HH / 2, HW, HH, fill=ORG_F, stroke=ORG_S,
              stroke_width=1.4, node_id=nid, node_kind="op", bbox=True)
    d.text(cx, cy - (4 if sub else 0), title, font_size=F[1], weight="bold",
           fill=INK, anchor="middle", bbox=BB)
    if sub:
        d.text(cx, cy + 14, sub, font_size=F[3], fill=SUB, anchor="middle",
               bbox=BB)


def proc(cx, cy, nid, title, sub=""):
    d.rect(cx - RW / 2, cy - RH / 2, RW, RH, rx=7, fill=BLU_F, stroke=BLU_S,
           stroke_width=1.4, node_id=nid, node_kind="op", bbox=True)
    d.text(cx, cy - (4 if sub else 0), title, font_size=F[1], weight="bold",
           fill=INK, anchor="middle", bbox=BB)
    if sub:
        d.text(cx, cy + 14, sub, font_size=F[3], fill=SUB, anchor="middle",
               bbox=BB)


def diamond(cx, cy, nid, label):
    d.decision(cx - DW / 2, cy - DH / 2, DW, DH, fill=YEL_F, stroke=YEL_S,
               stroke_width=1.6, node_id=nid, node_kind="op", bbox=True)
    d.text(cx, cy - 6, label, font_size=F[1], weight="bold", fill=INK,
           anchor="middle", bbox=BB)
    d.text(cx, cy + 14, "decision", font_size=F[3], fill=SUB,
           anchor="middle", bbox=BB)


def subprocess(cx, cy, nid, title, sub=""):
    """Purple process with an inset second border (double-border subprocess)."""
    d.rect(cx - RW / 2, cy - RH / 2, RW, RH, rx=7, fill=PUR_F, stroke=PUR_S,
           stroke_width=1.4, node_id=nid, node_kind="op", bbox=True)
    # decorative inset border — NOT a node (no collision/edge role).
    d.rect(cx - RW / 2 + 4, cy - RH / 2 + 4, RW - 8, RH - 8, rx=5,
           fill="none", stroke=PUR_S, stroke_width=1.0, role="decoration")
    d.text(cx, cy - (4 if sub else 0), title, font_size=F[1], weight="bold",
           fill=INK, anchor="middle", bbox=BB)
    if sub:
        d.text(cx, cy + 14, sub, font_size=F[3], fill=SUB, anchor="middle",
               bbox=BB)


def yes_no(start, end, txt):
    """Place a 是/否 flag CLEAR of its edge: perpendicular offset picked from
    the edge's dominant axis, so the label never sits on the line."""
    mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    dx, dy = abs(end[0] - start[0]), abs(end[1] - start[1])
    if dy >= dx:  # vertical spine -> label to the right of the line
        d.text(mx + 32, my + 4, txt, font_size=F[3], weight="bold",
               fill=SUB, anchor="middle", bbox=BB)
    else:         # horizontal branch -> label above the line
        d.text(mx, my - 16, txt, font_size=F[3], weight="bold",
               fill=SUB, anchor="middle", bbox=BB)


# --- nodes (center spine, then failure column) ---------------------------
# y-centers spaced ~200px (flowchart layout cheatsheet).
term(CX, 100, "start")
io_hex(CX, 200, "hook", "Webhook", "push event 触发")
proc(CX, 300, "build", "构建 Build", "编译 · 单元测试")
diamond(CX, 410, "build_ok", "构建成功?")
subprocess(CX, 530, "tests", "测试套件", "unit · integration")
diamond(CX, 650, "test_ok", "测试通过?")
proc(CX, 770, "deploy", "部署到生产", "Deploy to Prod")
term(CX, 880, "released")

# failure column (left): one notify process + one shared failure terminator.
proc(BX, 410, "notify", "通知失败", "Notify Failure")
term(BX, 650, "failed")

# terminator labels — placed OFF the circles (right of spine / left of column)
# so the text-overlap check never flags label-on-own-shape.
d.text(CX + 46, 104, "开始", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)
d.text(CX + 50, 884, "已发布", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)
d.text(BX - 46, 654, "失败", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)

# --- edges (all gray, snapped to node borders) ---------------------------
d.connect("start", "bottom", "hook", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")
d.connect("hook", "bottom", "build", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")
d.connect("build", "bottom", "build_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

# Build OK? -> No (left) -> notify -> down -> failed
b_no = d.connect("build_ok", "left", "notify", "right", stroke=EDGE,
                 stroke_width=1.8, marker_end="ah")
yes_no(b_no[0], b_no[1], "否 No")
d.connect("notify", "bottom", "failed", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

# Build OK? -> Yes (down) -> tests
b_yes = d.connect("build_ok", "bottom", "tests", "top", stroke=EDGE,
                  stroke_width=1.8, marker_end="ah")
yes_no(b_yes[0], b_yes[1], "是 Yes")
d.connect("tests", "bottom", "test_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

# Tests Pass? -> No (left, straight) -> failed (convergence)
t_no = d.connect("test_ok", "left", "failed", "right", stroke=EDGE,
                 stroke_width=1.8, marker_end="ah", dashed="6,4")
yes_no(t_no[0], t_no[1], "否 No")

# Tests Pass? -> Yes (down) -> deploy -> released
t_yes = d.connect("test_ok", "bottom", "deploy", "top", stroke=EDGE,
                  stroke_width=1.8, marker_end="ah")
yes_no(t_yes[0], t_yes[1], "是 Yes")
d.connect("deploy", "bottom", "released", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

# --- score + artifact triplet -------------------------------------------
svg = d.render()
score, rep = evaluate_svg(d)
print(f"Score: {score}")
for r in rep:
    print(f"  {r}")
sp = str(OUT / f"{NAME}.svg")
save_svg(svg, sp)
rasterize_svg(sp, str(OUT / f"{NAME}.png"), width=W)
try:
    svg_to_pptx(svg, str(OUT / f"{NAME}.pptx"),
                config=PptxConfig(slide_w=13.333, slide_h=7.5, scale=2.0))
except Exception as e:
    print(f"[pptx: {e}]")
print(f"\n✓ {NAME}.svg / .png / .pptx")
