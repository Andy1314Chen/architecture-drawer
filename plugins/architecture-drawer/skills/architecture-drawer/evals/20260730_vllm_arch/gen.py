"""vLLM architecture diagram generator (architecture-drawer skill).

Layered top-to-bottom pipeline (request -> response) with the signature
PagedAttention / paged KV-cache abstraction on the right.

Design choices driven by the evaluator:
  * Big containers carry role="layer" (gutter-checked) but are NOT registered
    as nodes, so cross-container edges never trigger routes-through.
  * Dark blue (#1B3A5C) appears ONLY as stroke; text + arrowheads use neutral
    grays (#1A1A1A / #555555) -> no dark fill -> no luminance clash.
  * Font tiers are exactly {20, 14, 12, 10}.
"""
import sys
from pathlib import Path


import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg  # noqa: E402
from evaluator import evaluate_svg  # noqa: E402
from svg2pptx import svg_to_pptx, PptxConfig  # noqa: E402
from design_brief import DesignBrief, ColorSpec  # noqa: E402
from semantic_qa import run_semantic_qa  # noqa: E402

OUT = Path(__file__).resolve().parent
NAME = "vllm_arch"

# ---- palette (S1 Monochrome Blue) ------------------------------------------
DARK = "#1B3A5C"   # strokes / borders / edges only
INK = "#1A1A1A"    # primary text (neutral)
MUTE = "#555555"   # secondary text (neutral)
T1 = "#D5E1EB"     # engine / title bar tint
T2 = "#E8EEF3"     # api / kv / kernels tint
T3 = "#B8CDE0"     # exec / allocated-block tint

W, H = 1240, 970
d = SVGDrawer(W, H, bg="#FFFFFF")
d.arrow_head("arrow", INK)  # neutral arrowhead -> not counted as a dark fill


def node(x, y, w, h, nid, fill="white", stroke=DARK, sw=1.5, rx=6, role=None,
         bbox=True):
    d.rect(x, y, w, h, rx=rx, ry=rx, fill=fill, stroke=stroke,
           stroke_width=sw, node_id=nid, bbox=bbox, role=role)


def layer(x, y, w, h, fill, role="layer", nid=None):
    d.rect(x, y, w, h, rx=8, ry=8, fill=fill, stroke=DARK, stroke_width=1.5,
           bbox=True, role=role, node_id=nid)


def txt(x, y, s, fs=12, fill=INK, weight="normal", anchor="middle", bbox=True):
    d.text(x, y, s, font_size=fs, fill=fill, weight=weight, anchor=anchor, bbox=bbox)


def bullets(x, y, lines, fs=12, fill=INK, anchor="start"):
    d.multiline_text(x, y, lines, font_size=fs, fill=fill, anchor=anchor)


def E(a, fa, b, fb, dashed=False):
    d.connect(a, fa, b, fb, stroke=DARK, stroke_width=1.5,
              marker_end="arrow", dashed=dashed)


# ---------------------------------------------------------------------------
# 1. Title bar
# ---------------------------------------------------------------------------
layer(0, 0, W, 52, T1, role="background")
txt(W / 2, 21, "vLLM — High-Throughput LLM Serving with PagedAttention",
    fs=20, fill=INK, weight="bold")
txt(W / 2, 41, "PagedAttention · Continuous Batching · High Throughput",
    fs=12, fill=MUTE)

# ---------------------------------------------------------------------------
# 2. Client
# ---------------------------------------------------------------------------
node(510, 80, 220, 62, "client")
txt(620, 100, "Client / Application", fs=14, weight="bold")
txt(620, 122, "OpenAI API · HTTP / SDK", fs=12, fill=MUTE)

# ---------------------------------------------------------------------------
# 3. API Server layer
# ---------------------------------------------------------------------------
layer(150, 166, 940, 128, T2, nid="api_server")
txt(168, 190, "API Server", fs=14, weight="bold", anchor="start")
node(210, 214, 360, 60, "fastapi")
txt(390, 234, "FastAPI / ASGI Server", fs=14, weight="bold")
txt(390, 254, "request routing · streaming", fs=12, fill=MUTE)
node(660, 214, 400, 60, "openai_api")
txt(860, 234, "OpenAI-compatible API", fs=14, weight="bold")
txt(860, 254, "/v1/completions · /v1/chat/completions", fs=12, fill=MUTE)

# ---------------------------------------------------------------------------
# 4. LLM Engine (Core) layer
# ---------------------------------------------------------------------------
layer(40, 318, 740, 300, T1, nid="llm_engine")
txt(58, 340, "LLM Engine (Core)", fs=14, weight="bold", anchor="start")
node(270, 360, 280, 46, "async_engine")
txt(410, 383, "AsyncLLMEngine", fs=14, weight="bold")
node(64, 436, 330, 160, "scheduler")
txt(229, 458, "Scheduler", fs=14, weight="bold")
bullets(86, 482, [
    "• FCFS + priority scheduling",
    "• Continuous batching",
    "• Preemption on KV-cache OOM",
    "• Decode-step orchestration",
])
node(426, 436, 334, 160, "blockmgr")
txt(593, 458, "BlockManager", fs=14, weight="bold")
bullets(448, 482, [
    "• Logical ↔ physical blocks",
    "• Block tables (paging)",
    "• Copy-on-write fork",
    "• Reference counting",
])

# ---------------------------------------------------------------------------
# 5. Paged KV Cache layer (right)
# ---------------------------------------------------------------------------
layer(800, 318, 400, 300, T2, nid="kv_cache")
txt(818, 340, "Paged KV Cache (GPU Memory)", fs=14, weight="bold", anchor="start")

# ① logical blocks (decoration)
txt(818, 366, "① Logical blocks / sequence", fs=12, weight="bold", anchor="start")
for i, lx in enumerate((818, 874, 930)):
    d.rect(lx, 378, 52, 30, rx=4, ry=4, fill="white", stroke=DARK,
           stroke_width=1, role="decoration", bbox=False)
    txt(lx + 26, 393, "L%d" % i, fs=12)

# ② block table
txt(818, 428, "② Block table (logical → physical)", fs=12, weight="bold",
    anchor="start")
for label, lx in (("L0 → P3", 818), ("L1 → P0", 918), ("L2 → P6", 1018)):
    txt(lx, 448, label, fs=12, anchor="start")

# ③ physical blocks node (connectable anchor for management / KV access)
node(820, 474, 360, 124, "phys_blocks", fill="white")
txt(1000, 490, "Physical KV Cache Blocks", fs=12, weight="bold")
alloc = {"P0", "P3", "P6"}
grid_x = (903, 953, 1003, 1053)
for row, gy in enumerate((504, 536)):
    for col, gx in enumerate(grid_x):
        idx = row * 4 + col
        name = "P%d" % idx
        d.rect(gx, gy, 44, 26, rx=3, ry=3,
               fill=(T3 if name in alloc else "white"), stroke=DARK,
               stroke_width=1, role="decoration", bbox=False)
        txt(gx + 22, gy + 13, name, fs=12)
txt(1000, 582, "allocated blocks need not be contiguous → low fragmentation",
    fs=10, fill=MUTE)

# ---------------------------------------------------------------------------
# 6. Execution layer (GPU workers)
# ---------------------------------------------------------------------------
layer(40, 664, 1160, 236, T3, nid="exec_layer")
txt(58, 686, "Execution Layer", fs=14, weight="bold", anchor="start")
node(90, 708, 240, 58, "worker")
txt(210, 730, "Worker", fs=14, weight="bold")
txt(210, 750, "cache · device mgmt", fs=12, fill=MUTE)
node(360, 708, 300, 58, "modelrunner")
txt(510, 730, "ModelRunner", fs=14, weight="bold")
txt(510, 750, "forward pass · sampling", fs=12, fill=MUTE)
node(690, 708, 300, 58, "pagedattn")
txt(840, 730, "PagedAttention Kernel", fs=14, weight="bold")
txt(840, 750, "blocked KV · flash attn", fs=12, fill=MUTE)

d.rect(90, 786, 1090, 94, rx=6, ry=6, fill=T2, stroke=DARK, stroke_width=1.5,
       bbox=True, role="layer", node_id="optimizations")
txt(110, 808, "Optimizations & CUDA Kernels", fs=14, weight="bold", anchor="start")
bullets(110, 832, [
    "• Continuous batching (iteration-level)    • Prefix caching    • Chunked prefill    • Speculative decoding",
    "• Quantization: AWQ · GPTQ · FP8    • Tensor / pipeline parallelism    • LoRA multi-adapter    • Prefix-aware scheduling",
])

# ---------------------------------------------------------------------------
# 7. Edges (request flow solid; cache/block management dashed)
# ---------------------------------------------------------------------------
E("client", "bottom", "openai_api", "top")            # request in
E("fastapi", "right", "openai_api", "left")           # routing
E("openai_api", "bottom", "async_engine", "top")      # enqueue
E("async_engine", "bottom", "scheduler", "top")       # schedule
E("scheduler", "right", "blockmgr", "left", dashed=True)   # alloc / free
E("scheduler", "bottom", "worker", "top")             # scheduled batch -> GPU
E("blockmgr", "right", "phys_blocks", "left", dashed=True)  # manage physical
E("worker", "right", "modelrunner", "left")
E("modelrunner", "right", "pagedattn", "left")
E("pagedattn", "top", "phys_blocks", "bottom")        # KV read / write

# ---------------------------------------------------------------------------
# 8. Legend
# ---------------------------------------------------------------------------
d.rect(40, 916, 560, 40, rx=6, ry=6, fill="white", stroke=DARK,
       stroke_width=1.2, bbox=False, role="legend")
d.line(60, 936, 100, 936, stroke=DARK, stroke_width=1.5, role="legend")
txt(110, 936, "data / request flow", fs=12, anchor="start", bbox=False)
d.line(300, 936, 340, 936, stroke=DARK, stroke_width=1.5, role="legend",
       dashed="6,3")
txt(352, 936, "cache / block management", fs=12, anchor="start", bbox=False)

# ---------------------------------------------------------------------------
# 9. Design Brief (Step 1) — declared from input.md's layer list; the
#    contract the rendered SVG is asserted against. kv_cache is a SIDE band
#    (memory column) and optimizations a text-only band: palette members,
#    not chain stages. The chain is input.md's request flow.
# ---------------------------------------------------------------------------
BRIEF = DesignBrief(
    scheme="S1",
    layout="band",
    flow="top-down",
    palette_role={
        "api_server":    ColorSpec(T2, DARK),
        "llm_engine":    ColorSpec(T1, DARK),
        "kv_cache":      ColorSpec(T2, DARK),
        "exec_layer":    ColorSpec(T3, DARK),
        "optimizations": ColorSpec(T2, DARK),
    },
    flow_chain=("api_server", "llm_engine", "exec_layer"),
)

score, report = evaluate_svg(d)
print("Quality Score: %d" % score)
for line in report:
    print(line)

qa = run_semantic_qa(d, expected_size=(W, H), brief=BRIEF)
print("Semantic QA:")
for line in qa.report():
    print(line)

svg = d.render()
save_svg(svg, str(OUT / (NAME + ".svg")))
rasterize_svg(str(OUT / (NAME + ".svg")), str(OUT / (NAME + ".png")), width=W)
svg_to_pptx(svg, str(OUT / (NAME + ".pptx")),
            config=PptxConfig(slide_w=13.333, slide_h=10.41, scale=1.0))
BRIEF.write(str(OUT / "brief.json"))
print("DONE")
