# -*- coding: utf-8 -*-
"""Satellite onboard-computing adaptive fault-tolerance & self-healing architecture.

Lives next to its SVG/PNG/PPTX output under output/<timestamp>_satellite_arch/.
Re-run to regenerate the triplet in place (timestamp fixed for this generation).
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

# Output dir = this script's own directory (script + triplet co-located).
OUT = Path(__file__).resolve().parent
NAME = "satellite_arch"

# Font tiers (<=4): 22 title / 15 header / 12 sub / 10 caption
W, H = 1400, 1160
d = SVGDrawer(W, H, bg="#F2F2F2")

d.arrow_head("up", "#222222", 10, 8, 9, 4)
d.arrow_head("dn", "#444444", 10, 8, 9, 4)
d.arrow_head("loop", "#333333", 10, 8, 9, 4)
d.arrow_head("glink", "#555555", 9, 7, 8, 3.5)

LAYERS = [
    ("L4", "#FFE6CC", "#C97B3C", "L4", "卫星任务管理层", "在轨自主运行 · 顶层自愈",
     [("自主任务规划", ["依据健康·资源余量", "动态调整观测/通信/计算"]),
      ("在轨软件升级", ["星地链路传补丁", "FPGA比特流·应用重编程"]),
      ("长期健康管理 PHM", ["ML分析遥测趋势", "预测故障·预防降频切换"]),
      ("地面协同接口", ["下行遥测压缩上报", "上行指令·星地混合容错"])]),
    ("L3", "#E1D5E7", "#7B3FA2", "L3", "系统 / 星务管理层", "全局决策大脑 · 整星协同",
     [("系统级故障诊断", ["FTA · 贝叶斯网络", "区分瞬时/间歇/永久"]),
      ("多分系统协同容错", ["姿轨控·热控·电源·数传", "调模式腾挪资源"]),
      ("任务降级重构决策", ["按优先级·资源余量", "降分辨率·减计算·重规划"]),
      ("软件容错", ["恢复块 · N版本编程", "逻辑错误自动回滚"])]),
    ("L2", "#D5EFEF", "#2E8B8B", "L2", "部件与模块层", "可重构资源池 · 故障替换",
     [("模块级冗余", ["冷备 · 温备 · 热备", "主故障无缝切换"]),
      ("可重构 FPGA/MPSoC", ["动态部分重配置 DPR", "毫秒级任务重映射"]),
      ("容错存储管理", ["内存镜像 · RAID-like", "坏块/单元失效不丢数"]),
      ("局部健康监测 BMC", ["电压·电流·温度", "模块级健康度评分"])]),
    ("L1", "#DAE8FC", "#2E5AAC", "L1", "核心器件与电路层", "硬件基座 · 抗辐射第一道防线",
     [("抗辐射加固器件", ["抗辐射筛选 CPU/FPGA", "工艺版图级降 SEU/TID"]),
      ("TMR 三模冗余 · 锁步", ["CPU核/寄存器/缓存", "瞬时故障零延迟屏蔽"]),
      ("ECC · CRC 校验", ["存储自动纠单错", "总线防数据腐化"]),
      ("看门狗 · 电源管理", ["心跳超时硬件复位", "异常模块下电限流"])]),
]

# ---- title ----
d.text(W/2, 28, "星载计算平台 · 自适应容错与痊愈架构", 22, fill="#1A1A1A", weight="bold")
d.text(W/2, 52, "感知—决策—执行 自适应闭环  ·  多粒度容错(晶体管级→系统级)  ·  星地协同", 12, fill="#333333")

# ---- ground station ----
gx, gy, gw, gh = 560, 70, 280, 54
d.cloud(gx, gy, gw, gh, fill="#FFE6CC", stroke="#C97B3C", stroke_width=1.4,
        node_id="ground", node_kind="op", bbox=True)
d.text(gx+gw/2, gy+21, "地面站 · 星地协同", 12, fill="#000", weight="bold", bbox=False)
d.text(gx+gw/2, gy+40, "星上自主 + 地面辅助", 10, fill="#333", bbox=False)

# ---- layers ----
CX, CW = 170, 1060
LY0, LH, GAP = 150, 178, 12
CARD_X0, CARD_W, CARD_GAP, CARD_H = 365, 200, 20, 140
JL_X, JR_X, JR = 120, 1280, 7

def layer_y(i):
    return LY0 + i * (LH + GAP)

centers = {}
for i, (lid, fill, stroke, num, name, role, cards) in enumerate(LAYERS):
    ly = layer_y(i)
    cy = ly + LH/2
    centers[lid] = cy
    d.rect(CX, ly, CW, LH, rx=10, ry=10, fill=fill, stroke=stroke,
           stroke_width=1.6, node_id=lid, node_kind="layer", bbox=True, opacity=0.55)
    lx = CX + 95
    d.text(lx, ly + 40, num, 22, fill="#1A1A1A", weight="bold", bbox=False)
    d.text(lx, ly + 74, name, 15, fill="#1A1A1A", weight="bold", bbox=False)
    d.text(lx, ly + 96, role, 10, fill="#333333", bbox=False)
    for j, (title, desc) in enumerate(cards):
        cxp = CARD_X0 + j * (CARD_W + CARD_GAP)
        cyp = ly + 24
        d.rect(cxp, cyp, CARD_W, CARD_H, rx=7, ry=7, fill="#FFFFFF",
               stroke=stroke, stroke_width=1.2, bbox=True)
        d.text(cxp + CARD_W/2, cyp + 22, title, 12, fill="#000", weight="bold", bbox=False)
        for k, ln in enumerate(desc):
            d.text(cxp + CARD_W/2, cyp + 50 + k*17, ln, 10, fill="#333", bbox=False)

# ---- junctions ----
for i, (lid, *_rest) in enumerate(LAYERS):
    cy = centers[lid]
    d.circle(JL_X, cy, JR, fill="#FFFFFF", stroke="#222", stroke_width=1.4,
             node_id="s"+lid, node_kind="junction", bbox=False)
    d.circle(JR_X, cy, JR, fill="#FFFFFF", stroke="#444", stroke_width=1.4,
             node_id="c"+lid, node_kind="junction", bbox=False)
    d.connect("s"+lid, "right", lid, "left",  stroke="#222", stroke_width=1.2, marker_end=None)
    d.connect("c"+lid, "left",  lid, "right", stroke="#444", stroke_width=1.2, marker_end=None)

# ---- up-sensing flow (solid) ----
order = ["L1", "L2", "L3", "L4"]
sense_lbl = {"L1->L2": "① 故障事件上报", "L2->L3": "② 健康摘要上送", "L3->L4": "③ 重构决策上报"}
for a, b in zip(order, order[1:]):
    d.connect("s"+a, "top", "s"+b, "bottom", stroke="#222222", stroke_width=2.0, marker_end="up")
    midy = (centers[a] + centers[b]) / 2
    d.text(66, midy, sense_lbl[f"{a}->{b}"], 10, fill="#222", weight="bold", bbox=False)
d.text(80, 176, "上行感知流", 12, fill="#222", weight="bold", bbox=False)
d.text(80, 192, "Sensing  ↑", 10, fill="#555", bbox=False)

# ---- down-control flow (dashed) ----
rorder = list(reversed(order))
ctrl_lbl = {"L4->L3": "① 任务调整/重构许可", "L3->L2": "② 重构方案拆解", "L2->L1": "③ 配置切换执行"}
for a, b in zip(rorder, rorder[1:]):
    d.connect("c"+a, "bottom", "c"+b, "top", stroke="#444444", stroke_width=2.0,
              marker_end="dn", dashed=True)
    midy = (centers[a] + centers[b]) / 2
    d.text(1336, midy, ctrl_lbl[f"{a}->{b}"], 10, fill="#444", weight="bold", bbox=False)
d.text(1320, 176, "下行控制流", 12, fill="#444", weight="bold", bbox=False)
d.text(1320, 192, "Control  ↓", 10, fill="#555", bbox=False)

# ---- ground <-> L4 (neutral, dark hues appear only as strokes) ----
d.connect("ground", "bottom", "L4", "top", stroke="#555555", stroke_width=1.6,
          marker_end="glink", dashed=True)
d.text(722, 138, "星地链路", 10, fill="#555555", anchor="start", bbox=False)

# ---- closed loop ----
band_y = 932
d.text(W/2, band_y, "自适应痊愈闭环 · 自感知 / 自修复 / 自优化",
       15, fill="#1A1A1A", weight="bold", bbox=False)
d.text(W/2, band_y + 20, "监测 → 诊断 → 决策 → 执行 → 验证  (持续循环至故障隔离且系统恢复稳定)",
       12, fill="#333", bbox=False)

steps = [("监测", "Monitor"), ("诊断", "Diagnose"), ("决策", "Decide"),
         ("执行", "Execute"), ("验证", "Verify")]
n, nw, nh, ngap = 5, 176, 54, 22
total = n*nw + (n-1)*ngap
nx0 = (W - total) / 2
ny = 985
node_ids = []
for k, (zh, en) in enumerate(steps):
    x = nx0 + k * (nw + ngap)
    nid = "cl%d" % k
    node_ids.append(nid)
    d.rect(x, ny, nw, nh, rx=8, ry=8, fill="#DAE8FC", stroke="#2E5AAC",
           stroke_width=1.4, node_id=nid, node_kind="op", bbox=True)
    d.text(x + nw/2, ny + 21, zh, 15, fill="#000", weight="bold", bbox=False)
    d.text(x + nw/2, ny + 41, en, 10, fill="#333", bbox=False)

for k in range(n - 1):
    d.connect(node_ids[k], "right", node_ids[k+1], "left",
              stroke="#333", stroke_width=1.8, marker_end="loop")

# return arc: orthogonal U (2 bends)
vbot = d.nodes[node_ids[-1]].edge_point("bottom")
mbot = d.nodes[node_ids[0]].edge_point("bottom")
drop = 1108
arc = (f"M{vbot[0]},{vbot[1]} L{vbot[0]},{drop} L{mbot[0]},{drop} L{mbot[0]},{mbot[1]}")
d.path(arc, fill="none", stroke="#333", stroke_width=1.8, marker_end="loop",
       register_edge=True, start=vbot, end=mbot, extra='stroke-dasharray="6,3"')
d.text(W/2, 1128, "若星上无法恢复 → 进入安全模式，等待地面干预", 10, fill="#555555",
       style="italic", bbox=False)

# ---- evaluate + write triplet next to this script ----
score, report = evaluate_svg(d)
print("SCORE:", score)
for line in report:
    print(line)

svg_path = OUT / f"{NAME}.svg"
png_path = OUT / f"{NAME}.png"
pptx_path = OUT / f"{NAME}.pptx"

save_svg(d.render(), str(svg_path))
rasterize_svg(svg_path, png_path, W)
from svg2pptx import svg_to_pptx
svg_to_pptx(str(svg_path), str(pptx_path))
print(f"SAVED triplet -> {OUT}")
