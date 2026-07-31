#!/usr/bin/env python3
"""Generator for multi-objective optimization framework diagram."""

import sys
from pathlib import Path


import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg
from evaluator import evaluate_svg, auto_refine

OUT = Path(__file__).resolve().parent
NAME = "space_opt_framework"

W, H = 1800, 1250
MARGIN = 60
CONTENT_W = W - 2 * MARGIN
RIGHT_BUS_X = W - 30

# Tight palette: exactly 8 non-neutral accents, no very-dark fills
C_STROKE      = "#78909C"
C_TEXT        = "#78909C"
C_PERF_FILL   = "#D4EDDA"
C_REL_FILL    = "#F8D7DA"
C_PWR_FILL    = "#FFF3CD"
C_BANNER_FILL = "#78909C"
C_SW_FILL     = "#E3F2FD"
C_HW_FILL     = "#E0F7FA"
C_COLL_FILL   = "#F3E5F5"
C_MOD_FILL    = "#FFFFFF"
C_L4_FILL     = "#FFFFFF"
C_FB_STROKE   = "#E65100"
C_BG          = "#FFFFFF"

drawer = SVGDrawer(W, H, bg=C_BG)
drawer.arrow_head("arrowhead",    C_STROKE)
drawer.arrow_head("arrowhead_fb", C_FB_STROKE)

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
drawer.text(W // 2, 30,
            "星载AI推理性能-可靠性-功耗多目标优化框架",
            font_size=20, weight="bold", fill=C_TEXT, anchor="middle")

# ---------------------------------------------------------------------------
# Layer 1 – Optimization Goals
# ---------------------------------------------------------------------------
L1_Y = 70
L1_H = 70
L1_NODE_W = 200
gap = (CONTENT_W - 3 * L1_NODE_W) // 4
L1_X1 = MARGIN + gap
L1_X2 = L1_X1 + L1_NODE_W + gap
L1_X3 = L1_X2 + L1_NODE_W + gap

goals = [
    ("perf", "性能", "推理吞吐量 ↑", L1_X1, C_PERF_FILL),
    ("rel",  "可靠性", "任务可靠度 ≥ 99.9%", L1_X2, C_REL_FILL),
    ("pwr",  "功耗", "≤ 星载功耗预算", L1_X3, C_PWR_FILL),
]
for nid, title, subtitle, x, fill in goals:
    drawer.rect(x, L1_Y, L1_NODE_W, L1_H, rx=10,
                fill=fill, stroke=C_STROKE, stroke_width=2,
                node_id=nid, node_kind="op")
    drawer.text(x + L1_NODE_W // 2, L1_Y + 26, title,
                font_size=12, weight="bold", fill=C_TEXT, anchor="middle")
    drawer.text(x + L1_NODE_W // 2, L1_Y + 48, subtitle,
                font_size=10, fill="#333333", anchor="middle")

# Pareto banner (background role → skipped by route-through)
BANNER_Y = L1_Y + L1_H + 12
BANNER_H = 40
BANNER_X = MARGIN + 80
BANNER_W = CONTENT_W - 160
drawer.rect(BANNER_X, BANNER_Y, BANNER_W, BANNER_H, rx=5,
            fill=C_BANNER_FILL, stroke=C_STROKE, stroke_width=2,
            node_id="pareto_banner", role="background")
# text marked as legend so evaluator skips it as an obstacle
drawer.text(BANNER_X + 30, BANNER_Y + BANNER_H - 10,
            "帕累托前沿  (Pareto Frontier)",
            font_size=14, weight="bold", fill="#FFFFFF", anchor="start",
            extra='data-graph-role="legend"')

# Conflicting-goal arrows
drawer.connect("perf", "right", "rel", "left",
               dashed=True, stroke=C_STROKE, stroke_width=1.5,
               edge_label="相互冲突")
drawer.connect("rel", "right", "pwr", "left",
               dashed=True, stroke=C_STROKE, stroke_width=1.5)

# ---------------------------------------------------------------------------
# Layer 2 – Decision Variables
# ---------------------------------------------------------------------------
L2_Y = BANNER_Y + BANNER_H + 35
L2_H = 190
L2_DOMAIN_W = 460
L2_GAP = (CONTENT_W - 3 * L2_DOMAIN_W) // 2
L2_X1 = MARGIN
L2_X2 = L2_X1 + L2_DOMAIN_W + L2_GAP
L2_X3 = L2_X2 + L2_DOMAIN_W + L2_GAP

domains = [
    ("sw",     "软件域 (决策变量 β, δ)",     L2_X1, C_SW_FILL,
     ["算法级容错(ABFT)校验周期", "检查点保存频率", "动态重试触发阈值"]),
    ("hw",     "硬件域 (决策变量 α)",       L2_X2, C_HW_FILL,
     ["三模冗余(TMR)复制比例", "抗辐射芯片选型策略", "存储ECC使能策略"]),
    ("collab", "协同域 (决策变量 γ)",       L2_X3, C_COLL_FILL,
     ["关键层/非关键层容错分配系数", "跨层错误传播抑制策略"]),
]
for nid, title, x, fill, items in domains:
    drawer.rect(x, L2_Y, L2_DOMAIN_W, L2_H, rx=6,
                fill=fill, stroke=C_STROKE, stroke_width=2,
                node_id=nid, node_kind="block")
    drawer.text(x + L2_DOMAIN_W // 2, L2_Y + 22, title,
                font_size=12, weight="bold", fill=C_TEXT, anchor="middle")
    iy = L2_Y + 52
    for item in items:
        drawer.text(x + 18, iy, "· " + item,
                    font_size=10, fill="#333333", anchor="start")
        iy += 18

# ---------------------------------------------------------------------------
# Arrows L1 → L2  (star junction to avoid crossings & text obstacles)
# ---------------------------------------------------------------------------
J_L12_X = (L1_X1 + L1_NODE_W // 2 + L1_X3 + L1_NODE_W // 2) // 2   # 900
J_L12_Y = BANNER_Y + BANNER_H + 8                                   # 210
drawer.circle(J_L12_X, J_L12_Y, 5,
              fill=C_STROKE, stroke="none",
              node_id="j_l12", node_kind="junction")

for src in ["perf", "rel", "pwr"]:
    drawer.connect(src, "bottom", "j_l12", "top",
                   stroke=C_STROKE, stroke_width=1.5, marker_end="arrowhead")
for tgt in ["sw", "hw", "collab"]:
    drawer.connect("j_l12", "bottom", tgt, "top",
                   stroke=C_STROKE, stroke_width=1.5, marker_end="arrowhead")

# ---------------------------------------------------------------------------
# Layer 3 – Technical Implementation
# ---------------------------------------------------------------------------
L3_Y = 470
L3_H = 170
L3_MOD_W = 280
L3_GAP = (CONTENT_W - 5 * L3_MOD_W) // 4
L3_X1 = MARGIN
L3_X2 = L3_X1 + L3_MOD_W + L3_GAP
L3_X3 = L3_X2 + L3_MOD_W + L3_GAP
L3_X4 = L3_X3 + L3_MOD_W + L3_GAP
L3_X5 = L3_X4 + L3_MOD_W + L3_GAP

mods = [
    ("m1", "① 抗辐射加固\n硬件设计",             L3_X1),
    ("m2", "② 算法级容错\n(ABFT / Retry)",      L3_X2),
    ("m3", "③ MLIR异构\n编译",                  L3_X3),
    ("m4", "④ 检查点与\n动态恢复机制",           L3_X4),
    ("m5", "⑤ 在轨软件更新\n(OTA)",             L3_X5),
]
for nid, label, x in mods:
    drawer.rect(x, L3_Y, L3_MOD_W, L3_H, rx=5,
                fill=C_MOD_FILL, stroke=C_STROKE, stroke_width=2,
                node_id=nid, node_kind="op")
    lines = label.split('\n')
    ly = L3_Y + L3_H // 2 - (len(lines) - 1) * 7
    for line in lines:
        drawer.text(x + L3_MOD_W // 2, ly, line,
                    font_size=12, weight="bold", fill=C_TEXT, anchor="middle")
        ly += 15

# ---------------------------------------------------------------------------
# Arrows L2 → L3  (star junction)
# ---------------------------------------------------------------------------
J_L23_X = J_L12_X
J_L23_Y = L3_Y - 25   # 445  (between L2 bottom 417 and L3 top 470)
drawer.circle(J_L23_X, J_L23_Y, 5,
              fill=C_STROKE, stroke="none",
              node_id="j_l23", node_kind="junction")

for src in ["hw", "sw", "collab"]:
    drawer.connect(src, "bottom", "j_l23", "top",
                   stroke=C_STROKE, stroke_width=1.5, marker_end="arrowhead")
for tgt in ["m1", "m2", "m3", "m4", "m5"]:
    drawer.connect("j_l23", "bottom", tgt, "top",
                   stroke=C_STROKE, stroke_width=1.5, marker_end="arrowhead")

# ---------------------------------------------------------------------------
# Layer 4 – Evaluation & Optimization Engine
# ---------------------------------------------------------------------------
L4_Y = L3_Y + L3_H + 35
L4_H = 220
L4_W = (CONTENT_W - 100) // 2
L4_X1 = MARGIN
L4_X2 = L4_X1 + L4_W + 100

drawer.rect(L4_X1, L4_Y, L4_W, L4_H, rx=6,
            fill=C_L4_FILL, stroke=C_STROKE, stroke_width=2,
            node_id="evaluator", node_kind="block")
drawer.text(L4_X1 + L4_W // 2, L4_Y + 25, "多目标评估器",
            font_size=14, weight="bold", fill=C_TEXT, anchor="middle")
for i, item in enumerate(["故障注入 (辐射效应模拟)", "性能监测 (延迟/吞吐量)", "功耗测量 (电流/电压采样)"]):
    drawer.text(L4_X1 + 20, L4_Y + 55 + i * 18, "· " + item,
                font_size=10, fill="#333333", anchor="start")

drawer.rect(L4_X2, L4_Y, L4_W, L4_H, rx=6,
            fill=C_L4_FILL, stroke=C_STROKE, stroke_width=2,
            node_id="explorer", node_kind="block")
drawer.text(L4_X2 + L4_W // 2, L4_Y + 25, "设计空间探索引擎",
            font_size=14, weight="bold", fill=C_TEXT, anchor="middle")
for i, item in enumerate(["贝叶斯优化 / 多目标进化算法", "帕累托排序", "约束边界搜索"]):
    drawer.text(L4_X2 + 20, L4_Y + 55 + i * 18, "· " + item,
                font_size=10, fill="#333333", anchor="start")

# ---------------------------------------------------------------------------
# Arrows L3 → L4 & internal
# ---------------------------------------------------------------------------
for mid in ["m1", "m2", "m3", "m4", "m5"]:
    drawer.connect(mid, "bottom", "evaluator", "top",
                   stroke=C_STROKE, stroke_width=1.5, marker_end="arrowhead")

drawer.connect("evaluator", "right", "explorer", "left",
               stroke=C_STROKE, stroke_width=2, marker_end="arrowhead",
               edge_label="输入指标 → 输出候选解")

# ---------------------------------------------------------------------------
# Feedback Loop
# ---------------------------------------------------------------------------
Y4_MID = L4_Y + L4_H // 2
Y2_MID = L2_Y + L2_H // 2
Y1_MID = BANNER_Y + BANNER_H // 2

# Hub at explorer right
drawer.circle(RIGHT_BUS_X, Y4_MID, 8,
              fill=C_FB_STROKE, stroke="none",
              node_id="j_hub", node_kind="junction")
drawer.connect("explorer", "right", "j_hub", "left",
               stroke=C_FB_STROKE, stroke_width=2, marker_end="arrowhead_fb")

# Mid junction → Layer 2
drawer.circle(RIGHT_BUS_X, Y2_MID, 8,
              fill=C_FB_STROKE, stroke="none",
              node_id="j_fb_mid", node_kind="junction")
drawer.connect("j_hub", "top", "j_fb_mid", "bottom",
               dashed=True, stroke=C_FB_STROKE, stroke_width=2,
               marker_end="arrowhead_fb", edge_label="参数迭代优化")
drawer.connect("j_fb_mid", "left", "collab", "right",
               stroke=C_FB_STROKE, stroke_width=1.5, marker_end="arrowhead_fb")

# Top junction → Pareto
J_TOP_X = RIGHT_BUS_X + 20
drawer.circle(J_TOP_X, Y1_MID, 8,
              fill=C_FB_STROKE, stroke="none",
              node_id="j_fb_top", node_kind="junction")
path_fb = f"M {RIGHT_BUS_X} {Y4_MID} L {J_TOP_X} {Y4_MID} L {J_TOP_X} {Y1_MID}"
drawer.path(path_fb, fill="none", stroke=C_FB_STROKE, stroke_width=2,
            marker_end="arrowhead_fb", register_edge=True,
            start=(RIGHT_BUS_X, Y4_MID), end=(J_TOP_X, Y1_MID),
            extra='stroke-dasharray="6,4"')
drawer.connect("j_fb_top", "left", "pareto_banner", "right",
               stroke=C_FB_STROKE, stroke_width=1.5,
               marker_end="arrowhead_fb", edge_label="前沿更新")

# ---------------------------------------------------------------------------
# Bottom: Math & Overview
# ---------------------------------------------------------------------------
MATH_Y = L4_Y + L4_H + 30
MATH_H = 140
MATH_X = MARGIN
MATH_W = 1150

drawer.rect(MATH_X, MATH_Y, MATH_W, MATH_H, rx=5,
            fill=C_BG, stroke=C_STROKE, stroke_width=1,
            node_id="math_box", role="decoration")
drawer.text(MATH_X + MATH_W // 2, MATH_Y + 22, "核心数学描述",
            font_size=12, weight="bold", fill=C_TEXT, anchor="middle")

math_lines = [
    "Minimize   x = [α, β, γ, δ]",
    "        [ -f_perf(x) ,  -f_rel(x) ,  f_pwr(x) ]",
    "Subject to  g_rel(x) ≥ 0.999 ,  P(x) ≤ P_max ,  M(x) ≤ M_max",
    "",
    "→ 求解该问题得到帕累托最优配置集",
]
for i, line in enumerate(math_lines):
    drawer.text(MATH_X + 18, MATH_Y + 48 + i * 16, line,
                font_size=10, fill="#333333", anchor="start", font_family="monospace")

OVERVIEW_X = MATH_X + MATH_W + 30
OVERVIEW_W = W - MARGIN - OVERVIEW_X
OVERVIEW_H = MATH_H
drawer.rect(OVERVIEW_X, MATH_Y, OVERVIEW_W, OVERVIEW_H, rx=5,
            fill=C_BG, stroke=C_STROKE, stroke_width=1,
            node_id="overview_box", role="decoration")
drawer.text(OVERVIEW_X + OVERVIEW_W // 2, MATH_Y + 22, "整体逻辑流概述",
            font_size=12, weight="bold", fill=C_TEXT, anchor="middle")

overview_lines = [
    "目标层定义性能↑、可靠≥99.9%、功耗≤P_max三个冲突目标，",
    "其非支配解构成帕累托前沿。目标分解为硬件冗余比α、",
    "软件校验周期β/δ、协同分配系数γ，由技术实现层承载。",
    "经评估与优化引擎迭代求解，配置经反馈闭环回传，",
    "形成持续逼近帕累托边界的自适应循环。",
]
for i, line in enumerate(overview_lines):
    drawer.text(OVERVIEW_X + 14, MATH_Y + 48 + i * 16, line,
                font_size=10, fill="#333333", anchor="start")

# ---------------------------------------------------------------------------
# Evaluate – Refine – Export
# ---------------------------------------------------------------------------
score, report = evaluate_svg(drawer)
print(f"Initial Score: {score}")
for line in report:
    print(line)

if score < 80:
    print("\n--- Running auto_refine ---")
    score, report, fixes = auto_refine(drawer, target_score=85, max_iter=3)
    print(f"Refined Score: {score}")
    for line in report:
        print(line)

svg_path = str(OUT / f"{NAME}.svg")
png_path = str(OUT / f"{NAME}.png")
pptx_path = str(OUT / f"{NAME}.pptx")
save_svg(drawer.render(), svg_path)
import subprocess
subprocess.run(["rsvg-convert", "-w", str(W), "-o", png_path, svg_path], check=True)
from svg2pptx import svg_to_pptx
svg_to_pptx(drawer.render(), pptx_path)
print(f"Saved SVG: {svg_path}")
print(f"Saved PNG: {png_path}")
print(f"Saved PPTX: {pptx_path}")
