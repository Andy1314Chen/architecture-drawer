"""LLM Distributed Inference Serving — 7-layer architecture diagram.

Layout: vertical layered stack. A neutral downward "spine" connects the client
(top) through seven architecture bands to the streaming output (bottom).
Internal edges show intra-layer flows (scheduler<->KV index, prefill->decode,
prefill cluster<->RDMA<->decode cluster).

Palette is held to exactly 8 accent colors (4 light fills + 4 dark strokes),
grouped by architectural function:
  blue   = control plane  (L1 Gateway, L2 Scheduler)
  teal   = compute        (L3 Inference Engine, L4 Parallelism)
  amber  = infra          (L5 Storage & Interconnect)
  purple = optimization   (L6 Hidden Optimizers, L7 Disaggregated)
Op cards are neutral white + gray stroke so they never inflate the palette.
Type scale is fixed at 4 tiers: 20 / 14 / 12 / 10.
"""

import sys
from pathlib import Path


import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg
from svg2pptx import svg_to_pptx
from evaluator import evaluate_svg, auto_refine

OUT = Path(__file__).resolve().parent
NAME = "llm_inference_arch"

# ---- palette --------------------------------------------------------------
BLUE_F, BLUE_S = "#DAE8FC", "#2E5AAC"
TEAL_F, TEAL_S = "#B2E2E2", "#2E8B8B"
AMBER_F, AMBER_S = "#FFE6CC", "#D79B00"
PURP_F, PURP_S = "#E1D5E7", "#9673A6"
CARD_F, CARD_S = "#FFFFFF", "#5A5A5A"   # neutral — not counted as accents
INK, SUB = "#222222", "#444444"          # neutral text
EDGE = "#6B6B6B"                          # neutral edges/arrows

W, H = 1400, 1400
CX = W // 2
BAND_X, BAND_W = 40, 1320

drawer = SVGDrawer(W, H, bg="#FFFFFF")
drawer.arrow_head("ah", EDGE, marker_width=10, marker_height=7, ref_x=9, ref_y=3.5)

# ---- band metadata: (num, name, fill, stroke, y, h) ----------------------
BANDS = [
    (1, "\u2460 \u63a5\u5165\u4e0e\u7f51\u5173\u5c42  Gateway Governance",            BLUE_F, BLUE_S, 138, 96),
    (2, "\u2461 \u5168\u5c40\u8c03\u5ea6\u4e0e\u8def\u7531  Scheduler & Routing",     BLUE_F, BLUE_S, 256, 120),
    (3, "\u2462 \u5206\u5e03\u5f0f\u63a8\u7406\u5f15\u64ce  Inference Engine",         TEAL_F, TEAL_S, 400, 210),
    (4, "\u2463 \u6a21\u578b\u5e76\u884c\u4e0e\u52a0\u901f  Model Parallelism",        TEAL_F, TEAL_S, 634, 150),
    (5, "\u2464 \u5f02\u6784\u5b58\u50a8\u4e0e\u901a\u4fe1  Storage & Interconnect",   AMBER_F, AMBER_S, 808, 160),
    (6, "\u2465 \u9690\u6027\u4f18\u5316\u7ec4\u4ef6  Hidden Optimizers",             PURP_F, PURP_S, 992, 130),
    (7, "\u2466 \u5206\u79bb\u5f0f\u90e8\u7f72  Disaggregated Serving",               PURP_F, PURP_S, 1146, 150),
]


def band_rect(n, fill, stroke, y, h):
    """Draw + register a layer band as a connectable layer node."""
    drawer.rect(BAND_X, y, BAND_W, h, rx=8, ry=8, fill=fill, stroke=stroke,
                stroke_width=1.5, node_id=f"band{n}", node_kind="layer",
                role="layer", bbox=False)


def badge(n, stroke, y):
    """Light layer-number badge (decoration, not a node)."""
    drawer.rect(55, y + 13, 42, 26, rx=5, ry=5, fill="#FFFFFF", stroke=stroke,
                stroke_width=1.5, role="decoration", bbox=False)
    drawer.text(76, y + 26, f"L{n}", 12, fill=INK, weight="bold", bbox=False)


def band_name(name, y):
    drawer.text(108, y + 27, name, 14, fill=INK, weight="bold",
                anchor="start", bbox=False)


def card(x, y, w, h, nid, title, desc, title_size=12, desc_size=10):
    """Neutral op card: rect node + two text lines (title / desc)."""
    drawer.rect(x, y, w, h, rx=6, ry=6, fill=CARD_F, stroke=CARD_S,
                stroke_width=1.2, node_id=nid, node_kind="op", role="node",
                bbox=True)
    cx = x + w / 2
    cy = y + h / 2
    drawer.text(cx, cy - 8, title, title_size, fill=INK, weight="bold", bbox=False)
    drawer.text(cx, cy + 9, desc, desc_size, fill=SUB, bbox=False)


# ---- title ----------------------------------------------------------------
drawer.text(CX, 32, "\u5927\u6a21\u578b\u5206\u5e03\u5f0f\u63a8\u7406\u670d\u52a1\u67b6\u6784  LLM Distributed Inference Serving",
            20, fill=INK, weight="bold", bbox=False)

# ---- client ---------------------------------------------------------------
drawer.rect(560, 70, 280, 46, rx=8, ry=8, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.4, node_id="client", node_kind="op", role="node",
            bbox=True)
drawer.text(CX, 84, "\u5ba2\u6237\u7aef Client", 12, fill=INK, weight="bold", bbox=False)
drawer.text(CX, 100, "HTTP / gRPC \u00b7 Prompt + \u91c7\u6837\u53c2\u6570", 10, fill=SUB, bbox=False)

# ---- bands (containers + headers) ----------------------------------------
for n, name, fill, stroke, y, h in BANDS:
    band_rect(n, fill, stroke, y, h)
    badge(n, stroke, y)
    band_name(name, y)

# ===== L1 Gateway: 4 cards ================================================
l1y = 164
for i, (nid, t, d) in enumerate([
    ("gw1", "\u8d1f\u8f7d\u5747\u8861", "Load Balancer"),
    ("gw2", "\u8ba4\u8bc1\u9274\u6743", "AuthN & AuthZ"),
    ("gw3", "\u6d41\u91cf\u63a7\u5236", "Rate Limit"),
    ("gw4", "Prompt \u8fc7\u6ee4", "Prompt Filter"),
]):
    card(415 + i * 215, l1y, 180, 44, nid, t, d)

# ===== L2 Scheduler: resource view | scheduler | KV index =================
drawer.rect(80, 294, 260, 58, rx=6, ry=6, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.2, node_id="resv", node_kind="op", role="node", bbox=True)
drawer.text(210, 314, "\u96c6\u7fa4\u8d44\u6e90\u89c6\u56fe", 12, fill=INK, weight="bold", bbox=False)
drawer.text(210, 332, "GPU \u663e\u5b58 / \u5229\u7528\u7387 / \u5065\u5eb7", 10, fill=SUB, bbox=False)

drawer.rect(420, 294, 340, 58, rx=6, ry=6, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.4, node_id="sched", node_kind="op", role="node", bbox=True)
drawer.text(590, 314, "\u5168\u5c40\u8c03\u5ea6\u5668 Scheduler", 12, fill=INK, weight="bold", bbox=False)
drawer.text(590, 332, "Prefix Cache \u67e5\u627e \u00b7 \u8d1f\u8f7d\u5747\u8861", 10, fill=SUB, bbox=False)

drawer.database(840, 294, 260, 58, fill=BLUE_F, stroke=BLUE_S, stroke_width=1.4,
                node_id="kvid", node_kind="op", role="node", bbox=True)
drawer.text(970, 314, "KV \u7f13\u5b58\u7d22\u5f15", 12, fill=INK, weight="bold", bbox=False)
drawer.text(970, 332, "KV Cache Index", 10, fill=SUB, bbox=False)

drawer.connect("resv", "right", "sched", "left", stroke=EDGE, stroke_width=1.5, marker_end="ah")
drawer.connect("sched", "right", "kvid", "left", stroke=EDGE, stroke_width=1.5,
               marker_end="ah", dashed=True)
drawer.text(800, 310, "Prefix \u547d\u4e2d", 10, fill=SUB, bbox=False)

# ===== L3 Inference Engine: prefill box -> decode box =====================
drawer.rect(70, 444, 590, 140, rx=8, ry=8, fill="#FFFFFF", stroke=TEAL_S,
            stroke_width=1.6, node_id="prefill_box", node_kind="layer",
            role="layer", bbox=True)
drawer.text(365, 466, "Prefill Worker\uff08\u8ba1\u7b97\u5bc6\u96c6\uff09", 12, fill=INK, weight="bold", bbox=False)
for i, (nid, t) in enumerate([
    ("pf1", "Sequence \u5207\u5206"),
    ("pf2", "Attention \u5e76\u884c"),
    ("pf3", "KV \u538b\u7f29\u5199\u5165"),
]):
    x = 96 + i * 176
    drawer.rect(x, 498, 156, 34, rx=5, ry=5, fill=TEAL_F, stroke=TEAL_S,
                stroke_width=1.1, node_id=nid, node_kind="op", role="node", bbox=True)
    drawer.text(x + 78, 515, t, 12, fill=INK, bbox=False)

drawer.rect(720, 444, 590, 140, rx=8, ry=8, fill="#FFFFFF", stroke=TEAL_S,
            stroke_width=1.6, node_id="decode_box", node_kind="layer",
            role="layer", bbox=True)
drawer.text(1015, 466, "Decode Worker\uff08\u8bbf\u5b58\u5bc6\u96c6\uff09", 12, fill=INK, weight="bold", bbox=False)
for i, (nid, t) in enumerate([
    ("dc1", "Continuous Batch"),
    ("dc2", "\u52a8\u6001\u63d2\u5165/\u8e22\u51fa"),
    ("dc3", "\u9010 Token \u751f\u6210"),
]):
    x = 746 + i * 176
    drawer.rect(x, 498, 156, 34, rx=5, ry=5, fill=TEAL_F, stroke=TEAL_S,
                stroke_width=1.1, node_id=nid, node_kind="op", role="node", bbox=True)
    drawer.text(x + 78, 515, t, 12, fill=INK, bbox=False)

drawer.connect("prefill_box", "right", "decode_box", "left", stroke=EDGE,
               stroke_width=1.6, marker_end="ah")
drawer.text(690, 500, "KV Cache \u8f6c\u79fb", 10, fill=SUB, bbox=False)
drawer.text(690, 528, "Continuous Batching", 10, fill=SUB, bbox=False)

# ===== L4 Parallelism: TP | PP | SP =======================================
for i, (nid, t, d) in enumerate([
    ("tp", "\u5f20\u91cf\u5e76\u884c TP", "QKV \u77e9\u9635\u5217\u5207\u5206 \u00b7 All-Reduce"),
    ("pp", "\u6d41\u6c34\u7ebf\u5e76\u884c PP", "\u6309\u5c42\u5207\u5206 \u00b7 Send / Recv"),
    ("sp", "\u5e8f\u5217\u5e76\u884c SP", "\u957f\u5e8f\u5217\u5207\u5206 \u00b7 \u5408\u5e76"),
]):
    card(90 + i * 420, 680, 380, 80, nid, t, d)

# ===== L5 Storage & Interconnect ==========================================
drawer.rect(70, 858, 360, 98, rx=8, ry=8, fill=AMBER_F, stroke=AMBER_S,
            stroke_width=1.4, role="layer", bbox=False)
drawer.text(250, 876, "\u5b58\u50a8\u5c42\u7ea7 Storage", 12, fill=INK, weight="bold", bbox=False)
for i, line in enumerate([
    "HBM \u663e\u5b58\uff1a\u6743\u91cd + \u6d3b\u8dc3 KV Cache",
    "CPU DRAM\uff1a\u5206\u7247\u6682\u5b58 / KV \u6362\u51fa",
    "\u5206\u5e03\u5f0f\u5b58\u50a8\uff1a\u6a21\u578b\u68c0\u67e5\u70b9",
]):
    drawer.text(250, 898 + i * 18, line, 10, fill=SUB, bbox=False)

drawer.rect(500, 860, 300, 34, rx=5, ry=5, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.2, node_id="nvlink", node_kind="op", role="node", bbox=True)
drawer.text(650, 877, "NVLink \u8282\u70b9\u5185\uff08TP All-Reduce\uff09", 10, fill=INK, bbox=False)
drawer.rect(500, 912, 300, 34, rx=5, ry=5, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.2, node_id="ib", node_kind="op", role="node", bbox=True)
drawer.text(650, 929, "InfiniBand/RoCE \u8de8\u8282\u70b9\uff08PP/RDMA\uff09", 10, fill=INK, bbox=False)

drawer.rect(880, 858, 400, 98, rx=8, ry=8, fill=AMBER_F, stroke=AMBER_S,
            stroke_width=1.4, role="layer", bbox=False)
drawer.text(1080, 876, "GPU \u8282\u70b9\u96c6\u7fa4\uff088\u00d7A100/H100\uff09", 12, fill=INK, weight="bold", bbox=False)
for i in range(4):
    gx = 910 + i * 90
    drawer.rect(gx, 898, 70, 30, rx=4, ry=4, fill="#FFFFFF", stroke="#999999",
                stroke_width=1.0, role="decoration", bbox=False)
    drawer.text(gx + 35, 913, f"GPU{i}", 10, fill=SUB, bbox=False)

# ===== L6 Hidden Optimizers ===============================================
card(90, 1044, 580, 56, "opt1",
     "\u901a\u4fe1\u5ef6\u8fdf\u9690\u85cf Compute-Comm Overlap",
     "\u8ba1\u7b97/\u901a\u4fe1\u5f02\u6b65\u91cd\u53e0\uff0c\u63a9\u76d6\u8de8\u5361\u540c\u6b65\u5ef6\u8fdf")
card(710, 1044, 580, 56, "opt2",
     "\u52a8\u6001\u663e\u5b58\u5206\u914d KV Cache Swap",
     "\u663e\u5b58\u7d27\u5f20\u65f6\u6362\u51fa\u51b7 KV \u81f3 CPU\uff0c\u6309\u9700\u6362\u56de")

# ===== L7 Disaggregated Serving ===========================================
drawer.rect(90, 1200, 360, 68, rx=6, ry=6, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.2, node_id="pre_cluster", node_kind="op", role="node", bbox=True)
drawer.text(270, 1222, "Prefill \u96c6\u7fa4", 12, fill=INK, weight="bold", bbox=False)
drawer.text(270, 1240, "\u957f\u4e0a\u4e0b\u6587 \u00b7 \u8ba1\u7b97\u9971\u548c", 10, fill=SUB, bbox=False)

drawer.hexagon(560, 1218, 240, 34, fill=PURP_F, stroke=PURP_S, stroke_width=1.3,
               node_id="rdma", node_kind="op", role="node", bbox=True)
drawer.text(680, 1235, "RDMA \u9ad8\u901f\u7f51\u7edc", 10, fill=INK, bbox=False)

drawer.rect(910, 1200, 360, 68, rx=6, ry=6, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.2, node_id="dec_cluster", node_kind="op", role="node", bbox=True)
drawer.text(1090, 1222, "Decode \u96c6\u7fa4", 12, fill=INK, weight="bold", bbox=False)
drawer.text(1090, 1240, "\u5feb\u901f\u751f\u6210 \u00b7 \u5e26\u5bbd\u9971\u548c", 10, fill=SUB, bbox=False)

drawer.connect("pre_cluster", "right", "rdma", "left", stroke=EDGE,
               stroke_width=1.5, marker_end="ah")
drawer.connect("rdma", "right", "dec_cluster", "left", stroke=EDGE,
               stroke_width=1.5, marker_end="ah", dashed=True)
drawer.text(855, 1222, "\u4efb\u52a1\u961f\u5217 / \u4e2d\u95f4\u6001", 10, fill=SUB, bbox=False)

# ===== streaming output ===================================================
drawer.rect(560, 1320, 280, 46, rx=8, ry=8, fill=CARD_F, stroke=CARD_S,
            stroke_width=1.4, node_id="output", node_kind="op", role="node", bbox=True)
drawer.text(CX, 1334, "\u91c7\u6837 Sampling\uff08Top-P / Top-K\uff09", 12, fill=INK, weight="bold", bbox=False)
drawer.text(CX, 1350, "\u6d41\u5f0f\u8fd4\u56de Stream Output\uff08SSE / WebSocket\uff09", 10, fill=SUB, bbox=False)

# ===== downward spine: client -> bands -> output ==========================
spine = [("client", "band1")] + [(f"band{i}", f"band{i+1}") for i in range(1, 7)] + [("band7", "output")]
for a, b in spine:
    drawer.connect(a, "bottom", b, "top", stroke=EDGE, stroke_width=2, marker_end="ah")
drawer.text(712, 128, "\u8bf7\u6c42 Request", 10, fill=SUB, anchor="start", bbox=False)

# ---- evaluate, auto-refine, emit triplet ---------------------------------
score, report = evaluate_svg(drawer)
print(f"Initial score: {score}")
for line in report:
    print(line)

if score < 100:
    score, report, fixes = auto_refine(drawer, target_score=100, max_iter=3)
    print(f"\nAfter auto_refine: {score}  (fixes: {len(fixes)})")
    for f in fixes:
        print("  -", f)
    for line in report:
        print(line)

svg = drawer.render()
save_svg(svg, str(OUT / f"{NAME}.svg"))
rasterize_svg(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.png"), width=W)
svg_to_pptx(svg, str(OUT / f"{NAME}.pptx"))
print(f"\nFinal score: {score}")
print(f"Wrote triplet to {OUT}")
