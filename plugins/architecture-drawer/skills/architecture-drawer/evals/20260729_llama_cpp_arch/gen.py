"""llama.cpp architecture diagram generator.

Three-section top-to-bottom layout:
  1. Core Library  — 4 stacked layer bands (Model / Execution / Graph / Backend)
  2. Inference Execution Flow — horizontal 6-stage pipeline
  3. Server Architecture (llama-server) — routes -> queue -> context(slots) -> response

Palette: S2 Categorical (Okabe-Ito, colorblind-safe). Each library layer gets a
distinct HUE so layer boundaries read at a glance — not a single-hue ramp whose
tiers blur together. Cards inherit their parent layer's stroke (visual grouping,
no extra accents). Text is neutral; connectors gray. The inference/server sections
are a different structural concern (runtime flow, not static architecture) so they
stay neutral-gray. 8 accents total (4 tints + 4 matching strokes), within budget.
4 font tiers (20 / 14 / 12 / 10).
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
from svg2pptx import svg_to_pptx
from design_brief import DesignBrief, ColorSpec
from semantic_qa import run_semantic_qa

OUT = Path(__file__).resolve().parent
NAME = "llama_cpp_arch"

W, H = 1400, 1060

# ---- palette: S2 Categorical (Okabe-Ito) ---------------------------------
# Each layer = (fill tint, matching stroke). Distinct hues → layer identity is
# visible. All fills are light pastels (L>0.8); all strokes medium (0.2<L<0.8),
# so no within-channel luminance clash. 8 accents total.
LAYERS = [
    ("Model Layer",               "#FAEED1", "#E69F00"),  # Orange
    ("Execution Layer",           "#E1F2FB", "#56B4E9"),  # Sky Blue
    ("Computation Graph Layer",   "#D1EEE6", "#009E73"),  # Bluish-Green
    ("Backend Abstraction Layer", "#D1E6F1", "#0072B2"),  # Deep Blue
]
TXT   = "#222222"   # primary text  (neutral -> not counted as accent)
SUB   = "#555555"   # subtitle text (neutral)
GRAY  = "#4D4D4D"   # connectors + arrowheads (neutral)
NSTK  = "#555555"   # neutral stroke for process-section cards (neutral)
CARD  = "#FFFFFF"
PANEL = "#F7F7F7"   # near-white section panel (neutral)
DIV   = "#CCCCCC"   # panel border (neutral)

drawer = SVGDrawer(W, H, bg="#FFFFFF")
drawer.arrow_head("arrow", GRAY)


def card(x, y, w, h, nid, title, sub=None, stroke="#555555", sw=1.5):
    """White op card with optional subtitle. Registered as a node when nid given."""
    drawer.rect(x, y, w, h, rx=6, ry=6, fill=CARD, stroke=stroke, stroke_width=sw,
                node_id=nid, node_kind="op", bbox=False)
    if sub:
        drawer.text(x + w / 2, y + h * 0.36, title, 12, fill=TXT, weight="bold", bbox=False)
        drawer.text(x + w / 2, y + h * 0.70, sub, 10, fill=SUB, bbox=False)
    else:
        drawer.text(x + w / 2, y + h / 2, title, 12, fill=TXT, weight="bold", bbox=False)


def flow(a, b):
    drawer.connect(a, "right", b, "left", stroke=GRAY, stroke_width=1.5, marker_end="arrow")


CLX, CLW = 40, 1320
LH, LGAP = 120, 20
NODE_IDS = ["L_model", "L_exec", "L_graph", "L_backend"]


def layer_y(i):
    return 88 + i * (LH + LGAP)


# ---- title ---------------------------------------------------------------
drawer.text(W / 2, 36, "llama.cpp — Architecture", 20, fill=TXT, weight="bold", bbox=False)

# ============================================================ Core Library
drawer.text(CLX, 70, "Core Library", 14, fill=TXT, weight="bold", anchor="start", bbox=False)

# Per-layer card contents: (x, y_off, w, h, nid, title, subtitle)
LAYER_CARDS = [
    [  # Model Layer
        (240, 350, 66, "m_model", "llama_model", "weights & hyperparams (GGUF)"),
        (610, 350, 66, "m_vocab", "llama_vocab", "tokenizer: BPE · SPM · WPM"),
        (980, 360, 66, "m_map", "Model Arch Mapping", "llama_model_mapping() → impl"),
    ],
    [  # Execution Layer
        (240, 350, 66, "e_ctx", "llama_context", "execution state · memory"),
        (610, 350, 66, "e_batch", "llama_batch / ubatch", "token input structures"),
        (980, 360, 66, "e_kv", "llama_kv_cache", "K/V vectors · avoid recompute"),
    ],
    [  # Computation Graph Layer
        (240, 500, 66, "g_cgraph", "ggml_cgraph", "DAG of ggml_tensor ops"),
        (760, 580, 66, "g_build", "Graph Building", "build_graph(): pooling + sampling"),
    ],
    [  # Backend Abstraction Layer
        (240, 300, 66, "b_backend", "ggml-backend", "SIMD + GPU offload"),
    ],
]
BACKEND_DEV = ["CPU", "CUDA", "Metal", "Vulkan", "SYCL"]

for li, (label, lfill, lstroke) in enumerate(LAYERS):
    y = layer_y(li)
    drawer.rect(CLX, y, CLW, LH, rx=8, ry=8, fill=lfill, stroke=lstroke, stroke_width=1.5,
                node_id=NODE_IDS[li], node_kind="layer", bbox=True)
    drawer.text(CLX + 18, y + 22, label, 14, fill=TXT, weight="bold", anchor="start", bbox=False)
    cy = y + 42
    for cx, cw, ch, nid, title, sub in LAYER_CARDS[li]:
        card(cx, cy, cw, ch, nid, title, sub, stroke=lstroke)
    if li == 3:  # backend devices
        for i, name in enumerate(BACKEND_DEV):
            card(562 + i * 156, cy, 140, 66, None, name, stroke=lstroke)

# layer dependency spine (top -> bottom)
drawer.connect(NODE_IDS[0], "bottom", NODE_IDS[1], "top", stroke=GRAY, stroke_width=1.5, marker_end="arrow")
drawer.connect(NODE_IDS[1], "bottom", NODE_IDS[2], "top", stroke=GRAY, stroke_width=1.5, marker_end="arrow")
drawer.connect(NODE_IDS[2], "bottom", NODE_IDS[3], "top", stroke=GRAY, stroke_width=1.5, marker_end="arrow")

# ============================================== Inference Execution Flow
iy = 648
drawer.rect(CLX, iy, CLW, 124, rx=8, ry=8, fill=PANEL, stroke=DIV, stroke_width=1,
            bbox=True, role="background")
drawer.text(CLX + 18, iy + 24, "Inference Execution Flow", 14, fill=TXT, weight="bold",
            anchor="start", bbox=False)
stages = [
    ("s1", "Token IDs", "input"),
    ("s2", "llama_batch", "batch API"),
    ("s3", "llama_ubatch", "internal rep"),
    ("s4", "build_graph", "construct DAG"),
    ("s5", "graph_compute", "backend exec"),
    ("s6", "logits / embeds", "output"),
]
sx0, sw, sgap = 60, 188, 30
for i, (nid, t, sub) in enumerate(stages):
    card(sx0 + i * (sw + sgap), iy + 46, sw, 56, nid, t, sub, stroke=NSTK)
for i in range(len(stages) - 1):
    flow(stages[i][0], stages[i + 1][0])

# ============================================== Server Architecture
sy_c = 786
drawer.rect(CLX, sy_c, CLW, 250, rx=8, ry=8, fill=PANEL, stroke=DIV, stroke_width=1,
            bbox=True, role="background")
drawer.text(CLX + 18, sy_c + 24, "Server Architecture — llama-server", 14, fill=TXT,
            weight="bold", anchor="start", bbox=False)

# server_context container (holds llama_context + active slots); center y = 912
drawer.rect(510, 822, 520, 180, rx=8, ry=8, fill=CARD, stroke=NSTK, stroke_width=1.5,
            node_id="sv_ctx", node_kind="block", bbox=True)
drawer.text(770, 845, "server_context", 12, fill=TXT, weight="bold", bbox=False)
drawer.text(770, 863, "holds llama_context + active slots", 10, fill=SUB, bbox=False)
drawer.text(770, 885, "server_slot — parallel sequences", 10, fill=SUB, bbox=False)
for i, x in enumerate((530, 695, 860)):
    card(x, 900, 150, 72, f"slot{i + 1}", f"slot {i + 1}", f"seq #{i + 1}", stroke=NSTK)

# I/O components (centered on y=912 to align with sv_ctx)
card(70, 867, 200, 90, "sv_routes", "server_routes", "HTTP interface · middleware", stroke=NSTK)
card(300, 867, 180, 90, "sv_queue", "server_queue", "task submission", stroke=NSTK)
card(1060, 867, 270, 90, "sv_resp", "server_response", "thread-safe results", stroke=NSTK)
flow("sv_routes", "sv_queue")
flow("sv_queue", "sv_ctx")
flow("sv_ctx", "sv_resp")

# ============================================================ Design Brief
# Declared from input.md's intent: Section 1 defines the four stacked Core
# Library layer bands (Model / Execution / Graph / Backend) as a top-down
# dependency/abstraction stack ("top depends on those below", arrows linking
# each band to the one beneath) -> band layout, vertical flow axis, palette
# from the S2 Okabe-Ito layer tints. The chain stays EMPTY: the dependency
# spine snaps band-border to band-border, and the arrowhead retraction leaves
# the path end in the 20px gutter (outside the target band box), so the
# contract checker cannot attribute those edges as inter-layer stages -- an
# unverifiable chain is not declared. The Inference Flow and Server sections
# are runtime-process panels (neutral gray, background role), not tinted
# library bands, so they stay outside the band contract.
BRIEF = DesignBrief(
    scheme="S2",
    layout="band",
    flow="top-down",
    palette_role={nid: ColorSpec(fill, stroke)
                  for nid, (_label, fill, stroke) in zip(NODE_IDS, LAYERS)},
    flow_chain=("L_model", "L_exec", "L_graph", "L_backend"),
)

# ============================================================ evaluate + save
score, report = evaluate_svg(drawer)
print(f"Quality Score: {score}")
for line in report:
    print(line)

qa = run_semantic_qa(drawer, expected_size=(W, H), brief=BRIEF)
print("Semantic QA:")
for line in qa.report():
    print(line)

save_svg(drawer.render(), str(OUT / f"{NAME}.svg"))
rasterize_svg(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.png"), width=W)
svg_to_pptx(drawer.render(), OUT / f"{NAME}.pptx")
BRIEF.write(str(OUT / "brief.json"))
print("Saved triplet to", OUT)
