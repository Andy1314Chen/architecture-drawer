# Agent Infrastructure — Layered Architecture

Draw a **5-layer horizontal stack** (top → bottom) representing an AI agent
infrastructure platform, plus a **cross-cutting Security & Observability band**
on the RIGHT that spans the full height of the stack.

Title: **Agent Infra 架构图** / "Agent Infrastructure · 分层架构 Layered Architecture".

## Layers (top → bottom)

Each layer is a neutral container with a bilingual CN header + EN subtitle,
and holds component cards (or accent modules) inside.

1. **应用层 / Application Layer** — end-user interfaces (3 cards):
   Web 应用 · Web App | REST / API · Gateway | CLI 工具 · CLI.
2. **编排与治理层 / Orchestration & Governance** — agent coordination & control (4 cards):
   生命周期管理 · Lifecycle | 任务调度 · Scheduling | 多智能体协作 · Multi-Agent | 策略控制 · Policy.
3. **核心能力层 / Core Capabilities** — two accent modules side by side:
   - **记忆与上下文 / Memory & Context** (teal): 向量数据库·Vector DB | 知识图谱·Knowledge Graph | RAG 检索·Retrieval.
   - **工具与网关 / Tools & Gateway** (orange): MCP 协议·MCP | API 集成·API Integration | 函数调用·Function Call.
4. **执行与环境层 / Execution & Environment** — two accent modules side by side:
   - **执行引擎 / Execution Engine** (green): 高并发·Concurrency | 秒级扩容·Autoscale | 快速启动·Fast Start.
   - **环境与沙箱 / Environment & Sandbox** (yellow): 代码执行·Code Exec | Serverless·Elastic | 安全隔离·Isolation.
5. **基础设施层 / Infrastructure** — foundation (4 cards):
   计算·Compute GPU/CPU | 存储·Storage | 网络·Network | K8s 编排·Kubernetes.

## Cross-cutting band (right side, full height)

**安全与可观测 / Security & Observability** (coral) — a single tall band on the
right spanning ALL five layers. It is the 5th accent color. Contains 6 cards:
身份认证·Authentication | 数据加密·Encryption | 行为审计·Behavior Audit | 日志·Logging | 监控·Metrics | 链路追踪·Tracing.

## Flow & connections

- **Dependency / control flow** — solid vertical arrows down the stack centerline
  linking each adjacent layer (L1→L2→L3→L4→L5).
- **Cross-cutting span** — a dashed horizontal line from each layer's right edge to
  the band's left edge, showing security & observability cut across every layer.
- A **legend** strip sits below the stack: core-module color swatches, the solid
  dependency arrow, and the dashed cross-cut line.

## Design Specification

### Canvas
- **1280 × 900**, background `#FFFFFF`.
- Two zones: **stack on the LEFT** (x 30–890, width 860) and **band on the RIGHT** (x 910–1240, width 330), separated by a ~20px channel for cross-cutting lines.

### Layout topology
- Stack occupies x 30–890. Card/module content inset with 18px padding → inner area x 48–872 (width 824).
- Five layers stacked top→bottom, stack spans y 90–806:
  - L1 Application y≈90 h≈90; L2 Orchestration y≈200 h≈92; L3 Core Capabilities y≈312 h≈188; L4 Execution & Environment y≈520 h≈176; L5 Infrastructure y≈716 h≈90.
  - **Inter-layer gap = 20px** (so vertical arrows stay ≥16px after the marker).
- L3 and L4 each hold **two accent modules side by side**: module width 410, gap 20 between the two modules.
- Band spans the full stack height (y 90–806) on the right; six security cards stacked inside it, each h≈92 with 12px gap.
- Legend strip below the stack (y≈822, h≈60, width 860).

### Palette (exact hex)
Neutrals (R==G==B grays — NOT counted as accents):
- Layer fill `#F2F2F2`, layer border `#B0B0B0`.
- Card fill `#FFFFFF`, card stroke `#BEBEBE`.
- Primary text `#333333`, secondary text `#666666`, connectors `#555555`.

5 accent FILLS only (borders stay neutral `#333333` so total accents = 5):
- Memory & Context → `#B2E2E2` (teal).
- Tools & Gateway → `#FFE0B2` (orange).
- Execution Engine → `#C5E1A5` (green).
- Environment & Sandbox → `#FFF59D` (yellow).
- Security band → `#EF9A9A` (coral).

**Contrast fix:** use `#333333` for ALL text that sits ON an accent fill
(golden used `#666666` for EN subtitles/notes on coral & pastel fills, which fails
WCAG ~2.7:1). Override to `#333333`. Secondary `#666666` text is fine only on white cards and neutral layer fill.

### Shape vocabulary
- Layer container → rounded rect, fill `#F2F2F2`, stroke `#B0B0B0` (width 1), rx 8.
- Component card → white rounded rect (fill `#FFFFFF`, stroke `#BEBEBE` width 1), rx 6; height ≈46 (L1/L2), ≈42 (L5); width auto-fits the row with 14px gaps.
- Accent module → rounded rect with accent fill + `#333333` border (width 1.2), rx 8, size 410×132 (L3) / 410×120 (L4); header centered at top, 3 sub-cards below.
- Security card → same white card style, 302×92 inside the band.
- Legend swatches → tiny accent rects 16×14 (rx 2) with `#333333` border.

### Typography
- Font tiers (exact): **22 / 14 / 11 / 9**.
  - 22 → diagram title (`#333333`, bold, centered).
  - 14 → layer headers, module headers, band header, legend title (`#333333`, bold).
  - 11 → card CN labels, subtitle line under title (`#666666` for the page subtitle; `#333333` for CN labels and for any label on accent fills).
  - 9 → EN sub-labels, layer EN subtitles, band EN/italic notes.
- Bilingual placement: CN label on top, EN label below (card EN offset below CN by ≈0.75× font size). Layer/module headers: CN then EN stacked, left-anchored for layers, centered for modules/band.
- Band: header CN bold (14) at `#333333`, EN (9) and italic "横向贯穿所有层 · Cross-cutting" note at `#333333` (corrected from `#666666`).

### Edges
- Solid dependency arrow: stroke `#555555`, width 1.8, arrow marker (head ~10×8). Routed vertically between layer bottom↔top at the stack centerline.
- Cross-cutting dashed line: stroke `#BEBEBE`, width 1.2, dash pattern `4,3`. Horizontal, layer right edge (x 890) → band left edge (x 910), at each layer's vertical center.
- Legend repeats both edge styles as samples.

### Design rationale
- Structural elements use PURE gray colors (R==G==B) so they read as neutral and are not counted as accents — keeping the palette at exactly 5 accent fills (the 5 module/band colors).
- Accents are applied ONLY to fills; borders stay `#333333`. This separates "categorical role" (fill hue) from "structure" (neutral outline).
- The band is full-height to visually express that security & observability cross-cut every layer, not just one — reinforced by the dashed links per layer.
- Inter-layer gaps are fixed at 20px to guarantee the vertical arrows remain clearly visible after arrowhead retraction.
- All text corrected to `#333333` on accent fills for WCAG-legibility (golden's `#666666` subtitles on pastel/coral fails contrast).
