# Diagram Type Presets — Shapes & Layout

Companion to `design_specs.md`. That file owns **color** (S1–S4 palettes) and global layout rules; this file owns **shape vocabulary and per-type layout conventions** — i.e. *what shape each element becomes* and *how the type is conventionally arranged*. Read both when the user names a diagram type.

Each preset maps a semantic role to one of the drawer's primitives (`rect` / `circle` / `database` / `decision` / `hexagon` / `component` / `cloud` / `line` / `connect` / `text` / `multiline_text` / `formula`) plus a palette tier. Coordinates are still hand-placed (this skill has no Graphviz); the layout rows below give the spacing/direction defaults that consistently pass the evaluator.

## How to choose

| Diagram type | Typical prompt keywords | Palette | Direction |
| :--- | :--- | :--- | :--- |
| Architecture (system / cloud / service) | 架构 / architecture / 微服务 / topology | S1 (≥4 modules) or S3 (component-type semantics) | TB; **≥4 tiers → TB**, else LR |
| Flowchart (process / decision logic) | 流程 / flow / pipeline / 审批 | S2 (2–4 branches) or S1 | TB |
| ML / DL model | 模型 / network / Transformer / CNN / encoder-decoder | S2 (layer-type hues) or S4 (one focal layer) | TB |
| ER (database schema) | ER / 表结构 / schema / 数据库设计 | S1 | TB |
| Sequence (interaction / 时序) | 时序 / sequence / 交互 / 协议流 | S1 | LR (lifelines) × TB (time) |
| Swimlane (cross-functional / 跨职能) | 泳道 / 谁做什么 / 跨部门 | S2 (per-lane hue) or S1 | LR inside lanes |
| Network topology | 网络 / topology / LAN / 部署拓扑 | S3 | TB by tier |

**Default = Architecture + S1** when the request is ambiguous.

## Universal shape vocabulary (role → primitive)

Use this as the canonical mapping. A node drawn with `node_id=` is connectable; `role="layer"|"background"` marks a container that the evaluator excludes from spacing/palette checks.

| Role | Primitive | Notes |
| :--- | :--- | :--- |
| Layer / tier / container / cluster | `rect(role="layer", fill=near-white, stroke=neutral)` | Dashed border for logical grouping; solid for physical |
| Service / process / module / op | `rect(node_id=…, fill=S-tier)` | The default connectable box |
| Database / persistent store | `database(node_id=…, fill=S-tier)` | Cylinder |
| Decision / branch | `decision(node_id=…, fill=S-tier)` | Diamond |
| Gateway / broker / bus (hub) | `hexagon(node_id=…, fill=S-tier)` | 6-sided; place centrally |
| External system / 3rd-party | `component(node_id=…, fill=S-tier, dashed=True)` | Tabbed box; dashed = outside boundary |
| Internet / WAN / cloud service | `cloud(node_id=…, fill=S-tier)` | Multi-lobe cloud |
| Start / End terminator | `circle(node_id=…, r=…)` or `rect(rx=h/2)` (stadium) | Small circle for start/end; stadium for labels |
| Junction / merge point | `circle(node_id=…, node_kind="junction", r=4–6)` | Tiny; auto-snaps edges |
| I/O (input/output data) | `hexagon(...)` *(no native parallelogram)* | Hexagon is the closest semantic match |
| Connector | `connect(from, side, to, side, …)` or `line(…, register_edge=True)` | Gray stroke, never colored |
| Label only (no node) | `text(...)` / `multiline_text(...)` | `role="label"` |

> **Gaps vs. draw.io**: there is no native parallelogram, ellipse, ER `table` container, or UML lifeline shape. Approximate per the notes above (I/O → hexagon; terminator → circle/stadium; ER table → `rect` container with child `rect` rows; lifeline → `rect` header + dashed `line`). Keep approximations consistent *within* a diagram.

---

## Architecture (system / cloud / service)

The default type and the one this skill is tuned for (see `evals/`).

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Tier / layer (Client / API / Service / Data) | `rect(role="layer", fill="#F7F7F7", stroke="#CCCCCC")` | Full-width band; gutter ≥20px inside |
| Service / module | `rect(node_id=…, fill=S-tier, stroke=unified)` | Op cards stay white in S1 |
| Database | `database(node_id=…, fill=S-tier)` | Green tier in S3 |
| Queue / bus / message broker (hub) | `hexagon(node_id=…, fill="#FFF2CC", stroke="#D6B656")` | **Place at the geometric center** of its clients |
| Gateway / load balancer | `hexagon(node_id=…, fill=S-tier)` | Orange tier in S3 |
| External system / 3rd-party API | `component(node_id=…, dashed=True, fill="#F5F5F5", stroke="#666666")` | Dashed = outside your boundary |
| Sync call | `connect(a, side, b, side, marker_end="arrowhead")` | Solid |
| Async / event | `connect(…, dashed=True)` | Dashed |

**Layout**: TB by default; switch to LR only when there are ≤3 tiers and the flow reads left→right. Hub nodes (queue/gateway) sit on the center column; clients radiate symmetrically so edges enter from different sides (zero crossings). Tier gap ≥40px; same-tier node gap ≥30px. Wrap each tier in a layer rect.

## Flowchart

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Start / End | `circle(node_id=…, r=20, fill="#D5E8D4", stroke="#82B366")` | Green terminator |
| Process / step | `rect(node_id=…, fill="#DAE8FC", stroke="#6C8EBF")` | Blue rectangle |
| Decision | `decision(node_id=…, fill="#FFF2CC", stroke="#D6B656")` | Yellow diamond |
| I/O (data in/out) | `hexagon(node_id=…, fill="#FFE6CC", stroke="#D79B00")` | Orange (parallelogram substitute) |
| Subprocess | `rect(node_id=…, fill="#E1D5E7", stroke="#9673A6")` + double border (draw a 2nd inset rect) | Purple |
| Yes / No branch labels | `text(...)` on the decision edges | Always label both branches |

**Layout**: TB; ~200px vertical gap between steps. Decision branches go LR, then merge back to the center column. Keep the main spine on a single x; branches are short detours, not parallel columns.

## ML / Deep Learning model

Ideal for paper figures (NeurIPS/ICML style). Leverages `formula()` for tensor shapes.

| Element | Primitive | Fill (by layer type) |
| :--- | :--- | :--- |
| Layer block | `rect(node_id=…)` | Input/Output → `#D5E8D4`/`#82B366`; Conv/Pool → `#DAE8FC`/`#6C8EBF`; Attention/Transformer → `#E1D5E7`/`#9673A6`; RNN/LSTM/GRU → `#FFF2CC`/`#D6B656`; FC/Linear → `#FFE6CC`/`#D79B00`; Loss/Activation → `#F8CECC`/`#B85450` |
| Tensor shape annotation | `multiline_text(...)` 2nd line, or `formula(...)` | `(B, C, H, W)` or `(B, T, D)` as the label's 2nd line |
| Skip / residual connection | `connect(…, as_curve=True, dashed=True)` | Curved dashed arrow bypassing layers |
| Encoder / Decoder group | `rect(role="layer", …)` | Swimlane-style container around each stack |

**Layout**: TB (data flows top→bottom); ~150px between layers. Stack layers on the center x; skip connections curve out to the side and back. Group encoder/decoder in layer rects. Annotate every layer with its tensor shape — this is the whole point of an ML diagram.

## ER (Entity-Relationship)

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Table (entity) | `rect(role="layer", node_id=…, fill="#DAE8FC", stroke="#6C8EBF")` | Container; header row is the table name |
| Column row | `rect(...)` child inside the table | One per column; PK row in `weight="bold"` |
| PK marker | `text("PK", weight="bold")` prefix or `text("🔑")` | Prefix the column label |
| FK relationship | `connect(…, dashed=True)` | Dashed; label with the FK column |

**Layout**: TB; ~300px between tables. Vertically stack related tables (parent above children) so FK edges read top→bottom and don't cross. No native crow's-foot — use a plain dashed arrow with the FK column as the label.

## Sequence (interaction)

The hardest to hand-place; prefer this only when the interaction *order* is the message.

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Actor / participant (lifeline header) | `rect(node_id=…, fill=S-tier)` at top | Box at the top of each column |
| Lifeline (dashed vertical) | `line(…, dashed=True, role="decoration")` | From header straight down |
| Activation bar | `rect(fill=S-tier, role="decoration")` | Narrow rect overlaid on the lifeline |
| Sync message | `connect(a, "bottom"/side, b, …, marker_end="arrowhead")` | Solid arrow between lifelines |
| Async message | `connect(…, dashed=True)` | Dashed |
| Return message | `connect(…, dashed=True, stroke="#999999")` | Grey dashed |

**Layout**: participants on a horizontal row, ~200px apart (LR). Time flows top→bottom; each message sits on its own y row, ~50px apart. Activation bars span the rows where that participant is "active". Messages are short horizontal segments between adjacent lifelines — avoid long diagonals.

## Swimlane (cross-functional)

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Pool (whole process) | `rect(role="layer", fill="#F7F7F7", stroke="#CCCCCC")` | Outer container |
| Lane (one role / team) | `rect(role="layer", fill=lane-tint, dashed=False)` | Child of pool; one per actor |
| Steps | Flowchart primitives (Start/Process/Decision/IO) | Each step's center sits inside its lane |
| Handoff (cross-lane edge) | `connect(…)` | Edges crossing a lane boundary *are* the handoffs — the diagram's point |

**Layout**: LR flow inside horizontal lanes; ≥160px horizontal step gap. Each lane is a full-height vertical slice of the pool; keep every step inside its actor's lane. Time flows left→right.

## Network topology

| Element | Primitive | Notes |
| :--- | :--- | :--- |
| Router / Switch / Firewall / LB | `component(node_id=…, fill=S3-tier)` | Tabbed box; type in the label |
| Server / compute | `rect(node_id=…, fill=S3-compute)` | |
| Storage / NAS | `database(node_id=…, fill=S3-storage)` | |
| Internet / WAN | `cloud(node_id=…, fill="#FFFFFF", stroke="#6881B3")` | |
| Zone (subnet / VLAN / DMZ) | `rect(role="layer", dashed=True, fill="#F5F5F5", stroke="#666666")` | Container; label = CIDR / zone name |
| Physical link | `connect(…, stroke_width=2)` | Plain; label = interface / VLAN |
| Logical / VPN link | `connect(…, dashed=True)` | Dashed |

**Layout**: TB by tier — Internet → edge (router/firewall) → distribution (switch/LB) → access (servers/clients). Wrap each subnet in a dashed zone container labelled with its CIDR. Label links with port/VLAN so the topology is self-documenting.

---

## Layout value cheatsheet (all types, evaluator-tuned)

These are the per-type spacing defaults. They all satisfy the evaluator floors (container gutter ≥20px, same-kind node spacing ≥14px); use them unless the diagram is crowded, then spread further.

| Type | Direction | Node gap (same row) | Tier/step gap (between rows) | Hub placement |
| :--- | :--- | :--- | :--- | :--- |
| Architecture | TB (≥4 tiers) / LR | 30px | 40px | center column, clients symmetric |
| Flowchart | TB | 40px | 200px | — |
| ML / DL | TB | 30px | 150px | — |
| ER | TB | — | 300px (table→table) | — |
| Sequence | LR × TB(time) | 200px (lifeline→lifeline) | 50px (msg→msg) | — |
| Swimlane | LR | 160px (step→step) | lane height | — |
| Network | TB | 30px | 40px | Internet at top center |

## Evaluator constraints to keep in mind

- **Font tiers**: 3–4 per diagram, adjacent tiers ≥1.15× apart (e.g. 20 / 14 / 12 / 10). Header / node-label / annotation / tensor-shape is a natural 4-tier split.
- **Palette**: ≤8 accents. Pick one scheme (S1–S4) and stay in it — don't mix tier colors from different schemes.
- **Containers**: nodes fully inside a layer rect need ≥20px gutter on every side.
- **Edges**: gray (`#4D4D4D`), never colored; arrowheads via `marker_end="arrowhead"`.
- **Hubs** (queue/gateway/broker): if multiple clients connect to one, fan them around it so edges enter from different sides — a single-side fan stack triggers the evaluator's bend/stretch warnings.
