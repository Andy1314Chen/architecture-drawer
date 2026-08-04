# π Agent — Architecture Diagram

Draw an AI agent runtime architecture with labels INSIDE component rectangles
(no text overflow). Bilingual labels (English title + Chinese subtitle).

## Layout

Left column: 4 horizontal layer bands stacked top→bottom, each a container
holding 3–4 component cards. Below the bands sit two full-width boxes (LLM API,
then an event-sequence info box).

1. **① 交互界面层 · Interface** (no package) — TUI (交互式终端), RPC (JSONL 协议),
   Print (打印 / JSON), SDK (createAgentSession()).
2. **② 编码智能体层 · pi-coding-agent** (`@earendil-works/pi-coding-agent`) —
   AgentSession (智能体协调器), SessionManager (持久化 · 压缩),
   ExtensionRunner (扩展 · 自定义工具), ResourceLoader (技能 · 模板 · 主题).
3. **③ 智能体核心层 · pi-agent-core** (`@earendil-works/pi-agent-core`) —
   Agent / agentLoop (回合生命周期管理), AgentContext (systemPrompt · messages · tools),
   AgentEvent (事件序列 · 工具执行).
4. **④ AI 抽象层 · pi-ai** (`@earendil-works/pi-ai`) — OpenAI (GPT-4o · o3),
   Anthropic (Claude 3.5/4), Google (Gemini).

Below the layers:
- **LLM API box** — dashed border, "LLM API · OpenAI / Anthropic / Google 统一流式调用".
- **Event sequence example** — a monospace info box showing one `prompt()` call's
  event lifecycle (agent_start → turn_start → message_start … → tool_execution … →
  agent_end) with Chinese explanations per line.

## Flow

- **Left spine (down, dark blue #1B3A5C)** — 请求下行 ↓: request travels
  top → bottom through all 4 layers and into the LLM API box.
- **Right spine (up, orange #D47130)** — ↑ AgentEvent 事件流: event stream
  bubbles bottom → top back up from the LLM API box through every layer.
- **Tool execution arrow** (dashed gray, far right of the Agent Core band) —
  points outward to "Bash · 文件操作".

## Design Specification

### Canvas
- Exact size: **1260 × 860**, background **#FFFFFF**.

### Layout topology
- Left column spans x ≈ 60 → 790 (width 730), starting at y ≈ 52.
- 4 layer bands stacked vertically; each band ≈ 136 px tall with an **18 px gap**
  between bands (top→bottom: Interface, pi-coding-agent, pi-agent-core, pi-ai).
- Inside each band: a 36 px header strip (layer label + thin divider line),
  a 62 px-tall component-card row, then a package-name footer.
- Card row distributes cards with EQUAL gaps: `(730 − n·cardW) / (n+1)`.
- Below the bands: LLM API box (730 × 40), then 18 px gap, then info box (730 × 76).
- Flow spines sit OUTSIDE the card area: left spine at x ≈ 24 (left of column);
  right spine at x ≈ 776 (near the band's right inner edge).
- Tool arrow sits at the right edge of the Agent Core band (x ≈ 798 → 894).

### Palette (exact hex) — 7 accents
- Skeleton / primary dark blue: **#1B3A5C** (band strokes, card strokes, down-flow, headers).
- Event orange: **#D47130** (up-flow spine + its arrowhead).
- Blue tint gradient (light → dark, one per band, top→bottom):
  **#D5E1EB → #BBCEDF → #9BB9D1 → #769EBF**.
- LLM-box blue fill: **#AAC8DE**.
- Neutrals (NOT accents): card fill **#FFFFFF**; info-box fill **#EEEEEE** with
  stroke **#B0B0B0**; secondary text **#555555**; muted text **#777 / #888**;
  tool arrowhead gray **#4D4D4D**.

### Text color — CONTRAST FIX (critical)
- **ALL node labels use dark text #1A1A1A on EVERY fill.** This corrects the
  golden's unreadable `#6699BB` blue text (≈1.08:1 on the blue-tint bands).
  Apply #1A1A1A to: every component card title + Chinese subtitle, the LLM API
  box label, and every band's package-name footer.
- Band header labels (e.g. "① 交互界面层 · Interface") may use **#1B3A5C** dark
  blue — it is itself contrast-safe on the tints.
- Gray secondary text (#555555 / #777 / #888) is reserved ONLY for flow labels,
  the tool arrow, and the info-box monospace body (all on white/light-gray).

### Shape vocabulary
- Layer band → rounded rect **rx=11**, 730 × 136, fill = blue tint (one per band),
  stroke #1B3A5C width 1.5; contains a 0.6 px #1B3A5C divider under the header.
- Component card → rounded rect **rx=7**, fill #FFFFFF, stroke #1B3A5C width 1,
  height 62. Widths per band: **150** (Interface), **152** (pi-coding-agent),
  **205** (pi-agent-core), **206** (pi-ai). Count: 4 / 4 / 3 / 3.
- LLM API box → rounded rect **rx=9**, 730 × 40, fill #AAC8DE, stroke #1B3A5C
  width 1.5, **dashed "6,4"**.
- Info box → rounded rect **rx=9**, 730 × 76, fill #EEEEEE, stroke #B0B0B0 width 1.
- Flow arrow → straight vertical line, width **2.8**, custom arrowhead marker
  (down = #1B3A5C; up = #D47130).
- Tool arrow → horizontal **dashed "5,3"** line, width 1.5, gray arrowhead #4D4D4D.
- No diamonds/circles — vocabulary is rectangles + lines + markers only.

### Typography
- Four tiers: **20 / 14 / 12 / 10**. All text drawn with **`bbox=False`**
  (text excluded from the collision registry).
- Tier 14 bold — band header labels ("① 交互界面层 · Interface").
- Tier 12 bold — component card English title + LLM API box label + info-box header.
- Tier 10 — component Chinese subtitle, band package-name footer, flow labels,
  tool labels, info-box monospace body (font-family `Consolas,monospace`).
- Tier 20 — reserved title tier (no diagram title is drawn).
- Placement: card titles centered inside the card; subtitle directly beneath.
  Band headers anchored left; package names centered at band bottom. Labels must
  stay INSIDE their rectangles — never overflow card edges.
- Bilingual format: band header = "序号 中文名 · English"; card = English title
  (bold) over Chinese subtitle; info box = Chinese header + monospace event
  sequence + Chinese gloss per line.

### Edges
- Down-flow (left spine, #1B3A5C, width 2.8, down arrowhead): one segment between
  each consecutive band bottom→next band top, final segment into the LLM box.
- Up-flow (right spine, #D47130, width 2.8, up arrowhead): mirrored segments from
  the LLM box back up to the top band.
- Tool arrow (dashed "5,3", #555555, width 1.5, gray arrowhead): horizontal,
  leaving the right edge of the Agent Core band.
- Flow labels sit beside their spines ("请求下行 ↓" left, "↑ AgentEvent 事件流" right).

### Design rationale
- The blue-tint **vertical gradient** (light top → dark bottom) reads as a depth
  stack: user-facing interfaces on top, raw model providers at the bottom.
- Two opposing spines encode a **request/response loop**: dark-blue request
  descends, orange event stream ascends — color = direction.
- The LLM API box is the only **dashed** rectangle, signalling it is an external
  boundary shared by all providers, distinct from the solid internal bands.
- Labels live **inside** white cards to keep band tints clean and avoid overflow.
- Correcting the golden's low-contrast `#6699BB` text to `#1A1A1A` makes every
  label WCAG-legible without altering the palette's accents.
