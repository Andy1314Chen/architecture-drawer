# -*- coding: utf-8 -*-
"""Pansharpening CS/MRA unified math abstraction, execution pipeline,
implementation framework and system-level co-optimization architecture.

Revision:
  - compressed left-column height (~18% shorter)
  - removed 4 redundant per-layer footer captions + duplicate subtitle lines
  - merged CS/MRA box desc lines into titles; consolidated L5 bottom note
"""
import sys
from pathlib import Path


import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg
from evaluator import evaluate_svg
from svg2pptx import svg_to_pptx, PptxConfig

OUT = Path(__file__).resolve().parent
NAME = "pansharpening_cs_mra"

# ---- palette ---------------------------------------------------------------
BLUE_S = "#1B3A5C"   # unified structural stroke (dark)
CS_S, CS_F = "#E8833A", "#FCEBD6"   # CS instance (orange)
MRA_S, MRA_F = "#2EA69A", "#D7EDE9"  # MRA instance (teal)
L1_F = "#E8E6F4"   # indigo  — math abstraction
L2_F = "#DCEAF7"   # sky     — injection pipeline
L3_F = "#DCF0E3"   # green   — implementation framework
L4_F = "#EFE2F2"   # violet  — system optimization
L5_F = "#F8E5EC"   # rose    — evaluation
BLACK = "#222222"   # text (neutral)
GRAY = "#555555"   # arrows (neutral)
MUTED = "#555555"   # secondary text (neutral)
MONO = "Consolas, 'Courier New', monospace"

# font tiers — compressed modular scale (each step >= 1.15x, range 1.57x)
T, H, B, N = 17, 14.5, 12.5, 10.8

W, Hh = 1640, 1032
d = SVGDrawer(W, Hh, bg="#FFFFFF")
d.arrow_head("ah", GRAY)
d.arrow_head("ah_thick", GRAY, marker_width=13, marker_height=9, ref_x=11)

MX0, MX1 = 30, 1160          # main column x-range
MCX = (MX0 + MX1) / 2        # main column center (595)
L5X = 1230                   # right column x
L5W = 380                    # right column width

# ---- layer y-coordinates (compressed, 24px gaps for arrows) ----------------
L1y, L1h = 78, 330           # end 408
L2y, L2h = 432, 140          # end 572
L3y, L3h = 596, 190          # end 786
L4y, L4h = 810, 178          # end 988
L5y = L1y                    # 78
L5h = L4y + L4h - L1y        # 910


def frame(x, y, w, h, fill, stroke=BLUE_S, sw=1.4, track=False, dashed=False):
    extra = ' stroke-dasharray="7,4"' if dashed else ""
    d.rect(x, y, w, h, rx=10, ry=10, fill=fill, stroke=stroke,
           stroke_width=sw, bbox=track, role="background", extra=extra)


def card(x, y, w, h, fill="#FFFFFF", stroke=BLUE_S, sw=1.3, dashed=False, extra=""):
    ex = extra
    if dashed:
        ex = (ex + ' stroke-dasharray="7,4"').strip()
    d.rect(x, y, w, h, rx=6, ry=6, fill=fill, stroke=stroke,
           stroke_width=sw, bbox=False, extra=ex)


def tx(x, y, s, size=B, fill=BLACK, anchor="middle", weight="normal", family="Arial, sans-serif"):
    d.text(x, y, s, size, font_family=family, fill=fill, anchor=anchor,
           weight=weight, bbox=False)


def arrow(x1, y1, x2, y2, marker="ah", sw=1.6, color=GRAY, dashed=False):
    extra = 'stroke-dasharray="6,4"' if dashed else ""
    d.line(x1, y1, x2, y2, stroke=color, stroke_width=sw,
           marker_end=marker, extra=extra, bbox=False)


def badge(x, y, label):
    d.rect(x, y, 30, 19, rx=4, ry=4, fill="#FFFFFF", stroke=BLUE_S, stroke_width=1.4,
           bbox=False, role="background")
    d.text(x + 15, y + 10, label, B, fill=BLACK, weight="bold", bbox=False)


# =====================================================================
# Title
# =====================================================================
d.text(W / 2, 34,
       "Pansharpening CS / MRA Unified Math Abstraction · Execution Framework · System Optimization",
       T, fill=BLACK, weight="bold")
d.text(W / 2, 58,
       "CS and MRA share one source — two parameterized instances of the same injection model",
       B, fill=MUTED)

# =====================================================================
# L1 — unified math abstraction
# =====================================================================
frame(MX0, L1y, 1130, L1h, L1_F, track=True)
badge(MX0 + 15, L1y + 13, "L1")
tx(MX0 + 58, L1y + 22,
   "Pansharpening Unified Math Abstraction (CS / MRA Same-Source Framework)",
   H, weight="bold", anchor="start")

# three sub-modules (row 1)
sub_w, sub_h = 340, 62
sub_y = L1y + 38
subs = [
    (MX0 + 25, "Multi-Source Alignment", "PAN / MS registration & preprocessing"),
    (MX0 + 395, "Common Injection Skeleton", "Unified detail injection: F = MS\u2191 + G\u00b7D"),
    (MX0 + 765, "Parameterized Operator Set", "Gain calc \u00b7 coef estimation \u00b7 resampling"),
]
for sx, title, sub in subs:
    card(sx, sub_y, sub_w, sub_h)
    tx(sx + sub_w / 2, sub_y + 24, title, B, weight="bold")
    tx(sx + sub_w / 2, sub_y + 46, sub, N, fill=MUTED)

# highlighted unified-equation card (row 2)
fc_x, fc_y, fc_w, fc_h = MX0 + 165, L1y + 114, 800, 92
card(fc_x, fc_y, fc_w, fc_h, fill="#FFFFFF", stroke=BLUE_S, sw=2.0)
tx(fc_x + fc_w / 2, fc_y + 18, "\u25c6  Unified Injection Equation", B,
   weight="bold", fill=BLACK)
tx(fc_x + fc_w / 2, fc_y + 44, "D  =  P \u2212 \u00ce", H, family=MONO, weight="bold")
d.formula(fc_x + fc_w / 2, fc_y + 70, "F_{k}  =  MS\u2191_{k}  +  g_{k} \u00b7 D", H)

# equation legend (right of card)
lg_x = fc_x + fc_w + 14
tx(lg_x, fc_y + 14, "Symbols", N, weight="bold", fill=BLACK, anchor="start")
for j, ln in enumerate(["P   = PAN (panchromatic)", "MS\u2191 = upsampled MS",
                        "\u00ce = intensity/approx.", "g_{k} = injection gain",
                        "D   = spatial detail"]):
    d.formula(lg_x, fc_y + 32 + j * 14, ln, N, fill=MUTED, anchor="start", weight="normal")

# CS / MRA instance boxes with per-instance formulas (row 3)
ib_y, ib_h = L1y + 220, 100
ib_w = 535
cs_x, mra_x = MX0 + 25, MX0 + 595
card(cs_x, ib_y, ib_w, ib_h, fill=CS_F, stroke=CS_S, sw=1.6, dashed=True)
card(mra_x, ib_y, ib_w, ib_h, fill=MRA_F, stroke=MRA_S, sw=1.6, dashed=True)

tx(cs_x + 16, ib_y + 18, "CS Subset \u2014 IHS \u00b7 PCA \u00b7 GS",
   B, fill=CS_S, weight="bold", anchor="start")
d.formula(cs_x + 16, ib_y + 44, "\u00ce = \u03a3 w_{k} \u00b7 MS_{k}   (e.g. IHS)", B, fill=BLACK, anchor="start")
d.formula(cs_x + 16, ib_y + 66, "g_{k} = Cov(P, \u00ce) / Var(\u00ce)", B, fill=CS_S, anchor="start")
d.formula(cs_x + 16, ib_y + 88, "Î = Φ(MS)", N, fill=MUTED, anchor="start", weight="normal")

tx(mra_x + 16, ib_y + 18, "MRA Subset \u2014 HPF \u00b7 Wavelet \u00b7 ATW",
   B, fill=MRA_S, weight="bold", anchor="start")
tx(mra_x + 16, ib_y + 44, "\u00ce = H \u2217 P   (low-pass approx.)", B, family=MONO, fill=BLACK, anchor="start")
tx(mra_x + 16, ib_y + 66, "D = P \u2212 H \u2217 P   (high-freq detail)", B, family=MONO, fill=BLACK, anchor="start")
d.formula(mra_x + 16, ib_y + 88, "g_{k} from multiresolution coefs", N, fill=MRA_S, anchor="start", weight="normal")

# =====================================================================
# L2 — unified injection pipeline
# =====================================================================
frame(MX0, L2y, 1130, L2h, L2_F, track=True)
badge(MX0 + 15, L2y + 13, "L2")
tx(MX0 + 58, L2y + 22, "Unified Injection Pipeline", H, weight="bold", anchor="start")

nw, nh = 160, 80
ny = L2y + 40
nx = [62, 290, 518, 746, 974]
node_lbl = [
    ("Upsample", "upsample MS \u2192 PAN scale"),
    ("Produce \u00ce", "extract \u00ce component"),
    ("Produce Gain", "compute injection gain \u26a1"),
    ("Inject", "F_{k} = MS\u2191_{k} + g_{k}\u00b7D"),
    ("Clip", "clip & radiometric"),
]
for i, _ in enumerate(nx):
    x0 = nx[i]
    title, sub = node_lbl[i]
    if i == 2:  # divergence node
        d.rect(x0, ny, nw, nh, rx=6, ry=6, fill="#FFFFFF", stroke=BLUE_S,
               stroke_width=1.6, bbox=False, node_id="n3", node_kind="op")
        tx(x0 + nw / 2, ny + 22, title, B, weight="bold")
        tx(x0 + nw / 2, ny + 40, sub, N, fill=MUTED)
        d.rect(x0 + 6, ny + nh - 26, 70, 20, rx=4, ry=4, fill=CS_F, stroke=CS_S,
               stroke_width=1.2, bbox=False)
        d.rect(x0 + nw - 76, ny + nh - 26, 70, 20, rx=4, ry=4, fill=MRA_F, stroke=MRA_S,
               stroke_width=1.2, bbox=False)
        tx(x0 + 41, ny + nh - 16, "CS\u00b7stat", N, fill=CS_S, weight="bold")
        tx(x0 + nw - 41, ny + nh - 16, "MRA\u00b7filt", N, fill=MRA_S, weight="bold")
    else:
        d.rect(x0, ny, nw, nh, rx=6, ry=6, fill="#FFFFFF", stroke=BLUE_S,
               stroke_width=1.4, bbox=False, node_id=f"n{i+1}", node_kind="op")
        tx(x0 + nw / 2, ny + 30, title, B, weight="bold")
        if '_{' in sub or '^{' in sub:
            d.formula(x0 + nw / 2, ny + 56, sub, N, fill=MUTED, weight="normal")
        else:
            tx(x0 + nw / 2, ny + 54, sub, N, fill=MUTED)

for i in range(4):
    d.connect(f"n{i+1}", "right", f"n{i+2}", "left",
              stroke=GRAY, stroke_width=1.7, marker_end="ah")

# =====================================================================
# L3 — unified implementation framework (2x2 grid)
# =====================================================================
frame(MX0, L3y, 1130, L3h, L3_F, track=True)
badge(MX0 + 15, L3y + 13, "L3")
tx(MX0 + 58, L3y + 22, "Unified Implementation Framework", H, weight="bold", anchor="start")

g_w, g_h = 520, 64
cells = [
    (MX0 + 25, L3y + 44, "Unified API", "Unified API for CS / MRA"),
    (MX0 + 605, L3y + 44, "Compute-Graph Scheduling", "dynamic / static graph orchestration"),
    (MX0 + 25, L3y + 118, "Multi-Backend Dispatch", "CPU \u00b7 GPU \u00b7 NPU heterogeneous"),
    (MX0 + 605, L3y + 118, "Shared Operator Library", "resample \u00b7 filter \u00b7 stats \u00b7 clip kernels"),
]
for cx, cy_, title, sub in cells:
    card(cx, cy_, g_w, g_h)
    tx(cx + g_w / 2, cy_ + 24, title, B, weight="bold")
    tx(cx + g_w / 2, cy_ + 46, sub, N, fill=MUTED)

# =====================================================================
# L4 — unified system-level co-optimization (3 blocks)
# =====================================================================
frame(MX0, L4y, 1130, L4h, L4_F, track=True)
badge(MX0 + 15, L4y + 13, "L4")
tx(MX0 + 58, L4y + 22, "Unified System-Level Co-Optimization", H, weight="bold", anchor="start")

bw, bh = 345, 124
by = L4y + 42
bx = [MX0 + 25, MX0 + 395, MX0 + 765]
blocks = [
    ("Graph-Level Optimization", ["Operator fusion", "Parallel pipeline orchestration", "Redundant computation removal"]),
    ("Operator-Level Optimization", ["Filter / stats kernel ISA accel.", "Register reuse", "Vectorization / SIMD"]),
    ("Memory / Data-Path Optimization", ["Tiled memory access (large RS images)", "Data layout reordering", "On-chip cache adaptation"]),
]
for i, (title, lines) in enumerate(blocks):
    x0 = bx[i]
    card(x0, by, bw, bh)
    tx(x0 + bw / 2, by + 24, title, B, weight="bold")
    for j, ln in enumerate(lines):
        tx(x0 + bw / 2, by + 52 + j * 22, "\u00b7 " + ln, N, fill=MUTED)

# =====================================================================
# inter-layer down arrows (short labels, no footer captions)
# =====================================================================
arrow(MCX, L1y + L1h, MCX, L2y - 2)               # L1 -> L2
tx(MCX + 17, L1y + L1h + 16, "instantiate config", N, fill=GRAY, anchor="start")
arrow(MCX, L2y + L2h, MCX, L3y - 2)               # L2 -> L3
tx(MCX + 17, L2y + L2h + 13, "submit sequence", N, fill=GRAY, anchor="start")
arrow(MCX, L3y + L3h, MCX, L4y - 2)               # L3 -> L4
tx(MCX + 17, L3y + L3h + 13, "call backend", N, fill=GRAY, anchor="start")

# =====================================================================
# feedback channel (L4 -> L3 -> L2) on the far-left margin
# =====================================================================
arrow(MX0 - 12, L4y + 90, MX0 - 12, L3y + 95, dashed=True)   # taps L3
arrow(MX0 - 12, L3y + 95, MX0 - 12, L2y + 70, dashed=True)    # taps L2
tx(50, L2y + L2h + 13,
   "Runtime tuning (tile size \u00b7 kernel selection)", N, fill=GRAY, anchor="start")

# =====================================================================
# L5 — output & edge evaluation (full-height right column)
# =====================================================================
frame(L5X, L5y, L5W, L5h, L5_F, track=False)
badge(L5X + 15, L5y + 13, "L5")
tx(L5X + 58, L5y + 22, "Output & Edge Evaluation", H, weight="bold", anchor="start")

eb_w = 350
eb_x = L5X + 15
evals = [
    (L5y + 56, "\u2460 Fusion Quality Metrics",
     ["QNR \u00b7 D_{\u03bb} \u00b7 D_{S}", "SAM \u00b7 ERGAS \u00b7 CC", "(full-ref / no-ref)"]),
    (L5y + 340, "\u2461 Downstream Task Performance",
     ["Classification \u00b7 change detection", "Object recognition (acc / IoU)"]),
    (L5y + 600, "\u2462 Edge Deployment Metrics",
     ["Inference latency \u00b7 memory", "Power / energy efficiency"]),
]
for ey, title, lines in evals:
    eh = 64 + len(lines) * 22
    card(eb_x, ey, eb_w, eh)
    tx(eb_x + eb_w / 2, ey + 22, title, B, weight="bold")
    for j, ln in enumerate(lines):
        if '_{' in ln or '^{' in ln:
            d.formula(eb_x + eb_w / 2, ey + 50 + j * 22, ln, N, fill=MUTED, weight="normal")
        else:
            tx(eb_x + eb_w / 2, ey + 48 + j * 22, ln, N, fill=MUTED)

# single consolidated closing note
tx(L5X + L5W / 2, L5y + L5h - 26,
   "Results feed back to params & optimization \u2192 closed loop", N, fill=MUTED)

# =====================================================================
# output arrow L2(Clip) -> L5  (thick)  +  L5 -> L1 feedback (dashed)
# =====================================================================
arrow(nx[4] + nw, ny + nh / 2, L5X - 4, ny + nh / 2, marker="ah_thick", sw=3.0)
tx((nx[4] + nw + L5X) / 2, ny + nh / 2 - 12, "fused image", N, fill=GRAY, weight="bold")

fb_y = L1y + 130
arrow(L5X - 2, fb_y, MX1 + 2, fb_y, dashed=True)
tx((MX1 + L5X) / 2, fb_y - 14, "closed loop", N, fill=GRAY, anchor="middle")

# =====================================================================
# footer color key
# =====================================================================
fy = 1012
d.rect(MX0, fy - 7, 14, 11, rx=2, ry=2, fill=CS_F, stroke=CS_S, stroke_width=1.3,
       bbox=False, role="legend")
tx(MX0 + 22, fy, "CS \u00b7 statistics / substitution", N, fill=BLACK, anchor="start")
d.rect(MX0 + 270, fy - 7, 14, 11, rx=2, ry=2, fill=MRA_F, stroke=MRA_S, stroke_width=1.3,
       bbox=False, role="legend")
tx(MX0 + 292, fy, "MRA \u00b7 filtering / multiresolution", N, fill=BLACK, anchor="start")
d.line(MX0 + 600, fy, MX0 + 622, fy, stroke=GRAY, stroke_width=1.6,
       extra='stroke-dasharray="6,4"', bbox=False, role="legend")
tx(MX0 + 630, fy, "runtime tuning feedback", N, fill=BLACK, anchor="start")

# =====================================================================
# evaluate + render
# =====================================================================
score, report = evaluate_svg(d)
print(f"Quality Score: {score}")
for line in report:
    print(line)

save_svg(d.render(), str(OUT / f"{NAME}.svg"))
rasterize_svg(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.png"), width=W)
svg_to_pptx(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.pptx"),
            config=PptxConfig(slide_w=13.333, slide_h=8.4, scale=1.0))
print("Done.")
