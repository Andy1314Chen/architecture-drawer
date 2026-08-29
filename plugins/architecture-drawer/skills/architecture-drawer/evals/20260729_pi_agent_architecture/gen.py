#!/usr/bin/env python3
"""pi agent architecture diagram — labels INSIDE components, no overflow."""
import sys

import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(_HERE, "..", "..", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
from svg_utils import SVGDrawer, save_svg, rasterize_svg
from evaluator import evaluate_svg
from svg2pptx import svg_to_pptx, PptxConfig
from design_brief import DesignBrief, ColorSpec  # noqa: E402
from semantic_qa import run_semantic_qa  # noqa: E402
from pathlib import Path

OUT = Path(__file__).resolve().parent
NAME = "pi_agent_architecture"

W, H = 1260, 860
d = SVGDrawer(W, H, bg="#FFFFFF")
d.arrow_head("dn", "#1B3A5C")
d.arrow_head("up", "#D47130")
d.arrow_head("tl", "#4D4D4D")

# Palette (7 accents)
SK = "#1B3A5C"; EV = "#D47130"
LB = ["#D5E1EB","#BBCEDF","#9BB9D1","#769EBF"]
LF = "#AAC8DE"; WH = "#FFFFFF"
TX = ["#1A1A1A","#555555"]

F = [20, 14, 12, 10]; BB = False

LX, LW = 60, 730
HH, CH, GAP = 36, 62, 18   # header, component height, gap between layers

layers = [
    ("① 交互界面层 · Interface",           "",    4, 150),
    ("② 编码智能体层 · pi-coding-agent",  "@earendil-works/pi-coding-agent", 4, 152),
    ("③ 智能体核心层 · pi-agent-core",    "@earendil-works/pi-agent-core",   3, 205),
    ("④ AI 抽象层 · pi-ai",              "@earendil-works/pi-ai",          3, 206),
]
# Brief palette keys for the four layer bands (identity for the contract).
LAYER_IDS = ["interface", "coding_agent", "agent_core", "ai_abstraction"]

ly = 52; all_pos = []
for label, pkg, n, cw in layers:
    lh = HH + CH + 38
    all_pos.append((ly, lh, cw, n, label, pkg))
    ly += lh + GAP

LLMY = ly + 4; LLMH = 40
INFY = LLMY + LLMH + GAP; INFH = 76

def draw_layer(y, lh, cw, ncomp, label, pkg, idx, nid=None):
    fill = LB[idx % 4]
    d.rect(LX, y, LW, lh, rx=11, fill=fill, stroke=SK, stroke_width=1.5, node_id=nid)
    d.text(LX+16, y+HH//2, label, font_size=F[1], weight="bold", fill=SK, anchor="start", bbox=BB)
    d.line(LX+12, y+HH, LX+LW-12, y+HH, stroke=SK, stroke_width=0.6)
    if pkg:
        d.text(LX+LW//2, y+lh-8, pkg, font_size=F[3], fill="#6699BB", anchor="middle", bbox=BB)
    gap = (LW - ncomp*cw) // (ncomp + 1)
    cx0 = LX + gap; cy0 = y + HH + (lh - HH - CH)//2
    for j in range(ncomp):
        cx = cx0 + j*(cw + gap)
        d.rect(cx, cy0, cw, CH, rx=7, fill=WH, stroke=SK, stroke_width=1)

for idx, (y, lh, cw, ncomp, label, pkg) in enumerate(all_pos):
    draw_layer(y, lh, cw, ncomp, label, pkg, idx, LAYER_IDS[idx])

# Labels INSIDE component rects
def clab(lx, ty, title, sub=""):
    y_center = ty + CH//2
    if sub:
        d.text(lx, y_center-8, title, font_size=F[2], weight="bold", fill=TX[0], anchor="middle", bbox=BB)
        d.text(lx, y_center+10, sub, font_size=F[3], fill=TX[1], anchor="middle", bbox=BB)
    else:
        d.text(lx, y_center+1, title, font_size=F[2], weight="bold", fill=TX[0], anchor="middle", bbox=BB)

# Layer 0
y0, lh0, cw0, n0 = all_pos[0][0], all_pos[0][1], all_pos[0][2], all_pos[0][3]
cy0 = y0 + HH + (lh0-HH-CH)//2
gap0 = (LW - n0*cw0)//(n0+1)
for j, (t, s) in enumerate([("TUI","交互式终端"),("RPC","JSONL 协议"),("Print","打印 / JSON"),("SDK","createAgentSession()")]):
    clab(LX+gap0+j*(cw0+gap0)+cw0//2, cy0, t, s)

# Layer 1
y1, lh1, cw1, n1 = all_pos[1][0], all_pos[1][1], all_pos[1][2], all_pos[1][3]
cy1 = y1 + HH + (lh1-HH-CH)//2
gap1 = (LW - n1*cw1)//(n1+1)
for j, (t, s) in enumerate([("AgentSession","智能体协调器"),("SessionManager","持久化 · 压缩"),
                             ("ExtensionRunner","扩展 · 自定义工具"),("ResourceLoader","技能 · 模板 · 主题")]):
    clab(LX+gap1+j*(cw1+gap1)+cw1//2, cy1, t, s)

# Layer 2
y2, lh2, cw2, n2 = all_pos[2][0], all_pos[2][1], all_pos[2][2], all_pos[2][3]
cy2 = y2 + HH + (lh2-HH-CH)//2
gap2 = (LW - n2*cw2)//(n2+1)
for j, (t, s) in enumerate([("Agent / agentLoop","回合生命周期管理"),("AgentContext","systemPrompt · messages · tools"),
                             ("AgentEvent","事件序列 · 工具执行")]):
    clab(LX+gap2+j*(cw2+gap2)+cw2//2, cy2, t, s)

# Layer 3
y3, lh3, cw3, n3 = all_pos[3][0], all_pos[3][1], all_pos[3][2], all_pos[3][3]
cy3 = y3 + HH + (lh3-HH-CH)//2
gap3 = (LW - n3*cw3)//(n3+1)
for j, (t, s) in enumerate([("OpenAI","GPT-4o · o3"),("Anthropic","Claude 3.5/4"),("Google","Gemini")]):
    clab(LX+gap3+j*(cw3+gap3)+cw3//2, cy3, t, s)

# LLM box
d.rect(LX, LLMY, LW, LLMH, rx=9, fill=LF, stroke=SK, stroke_width=1.5, dashed="6,4", node_id="llm_api")
d.text(LX+LW//2, LLMY+LLMH//2+1, "LLM API · OpenAI / Anthropic / Google 统一流式调用",
       font_size=F[2], anchor="middle", weight="bold", fill=SK, bbox=BB)

# Info box
d.rect(LX, INFY, LW, INFH, rx=9, fill="#EEEEEE", stroke="#B0B0B0", stroke_width=1, node_id="event_seq")
d.text(LX+18, INFY+18, "事件序列示例（一次 prompt（）调用）：", font_size=F[2], weight="bold", fill=TX[0], anchor="start", bbox=BB)
yy = INFY+38
for a, b in [("agam_start → turn_start → message_start … message_end →","→ 回合开始，消息流式生成"),
             ("tool_execution_start … tool_execution_end → turn_end → agent_end","→ 工具执行（如果有），回合收敛，会话结束")]:
    d.text(LX+18, yy, a, font_size=F[3], fill=TX[1], anchor="start", bbox=BB, font_family="Consolas,monospace")
    d.text(LX+420, yy, b, font_size=F[3], fill="#777", anchor="start", bbox=BB)
    yy += 17

# Flow arrows
FL, FR = 24, LX+LW-14
bts = [p[0]+p[1] for p in all_pos]
tps = [p[0] for p in all_pos]

for tp, bt in [(bts[0],tps[1]),(bts[1],tps[2]),(bts[2],tps[3]),(bts[3],LLMY)]:
    d.line(FL, tp+14, FL, bt-14, stroke=SK, stroke_width=2.8, marker_end="dn")
d.text(FL+14, (bts[0]+tps[1])//2+4, "请求下行 ↓", font_size=F[3], fill=TX[1], anchor="start", bbox=BB)

# Right spine (up, AgentEvent). All segments live in the inter-band gutters;
# the first one kisses the LLM box's TOP edge (LLMY+8) instead of starting
# 24px INSIDE it — the old LLMY+LLMH-16 start painted the orange arrow over
# the LLM component's interior (箭头盖在组件上).
for y_from, y_to in [(LLMY+8, bts[3]+16), (tps[3]-16, bts[2]+16),
                     (tps[2]-16, bts[1]+16), (tps[1]-16, bts[0]+16)]:
    d.line(FR, y_from, FR, y_to, stroke=EV, stroke_width=2.8, marker_end="up")
d.text(FR+10, (bts[0]+tps[1])//2+4, "↑ AgentEvent 事件流", font_size=F[3], fill=EV, anchor="start", bbox=BB)

# Tool arrow
ty = all_pos[2][0]+all_pos[2][1]-16
d.line(LX+LW+8, ty, LX+LW+104, ty, stroke=TX[1], stroke_width=1.5, marker_end="tl", dashed="5,3")
mx = LX+LW+56
d.text(mx, ty-14, "工具执行", font_size=F[3], fill=TX[1], anchor="middle", bbox=BB)
d.text(mx, ty+17, "Bash · 文件操作", font_size=10, fill="#888", anchor="middle", bbox=BB)

# Design Brief (Step 1) — declared from input.md's band structure; the
# contract the rendered SVG is asserted against. The four package bands plus
# the LLM API box are palette members; event_seq is a text-only band (the
# event-lifecycle example). Both spines are antiparallel (request down /
# AgentEvent up) and terminate in the gutters, so no chain is declared.
BRIEF = DesignBrief(
    scheme="S1",
    layout="band",
    flow="top-down",
    palette_role={
        "interface":      ColorSpec(LB[0], SK),
        "coding_agent":   ColorSpec(LB[1], SK),
        "agent_core":     ColorSpec(LB[2], SK),
        "ai_abstraction": ColorSpec(LB[3], SK),
        "llm_api":        ColorSpec(LF, SK),
        "event_seq":      ColorSpec("#EEEEEE", "#B0B0B0"),
    },
    flow_chain=(),
)

svg = d.render()
score, rep = evaluate_svg(d)
print(f"Score: {score}")
for r in rep: print(f"  {r}")
qa = run_semantic_qa(d, expected_size=(W, H), brief=BRIEF)
print("Semantic QA:")
for line in qa.report():
    print(line)

sp = str(OUT/f"{NAME}.svg")
save_svg(svg, sp)
rasterize_svg(sp, str(OUT/f"{NAME}.png"), width=1260)
try:
    svg_to_pptx(svg, str(OUT/f"{NAME}.pptx"), config=PptxConfig(slide_w=13.333, slide_h=7.5, scale=2.0))
except Exception as e: print(f"[pptx: {e}]")
BRIEF.write(str(OUT / "brief.json"))
print(f"\n✓ {NAME}.svg / .png /.pptx")