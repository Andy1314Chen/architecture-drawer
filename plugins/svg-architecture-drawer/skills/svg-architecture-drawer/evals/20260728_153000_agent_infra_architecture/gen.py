"""Agent Infra layered architecture diagram generator.

Layout: 5 horizontal layers (Application -> Orchestration -> Core Capabilities ->
Execution & Environment -> Infrastructure) with the 5 core modules colored, and a
"Security & Observability" band spanning all layers on the right (cross-cutting).

Output: agent_infra_architecture.svg
"""
from pathlib import Path
import sys

import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg
from evaluator import evaluate_svg

# Script co-located with its SVG/PNG/PPTX in this dir (output/<ts>_<name>/).
# Re-run refreshes the triplet in place.
NAME = "agent_infra_architecture"
OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
W, H = 1280, 900

# Stack (left) + cross-cutting band (right)
SX0, SW = 30, 860          # stack x-range 30..890
SX1 = SX0 + SW             # 890
BX0, BW = 910, 330         # band x-range 910..1240

# Structural colors are PURE grays (R==G==B) so the validator treats them as
# neutral and does NOT count them as accents -> palette stays at the 5 module fills.
INK = "#333333"            # primary text / module borders
SUB = "#666666"            # secondary text
NEU_FILL = "#F2F2F2"       # neutral layer fill
NEU_STROKE = "#B0B0B0"     # neutral layer border
CARD_FILL = "#FFFFFF"
CARD_STROKE = "#BEBEBE"
EDGE = "#555555"           # connectors (pure gray)

# 5 core-module accent FILLS only (borders stay neutral gray -> 5 accents total)
C_MEM = "#B2E2E2"     # Memory & Context  (teal)
C_TOOL = "#FFE0B2"    # Tools & Gateway   (orange)
C_EXEC = "#C5E1A5"    # Execution Engine  (green)
C_SAND = "#FFF59D"    # Environment/Sandbox(yellow)
C_SEC = "#EF9A9A"     # Security band     (coral)

# Font tiers (<=4 distinct, adjacent ratio >=1.15): 22 / 14 / 11 / 9
F_TITLE, F_HEAD, F_LABEL, F_NOTE = 22, 14, 11, 9

drawer = SVGDrawer(W, H, bg="#FFFFFF")
drawer.arrow_head("arrow", EDGE, marker_width=10, marker_height=8, ref_x=9, ref_y=4)


def head_two(x, y_cn, y_en, cn, en, fill=INK, weight="bold", anchor="middle"):
    drawer.text(x, y_cn, cn, F_HEAD, fill=fill, anchor=anchor, weight=weight)
    if en:
        drawer.text(x, y_en, en, F_NOTE, fill=SUB, anchor=anchor)


def card(x, y, w, h, cn, en, fs_cn=F_LABEL, fs_en=F_NOTE):
    drawer.rect(x, y, w, h, rx=6, ry=6, fill=CARD_FILL, stroke=CARD_STROKE,
                stroke_width=1, bbox=True)
    if en:
        drawer.text(x + w / 2, y + h / 2 - fs_cn * 0.55, cn, fs_cn, fill=INK, anchor="middle")
        drawer.text(x + w / 2, y + h / 2 + fs_en * 0.75, en, fs_en, fill=SUB, anchor="middle")
    else:
        drawer.text(x + w / 2, y + h / 2, cn, fs_cn, fill=INK, anchor="middle")


def card_row(items, y, h, inner_x, inner_w, cn_fs=F_LABEL):
    n = len(items)
    gap = 14
    cw = (inner_w - gap * (n - 1)) / n
    for i, (cn, en) in enumerate(items):
        x = inner_x + i * (cw + gap)
        card(x, y, cw, h, cn, en, fs_cn=cn_fs)


def module(x, y, w, h, fill, cn, en, sub_items):
    drawer.rect(x, y, w, h, rx=8, ry=8, fill=fill, stroke=INK, stroke_width=1.2, bbox=True)
    head_two(x + w / 2, y + 22, y + 37, cn, en)
    pad = 12
    sub_y = y + 50
    sub_h = h - 50 - pad
    card_row(sub_items, sub_y, sub_h, x + pad, w - 2 * pad)


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
drawer.text(W / 2, 34, "Agent Infra 架构图", F_TITLE, fill=INK, anchor="middle", weight="bold")
drawer.text(W / 2, 58, "Agent Infrastructure  ·  分层架构 Layered Architecture",
            F_LABEL, fill=SUB, anchor="middle")

# ---------------------------------------------------------------------------
# Layer containers (neutral) + their nodes for inter-layer arrows.
# Each layer: header band (cn y+18 / en y+32), content starts at y+44.
# Inter-layer gaps = 20px so arrow segments stay >=16px after marker retraction.
# ---------------------------------------------------------------------------
inner_x, inner_w = SX0 + 18, SW - 36   # 48 .. 872  (width 824)
layers = [
    (90, 90, "应用层", "Application Layer", "L1"),
    (200, 92, "编排与治理层", "Orchestration & Governance", "L2"),
    (312, 188, "核心能力层", "Core Capabilities", "L3"),
    (520, 176, "执行与环境层", "Execution & Environment", "L4"),
    (716, 90, "基础设施层", "Infrastructure", "L5"),
]
for y, h, hcn, hen, nid in layers:
    drawer.rect(SX0, y, SW, h, rx=8, ry=8, fill=NEU_FILL, stroke=NEU_STROKE,
                stroke_width=1, node_id=nid, node_kind="layer", bbox=True)
    head_two(inner_x + 4, y + 18, y + 32, hcn, hen, anchor="start")

# L1 - Application (3 cards)
card_row([("Web 应用", "Web App"), ("REST / API", "Gateway"), ("CLI 工具", "CLI")],
         134, 46, inner_x, inner_w)
# L2 - Orchestration (4 cards)
card_row([("生命周期管理", "Lifecycle"), ("任务调度", "Scheduling"),
          ("多智能体协作", "Multi-Agent"), ("策略控制", "Policy")],
         244, 46, inner_x, inner_w)

# L3 - Core Capabilities: Memory & Context (teal) | Tools & Gateway (orange)
mW = 410
module(SX0 + 18, 356, mW, 132, C_MEM, "记忆与上下文", "Memory & Context",
       [("向量数据库", "Vector DB"), ("知识图谱", "Knowledge Graph"), ("RAG 检索", "Retrieval")])
module(SX0 + 18 + mW + 20, 356, mW, 132, C_TOOL, "工具与网关", "Tools & Gateway",
       [("MCP 协议", "MCP"), ("API 集成", "API Integration"), ("函数调用", "Function Call")])

# L4 - Execution & Environment: Execution Engine (green) | Sandbox (yellow)
module(SX0 + 18, 564, mW, 120, C_EXEC, "执行引擎", "Execution Engine",
       [("高并发", "Concurrency"), ("秒级扩容", "Autoscale"), ("快速启动", "Fast Start")])
module(SX0 + 18 + mW + 20, 564, mW, 120, C_SAND, "环境与沙箱", "Environment & Sandbox",
       [("代码执行", "Code Exec"), ("Serverless", "Elastic"), ("安全隔离", "Isolation")])

# L5 - Infrastructure (4 cards)
card_row([("计算", "Compute · GPU/CPU"), ("存储", "Storage"), ("网络", "Network"), ("K8s 编排", "Kubernetes")],
         760, 42, inner_x, inner_w)

# ---------------------------------------------------------------------------
# Security & Observability - cross-cutting band (spans full stack height)
# ---------------------------------------------------------------------------
BY0, BH = 90, 716     # 90..806, matches the layer stack
drawer.rect(BX0, BY0, BW, BH, rx=10, ry=10, fill=C_SEC, stroke=INK,
            stroke_width=1.2, node_id="SEC", node_kind="region", bbox=True)
drawer.text(BX0 + BW / 2, BY0 + 26, "安全与可观测", F_HEAD, fill=INK, anchor="middle", weight="bold")
drawer.text(BX0 + BW / 2, BY0 + 44, "Security & Observability", F_NOTE, fill=SUB, anchor="middle")
drawer.text(BX0 + BW / 2, BY0 + 60, "横向贯穿所有层 · Cross-cutting", F_NOTE, fill=SUB,
            anchor="middle", style="italic")

sec_items = [("身份认证", "Authentication"), ("数据加密", "Encryption"),
             ("行为审计", "Behavior Audit"), ("日志", "Logging"),
             ("监控", "Metrics"), ("链路追踪", "Tracing")]
s_y0, s_h, s_gap = 180, 92, 12
for i, (cn, en) in enumerate(sec_items):
    yy = s_y0 + i * (s_h + s_gap)
    card(BX0 + 14, yy, BW - 28, s_h, cn, en)

# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
# 1) Vertical dependency flow between adjacent layers (stack centerline, x=460)
for a, b in [("L1", "L2"), ("L2", "L3"), ("L3", "L4"), ("L4", "L5")]:
    drawer.connect(a, "bottom", b, "top", stroke=EDGE, stroke_width=1.8, marker_end="arrow")

# 2) Cross-cutting dashed links: each layer's right edge -> band left edge
for y, h, _hcn, _hen, _nid in layers:
    cy = y + h / 2
    drawer.line(SX1, cy, BX0, cy, stroke=CARD_STROKE, stroke_width=1.2,
                register_edge=True, extra='stroke-dasharray="4,3"')

# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------
LY0 = 822
drawer.rect(SX0, LY0, SW, 60, rx=8, ry=8, fill=NEU_FILL, stroke=NEU_STROKE,
            stroke_width=1, bbox=True)
drawer.text(SX0 + 14, LY0 + 19, "图例 Legend", F_HEAD, fill=INK, anchor="start", weight="bold")

# item 1: core-module swatches
drawer.text(SX0 + 14, LY0 + 42, "核心模块 Core Modules", F_LABEL, fill=INK, anchor="start")
lx = SX0 + 14 + 158
for c in (C_MEM, C_TOOL, C_EXEC, C_SAND, C_SEC):
    drawer.rect(lx, LY0 + 35, 16, 14, rx=2, ry=2, fill=c, stroke=INK, stroke_width=0.8, bbox=False)
    lx += 22

# item 2: dependency arrow
i2 = SX0 + 470
drawer.line(i2, LY0 + 42, i2 + 34, LY0 + 42, stroke=EDGE, stroke_width=1.8, marker_end="arrow")
drawer.text(i2 + 44, LY0 + 42, "依赖 / 控制流", F_LABEL, fill=INK, anchor="start")

# item 3: dashed cross-cut
i3 = SX0 + 680
drawer.line(i3, LY0 + 42, i3 + 34, LY0 + 42, stroke=CARD_STROKE, stroke_width=1.2,
            extra='stroke-dasharray="4,3"')
drawer.text(i3 + 44, LY0 + 42, "安全可观测横跨各层", F_LABEL, fill=INK, anchor="start")

# ---------------------------------------------------------------------------
# Evaluate + save
# ---------------------------------------------------------------------------
score, report = evaluate_svg(drawer)
print(f"Quality Score: {score}")
for line in report:
    print(line)

svg_path = str(OUT / f"{NAME}.svg")
png_path = str(OUT / f"{NAME}.png")
pptx_path = str(OUT / f"{NAME}.pptx")
save_svg(drawer.render(), svg_path)
# Rasterize SVG -> PNG (enforces output/<task>/ convention)
rasterize_svg(svg_path, png_path, W)
# Export to PPTX (native editable shapes)
from svg2pptx import svg_to_pptx
svg_to_pptx(drawer.render(), pptx_path)
print(f"Saved {svg_path}")
print(f"Saved {png_path}")
print(f"Saved {pptx_path} (editable shapes)")
