# -*- coding: utf-8 -*-
"""天地一体化卫星系统架构分层图 (Integrated Space-Ground Satellite Architecture).

Bottom = ground, top = deep space. Five vertical layers + a horizontal
functional color code (blue=comm, green=nav, orange=sensing/research,
slate=manned/station). Concrete validated edges: LEO constellation mesh and
the LEO->GEO-relay->ground data chain. Broadcast/conceptual flows (MEO
coverage beams, ground uplink/downlink) are drawn as decoration.

Palette idiom: pastel fill + same-family dark stroke per hue; all text and
arrowheads neutral black so no dark/light clash appears in either channel.
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
NAME = "satellite_arch"

# ---- Palette: 4 hue families (light fill + dark stroke) + neutrals -----------
BLUE, BLUE_F = "#2563EB", "#DBEAFE"       # communication / data links
GREEN, GREEN_F = "#16A34A", "#DCFCE7"     # navigation
ORANGE, ORANGE_F = "#EA580C", "#FFEDD5"   # sensing / research
SLATE, SLATE_F = "#475569", "#E2E8F0"     # manned / structural
BLACK = "#000000"                         # all text + arrowheads (neutral)
LINE = "#A8A8A8"                          # neutral scale / divider lines
BAND_A, BAND_B = "#F6F6F6", "#EFEFEF"     # neutral layer bands
EARTH_F, EARTH_S = "#E4E4E4", "#9A9A9A"   # neutral earth

F_TITLE, F_HEAD, F_BODY = 22, 15, 12

W, Hh = 1400, 1180
d = SVGDrawer(W, Hh, bg="#FFFFFF")
d.arrow_head("ah", BLACK)   # single neutral arrowhead


def band(x, y, w, h, fill):
    d.rect(x, y, w, h, rx=10, ry=10, fill=fill, stroke="none", opacity=0.9,
           role="background")


def layer_header(x, y, text):
    d.text(x, y, text, F_HEAD, fill=BLACK, anchor="start", weight="bold", bbox=False)


def sat_circle(cx, cy, r, fill, stroke, nid, sw=1.6):
    d.circle(cx, cy, r, fill=fill, stroke=stroke, stroke_width=sw,
             node_id=nid, node_kind="op")


def sat_square(cx, cy, s, fill, stroke, nid, sw=1.6):
    d.rect(cx - s / 2, cy - s / 2, s, s, rx=2, ry=2, fill=fill, stroke=stroke,
           stroke_width=sw, node_id=nid, node_kind="op")


def sat_triangle(cx, cy, r, fill, stroke, nid, sw=1.6):
    pts = f'{cx},{cy - r} {cx - r},{cy + r * 0.8} {cx + r},{cy + r * 0.8}'
    d.add_element(
        f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{sw}" stroke-linejoin="round" />', None)
    d.register_node(nid, cx - r, cy - r, 2 * r, 2 * r, kind="op", visible=True)
    d._record_color(fill, stroke)


def lbl(cx, cy, text, anchor="middle", weight="normal"):
    d.text(cx, cy, text, F_BODY, fill=BLACK, anchor=anchor, weight=weight, bbox=False)


# ---------------- Title + subtitle ----------------
d.text(W / 2, 34, "天地一体化卫星系统架构分层图", F_TITLE, fill=BLACK, weight="bold")
d.text(W / 2, 62, "涵盖轨道高度 · 卫星分类 · 数据流向", F_BODY, fill=BLACK)

# ---------------- Legend (centered row below subtitle) ----------------
LY = 88
legend = [(BLUE, BLUE_F, "通信类（含中继）"), (GREEN, GREEN_F, "导航类"),
          (ORANGE, ORANGE_F, "遥感 / 科研类"), (SLATE, SLATE_F, "载人 / 空间站")]
item_w = 168
lx0 = (W - item_w * len(legend)) / 2
for i, (dark, light, t) in enumerate(legend):
    x = lx0 + i * item_w
    d.circle(x, LY, 7, fill=light, stroke=dark, stroke_width=1.4, role="legend")
    d.text(x + 14, LY, t, F_BODY, fill=BLACK, anchor="start", bbox=False)

# ---------------- Layer bands (gapped, tracked) ----------------
CX0, CX1 = 150, 1350
BW = CX1 - CX0
bands = [
    (125, 115, "⑤ 深空探测 / 拉格朗日点层", BAND_B),
    (268, 120, "④ 地球静止轨道 GEO / 倾斜同步 IGSO", BAND_A),
    (420, 125, "③ 中地球轨道 MEO · 导航定位层", BAND_B),
    (580, 210, "② 低地球轨道 LEO · 近地密集层（200–2,000 km）", BAND_A),
    (865, 80, "① 地面支撑层", BAND_B),
]
for y, h, name, fill in bands:
    band(CX0, y, BW, h, fill)
    layer_header(CX0 + 14, y + 20, name)

# ---------------- Left altitude scale ----------------
SX = 108
d.line(SX, 120, SX, 960, stroke=LINE, stroke_width=1.5, role="decoration")
alt = [(180, ["L1 / L2 点", "百万公里级"]),
       (320, ["≈35,786 km", "GEO 同步高度"]),
       (480, ["≈20,200 km", "MEO 导航"]),
       (590, ["2,000 km"]),
       (780, ["200 km"]),
       (905, ["0 km 地面"])]
for ty, lines in alt:
    d.line(SX - 5, ty, SX + 5, ty, stroke=LINE, stroke_width=1.5, role="decoration")
    for j, ln in enumerate(lines):
        d.text(SX - 10, ty - (len(lines) - 1) * 7 + j * 14, ln,
               F_BODY, fill=BLACK, anchor="end", bbox=False)
d.text(SX, 105, "轨道高度", F_BODY, fill=BLACK, weight="bold", bbox=False)

# ---------------- Layer 5 — Deep space ----------------
Y5 = 185
for cx, t, nid in [(300, "韦伯望远镜", "ds1"), (470, "爱因斯坦探针", "ds2"),
                   (640, "太阳观测卫星", "ds3")]:
    sat_triangle(cx, Y5, 14, ORANGE_F, ORANGE, nid)
    lbl(cx, Y5 - 26, t)
for cx, t in [(860, "L1"), (980, "L2")]:
    d.add_element(
        f'<polygon points="{cx},{Y5-9} {cx+9},{Y5} {cx},{Y5+9} {cx-9},{Y5}" '
        f'fill="{SLATE_F}" stroke="{SLATE}" stroke-width="1.4"/>', None)
    lbl(cx, Y5 - 26, t)
lbl(1340, Y5 - 6, "大椭圆 / 闪电轨道", anchor="end")
lbl(1340, Y5 + 14, "地日 · 地月 L1 / L2 拉格朗日点", anchor="end")

# ---------------- Layer 4 — GEO / IGSO ----------------
Y4 = 345
d.add_element(
    f'<path d="M 175,{Y4+18} Q {(175+1145)/2},{Y4-30} 1145,{Y4+18}" '
    f'fill="none" stroke="{LINE}" stroke-width="1.6" stroke-dasharray="5,4"/>', None)
geo = [("geo_comm1", 360, Y4 + 4, BLUE_F, BLUE, "通信广播 · 亚太"),
       ("geo_met", 540, Y4 - 6, ORANGE_F, ORANGE, "气象预警 · 风云"),
       ("geo_warn", 720, Y4 - 10, ORANGE_F, ORANGE, "战略预警 · 红外"),
       ("geo_comm2", 900, Y4 - 6, BLUE_F, BLUE, "通信广播 · 广电"),
       ("geo_relay", 1230, Y4 + 4, BLUE_F, BLUE, "数据中继 · 天链")]
for nid, cx, cy, f, s, _ in geo:
    sat_square(cx, cy, 30, f, s, nid)
for nid, cx, cy, f, s, t in geo:
    lbl(cx, cy - 24, t)

# ---------------- Layer 3 — MEO navigation ----------------
meo = [("meo1", 300, 490, "北斗"), ("meo2", 460, 508, "GPS"),
       ("meo3", 620, 490, "Galileo"), ("meo4", 780, 508, "北斗"),
       ("meo5", 940, 490, "GPS"), ("meo6", 1100, 508, "Galileo")]
for nid, cx, cy, name in meo:
    sat_circle(cx, cy, 15, GREEN_F, GREEN, nid)
    lbl(cx, cy - 28, name)
lbl(700, 435, "导航定位星座（3–6 轨道面均匀分布）")
for nid, cx, cy, name in meo[::2]:  # top row only: coverage beams stay in band
    d.add_element(
        f'<polygon points="{cx-18},{cy+15} {cx+18},{cy+15} {cx},{cy+54}" '
        f'fill="{GREEN_F}" fill-opacity="0.55" stroke="{GREEN}" stroke-width="0.8" '
        f'stroke-dasharray="3,3"/>', None)
lbl(300, 558, "导航覆盖波束", anchor="start")

# ---------------- Layer 2 — LEO ----------------
comm_x = [220, 350, 480, 610, 740, 870, 1000, 1130]
Ycomm = 635
for i, cx in enumerate(comm_x):
    sat_circle(cx, Ycomm, 12, BLUE_F, BLUE, f"comm{i+1}")
for i in range(len(comm_x) - 1):
    d.connect(f"comm{i+1}", "right", f"comm{i+2}", "left",
              stroke=BLUE, stroke_width=1.4, marker_end=None)
lbl(675, Ycomm + 34, "低轨通信星座（星链 / 千帆）· 星间链路网状互联")

sense = [("sense1", 300, 695, "光学遥感"), ("sense2", 540, 695, "雷达遥感"),
         ("sense3", 790, 695, "资源勘探"), ("src", 1230, 695, None)]
for nid, cx, cy, t in sense:
    sat_square(cx, cy, 22, ORANGE_F, ORANGE, nid)
    if t:
        lbl(cx, cy + 24, t)
lbl(1230, 695 + 24, "遥感数据源")

sci = [("sci1", 430, 752, "实践 · 科学试验"), ("sci2", 670, 752, "空间环境探测")]
for nid, cx, cy, t in sci:
    sat_triangle(cx, cy, 13, ORANGE_F, ORANGE, nid)
    lbl(cx, cy + 26, t)

sat_square(980, 740, 54, SLATE_F, SLATE, "station", sw=2.0)
lbl(980, 740, "天宫", weight="bold")
lbl(980, 740 + 38, "空间站（载人航天）")

# ---------------- Layer 1 — Ground ----------------
ground = [("gs1", 360, 905, "地面测控站"), ("gs2", 740, 905, "数据接收天线"),
          ("gs3", 1130, 905, "卫星控制中心")]
for nid, cx, cy, t in ground:
    sat_square(cx, cy, 34, "#FFFFFF", SLATE, nid, sw=1.8)
    lbl(cx, cy + 30, t, weight="bold")
    # symbolic uplink / downlink (decorative)
    d.line(cx - 16, cy - 17, cx - 16, cy - 52, stroke=BLUE, stroke_width=1.6,
           marker_end="ah", role="decoration")
    d.line(cx + 16, cy - 52, cx + 16, cy - 17, stroke=BLUE, stroke_width=1.6,
           marker_end="ah", extra='stroke-dasharray="5,3"', role="decoration")
lbl(360, 905 - 62, "指令↑  数据↓")

# ---------------- Relay chain (concrete validated edges) ----------------
d.connect("src", "top", "geo_relay", "bottom",
          stroke=BLUE, stroke_width=1.8, marker_end="ah")
d.connect("geo_relay", "bottom", "gs3", "top",
          stroke=BLUE, stroke_width=1.8, marker_end="ah")

# LEO<->MEO inter-satellite dashed link
d.connect("comm4", "top", "meo3", "bottom",
          stroke=BLUE, stroke_width=1.3, marker_end=None, dashed=True)
lbl(640, 552, "星间链路", anchor="start")

# ---------------- Earth horizon ----------------
d.add_element(
    f'<path d="M 0,{Hh} Q {W/2},{1005} {W},{Hh} Z" '
    f'fill="{EARTH_F}" stroke="{EARTH_S}" stroke-width="1.6"/>', None)
lbl(W / 2, 1050, "地面段 · 测控 / 数收 / 控制中心")

# ---------------- Footer ----------------
d.text(CX0 + 4, 965,
       "色系：  蓝=信息传输（通信/中继）   绿=导航感知   橙=探测与科研   深灰=载人/平台",
       F_BODY, fill=BLACK, anchor="start", bbox=False)
d.text(CX0 + 4, 987,
       "数据通路：  遥感星 → 高轨中继（天链） → 地面站；星座内部及层间由星间链路互联。",
       F_BODY, fill=BLACK, anchor="start", bbox=False)

# ---------------- Evaluate + render ----------------
score, report = evaluate_svg(d)
print(f"Quality Score: {score}")
for line in report:
    print(line)

save_svg(d.render(), str(OUT / f"{NAME}.svg"))
rasterize_svg(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.png"), width=1400)
svg_to_pptx(str(OUT / f"{NAME}.svg"), str(OUT / f"{NAME}.pptx"),
            config=PptxConfig(slide_w=13.333, slide_h=11.25, scale=1.0))
print("Done.")
