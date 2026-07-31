# -*- coding: utf-8 -*-
"""Satellite LLM-inference multi-objective optimization framework (perf/rel/power)."""
import sys
import re as _re
import shutil
import subprocess
import tempfile
from pathlib import Path


import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg

def render_latex(tex):
    """Render TeX math to clean inline-path SVG via latex+dvisvgm.
    Returns (inner_svg, minx, miny, vbw, vbh) in dvisvgm's pt coord space."""
    wd = tempfile.mkdtemp(prefix="mtex_")
    (Path(wd) / "f.tex").write_text(
        r"\documentclass[border=2pt,preview]{standalone}"
        r"\usepackage{amsmath,amssymb}\begin{document}" + tex + r"\end{document}")
    subprocess.run(["latex", "-interaction=nonstopmode", "f.tex"], cwd=wd,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", "f.dvi", "-o", "f.svg"],
                   cwd=wd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    svg = (Path(wd) / "f.svg").read_text()
    shutil.rmtree(wd)
    hdr = _re.search(r"<svg([^>]*)>", svg).group(1)
    vb = _re.search(r"viewBox='([^']+)'", hdr).group(1).split()
    minx, miny, vbw, vbh = map(float, vb)
    inner = _re.search(r"<svg[^>]*>(.*)</svg>", svg, _re.S).group(1).strip()
    # Resolve <use x= y= xlink:href='#glyph'/> -> inline <path d=.. transform=translate(x,y)/>.
    # dvisvgm emits glyph defs as <path id='gN-M' d='D'/> + <use> refs; both rsvg (needs xlink
    # ns) and svg2pptx (no <use> handling) break on unresolved refs, so inline them.
    glyph_d = {}
    for m in _re.finditer(r"<path\s+([^>]*)/>", inner):
        attrs = m.group(1)
        gid = _re.search(r"\bid='([^']+)'", attrs)
        dd = _re.search(r"\bd='([^']*)'", attrs)
        if gid and dd:
            glyph_d[gid.group(1)] = dd.group(1)
    def _inline_use(m):
        a = m.group(1)
        gid = _re.search(r"xlink:href='#([^']+)'", a)
        if not gid or gid.group(1) not in glyph_d:
            return ""           # unresolved ref -> drop
        x = _re.search(r"x='([^']*)'", a); y = _re.search(r"y='([^']*)'", a)
        txu = x.group(1) if x else "0"; tyu = y.group(1) if y else "0"
        return f"<path d='{glyph_d[gid.group(1)]}' transform='translate({txu} {tyu})'/>"
    inner = _re.sub(r"<use ([^/]*)/>", _inline_use, inner)
    inner = _re.sub(r"<defs>.*?</defs>", "", inner, flags=_re.S)   # drop now-empty glyph defs
    return inner, minx, miny, vbw, vbh

def embed_latex(drawer, tex, tx, ty, target_w, color="#1A1A1A"):
    """Place a rendered LaTeX formula with bbox top-left at (tx,ty), scaled to target_w px.
    Paths carry no explicit fill -> wrapper <g fill=color> makes children inherit it.
    Affine = translate(tx,ty) scale(s) translate(-minx,-miny) (svg2pptx composes it)."""
    inner, minx, miny, vbw, vbh = render_latex(tex)
    s = target_w / vbw
    drawer.add_element(
        f'<g fill="{color}" transform="translate({tx} {ty}) scale({s}) '
        f'translate({-minx} {-miny})">{inner}</g>', bbox=None)
    return vbw * s, vbh * s   # rendered w,h in px
from evaluator import evaluate_svg

OUT = Path(__file__).resolve().parent
NAME = "opt_framework"

# Font tiers (<=4): 22 title / 15 header / 12 body / 10 caption
W, H = 1680, 990
d = SVGDrawer(W, H, bg="#FAFAFA")

d.arrow_head("arr", "#444444", 10, 8, 9, 4)
d.arrow_head("farr", "#5B9D5B", 11, 9, 10, 4.5)   # green feedback (reuses perf accent)
# palette: 8 accents = 3 objective pairs (6) + L2 blue + L4 purple
GN_S, GN_F = "#5B9D5B", "#D5E8D4"   # 性能 green
RD_S, RD_F = "#C76B5E", "#F8CECC"   # 可靠 red
YL_S, YL_F = "#C9A23E", "#F5DD95"   # 功耗 yellow (L<0.8)
BL_S = "#5688CF"                    # L2 blue (L>0.2)
PP_S = "#A065C4"                    # L4 purple (L>0.2)
GRY = "#555555"                     # neutral (L3 / arrows / pareto)
# ===================== TITLE =====================
d.text(W/2, 30, "星载大模型推理 · 性能–可靠性–功耗 多目标优化框架",
       22, fill="#1A1A1A", weight="bold")
d.text(W/2, 55, "软硬件协同设计范式  ·  逼近帕累托最优前沿  ·  80亿参数模型在轨服务",
       12, fill="#333333")

# ===================== L1 : OPTIMIZATION OBJECTIVES =====================
objs = [("性能 Performance", "推理吞吐量 ↑", "极致算效", GN_F, GN_S, "obj_p"),
        ("可靠性 Reliability", "任务可靠度 ≥ 99.9%", "刚性约束", RD_F, RD_S, "obj_r"),
        ("功耗 Power", "≤ 星载功耗预算", "资源天花板", YL_F, YL_S, "obj_w")]
OW, OH, OY = 290, 70, 78
ox = [215, 555, 895]
for i, (t, s, b, f, st, nid) in enumerate(objs):
    x = ox[i]
    d.rect(x, OY, OW, OH, rx=10, ry=10, fill=f, stroke=st, stroke_width=1.6,
           node_id=nid, node_kind="op", bbox=True)
    d.text(x + OW/2, OY + 22, t, 15, fill="#1A1A1A", weight="bold", bbox=False)
    d.text(x + OW/2, OY + 44, s, 12, fill="#222", bbox=False)
    d.text(x + OW/2, OY + 62, b, 10, fill=st, weight="bold", bbox=False)

# conflict arrows (dashed) between adjacent objectives
d.connect("obj_p", "right", "obj_r", "left", stroke=RD_S, stroke_width=1.4,
          marker_end="arr", dashed=True)
d.connect("obj_r", "right", "obj_w", "left", stroke=RD_S, stroke_width=1.4,
          marker_end="arr", dashed=True)
d.text((ox[0]+OW + ox[1])/2, OY - 6, "冲突", 10, fill=RD_S, weight="bold", bbox=False)
d.text((ox[1]+OW + ox[2])/2, OY - 6, "冲突", 10, fill=RD_S, weight="bold", bbox=False)

# ===================== PARETO FRONTIER (refined mini-plot, decoration) =====================
import random as _rnd
_rnd.seed(7)
PY1, PH = 160, 96                       # band 160..256 (taller for real plot structure)
PLX, PRX = 250, 1155                    # plot x-range
PTY, PBY = PY1 + 30, PY1 + PH - 10      # curve top/bottom y (190..246)
def front_y(x):                         # convex decreasing frontier (concave-up)
    t = (x - PLX) / (PRX - PLX)
    return PTY + (PBY - PTY) * (t ** 0.55)
# band background + subtle feasible-region fill under the curve
d.add_element(
    f'<rect x="215" y="{PY1}" width="970" height="{PH}" rx="8" ry="8" '
    f'fill="#FFFFFF" fill-opacity="0.65" stroke="#CCCCCC" stroke-width="1" '
    f'data-graph-role="decoration"/>', bbox=None)
# feasible-region polygon (light green) under the frontier
feas_pts = " ".join(f"{x},{front_y(x)}" for x in range(int(PLX), int(PRX)+1, 18))
feas_poly = (f"{PLX},{PBY} " + feas_pts + f" {PRX},{PBY}")
d.add_element(
    f'<polygon points="{feas_poly}" fill="{GN_F}" fill-opacity="0.28" stroke="none" '
    f'data-graph-role="decoration"/>', bbox=None)
# faint objective axes (left = perf, bottom = power)
d.add_element(f'<line x1="{PLX-6}" y1="{PTY-4}" x2="{PLX-6}" y2="{PBY+4}" '
              f'stroke="#999999" stroke-width="1" data-graph-role="decoration"/>', bbox=None)
d.add_element(f'<line x1="{PLX-10}" y1="{PBY}" x2="{PRX+10}" y2="{PBY}" '
              f'stroke="#999999" stroke-width="1" data-graph-role="decoration"/>', bbox=None)
# smooth frontier curve (dense polyline, decoration -> not bend-checked)
curve_d = "M " + " L ".join(f"{x},{front_y(x):.1f}" for x in range(int(PLX), int(PRX)+1, 12))
d.add_element(
    f'<path d="{curve_d}" fill="none" stroke="{GN_S}" stroke-width="2.4" '
    f'stroke-linecap="round" data-graph-role="decoration"/>', bbox=None)
# non-dominated solutions ON the frontier (12 green dots)
nd_x = [PLX + i*(PRX-PLX)/11 for i in range(12)]
for x in nd_x:
    d.add_element(
        f'<circle cx="{x:.1f}" cy="{front_y(x):.1f}" r="4.5" fill="{GN_S}" '
        f'stroke="#FFFFFF" stroke-width="1.4" data-graph-role="decoration"/>', bbox=None)
# dominated solutions scattered in the feasible region above the curve (gray, small)
for _ in range(22):
    x = _rnd.uniform(PLX+20, PRX-10)
    y = _rnd.uniform(front_y(x)+8, PBY-3)      # below curve (screen) = dominated
    d.add_element(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#AAAAAA" fill-opacity="0.55" '
        f'stroke="none" data-graph-role="decoration"/>', bbox=None)
# direction arrow (帕累托改进 ↘) in the gap between L1->L2 arrows (x 420-660)
d.add_element(
    f'<path d="M 430,{PTY+6} L 640,{PBY-6}" stroke="{GRY}" stroke-width="1.4" '
    f'fill="none" stroke-dasharray="4,3" marker-end="url(#arr)" '
    f'data-graph-role="decoration"/>', bbox=None)
d.add_element(
    f'<text x="535" y="{PTY-2}" font-family="Arial" font-size="10" font-weight="bold" '
    f'fill="{GRY}" text-anchor="middle" data-graph-role="decoration">帕累托改进 ↘</text>', bbox=None)
# title (left, clear of arrow at x=360) + axis labels (clear of arrows)
d.add_element(
    f'<text x="228" y="{PY1+18}" font-family="Arial" font-size="12" font-weight="bold" '
    f'fill="{GRY}" data-graph-role="decoration">帕累托前沿</text>', bbox=None)
d.add_element(
    f'<text x="228" y="{PY1+32}" font-family="Arial" font-size="10" '
    f'fill="#888888" data-graph-role="decoration">Pareto Frontier</text>', bbox=None)
d.add_element(
    f'<text x="248" y="{PBY+14}" font-family="Arial" font-size="10" '
    f'fill="#888888" data-graph-role="decoration">功耗 f_pwr →</text>', bbox=None)
d.add_element(
    f'<text x="{PLX+4}" y="{PTY-8}" font-family="Arial" font-size="10" '
    f'fill="#888888" text-anchor="end" data-graph-role="decoration">↑ 性能</text>', bbox=None)
# legend (right, clear of arrow at x=1040)
d.add_element(
    f'<circle cx="1085" cy="{PY1+18}" r="4" fill="{GN_S}" stroke="#FFFFFF" '
    f'stroke-width="1" data-graph-role="decoration"/>', bbox=None)
d.add_element(
    f'<text x="1094" y="{PY1+21}" font-family="Arial" font-size="10" fill="{GRY}" '
    f'data-graph-role="decoration">非支配解</text>', bbox=None)
d.add_element(
    f'<circle cx="1085" cy="{PY1+34}" r="2.6" fill="#AAAAAA" fill-opacity="0.55" '
    f'stroke="none" data-graph-role="decoration"/>', bbox=None)
d.add_element(
    f'<text x="1094" y="{PY1+37}" font-family="Arial" font-size="10" fill="{GRY}" '
    f'data-graph-role="decoration">支配解</text>', bbox=None)
# ===================== L2 : DECISION VARIABLES (3 domains) =====================
DVY, DVH = 300, 150
domains = [
    ("软件域 · 决策变量 β / δ", ["ABFT 校验周期 β", "检查点保存频率 δ", "动态重试触发阈值"],
     "← 性能 / 可靠性", "dv_s"),
    ("协同域 · 决策变量 γ", ["关键/非关键层容错分配系数", "跨层错误传播抑制策略", "软硬件冗余预算分配"],
     "← 可靠 / 功耗", "dv_c"),
    ("硬件域 · 决策变量 α", ["TMR 三模冗余复制比例", "抗辐射芯片选型策略", "存储 ECC 使能策略"],
     "← 性能 / 可靠 / 功耗", "dv_h"),
]
for i, (hdr, items, badge, nid) in enumerate(domains):
    x = ox[i]
    d.rect(x, DVY, OW, DVH, rx=8, ry=8, fill="#FFFFFF", stroke=BL_S,
           stroke_width=1.5, node_id=nid, node_kind="op", bbox=True)
    d.text(x + OW/2, DVY + 14, hdr, 12, fill=BL_S, weight="bold", bbox=False)
    for k, it in enumerate(items):
        d.text(x + 14, DVY + 46 + k*24, "· " + it, 12, fill="#222", anchor="start", bbox=False)
    d.text(x + OW/2, DVY + DVH - 12, badge, 10, fill=BL_S, weight="bold", bbox=False)

# ---- L1 -> L2 : objective decomposition ----
d.connect("obj_p", "bottom", "dv_s", "top", stroke=BL_S, stroke_width=1.6, marker_end="arr")
d.connect("obj_r", "bottom", "dv_c", "top", stroke=BL_S, stroke_width=1.6, marker_end="arr")   # 可靠性 → 协同域
d.connect("obj_w", "bottom", "dv_h", "top", stroke=BL_S, stroke_width=1.6, marker_end="arr")   # 功耗 → 硬件域
d.text(120, 240, "目标分解 ↓", 10, fill=BL_S, weight="bold", bbox=False)

# ===================== L3 : TECHNICAL IMPLEMENTATION (5 modules) =====================
# module centers widened for >=14px gap; reordered to cluster under swapped
# domains (软件→①② | 协同→④⑤ | 硬件→③) so L2->L3 arrows stay local, no crossing.
mc = [250, 470, 700, 940, 1140]
mtops, TH, TW = 500, 115, 170
def mx(i):
    return mc[i]
mods = [("① 抗辐射加固硬件", "辐射加固器件 / 版图", "[硬件域 α]", "t0"),
        ("② 算法级容错 ABFT", "ABFT · RetryTrigger", "[软件β / 协同γ]", "t1"),
        ("④ 检查点与恢复", "Checkpoint · 动态回滚", "[软件域 β]", "t3"),
        ("⑤ 在轨软件更新 OTA", "比特流 / 固件重编程", "[硬件α / 协同γ]", "t4"),
        ("③ MLIR 异构编译", "多层次IR · 软硬桥接", "[协同域 γ]", "t2")]
for i, (t, s, tag, nid) in enumerate(mods):
    x = mx(i) - TW/2
    d.rect(x, mtops, TW, TH, rx=7, ry=7, fill="#FFFFFF", stroke=GRY,
           stroke_width=1.3, node_id=nid, node_kind="op", bbox=True)
    d.text(mx(i), mtops + 26, t, 12, fill="#1A1A1A", weight="bold", bbox=False)
    d.text(mx(i), mtops + 52, s, 10, fill="#444", bbox=False)
    d.text(mx(i), mtops + 92, tag, 10, fill=BL_S, weight="bold", bbox=False)

# ---- L2 -> L3 : decision vars -> tech ----
d.connect("dv_s", "bottom", "t0", "top", stroke=GRY, stroke_width=1.4, marker_end="arr")
d.connect("dv_s", "bottom", "t1", "top", stroke=GRY, stroke_width=1.4, marker_end="arr")
d.connect("dv_h", "bottom", "t2", "top", stroke=GRY, stroke_width=1.4, marker_end="arr")
d.connect("dv_c", "bottom", "t3", "top", stroke=GRY, stroke_width=1.4, marker_end="arr")
d.connect("dv_c", "bottom", "t4", "top", stroke=GRY, stroke_width=1.4, marker_end="arr")
d.text(120, 460, "技术承载 ↓", 10, fill=GRY, weight="bold", bbox=False)

# ===================== L3 -> L4 : tech -> evaluator (fan-in, monotonic landing) =====================
EY, EH = 680, 110
EX, EW_eval = 215, 600   # evaluator spans x 215..815
landings = [250, 410, 570, 700, 790]
for i, (_, _, _, nid) in enumerate(mods):     # visual order t0,t1,t3,t4,t2
    sx = mc[i]
    d.line(sx, mtops + TH, landings[i], EY, stroke=GRY, stroke_width=1.3,
           marker_end="arr", register_edge=True)
d.text(120, 635, "汇入评估 ↓", 10, fill=GRY, weight="bold", bbox=False)

# ===================== L4 : EVALUATION & OPTIMIZATION ENGINE =====================
# evaluator (left)
d.rect(EX, EY, EW_eval, EH, rx=10, ry=10, fill="#FFFFFF", stroke=PP_S,
       stroke_width=1.6, node_id="eval", node_kind="op", bbox=True)
d.text(EX + EW_eval/2, EY + 14, "多目标评估器  Multi-Objective Evaluator", 15,
       fill=PP_S, weight="bold", bbox=False)
d.multiline_text(EX + EW_eval/2, EY + 48,
                 ["故障注入 · 模拟辐射单粒子效应", "性能监测 · 推理延迟 / 吞吐量",
                  "功耗测量 · 实时电流 / 电压采样"], 12, fill="#222")
# exploration engine (right)
GX2, GW2 = 855, 330
d.rect(GX2, EY, GW2, EH, rx=10, ry=10, fill="#FFFFFF", stroke=PP_S,
       stroke_width=1.6, node_id="dse", node_kind="op", bbox=True)
d.text(GX2 + GW2/2, EY + 14, "设计空间探索引擎", 15, fill=PP_S, weight="bold", bbox=False)
d.multiline_text(GX2 + GW2/2, EY + 48,
                 ["贝叶斯优化 / 多目标进化", "帕累托排序 · 非支配筛选", "约束边界搜索"], 12, fill="#222")

# evaluator <-> engine (two offset arrows + labels clear of lines)
d.line(EX + EW_eval, EY + 45, GX2, EY + 45, stroke=GRY, stroke_width=1.5,
       marker_end="arr", register_edge=True)
d.line(GX2, EY + 75, EX + EW_eval, EY + 75, stroke=PP_S, stroke_width=1.5,
       marker_end="farr", register_edge=True)
d.text((EX + EW_eval + GX2)/2, EY + 60, "实测指标 ↔ 候选解", 10, fill=GRY, bbox=False)

# ===================== FEEDBACK LOOP (right channel x=1260, clear of t4<=1225) =====================
CHX = 1245
dv_ry = DVY + DVH/2               # decision-var row mid-y (shared by all domains)
pf_y = PY1 + PH/2                 # pareto band mid y
# junctions (visible anchors)
d.circle(CHX, EY + 55, 5, fill=GN_S, stroke="#FFFFFF", stroke_width=1.5,
         node_id="fb1", node_kind="junction", bbox=False)
d.circle(1185, pf_y, 6, fill=GN_S, stroke="#FFFFFF", stroke_width=1.5,
         node_id="pf", node_kind="junction", bbox=False)
# path1: engine -> fb1 -> up -> dv_h (参数迭代). After the 硬件/协同 swap dv_h is the
# rightmost domain, so the feedback lands on it — the label covers all α/β/γ/δ.
dv_h_rx = d.nodes["dv_h"].edge_point("right")[0]
p1 = (f"M{GX2+GW2},{EY+55} L{CHX-5},{EY+55} L{CHX-5},{dv_ry} L{dv_h_rx},{dv_ry}")
d.path(p1, fill="none", stroke=GN_S, stroke_width=2.0, marker_end="farr",
       register_edge=True, start=(GX2+GW2, EY+55), end=(dv_h_rx, dv_ry),
       extra='stroke-dasharray="7,4"')
d.text(CHX + 45, (EY + dv_ry) / 2, "参数迭代", 10, fill=GN_S, weight="bold", anchor="start", bbox=False)
d.text(CHX + 45, (EY + dv_ry) / 2 + 14, "优化 α/β/γ/δ", 10, fill=GN_S, anchor="start", bbox=False)
# path2: fb1 -> up -> pf (前沿更新), orthogonal at CHX then left to pf
p2 = (f"M{CHX-5},{EY+50} L{CHX-5},{pf_y} L1191,{pf_y}")
d.path(p2, fill="none", stroke=GN_S, stroke_width=2.0, marker_end="farr",
       register_edge=True, start=(CHX-5, EY+50), end=(1191, pf_y),
       extra='stroke-dasharray="7,4"')
d.text(CHX + 45, (EY + pf_y) / 2, "前沿更新", 10, fill=GN_S, weight="bold", anchor="start", bbox=False)
d.text(CHX + 45, (EY + pf_y) / 2 - 14, "反馈闭环", 10, fill=GN_S, weight="bold", anchor="start", bbox=False)
# ===================== MATH FORMULATION (bottom) =====================
MY, MH2 = 815, 135                       # band 815..950 (taller -> formula breathes)
d.rect(215, MY, 970, MH2, rx=8, ry=8, fill="#F0F0F0", stroke="#BBBBBB",
       stroke_width=1, bbox=False, role="decoration")
d.text(700, MY + 18, "多目标优化问题形式化", 15, fill="#1A1A1A", weight="bold", bbox=False)
# Rendered LaTeX (real math typography via latex+dvisvgm -> clean inline paths,
# PPTX-editable as freeforms). Vertically CENTER the ink in the band.
tex = (r"$\displaystyle\min_{\mathbf{x}=[\alpha,\beta,\gamma,\delta]}"
       r"\big[-f_{\mathrm{perf}}(\mathbf{x}),\;-f_{\mathrm{rel}}(\mathbf{x}),\;f_{\mathrm{pwr}}(\mathbf{x})\big]"
       r"\quad\mathrm{s.t.}\quad g_{\mathrm{rel}}\geq 0.999,\;P\leq P_{\max},\;M\leq M_{\max}$")
inner, minx, miny, vbw, vbh = render_latex(tex)
s = 780 / vbw                              # scale to ~780px wide
fw, fh = vbw * s, vbh * s                  # rendered ink w,h in px
tx = (215 + 970) / 2 - fw / 2             # horizontally centered in band
ty = MY + MH2 / 2 - fh / 2               # vertically centered in band (ink, not viewBox)
d.add_element(
    f'<g fill="#1A1A1A" transform="translate({tx} {ty}) scale({s}) '
    f'translate({-minx} {-miny})">{inner}</g>', bbox=None)
d.text((215 + 970) / 2, MY + MH2 - 12,
       "→ 求解该多目标问题  ⟹  得到帕累托最优配置集（逼近非支配前沿）",
       12, fill=PP_S, weight="bold", bbox=False)

# footer
d.text(W/2, 972, "目标驱动 → 配置映射 → 技术支撑 → 评估反馈  ·  持续逼近帕累托边界的自适应闭环",
       10, fill="#555", style="italic", bbox=False)

# ===================== EVALUATE + WRITE TRIPLET =====================
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
