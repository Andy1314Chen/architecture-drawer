# -*- coding: utf-8 -*-
"""MLIR AI Compiler · Multi-Stream Execution Pipeline (4-layer matrix diagram)."""
import sys, math, html
from pathlib import Path

import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg, BBox
from evaluator import evaluate_svg

# Script co-located with its SVG/PNG/PPTX in this dir (output/<ts>_<name>/).
NAME = "mlir_pipeline"
OUT = Path(__file__).resolve().parent

W, H = 1440, 1200
d = SVGDrawer(W, H, bg="#F7F7F7")
esc = html.escape

# ---- palette: exactly 8 accents (5 dark strokes + 3 light fills) ----
PURPLE = "#9673A6"; BLUE = "#2E5AAC"; ORANGE = "#B45F06"
GREEN = "#82B366"; YELLOW = "#D6B656"
ORANGE_F = "#FFCC99"; GREEN_F = "#D5E8D4"; BLUE_F = "#DAE8FC"
GRAY_S = "#888888"; GRAY_D = "#555555"; GRAY_L = "#BBBBBB"

def txt(x, y, s, sz=12, fill="#222222", anchor="middle", weight="normal"):
    d.add_element(
        f'<text x="{x}" y="{y}" font-family="Arial, sans-serif" font-size="{sz}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')

def rrect(x, y, w, h, fill, stroke, sw=1.5, rx=8, ry=8, extra="", role=None, bbox=False):
    ra = f' data-graph-role="{role}"' if role else ""
    d.add_element(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{ry}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{ra} {extra}/>',
        BBox(x, y, w, h) if bbox else None)

def _tw(s, fs, bold=False):
    # text width estimate, matching evaluator's metric (0.55 regular / 0.62 bold, CJK x1)
    coef = 0.62 if bold else 0.55
    return sum(fs * (1.0 if ord(c) > 0x2E80 else coef) for c in s)

def card(x, y, w, title, body, stroke, h=None, pad=12, body_fs=10, title_fs=12):
    """White legend card; body auto-wraps to fit width, height auto-grows."""
    inner = w - 2 * pad
    words = body.split(' ')
    lines, cur = [], ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if _tw(trial, body_fs) <= inner or not cur:
            cur = trial
        else:
            lines.append(cur); cur = wd
    if cur:
        lines.append(cur)
    title_h = title_fs + 8
    line_h = body_fs * 1.35
    total = pad + title_h + len(lines) * line_h + pad
    if h:
        total = max(total, h)
    rrect(x, y, w, total, "#FFFFFF", stroke, 1.4, 8, role="legend")
    txt(x + pad, y + pad + title_fs - 1, title, title_fs, stroke, "start", "bold")
    for i, ln in enumerate(lines):
        txt(x + pad, y + pad + title_h + i * line_h + body_fs - 1, ln, body_fs, GRAY_D, "start")
    return total

# ---- arrow markers (colors reused from the 8-accent set + neutral) ----
d.arrow_head("ah", GRAY_S, 10, 7, 9, 3.5)
d.arrow_head("ap", PURPLE)
d.arrow_head("ab", BLUE)
d.arrow_head("ao", ORANGE)
d.arrow_head("ag", GREEN)

# =================== TITLE ===================
txt(W / 2, 34, "MLIR AI Compiler · Multi-Stream Execution Pipeline", 20, "#1a1a1a", "middle", "bold")
txt(W / 2, 54, "Static Graph Optimization → Runtime Scheduling → Hardware Concurrency → Memory Reuse",
    12, GRAY_D, "middle")

# =================== BAND 1 : GRAPH OPTIMIZATION ===================
rrect(50, 64, 1340, 266, "#FCFCFC", PURPLE, 2, 12, role="background")
txt(72, 92, "Graph Optimization — Compile-time · Static DAG & Fusion", 14, PURPLE, "start", "bold")
txt(72, 110, "Operator fusion · algebraic reordering · parallel-branch detection", 12, GRAY_D, "start")

# fusion dashed box
rrect(76, 140, 482, 110, "none", PURPLE, 1.5, 8, extra='stroke-dasharray="7,4" ', role="decoration")
txt(86, 158, "Vertical Fusion · 3 Kernels → 1", 12, PURPLE, "start", "bold")

# DAG op nodes (white fill, colored stroke)
def opnode(nid, x, y, w, h, top, sub, stroke):
    d.rect(x, y, w, h, rx=6, ry=6, fill="#FFFFFF", stroke=stroke, stroke_width=1.6,
           node_id=nid, node_kind="op", bbox=True)
    txt(x + w / 2, y + 20, top, 12, "#222222", "middle", "bold")
    txt(x + w / 2, y + 36, sub, 10, GRAY_D, "middle")

opnode("opA", 96, 178, 100, 52, "A · Conv", "Conv2D", PURPLE)
opnode("opB", 246, 178, 100, 52, "B · BN", "BatchNorm", PURPLE)
opnode("opC", 396, 178, 100, 52, "C · ReLU", "ReLU", PURPLE)
opnode("opD", 612, 178, 100, 52, "D · Add", "elementwise", BLUE)
opnode("opPar", 558, 268, 130, 40, "Parallel Branch", "no data dep", BLUE)

# chain edges
d.connect("opA", "right", "opB", "left", stroke=PURPLE, stroke_width=1.6, marker_end="ap")
d.connect("opB", "right", "opC", "left", stroke=PURPLE, stroke_width=1.6, marker_end="ap")
d.connect("opC", "right", "opD", "left", stroke=GRAY_S, stroke_width=1.6, marker_end="ah")
# parallel branch feeds D's second input (dashed)
d.connect("opPar", "top", "opD", "bottom", stroke=BLUE, stroke_width=1.5, marker_end="ab",
          dashed=True)
txt(690, 262, "③ Stream Concurrency", 10, BLUE, "start", "bold")

# reorder swap indicator (decorative curved double-arrow above C-D)
d.add_element(
    f'<path d="M446,168 C500,140 612,140 662,168" fill="none" stroke="{PURPLE}" '
    f'stroke-width="1.4" stroke-dasharray="5,3" marker-end="url(#ap)" '
    f'data-graph-role="decoration"/>')
txt(530, 132, "② Reorder D↔C (commutativity)", 10, PURPLE, "middle", "bold")

# right annotation cards (legend)
h1 = card(870, 140, 250, "① Vertical Fusion",
     "Conv+BN+ReLU → 1 fused kernel; ↓ global mem R/W (cf. FlashAttention, Fused GEMV)", PURPLE)
h2 = card(1140, 140, 240, "② Reordering",
     "Algebraic simplification / commutativity → eliminate intermediate buffer storage", BLUE)
card(870, 140 + max(h1, h2) + 14, 510, "③ Parallel Branch Detection",
     "Data-independent branches tagged as stream-concurrency candidates → overlapped at runtime", GREEN)

# fused-kernel output badge (under the fusion box, away from the opPar→opD edge)
rrect(200, 258, 160, 42, ORANGE_F, ORANGE, 1.4, 6, role="legend")
txt(280, 277, "Fused Kernel K1", 12, ORANGE, "middle", "bold")
txt(280, 292, "Conv + BN + ReLU", 10, GRAY_D, "middle")
d.add_element(
    f'<line x1="290" y1="250" x2="290" y2="257" stroke="{ORANGE}" stroke-width="1.4" '
    f'marker-end="url(#ao)" data-graph-role="decoration"/>')
txt(298, 248, "fuses", 10, ORANGE, "start")

# =================== BAND 2 : RUNTIME SCHEDULING ===================
rrect(50, 340, 1340, 235, "#FCFCFC", BLUE, 2, 12, role="background")
txt(72, 368, "Runtime Scheduling — Async Launch · Priority · Load Balance", 14, BLUE, "start", "bold")
txt(72, 386, "Host launch / device-exec split · work stealing for dynamic shapes", 12, GRAY_D, "start")

# scheduler
d.rect(82, 408, 196, 116, rx=10, ry=10, fill=BLUE_F, stroke=BLUE, stroke_width=1.6,
       node_id="sched", node_kind="layer", bbox=True)
txt(180, 436, "Task Scheduler", 14, BLUE, "middle", "bold")
txt(180, 456, "Host (CPU)", 12, "#333333", "middle")
txt(180, 474, "Async Launch", 10, GRAY_D, "middle")
txt(180, 490, "dependency resolve", 10, GRAY_D, "middle")
txt(180, 506, "graph capture", 10, GRAY_D, "middle")

# streams
streams = [("s0", 420, "Stream 0 · Comm", "high priority", BLUE),
           ("s1", 478, "Stream 1 · Compute", "kernel queue", ORANGE),
           ("s2", 536, "Stream 2 · D2D Copy", "low priority", GREEN)]
for nid, y, lbl, sub, st in streams:
    fl = {BLUE: BLUE_F, ORANGE: ORANGE_F, GREEN: GREEN_F}[st]
    d.rect(360, y, 214, 42, rx=6, ry=6, fill=fl, stroke=st, stroke_width=1.5,
           node_id=nid, node_kind="op", bbox=True)
    txt(467, y + 18, lbl, 12, "#222222", "middle", "bold")
    txt(467, y + 33, sub, 10, GRAY_D, "middle")
    d.connect("sched", "right", nid, "left", stroke=BLUE, stroke_width=1.4, marker_end="ab")

# queued task chips (decorative)
chip_sets = [(420, ["T", "T", "T"], BLUE),
             (478, ["K1", "K2", "K3"], ORANGE),
             (536, ["cp", "cp", "cp"], GREEN)]
for y, labs, st in chip_sets:
    for i, lb in enumerate(labs):
        cx = 600 + i * 42
        rrect(cx, y + 9, 36, 24, "#FFFFFF", st, 1.1, 4, role="legend")
        txt(cx + 18, y + 25, lb, 10, st, "middle", "bold")

txt(745, 470, "device-side queues", 10, GRAY_D, "start")
d.add_element(
    f'<path d="M738,446 C770,446 770,500 738,500" fill="none" stroke="{GRAY_S}" '
    f'stroke-width="1.2" stroke-dasharray="4,3" data-graph-role="decoration"/>')

h1 = card(870, 398, 510, "Async Launch · Priority Preemption · Work Stealing",
     "Host enqueues kernels non-blocking; high-prio comm stream preempts; idle SMs steal tasks under dynamic shapes",
     BLUE)
card(870, 398 + h1 + 12, 510, "Back-pressure & Amortization",
     "Device queues throttle host when saturated; CUDA-graph capture amortizes per-kernel launch overhead", GRAY_S)

# =================== BAND 3 : HARDWARE CONCURRENCY ===================
rrect(50, 585, 1340, 340, "#FCFCFC", ORANGE, 2, 12, role="background")
txt(72, 613, "Hardware Concurrency — Multi-Stream Overlap · SM Partition", 14, ORANGE, "start", "bold")
txt(72, 631, "GPU SM array · timeline swimlanes · MPS / MIG spatial multiplexing", 12, GRAY_D, "start")

# GPU chip
rrect(70, 658, 214, 244, "#F2F2F2", GRAY_S, 1.4, 10, role="decoration", bbox=True)
txt(177, 681, "GPU · SM Array", 12, "#333333", "middle", "bold")
sm_x0, sm_y0, cell, sm = 88, 696, 42, 36
for r in range(4):
    for c in range(4):
        x, y = sm_x0 + c * cell, sm_y0 + r * cell
        if c < 2:
            fl, st = ORANGE_F, ORANGE
        elif c == 2:
            fl, st = GREEN_F, GREEN
        else:
            fl, st = BLUE_F, BLUE
        rrect(x, y, sm, sm, fl, st, 1, 2, role="decoration")
# MPS partition dividers (span the grid height)
for xx in [sm_x0 + 2 * cell - 4, sm_x0 + 3 * cell - 4]:
    d.add_element(
        f'<line x1="{xx}" y1="{sm_y0 - 4}" x2="{xx}" y2="{sm_y0 + 4 * cell - 4}" '
        f'stroke="{GRAY_D}" stroke-width="1" stroke-dasharray="3,2" data-graph-role="decoration"/>')
txt(128, 882, "compute", 10, ORANGE, "middle", "bold")
txt(191, 882, "copy", 10, GREEN, "middle", "bold")
txt(233, 882, "comm", 10, BLUE, "middle", "bold")
txt(177, 898, "MPS / MIG partition", 10, GRAY_D, "middle")

# time axis
AX0, AX1, AY = 320, 1370, 712
d.add_element(f'<line x1="{AX0}" y1="{AY}" x2="{AX1}" y2="{AY}" stroke="{GRAY_S}" stroke-width="1.4"/>')
for xx, lab in [(380, "T0"), (680, "T1"), (980, "T2"), (1280, "T3")]:
    d.add_element(f'<line x1="{xx}" y1="{AY-5}" x2="{xx}" y2="{AY+5}" stroke="{GRAY_S}" stroke-width="1.4"/>')
    txt(xx, AY + 19, lab, 10, GRAY_D, "middle")
txt(1342, AY - 6, "time →", 10, GRAY_S, "start")

# swimlanes
def lane_label(y, lbl, sub, st):
    txt(348, y + 16, lbl, 10, st, "end", "bold")
    txt(348, y + 30, sub, 10, GRAY_D, "end")

def bar(x, y, w, lbl, fl, st, big=False):
    rrect(x, y, w, 40, fl, st, 1.5, 5, role="decoration", bbox=True)
    txt(x + w / 2, y + 17, lbl, 12 if big else 10, "#222222", "middle", "bold")
    txt(x + w / 2, y + 31, "active" if big else "", 10, GRAY_D, "middle")

lane_label(732, "Compute", "(Tensor Core)", ORANGE)
bar(380, 736, 360, "Kernel A · MatMul", ORANGE_F, ORANGE, big=True)
bar(780, 736, 320, "Kernel B", ORANGE_F, ORANGE)
lane_label(786, "Copy D2D", "(layout xform)", GREEN)
bar(430, 790, 250, "NHWC→NCHW", GREEN_F, GREEN)
bar(820, 790, 230, "D2D copy", GREEN_F, GREEN)
lane_label(840, "Comm H2D", "(next batch)", BLUE)
bar(380, 844, 180, "H2D preload", BLUE_F, BLUE)
bar(720, 844, 220, "H2D preload", BLUE_F, BLUE)
bar(1080, 844, 220, "H2D preload", BLUE_F, BLUE)

# overlap region guides
for xx in [430, 680]:
    d.add_element(
        f'<line x1="{xx}" y1="730" x2="{xx}" y2="886" stroke="{ORANGE}" '
        f'stroke-width="1" stroke-dasharray="3,3" data-graph-role="decoration"/>')
txt(555, 902, "↕ fully concurrent · Multi-Stream Overlap", 10, ORANGE, "middle", "bold")

# =================== BAND 4 : MEMORY POOL ===================
rrect(50, 935, 1340, 235, "#FCFCFC", YELLOW, 2, 12, role="background")
txt(72, 963, "Memory Pool — Lifetime · In-place · Workspace Reuse", 14, YELLOW, "start", "bold")
txt(72, 981, "Ring buffer · producer→consumer L2 locality", 12, GRAY_D, "start")

# ring buffer
cx, cy, R = 188, 1062, 56
segs = [(0, 90, YELLOW), (90, 180, ORANGE), (180, 270, GREEN), (270, 360, BLUE)]
for a0, a1, st in segs:
    x1 = cx + R * math.cos(math.radians(a0)); y1 = cy + R * math.sin(math.radians(a0))
    x2 = cx + R * math.cos(math.radians(a1)); y2 = cy + R * math.sin(math.radians(a1))
    d.add_element(
        f'<path d="M{x1:.1f},{y1:.1f} A{R},{R} 0 0 1 {x2:.1f},{y2:.1f}" fill="none" '
        f'stroke="{st}" stroke-width="15" data-graph-role="decoration"/>')
txt(cx, cy - 2, "Memory Pool", 12, "#333333", "middle", "bold")
txt(cx, cy + 15, "Ring Buffer", 10, GRAY_D, "middle")
# rotation arrow
d.add_element(
    f'<path d="M{cx + R + 4},{cy - 14} A{R + 14},{R + 14} 0 0 1 {cx + R + 4},{cy + 14}" '
    f'fill="none" stroke="{GRAY_S}" stroke-width="1.4" marker-end="url(#ah)" '
    f'data-graph-role="decoration"/>')

h_i = card(330, 988, 330, "In-place Update",
     "Add / ReLU overwrite the input buffer → zero extra allocation", YELLOW)
h_w = card(690, 988, 330, "Workspace Reuse",
     "Operators share one scratch buffer → ↓ allocation overhead", ORANGE)
h_p = card(1050, 988, 330, "Producer→Consumer Locality",
     "Next kernel consumes output while still warm in L2 cache", GREEN)
ht = max(h_i, h_w, h_p)
# arrows ring -> cards (decorative)
for ex in [330, 690, 1050]:
    d.add_element(
        f'<line x1="{cx + R}" y1="{cy}" x2="{ex}" y2="1018" stroke="{GRAY_L}" '
        f'stroke-width="1" stroke-dasharray="3,3" data-graph-role="decoration"/>')
card(330, 988 + ht + 12, 1050, "Buffer Lifetime Timeline",
     "t0 alloc K1 → t1 in-place ReLU → t2 workspace reused by K2 → t3 free   (ring arcs = ownership)", GRAY_S)

# =================== LEFT PIPELINE SPINE (drawn LAST → sits above bands, never occluded) ===================
SPX = 26
d.add_element(
    f'<line x1="{SPX}" y1="80" x2="{SPX}" y2="1156" stroke="{GRAY_L}" stroke-width="2" '
    f'stroke-dasharray="4,4" data-graph-role="decoration"/>')
for num, yy in [("1", 165), ("2", 457), ("3", 755), ("4", 1052)]:
    d.add_element(
        f'<circle cx="{SPX}" cy="{yy}" r="13" fill="#FFFFFF" stroke="{GRAY_S}" '
        f'stroke-width="1.5" data-graph-role="decoration"/>')
    txt(SPX, yy + 4, num, 12, GRAY_D, "middle", "bold")
# verbs sit inside the band gutters (330-340 / 575-585 / 925-935) so they clear every band
for yy, vb in [(330, "lowers"), (575, "dispatches"), (925, "reclaims")]:
    d.add_element(
        f'<polygon points="{SPX-5},{yy} {SPX+5},{yy} {SPX},{yy+9}" fill="{GRAY_S}" '
        f'data-graph-role="decoration"/>')
    txt(SPX + 16, yy + 7, vb, 10, GRAY_S, "start")

# =================== EVALUATE & SAVE ===================
score, report = evaluate_svg(d, conn_tolerance=12.0)
print(f"Score: {score}")
for line in report:
    print(line)
svg_path = OUT / f"{NAME}.svg"
png_path = OUT / f"{NAME}.png"
pptx_path = OUT / f"{NAME}.pptx"
save_svg(d.render(), str(svg_path))
rasterize_svg(svg_path, png_path, W)
from svg2pptx import svg_to_pptx
svg_to_pptx(str(svg_path), str(pptx_path))
print(f"Saved triplet -> {OUT}")
