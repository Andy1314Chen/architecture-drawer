# vLLM — High-Throughput LLM Serving with PagedAttention

Draw a layered top-to-bottom pipeline (request → response) for the vLLM inference
serving stack, with the PagedAttention / paged KV-cache abstraction on the right.

## Layers (top → bottom)

1. **Title bar** — "vLLM — High-Throughput LLM Serving with PagedAttention",
   subtitle "PagedAttention · Continuous Batching · High Throughput".
2. **Client** — single node: "Client / Application" (OpenAI API · HTTP / SDK).
3. **API Server** — container with two nodes: "FastAPI / ASGI Server" (request
   routing · streaming) and "OpenAI-compatible API"
   (/v1/completions · /v1/chat/completions).
4. **LLM Engine (Core)** — left container with three nodes:
   - AsyncLLMEngine (top center)
   - Scheduler (left, bullets: FCFS + priority scheduling · continuous batching ·
     preemption on KV-cache OOM · decode-step orchestration)
   - BlockManager (right, bullets: logical ↔ physical blocks · block tables
     (paging) · copy-on-write fork · reference counting)
5. **Paged KV Cache (GPU Memory)** — right container: logical blocks row,
   block table mapping (L0→P3 etc.), and a physical KV cache blocks grid
   showing allocated vs free blocks.
6. **Execution Layer (GPU workers)** — bottom container: Worker → ModelRunner →
   PagedAttention Kernel, plus an Optimizations & CUDA Kernels band
   (continuous batching · prefix caching · chunked prefill · speculative
   decoding; quantization AWQ/GPTQ/FP8 · tensor/pipeline parallelism · LoRA
   multi-adapter · prefix-aware scheduling).

## Edges

- **Solid** (data / request flow): client → openai_api; fastapi → openai_api;
  openai_api → async_engine → scheduler → worker → modelrunner → pagedattn →
  phys_blocks.
- **Dashed** (cache / block management): scheduler ↔ blockmanager (alloc /
  free); blockmanager ↔ phys_blocks (manage physical).

## Design Specification

### Canvas
- 1240 × 970, background `#FFFFFF`.
- Five horizontal bands stacked top-to-bottom: title bar (h=52) → client row →
  API Server band → middle band (Engine left + KV Cache right, side by side) →
  Execution band → legend (bottom).

### Layout topology
- **Title bar**: full canvas width across the top (h=52).
- **Client**: single node centered on the vertical axis at ~x=620 (~50% width).
- **API Server band**: wide container (~x150–1090, h≈128); two nodes side by
  side — FastAPI (left) and OpenAI-compatible API (right).
- **Middle band (the key split)**: two adjacent containers at the same vertical
  range (~y318–618):
  - **LLM Engine (Core)** — LEFT, ~60% width (x≈40–780). AsyncLLMEngine centered
    at top; Scheduler (left) and BlockManager (right) as a wide pair below it.
  - **Paged KV Cache** — RIGHT, ~32% width (x≈800–1200). Logical-blocks row →
    block-table mapping → physical-blocks grid stacked vertically inside.
- **Execution band**: full-width container (~x40–1200, h≈236); three nodes in a
  horizontal Worker → ModelRunner → PagedAttention row, with a nested
  Optimizations & CUDA Kernels band beneath them spanning the row.
- **Legend**: a small box bottom-left (~x40–600).
- Minimum node spacing ~20–30px; containers add a ~18px inner label gutter.
- Big containers are `role='layer'` (gutter-checked, NOT registered as nodes) so
  cross-container edges never trigger routes-through.

### Palette (exact hex)
- **DARK `#1B3A5C`** — accent; appears ONLY as stroke / border / edge. NEVER as
  text or fill.
- **INK `#1A1A1A`** — primary text (neutral dark). All node/layer titles + body.
- **MUTE `#555555`** — secondary text (neutral gray) for subtitles & captions.
- **Tint fills** (neutrals are grays; tints are the only colored fills):
  - T1 `#D5E1EB` — title bar + LLM Engine (Core) container.
  - T2 `#E8EEF3` — API Server, Paged KV Cache, Optimizations band, free KV
    blocks region.
  - T3 `#B8CDE0` — Execution Layer container + allocated KV cache blocks.
- Operation cards fill = `#FFFFFF` (white).
- Arrowheads = INK `#1A1A1A` (neutral) → NOT counted as a dark fill.
- Accents ≤ 8 (DARK + 3 tints); text is neutral INK/MUTE — WCAG-legible on all
  fills. No contrast defects to correct.

### Shape vocabulary
- Layer container → rect, rx=8, fill=tint, stroke=DARK 1.5px.
- Operation node → rect, rx=6, fill=white, stroke=DARK 1.5px.
- Node sizes (W×H design tokens): Client 220×62; FastAPI 360×60; OpenAI API
  400×60; AsyncLLMEngine 280×46; Scheduler 330×160; BlockManager 334×160;
  Physical KV Cache Blocks 360×124; Worker 240×58; ModelRunner 300×58;
  PagedAttention Kernel 300×58.
- Optimizations band → rect rx=6, fill=T2, stroke=DARK 1.5px, nested inside the
  Execution Layer.
- Logical block (decoration) → rect rx=4, 52×30, fill=white, stroke=DARK 1px.
- Physical KV block → rect rx=3, 44×26; allocated = fill=T3, free = fill=white;
  stroke=DARK 1px.
- Legend box → rect rx=6, fill=white, stroke=DARK 1.2px.

### Typography
- Tier 20 — bold, INK — diagram title.
- Tier 14 — bold, INK — node titles + container/layer labels.
- Tier 12 — bold, INK — KV-cache sub-labels (① ② ③); also tier 12 normal for
  bullet lists (INK) and node subtitles (MUTE).
- Tier 10 — MUTE — tiny footnote captions (e.g. "allocated blocks need not be
  contiguous → low fragmentation").
- Node text centered (`anchor=middle`); container/layer labels + bullet lists
  left-aligned (`anchor=start`), indented ~18px from the container's left edge.
- English only — no bilingual format.

### Edges
- Stroke = DARK `#1B3A5C`, width 1.5px, end-marker = neutral INK arrowhead.
- **Solid** = data / request flow.
- **Dashed** (`6,3`) = cache / block management.
- Edges connect node faces (top/bottom/left/right); horizontal pairs route left
  ↔ right, vertical pipeline flows top → bottom.

### PagedAttention visualization
- Three stacked tiers inside the KV Cache container, numbered ① ② ③:
  1. **Logical blocks** — a row of small white rounded rects (L0, L1, L2).
  2. **Block table** — left-aligned mapping lines: L0 → P3, L1 → P0, L2 → P6.
  3. **Physical KV Cache Blocks** — a 4×2 grid of small rounded rects labelled
     P0..P7; the blocks referenced by the table (P0, P3, P6) are filled T3
     (allocated); the rest are white (free) — deliberately non-contiguous.
- A tier-10 MUTE caption under the grid states the fragmentation benefit.

### Design rationale
- Dark blue (`#1B3A5C`) is reserved exclusively for strokes/borders/edges; text
  and arrowheads stay neutral INK/MUTE → no luminance clash, no colored text on
  pastel fills.
- Neutral INK arrowheads also keep arrowheads from being scored as "dark fills".
- Monochrome-blue tints encode hierarchy by saturation: lightest (T2) for
  API/KV/kernels surfaces, mid (T1) for the engine core + title, darkest (T3)
  for execution + "allocated" emphasis.
- Containers are `role='layer'` (not registered nodes) so request-flow edges
  crossing container bounds render as straight clean lines.
- PagedAttention grid shows allocated blocks scattered (non-contiguous) to
  visually justify PagedAttention's low-fragmentation claim.

### Legend
- Bottom-left box: a solid DARK line → "data / request flow"; a dashed DARK
  line → "cache / block management".
