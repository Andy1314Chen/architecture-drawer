#!/usr/bin/env python3
"""CI/CD deployment pipeline — a process FLOWCHART (role palette, all roles).

The first eval case that is not an architecture diagram. Exercises primitives
and the documented flowchart role palette that no other case touches:
  - circle()  as green start/end terminators + gray junction merge points
  - decision()  as yellow branch diamonds (zero usages elsewhere in evals/)
  - hexagon()  as orange I/O (parallelogram substitute)
  - rect()     as blue process steps
  - rect() + inset rect() as purple double-border subprocess
Four quality-gate decisions branch "No" to a shared failure column that
converges via junction merge points on a single Failed terminator.
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

# Compact TB layout: ~105px center-to-center (well above the evaluator's
# ≥14px min gap — the diamond's 84px height needs ≥84px c2c). Render the PNG
# at 2× width for crisp display on high-DPI screens (SVG is vector, so the
# upscale is lossless).
W, H = 1000, 1520
PNG_W = W * 2          # 2× rasterize for a sharp showcase PNG
CX = 500               # center spine x
BX = 210               # left failure-column x

# --- flowchart role palette (color = role) -------------------------------
GRN_F, GRN_S = "#D5E8D4", "#82B366"   # start / end terminator
BLU_F, BLU_S = "#DAE8FC", "#6C8EBF"   # process
YEL_F, YEL_S = "#FFF2CC", "#D6B656"   # decision
ORG_F, ORG_S = "#FFE6CC", "#D79B00"   # I/O (hexagon)
PUR_F, PUR_S = "#E1D5E7", "#9673A6"   # subprocess (double border)
JCT_F, JCT_S = "#B0B0B0", "#666666"   # junction merge point (neutral gray)
EDGE = "#4D4D4D"                      # all edges gray
INK = "#1A1A1A"
SUB = "#555555"

F = [20, 14, 12, 10]          # title / node-label / subtitle / sub-label
BB = False                    # text stays out of the collision registry

d = SVGDrawer(W, H, bg="#FFFFFF")
d.arrow_head("ah", EDGE)

# --- title ----------------------------------------------------------------
d.text(CX, 38, "CI/CD 部署流水线", font_size=F[0], weight="bold",
       fill=INK, anchor="middle", bbox=BB)
d.text(CX, 62, "Continuous Integration & Continuous Deployment Pipeline",
       font_size=F[2], fill=SUB, anchor="middle", bbox=BB)

# --- geometry helpers -----------------------------------------------------
# decision(x,y,w,h) & rect/hexagon are corner-anchored; circle is centered.
DW, DH = 170, 84             # decision diamond
RW, RH = 220, 56             # process rect (wide enough for tool names)
HW, HH = 240, 56             # I/O hexagon
RR = 30                      # terminator radius
JR = 6                       # junction radius


def term(cx, cy, nid):
    """Green terminator circle. Label is placed separately, OFF the circle."""
    d.circle(cx, cy, RR, fill=GRN_F, stroke=GRN_S, stroke_width=1.8,
             node_id=nid, node_kind="op", bbox=True)


def junction(cx, cy, nid):
    """Small gray merge point on the failure column."""
    d.circle(cx, cy, JR, fill=JCT_F, stroke=JCT_S, stroke_width=1.2,
             node_id=nid, node_kind="junction", bbox=True)


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


def diamond(cx, cy, nid, label, sub_label):
    d.decision(cx - DW / 2, cy - DH / 2, DW, DH, fill=YEL_F, stroke=YEL_S,
               stroke_width=1.6, node_id=nid, node_kind="op", bbox=True)
    d.text(cx, cy - 6, label, font_size=F[1], weight="bold", fill=INK,
           anchor="middle", bbox=BB)
    d.text(cx, cy + 14, sub_label, font_size=F[3], fill=SUB,
           anchor="middle", bbox=BB)


def subprocess_box(cx, cy, nid, title, sub=""):
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


# --- nodes: center spine (compact ~105px c2c) ----------------------------
term(CX, 105, "start")
io_hex(CX, 207, "hook", "Webhook", "push · PR merge")
subprocess_box(CX, 312, "checkout", "检出 & 构建", "git clone · npm ci · compile")
diamond(CX, 430, "build_ok", "构建成功?", "Build OK?")
subprocess_box(CX, 548, "lint", "代码检查", "ESLint · MyPy · SAST scan")
diamond(CX, 666, "lint_ok", "检查通过?", "Lint OK?")
subprocess_box(CX, 784, "tests", "测试套件", "unit · integration · e2e")
diamond(CX, 902, "test_ok", "测试通过?", "Tests Pass?")
proc(CX, 1010, "staging", "部署预发布", "Deploy Staging · kubectl rolling")
proc(CX, 1115, "smoke", "冒烟测试", "Smoke Test · health · contract")
diamond(CX, 1233, "smoke_ok", "冒烟通过?", "Smoke OK?")
proc(CX, 1351, "deploy", "部署生产", "Deploy Prod · canary → blue-green")
term(CX, 1456, "released")

# --- nodes: failure column (shares spine y at each decision) -------------
proc(BX, 430, "notify", "通知失败", "Notify · Slack · Email")
junction(BX, 666, "m1")
junction(BX, 902, "m2")
term(BX, 1233, "failed")

# --- terminator labels (off-circle, +4 from center) ----------------------
d.text(CX + 46, 109, "开始", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)
d.text(CX + 50, 1460, "已发布", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)
d.text(BX - 46, 1237, "失败", font_size=F[1], weight="bold", fill=INK,
       anchor="middle", bbox=BB)

# --- edges: spine (down) -------------------------------------------------
d.connect("start", "bottom", "hook", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")
d.connect("hook", "bottom", "checkout", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")
d.connect("checkout", "bottom", "build_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("build_ok", "bottom", "lint", "top", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "是 Yes")
d.connect("lint", "bottom", "lint_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("lint_ok", "bottom", "tests", "top", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "是 Yes")
d.connect("tests", "bottom", "test_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("test_ok", "bottom", "staging", "top", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "是 Yes")
d.connect("staging", "bottom", "smoke", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")
d.connect("smoke", "bottom", "smoke_ok", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("smoke_ok", "bottom", "deploy", "top", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "是 Yes")
d.connect("deploy", "bottom", "released", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

# --- edges: failure column (convergence via junctions) -------------------
# D1 No → Notify → (down) → m1;  D2 No → m1 → (down) → m2;
# D3 No → m2 → (down) → Failed;  D4 No → Failed.
e = d.connect("build_ok", "left", "notify", "right", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "否 No")
d.connect("notify", "bottom", "m1", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("lint_ok", "left", "m1", "right", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "否 No")
d.connect("m1", "bottom", "m2", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("test_ok", "left", "m2", "right", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "否 No")
d.connect("m2", "bottom", "failed", "top", stroke=EDGE,
          stroke_width=1.8, marker_end="ah")

e = d.connect("smoke_ok", "left", "failed", "right", stroke=EDGE,
              stroke_width=1.8, marker_end="ah")
yes_no(e[0], e[1], "否 No")

# --- score + artifact triplet -------------------------------------------
svg = d.render()
score, rep = evaluate_svg(d)
print(f"Score: {score}")
for r in rep:
    print(f"  {r}")
sp = str(OUT / f"{NAME}.svg")
save_svg(svg, sp)
rasterize_svg(sp, str(OUT / f"{NAME}.png"), width=PNG_W)
try:
    svg_to_pptx(svg, str(OUT / f"{NAME}.pptx"),
                config=PptxConfig(slide_w=13.333, slide_h=7.5, scale=2.0))
except Exception as e:
    print(f"[pptx: {e}]")
print(f"\n✓ {NAME}.svg / .png / .pptx")
