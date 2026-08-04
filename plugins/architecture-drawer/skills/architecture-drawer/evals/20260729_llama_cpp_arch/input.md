# llama.cpp Architecture

Draw a three-section top-to-bottom layout for the llama.cpp project.

## Section 1: Core Library

Four stacked layer bands (each a container with components):
- **Model Layer** — GGUF format, tokenizer, weight loading, quantization formats.
- **Execution Layer** — compute graph, tensor operations, memory management.
- **Graph Layer** — operator definitions, kernel dispatch, shape inference.
- **Backend Layer** — CPU (BLAS), CUDA, Metal, Vulkan backends.

## Section 2: Inference Execution Flow

A horizontal 6-stage pipeline showing the inference path:
prompt → tokenize → embed → forward pass → sample → detokenize → output.
Connect with solid arrows left → right.

## Section 3: Server Architecture (llama-server)

Routes → request queue → context (slots) → model eval → response.
Show how concurrent slots share the model context.

## Design Specification

### Canvas
- 1400 × 1060, background `#FFFFFF`.

### Layout topology
- Title centered at top (y≈36).
- **Section 1 — Core Library** occupies the upper third (y≈88 to y≈628).
  - Four layer bands stacked vertically; first band starts at y=88.
  - Band height 120, vertical gap 20 between bands (so bands at y ≈ 88, 228, 368, 508).
  - Bands span full content width: x=40, width=1320.
  - Layer label text sits at the band's top-left interior (x≈58, y≈ band_top+22).
  - Component cards sit in a single row inside each band (row top ≈ band_top+42).
- **Section 2 — Inference Flow** is a single horizontal panel (y≈648, height 124).
  - 6 stage cards in one row, equal spacing, left→right.
- **Section 3 — Server Architecture** is the bottom panel (y≈786, height 250).
  - A central `server_context` block (x≈510, width 520) holds 3 slot cards in a row.
  - I/O components flank it left and right, all centered on the same horizontal line (y≈912) as the `server_context` center.
- Content is data-driven: components are defined in lists and rendered programmatically.

### Palette (exact hex)
Accents (8 total = 4 layer tints + 4 matching strokes), Okabe-Ito (S2 Categorical, colorblind-safe):
- Model Layer — fill `#FAEED1`, stroke `#E69F00` (orange).
- Execution Layer — fill `#E1F2FB`, stroke `#56B4E9` (sky blue).
- Computation Graph Layer — fill `#D1EEE6`, stroke `#009E73` (green).
- Backend Abstraction Layer — fill `#D1E6F1`, stroke `#0072B2` (deep blue).

Neutrals (grays, not counted as accents):
- Primary text `#222222`, subtitle text `#555555`.
- Connectors / arrowheads `#4D4D4D`.
- Neutral card stroke (inference + server sections) `#555555`.
- Card fill `#FFFFFF`, section panel fill `#F7F7F7`, panel border `#CCCCCC`.

All text is dark on light fills — no contrast correction needed. All fills are light pastels (L>0.8); all accent strokes are mid-luminance (0.2<L<0.8), so there is no within-channel luminance clash.

### Shape vocabulary
- **Layer band** → rounded rect (1320×120, rx=8), fill=layer tint, stroke=layer stroke, sw=1.5, node kind `layer`.
- **Component card** → rounded rect (rx=6, sw=1.5), white fill; stroke INHERITS the parent layer's accent stroke (visual grouping). Card height ≈66; widths vary (e.g. 300–360 for text cards, 140 for small backend-device chips).
- **Inference stage card** → rounded rect (188×56, rx=6), white fill, neutral stroke `#555555`.
- **server_context container** → rounded rect (520×180, rx=8), white fill, neutral stroke `#555555`, node kind `block`.
- **Server slot / I/O card** → rounded rect (rx=6), white fill, neutral stroke `#555555`. Slot cards 150×72; I/O cards 90 tall.
- **Section panel** → rounded rect (1320×124 or ×250, rx=8), fill `#F7F7F7`, border `#CCCCCC` sw=1, role=`background`.

### Typography
- Title: 20, bold, `#222222`, centered.
- Section headers and layer-band labels: 14, bold, `#222222` (headers left-aligned at panel interior; layer labels left-aligned inside each band).
- Card titles: 12, bold, `#222222`, centered, placed at ≈36% of card height.
- Card subtitles: 10, regular, `#555555`, centered, placed at ≈70% of card height.
- `server_context` block: title 12 bold `#222222`; descriptive lines 10 `#555555`.

### Edges
- All connectors: stroke `#4D4D4D`, stroke-width 1.5, solid.
- Arrowhead marker (defined once) filled `#4D4D4D`.
- **Layer dependency spine**: top→bottom arrows linking each layer band to the one below (bottom of upper → top of lower), conveying the dependency/abstraction stack.
- **Inference flow**: left→right arrows between consecutive stage cards (right of one → left of next).
- **Server flow**: `server_routes` → `server_queue` → `server_context` → `server_response`, left→right.
- No dashed edges.

### Design rationale
- One Okabe-Ito hue per library layer makes layer identity immediately readable while staying colorblind-safe; the pastel fill + mid-luminance stroke pairing avoids luminance clash between fill and stroke.
- Cards inherit their parent layer's stroke so a card is visually claimed by its band without adding new colors — the whole palette stays at exactly 8 accents.
- Inference and Server sections deliberately use only neutral gray: they are process/flow concerns, not the layered architecture, so color is reserved to reinforce that distinction.
- Section panels (role=`background`) sit behind their contents to separate the three concerns visually without competing with the figure.
- Server I/O components are aligned on the `server_context` centerline so the left-flank → context → right-flank flow reads as a single horizontal pipeline.
