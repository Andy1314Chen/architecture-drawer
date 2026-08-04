# MLIR AI Compiler — Multi-Stream Execution Pipeline

Draw a 4-layer MATRIX diagram of an AI-compiler runtime pipeline. Four
horizontal layer bands stack top → bottom (the matrix rows); within each band
stages and streams read left → right (the matrix columns). A vertical numbered
spine on the far left links the four bands into one downward flow.

## Structure

A matrix grid: 4 horizontal layers (top → bottom) × multiple stage columns
(left → right). Data and execution flow left → right inside every band.

### Layer 1 — Graph Optimization (compile-time · static DAG & fusion)
- Operator fusion, algebraic reordering, parallel-branch detection.
- A 3-node DAG (Conv → BatchNorm → ReLU) feeding an Add node; a parallel
  branch (no data dependency) feeds Add's second input.
- Vertical-fusion group drawn as a dashed box around Conv+BN+ReLU → fused into
  one kernel K1. A curved reorder-swap arc marks a commutative D↔C swap.

### Layer 2 — Runtime Scheduling (async launch · priority · load balance)
- A host-side Task Scheduler (CPU) fans out to three device streams:
  Stream 0 · Comm (high priority), Stream 1 · Compute (kernel queue),
  Stream 2 · D2D Copy (low priority).
- Each stream owns a device-side queue of small task chips (T / K / cp).

### Layer 3 — Hardware Concurrency (multi-stream overlap · SM partition)
- A GPU SM array (4×4 grid) partitioned into MPS/MIG zones: compute, copy, comm.
- A horizontal time axis (T0→T3) with three swimlanes — Compute (Tensor Core),
  Copy D2D (layout xform), Comm H2D (next batch) — whose bars overlap in time.

### Layer 4 — Memory Pool (lifetime · in-place · workspace reuse)
- A 4-quadrant ring buffer (Memory Pool) whose colored arcs encode ownership.
- Three reuse-strategy cards: In-place Update, Workspace Reuse,
  Producer→Consumer (L2) Locality; a full-width Buffer Lifetime Timeline below.

### Cross-cutting
- Far-left dashed vertical spine (x≈26) with numbered circles 1–4 marking the
  bands; downward-triangle verbs in the band gutters: "lowers", "dispatches",
  "reclaims".
- Right-edge annotation cards in every band explain each stage's technique.

## Design Specification

### Canvas
- Exactly 1440 × 1200 px; background fill `#F7F7F7` (light gray, NOT white).
- 50-px left/right margins; bands span x=50 → x=1390 (width 1340).

### Layout topology
- Four full-width horizontal bands stacked with small gutters:
  - Band 1 Graph Optimization — y≈64, height≈266, gutter "lowers" before Band 2.
  - Band 2 Runtime Scheduling — y≈340, height≈235, gutter "dispatches".
  - Band 3 Hardware Concurrency — y≈585, height≈340, gutter "reclaims".
  - Band 4 Memory Pool — y≈935, height≈235.
- Each band: header label + subtitle at top-left (x≈72); content fills the rest.
- Recurring column zones within a band: left body (x≈70–700), middle task area
  (x≈700–860), right legend cards (x≈870–1380).
- Left pipeline spine at x≈26 runs the full band height, above everything.
- Minimum node spacing ≈ 50 px between siblings; op-row nodes ≈100 wide.

### Palette (exact hex)
- Dark strokes (5 accents): PURPLE `#9673A6`, BLUE `#2E5AAC`, ORANGE `#B45F06`,
  GREEN `#82B366`, YELLOW `#D6B656`.
- Light fills (3 accents): ORANGE_F `#FFCC99`, GREEN_F `#D5E8D4`, BLUE_F `#DAE8FC`.
- Neutrals (NOT accents): GRAY_S `#888888`, GRAY_D `#555555`, GRAY_L `#BBBBBB`,
  band fill `#FCFCFC`, GPU chip fill `#F2F2F2`, text default `#222222`,
  mid-gray `#333333`, title `#1A1A1A`.
- Role → color map: PURPLE = fusion & reordering (Band 1); BLUE = scheduling,
  comm stream, SM comm (Band 2); ORANGE = compute stream/kernel/SM compute
  (Band 3); GREEN = copy stream/SM copy; YELLOW = memory pool (Band 4).
- Band → accent stroke: Band1 PURPLE, Band2 BLUE, Band3 ORANGE, Band4 YELLOW.
- CONTRAST FIX: GREEN `#82B366` and YELLOW `#D6B656` text FAILS WCAG on light
  or white fills — render such text labels in `#1A1A1A`, keeping the accent only
  for strokes/fills. PURPLE/BLUE/ORANGE are dark enough for bold labels on white.

### Shape vocabulary
- Band container → rounded rect, width 1340, height per band, rx=12, fill
  `#FCFCFC`, stroke = band accent, stroke-width 2.
- Op node (DAG) → rounded rect ~100×52, rx=6, fill `#FFFFFF`, stroke = accent,
  sw 1.6 (Conv/BN/ReLU PURPLE; Add BLUE).
- Parallel-branch node → rounded rect ~130×40, rx=6, white fill, BLUE stroke.
- Stream box → rounded rect ~214×42, rx=6, fill = tinted accent, stroke =
  accent, sw 1.5.
- Scheduler → rect ~196×116, rx=10, fill `#DAE8FC`, BLUE stroke 1.6.
- GPU chip → rounded rect ~214×244, rx=10, fill `#F2F2F2`, GRAY_S stroke 1.4.
- SM cell → rounded rect ~36×36, rx=2, fill = tinted accent, colored stroke 1
  (compute=ORANGE_F/ORANGE, copy=GREEN_F/GREEN, comm=BLUE_F/BLUE).
- Timeline bar → rounded rect, height 40, rx=5, fill = tinted accent, colored
  stroke 1.5 (variable width encodes duration).
- Task chip → small rounded rect ~36×24, rx=4, white fill, colored stroke 1.1.
- Legend / annotation card → rounded rect, rx=8, white fill, colored stroke 1.4,
  height auto-grows with wrapped body text.
- Fusion group → rounded rect, fill none, dashed accent stroke 1.5
  (dasharray "7,4").
- Fused-kernel badge → rounded rect ~160×42, rx=6, fill `#FFCC99`, ORANGE 1.4.
- Ring buffer → 4 quadrant arcs, radius ≈56, stroke-width 15 (no fill), colored
  per quadrant (YELLOW/ORANGE/GREEN/BLUE).
- Spine node → circle r≈13, white fill, GRAY_S stroke 1.5; verb marker = small
  downward triangle (polygon) in GRAY_S.

### Typography
- Title 20 px bold `#1A1A1A`, centered.
- Subtitle 12 px `#555555`, centered (the four-stage arrow string).
- Band header 14 px bold in band accent color (left-aligned).
- Band subtitle 12 px `#555555`.
- Node / stream title 12 px bold `#222222` (centered in box).
- Node subtitle / small annotation 10 px `#555555`.
- Timeline "big" bar label 12 px bold `#222222`; other bars 10 px bold.
- Numbered spine labels 12 px bold `#555555`; verb labels 10 px `#888888`.
- Font family Arial, sans-serif throughout; `·` separators and circled numerals
  ①②③ for enumerated sub-techniques.

### Edges
- One arrow-head marker per accent color plus one neutral gray
  (ap=Purple, ab=Blue, ao=Orange, ag=Green, ah=Gray).
- DAG chain edges: solid, stroke-width 1.6, color = source accent (PURPLE for
  the fused chain; GRAY_S where the chain crosses accent boundaries).
- Parallel-branch feed to Add's second input: dashed BLUE 1.5.
- Scheduler → stream: solid BLUE 1.4.
- Reorder-swap indicator: curved dashed arc PURPLE (dasharray "5,3").
- Decorative guides (overlap regions, ring→card links, device-queue loop, MPS
  dividers): thin dashed lines, neutral gray or accent, sw 1.0–1.4.
- Solid strokes for real data flow; dashed for annotations / ownership /
  partitions.

### Design rationale
- Op cards use WHITE fill + colored BORDER (not colored fill) so the palette
  stays at exactly 8 accents — color is carried by strokes, not floods.
- Per-accent arrow markers give each stream/concept a stable visual identity
  along its whole path.
- Near-white band fill `#FCFCFC` lets the saturated accent band-stroke pop while
  staying softer than pure white.
- Fusion groups are dashed overlays on top of the DAG so the original nodes stay
  visible.
- The SM grid is partitioned by MPS/MIG dashed dividers that map columns to
  compute/copy/comm workloads — spatial multiplexing made literal.
- Timeline swimlanes with overlapping bars visualize concurrency; dashed overlap
  guides mark the fully-concurrent window.
- The ring buffer's four colored arcs encode buffer-phase ownership so the
  lifetime concept reads at a glance.
- The left pipeline spine is drawn LAST so its numbers and verb triangles sit on
  top of the bands and are never occluded.
