# LLM Distributed Inference Serving — 7-Layer Architecture

Draw a vertical layered stack showing a distributed LLM inference serving
system. A neutral downward "spine" connects the client (top) through seven
architecture bands to the streaming output (bottom).

## Layers (top → bottom)

Each band is one layer, named bilingually (circled number ①–⑦ + CN + EN).
Components inside each band are neutral white op cards.

1. **① 接入与网关层  Gateway Governance** (BLUE) — 4 op cards side-by-side:
   负载均衡 Load Balancer, 认证鉴权 AuthN & AuthZ, 流量控制 Rate Limit,
   Prompt 过滤 Prompt Filter.
2. **② 全局调度与路由  Scheduler & Routing** (BLUE) — three nodes in a row:
   集群资源视图 (GPU 显存/利用率/健康) → 全局调度器 Scheduler (Prefix Cache
   查找 · 负载均衡) ⇢ KV 缓存索引 KV Cache Index (database shape). Edge
   sched→kvid is dashed (cache-hit lookup).
3. **③ 分布式推理引擎  Inference Engine** (TEAL) — two nested worker
   containers side-by-side: Prefill Worker（计算密集）containing Sequence
   切分 / Attention 并行 / KV 压缩写入 chips; Decode Worker（访存密集）
   containing Continuous Batch / 动态插入踢出 / 逐 Token 生成 chips. Connected
   by a "KV Cache 转移 · Continuous Batching" arrow.
4. **④ 模型并行与加速  Model Parallelism** (TEAL) — 3 wide cards:
   张量并行 TP (QKV 矩阵列分割 · All-Reduce), 流水线并行 PP (按层分割 ·
   Send/Recv), 序列并行 SP (长序列分割 · 合并).
5. **⑤ 异构存储与通信  Storage & Interconnect** (AMBER) — Storage container
   (HBM 显存 / CPU DRAM / 分布式存储) + NVLink 节点内 and InfiniBand/RoCE
   跨节点 interconnect cards + GPU 节点集群 (8×A100/H100) with 4 GPU chips.
6. **⑥ 隐性优化组件  Hidden Optimizers** (PURPLE) — 2 wide cards:
   通信延迟隐藏 Compute-Comm Overlap (计算/通信异步重叠), 动态显存分配 KV
   Cache Swap (换出冷 KV 至 CPU).
7. **⑦ 分离式部署  Disaggregated Serving** (PURPLE) — Prefill 集群 (长上下文
   · 计算饱和) → RDMA 高速网络 (hexagon) ⇢ Decode 集群 (快速生成 ·
   带宽饱和). Edge rdma→dec_cluster is dashed (任务队列/中间态).

Top anchor: 客户端 Client (HTTP / gRPC · Prompt + 采样参数). Bottom anchor:
采样 Sampling (Top-P/Top-K) / 流式返回 Stream Output (SSE / WebSocket).

## Flow

A central vertical spine (neutral gray) carries the request downward through
all seven band nodes (client → band1 → … → band7 → output). Internal
horizontal edges show intra-layer flows (L2 resource→scheduler→KV, L3
prefill→decode, L7 prefill→RDMA→decode).

## Design Specification

### Canvas
- 1400 × 1400, background `#FFFFFF`. Horizontal center CX = 700.

### Layout topology
- Full-bleed bands: x = 40, width = 1320 (40 px side margins). rx = 8.
- Vertical band positions (y, height): L1 (138, 96), L2 (256, 120), L3 (400,
  210), L4 (634, 150), L5 (808, 160), L6 (992, 130), L7 (1146, 150).
- Title at y≈32; Client centered x≈560–840, y≈70; Output centered y≈1320.
- Left margin columns: layer-number badge pill at x≈55 (42×26); band name
  left-anchored at x≈108.
- Per-band content rows: L1 four cards start x≈415, step 215. L2 three nodes
  left→right (x≈80 / 420 / 840). L3 two 590-wide containers (x≈70, x≈720).
  L4 three 380-wide cards start x≈90, step 420. L5 three zones (Storage
  360w left / interconnect 300w center stacked / GPU-cluster 400w right). L6
  two 580-wide cards (x≈90, x≈710). L7 cluster(360w) / hexagon(center) /
  cluster(360w). Minimum inter-card gap ≈ 30 px.

### Palette (exact hex)
Exactly **8 accents** (4 fills + 4 strokes); all op-card and text colors are
neutral grays (R==G==B), not counted.
- BLUE  (control plane, L1–L2): fill `#DAE8FC`, stroke `#2E5AAC`.
- TEAL  (compute, L3–L4):        fill `#B2E2E2`, stroke `#2E8B8B`.
- AMBER (infra, L5):             fill `#FFE6CC`, stroke `#D79B00`.
- PURPLE (optimization, L6–L7):  fill `#E1D5E7`, stroke `#9673A6`.
- Neutral op card: fill `#FFFFFF`, stroke `#5A5A5A`.
- Text: primary INK `#222222`, secondary SUB `#444444` (both already
  WCAG-legible on every pastel fill — use as-is, no correction needed).
- Edges/arrows: `#6B6B6B`. Decoration gray (GPU chips): stroke `#999999`.

### Shape vocabulary
- Layer band → full-width rounded rect (1320 × band-height, rx=8, stroke 1.5);
  registered as connectable layer node `band{n}`.
- Op card (generic) → rounded rect (variable W×H, rx=6, white fill, stroke
  1.2); title + desc centered.
- Terminal (client/output) → rounded rect 280×46, rx=8, stroke 1.4.
- KV Cache Index → **database cylinder** 260×58, BLUE fill (distinct from
  rectangular op cards).
- L3 worker container → nested layer rect 590×140, rx=8, white fill, TEAL
  stroke, stroke 1.6.
- L3 inner chip → rounded rect 156×34, rx=5, TEAL fill, stroke 1.1.
- L4 / L6 wide card → rounded rect 380×80 (L4) or 580×56 (L6), rx=6.
- L5 storage & GPU-cluster → accent-tinted container rect (360×98 / 400×98,
  rx=8, AMBER fill, stroke 1.4); **decorative, not connectable nodes**.
- L5 interconnect → thin rounded rect 300×34, rx=5, stroke 1.2.
- L5 GPU chip → tiny decoration rect 70×30, rx=4, white fill, `#999999`
  stroke 1.0 (decorative).
- L7 cluster → rounded rect 360×68, rx=6, stroke 1.2.
- L7 RDMA → **hexagon** 240×34, PURPLE fill, stroke 1.3.
- Layer-number badge → pill rect 42×26, rx=5, white fill, band-stroke
  (decoration, not a node).

### Typography
- Exactly 4 tiers: **20 / 14 / 12 / 10**.
- 20 — diagram title, bold, INK, centered.
- 14 — band name, bold, INK, left-anchored.
- 12 — card titles, band sub-headers, badge "L{n}", worker-container titles;
  bold INK.
- 10 — card descriptions, edge labels, GPU-chip labels; SUB `#444444`.
- Card text placement: title at center-y − 8, desc at center-y + 9 (both
  centered horizontally). Band name left-anchored at x≈108.
- Bilingual format: circled number + CN + two spaces + EN
  (e.g. "① 接入与网关层  Gateway Governance").

### Edges
- Spine: stroke `#6B6B6B`, width **2**, arrowhead marker (`ah`: triangle
  10×7, ref_x=9, ref_y=3.5), routed bottom-anchor → top-anchor between every
  consecutive node client→band1→…→band7→output.
- Internal flow edges: width 1.5 (L2, L7) / 1.6 (L3), same `#6B6B6B` + `ah`,
  left↔right routed. **Solid** = synchronous request/data flow; **dashed** =
  cache-hit lookup (sched→kvid) or async state transfer (rdma→dec_cluster).
- Edge labels in tier-10 SUB inline beside the arrow.

### Design rationale
- Only **4 functional colors** encode the 7-band domain grouping (control →
  compute → infra → optimization); op cards stay neutral white+gray so color
  never implies component type, only layer domain.
- Bands are connectable layer nodes, so a single bottom→top spine threads the
  whole stack without per-node routing clutter.
- L3 nests layer-boxes-within-a-layer to contrast Prefill (compute-bound) vs
  Decode (memory-bound) — a deliberate two-level hierarchy.
- Shape variety (database for KV index, hexagon for RDMA, tinted containers
  for L5) signals non-op concepts without adding palette colors.
- Decorative elements (badges, GPU chips) deliberately use neutral grays to
  hold the accent count at exactly 8 and avoid competing with band tints.
