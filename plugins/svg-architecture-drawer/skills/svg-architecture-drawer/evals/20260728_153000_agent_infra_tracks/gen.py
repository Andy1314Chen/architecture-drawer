"""Agent Infra track-style (赛道式) architecture diagram generator.

View: parallel capability domains as vertical lanes (tracks), showing the
ecosystem layout rather than the dependency stack.

  - Top:    Agent 应用 / Application bar (the consumer of all tracks)
  - Middle: 4 vertical tracks — Environment · Context · Tools · Security
  - Bottom: 开放协议与生态 Open Protocols foundation (MCP · OpenAPI)

Output: agent_infra_tracks.svg
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
NAME = "agent_infra_tracks"
OUT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
W, H = 1280, 840

# Structural colors are PURE grays (R==G==B) -> not counted as accents.
INK = "#333333"
SUB = "#666666"
NEU_FILL = "#F2F2F2"
NEU_STROKE = "#B0B0B0"
CARD_FILL = "#FFFFFF"
CARD_STROKE = "#BEBEBE"
EDGE = "#555555"

# 4 track accent fills (borders stay neutral gray -> 4 accents total)
C_ENV = "#B2E2E2"     # Environment  (teal)
C_CTX = "#DCD0FF"     # Context      (purple)
C_TOOL = "#FFE0B2"    # Tools        (orange)
C_SEC = "#EF9A9A"     # Security     (coral)
C_PROTO = "#C5E1A5"   # foundation   (green)

# Font tiers (<=4 distinct, adjacent ratio >=1.15): 22 / 14 / 11 / 9
F_TITLE, F_HEAD, F_LABEL, F_NOTE = 22, 14, 11, 9

drawer = SVGDrawer(W, H, bg="#FFFFFF")
drawer.arrow_head("arrow", EDGE, marker_width=10, marker_height=8, ref_x=9, ref_y=4)


def card(x, y, w, h, cn, en, fs_cn=F_LABEL, fs_en=F_NOTE):
    drawer.rect(x, y, w, h, rx=6, ry=6, fill=CARD_FILL, stroke=CARD_STROKE,
                stroke_width=1, bbox=True)
    drawer.text(x + w / 2, y + h / 2 - fs_cn * 0.55, cn, fs_cn, fill=INK, anchor="middle")
    drawer.text(x + w / 2, y + h / 2 + fs_en * 0.75, en, fs_en, fill=SUB, anchor="middle")


def track(x, w, y, h, fill, nid, cn, en, tag, items):
    """Vertical lane: outer container (node) + colored header + stacked cards."""
    drawer.rect(x, y, w, h, rx=10, ry=10, fill=NEU_FILL, stroke=NEU_STROKE,
                stroke_width=1, node_id=nid, node_kind="region", bbox=True)
    # colored header band
    drawer.rect(x, y, w, 52, rx=10, ry=10, fill=fill, stroke=INK,
                stroke_width=1.2, bbox=False)
    drawer.rect(x, y + 30, w, 22, fill=fill, stroke="none", bbox=False)  # square off bottom of header
    drawer.text(x + w / 2, y + 20, cn, F_HEAD, fill=INK, anchor="middle", weight="bold")
    drawer.text(x + w / 2, y + 38, en, F_NOTE, fill=SUB, anchor="middle")
    if tag:
        drawer.text(x + w / 2, y + h - 12, tag, F_NOTE, fill=SUB, anchor="middle", style="italic")
    # stacked cards
    n = len(items)
    gap = 12
    pad = 14
    top = y + 52 + 12
    avail = h - 52 - 12 - 24 - (n - 1) * gap   # leave 24px footer for tag
    ch = avail / n
    for i, (ccn, cen) in enumerate(items):
        cy = top + i * (ch + gap)
        card(x + pad, cy, w - 2 * pad, ch, ccn, cen)


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
drawer.text(W / 2, 34, "Agent Infra 赛道式架构图", F_TITLE, fill=INK, anchor="middle", weight="bold")
drawer.text(W / 2, 58, "Agent Infrastructure  ·  功能域赛道 Track / Domain View",
            F_LABEL, fill=SUB, anchor="middle")

# ---------------------------------------------------------------------------
# Track geometry: 4 lanes across the canvas
# ---------------------------------------------------------------------------
MX = 24
TW = 296
GAP = 16
track_x = [MX + i * (TW + GAP) for i in range(4)]   # 24, 336, 648, 960
track_cx = [x + TW / 2 for x in track_x]            # 172, 484, 796, 1108

# Agent application bar (consumer) at top
AY, AH = 90, 54
drawer.rect(MX, AY, W - 2 * MX, AH, rx=8, ry=8, fill=NEU_FILL, stroke=NEU_STROKE,
            stroke_width=1, node_id="AGENT", node_kind="layer", bbox=True)
drawer.text(W / 2, AY + 22, "Agent 应用 / 智能体", F_HEAD, fill=INK, anchor="middle", weight="bold")
drawer.text(W / 2, AY + 40, "Agent Application  ·  消费各赛道能力", F_NOTE, fill=SUB, anchor="middle")

# The 4 tracks
TY, TH = 184, 446
tracks = [
    (C_ENV,  "T1", "Environment 域", "Environment", "沙箱 · 隔离运行",
     [("代码沙箱", "Code Sandbox"), ("浏览器基础设施", "Browser Infra"),
      ("容器 / VM", "Container · VM"), ("Serverless 弹性", "Serverless")]),
    (C_CTX,  "T2", "Context 域", "Context", "记忆 · 知识 · 检索",
     [("RAG 检索", "RAG Retrieval"), ("短期记忆", "Short-term Memory"),
      ("长期记忆", "Long-term Memory"), ("向量数据库", "Vector DB"),
      ("知识图谱", "Knowledge Graph")]),
    (C_TOOL, "T3", "Tools 域", "Tools", "连接外部世界",
     [("MCP 协议", "MCP Protocol"), ("搜索", "Search"),
      ("金融 / 支付", "Finance · Payment"), ("工作流编排", "Workflow"),
      ("软件操作", "Software Ops")]),
    (C_SEC,  "T4", "Security 域", "Security", "行为 · 数据安全",
     [("身份认证", "Authentication"), ("数据加密", "Encryption"),
      ("行为审计", "Behavior Audit"), ("访问控制", "Access Control"),
      ("合规治理", "Compliance")]),
]
for i, (fill, nid, cn, en, tag, items) in enumerate(tracks):
    track(track_x[i], TW, TY, TH, fill, nid, cn, en, tag, items)

# Open protocols foundation bar at bottom
FY, FH = 660, 64
drawer.rect(MX, FY, W - 2 * MX, FH, rx=8, ry=8, fill=C_PROTO, stroke=INK,
            stroke_width=1.2, node_id="PROTO", node_kind="layer", bbox=True)
drawer.text(W / 2, FY + 24, "开放协议与生态", F_HEAD, fill=INK, anchor="middle", weight="bold")
drawer.text(W / 2, FY + 44, "Open Protocols & Ecosystem  ·  MCP  ·  OpenAPI  ·  跨赛道共享标准",
            F_NOTE, fill=SUB, anchor="middle")

# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------
# Agent bar -> each track header (clean vertical drops at track center x).
# Endpoints lie exactly on node borders (AGENT bottom / track top) -> dist 0.
AB = AY + AH   # 144, agent bar bottom
TT = TY        # 184, track top
for cx in track_cx:
    drawer.line(cx, AB, cx, TT, stroke=EDGE, stroke_width=1.8, marker_end="arrow",
                register_edge=True)

# Each track -> foundation (dashed, "built on open protocols")
TB = TY + TH   # 630, track bottom
FT = FY        # 660, foundation top
for cx in track_cx:
    drawer.line(cx, TB, cx, FT, stroke=CARD_STROKE, stroke_width=1.2,
                register_edge=True, extra='stroke-dasharray="4,3"')

# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------
LY0 = 748
drawer.rect(MX, LY0, W - 2 * MX, 60, rx=8, ry=8, fill=NEU_FILL, stroke=NEU_STROKE,
            stroke_width=1, bbox=True)
drawer.text(MX + 14, LY0 + 19, "图例 Legend", F_HEAD, fill=INK, anchor="start", weight="bold")

drawer.text(MX + 14, LY0 + 42, "能力赛道 Capability Tracks", F_LABEL, fill=INK, anchor="start")
lx = MX + 14 + 170
for c in (C_ENV, C_CTX, C_TOOL, C_SEC):
    drawer.rect(lx, LY0 + 35, 16, 14, rx=2, ry=2, fill=c, stroke=INK, stroke_width=0.8, bbox=False)
    lx += 22

i2 = MX + 430
drawer.line(i2, LY0 + 42, i2 + 34, LY0 + 42, stroke=EDGE, stroke_width=1.8, marker_end="arrow")
drawer.text(i2 + 44, LY0 + 42, "Agent 调用能力", F_LABEL, fill=INK, anchor="start")

i3 = MX + 640
drawer.line(i3, LY0 + 42, i3 + 34, LY0 + 42, stroke=CARD_STROKE, stroke_width=1.2,
            extra='stroke-dasharray="4,3"')
drawer.text(i3 + 44, LY0 + 42, "构建于开放协议", F_LABEL, fill=INK, anchor="start")

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
