# Integrated Space-Ground Satellite System Architecture

天地一体化卫星系统架构分层图 (Integrated Space-Ground Satellite Architecture) — a layered
diagram mapping satellite subsystems across orbital-altitude bands (bottom = ground,
top = deep space), with a horizontal functional color code distinguishing what each
satellite does (comm / nav / sensing / manned).

Bottom = ground, top = deep space. Five vertical layers, with a horizontal functional
color code distinguishing satellite subsystems.

## Layers (bottom → top)

1. **Ground Segment (地面支撑层, ~80 km band)** — ground stations, TT&C, mission control,
   data receiving antennas, satellite control center. White-filled nodes.
2. **LEO Constellation (低地球轨道, ~210 km band, the densest layer)** — three sub-rows:
   a mesh of low-orbit comm satellites (starlink/千帆 style) with inter-satellite links;
   a row of sensing satellites (optical/radar/resource) and a remote-sensing data source;
   a small science-probe sub-row; plus the manned 天宫 space station.
3. **MEO Navigation (中地球轨道, ~125 km band)** — navigation constellation (北斗/GPS/Galileo)
   arranged as a staggered two-row ring with downward coverage beams.
4. **GEO / IGSO (地球静止轨道, ~120 km band)** — geostationary relay, broadcast, weather,
   and strategic-warning satellites riding a single dashed orbital arc.
5. **Deep Space (深空探测 / 拉格朗日点, ~115 km band)** — space telescopes and probes near
   the L1/L2 Lagrange points, plus a note on highly-elliptical (闪电) orbits.

## Functional color code (horizontal)

- **Blue** = communication payloads and data-relay links (incl. 天链 relay)
- **Green** = navigation / positioning (北斗, GPS, Galileo)
- **Orange** = sensing / earth observation / research probes
- **Slate** = manned platforms / stations / structural (天宫, ground stations)

Each layer contains nodes colored by their function; bidirectional arrows show sensing
(up) and control (down) flows between layers.

## Design Specification

### Canvas
- Size: **1400 × 1180**, background `#FFFFFF`.

### Layout topology
- **Top band (y≈0–100):** centered title (y≈34) + subtitle (y≈62) + centered **legend row** (y≈88).
- **Left altitude scale:** vertical line at **x≈108** spanning y≈120→960, with the bold
  heading "轨道高度" at its top (y≈105). The diagram content begins to the right of it.
- **Layer-band zone:** five rounded-rect bands stacked vertically, spanning x≈150→1350
  (width ≈1200), with **alternating neutral fills** and a bold layer header at the
  top-left of each band. From top to bottom (deep space → ground), band heights are
  roughly **115, 120, 125, 210, 80** px; the LEO band is intentionally the tallest
  because it holds three sub-rows plus the space station.
- **Right margin** holds right-aligned notes (闪电轨道 / 拉格朗日点) in the top band.
- **Bottom:** an earth-horizon curve (concave-up) spanning the full width peaking near
  y≈1005, with a ground-segment caption centered below it; a two-line footer at y≈965/987.
- Minimum node spacing ≈ 120–140 px horizontally; sub-rows within a band are vertically
  offset ~55–60 px.

### Palette (exact hex)
- **Blue (comm/relay):** fill `#DBEAFE`, stroke `#2563EB`
- **Green (nav):** fill `#DCFCE7`, stroke `#16A34A`
- **Orange (sensing/research):** fill `#FFEDD5`, stroke `#EA580C`
- **Slate (manned/station/ground):** fill `#E2E8F0`, stroke `#475569`
- **All text & arrowheads:** neutral `#000000` (black) — no contrast issues.
- **Scale/divider/orbital-path lines:** `#A8A8A8` (neutral gray).
- **Alternating layer-band fills:** `#F6F6F6` / `#EFEFEF` (top→bottom alternates; LEO band uses the darker of the two).
- **Earth horizon:** fill `#E4E4E4`, stroke `#9A9A9A`.
- Ground-segment nodes use a **white fill** (`#FFFFFF`) with the slate stroke.
- Coverage beams are green fill at **0.55 opacity** with a dashed green stroke.
- Accents = the 4 hue families (≤4). Everything else is neutral gray (R==G==B).

### Shape vocabulary
Each satellite concept maps to one SVG primitive; **functional hue colors the fill,
shape distinguishes role:**
- **Circle** — generic satellite. Comm nodes r=12; nav nodes r=15. (`circle`)
- **Rounded square (rx=2)** — relay/station/structural or sensing source. GEO nodes
  s=30; sensing nodes s=22; ground-station nodes s=34 (white fill); 天宫 station s=54,
  stroke-width 2.0 (heavier, the largest node). (`rect` rounded)
- **Triangle (apex up)** — science probe / deep-space telescope. Deep-space r=14;
  science sub-row r=13. (`polygon`, apex at cy−r, base at cy+0.8·r)
- **Diamond/rhombus (4-point)** — Lagrange-point marker (L1/L2), half-width 9, slate.
  (`polygon` with 4 vertices)
- **Legend swatch:** small circle r=7 (light fill, dark stroke, sw 1.4).
- **Layer band:** rounded rect rx=10, no stroke, opacity 0.9, `role="background"`.
- **Orbital path (GEO arc):** a single dashed quadratic Bézier spanning the band.
- **Coverage beams (MEO):** downward dashed triangles below each top-row nav satellite.
- **Earth horizon:** large concave-up quadratic fill across the canvas bottom.

### Typography
- **Only 3 font tiers** (do NOT invent a 4th):
  - **Title:** 22, bold, black, centered.
  - **Layer header:** 15, bold, black, left-anchored at band top-left.
  - **Body / labels / legend / scale / footer:** 12, black (weight `normal`, except
    天宫 label and ground-station labels which are `bold`).
- Satellite name labels sit **above** the node (offset ~−24 to −28) for circles/squares
  in upper layers, **below** (offset ~+24 to +26) for sensing/science sub-rows; the
  天宫 station label sits **inside** the large square.
- Scale tick labels are **right-anchored** (to the left of the scale line); band-internal
  captions and the footer are start-anchored; right-margin notes are end-anchored.
- **Bilingual:** Chinese titles/labels throughout; an optional English gloss in the
  diagram header line. Title = "天地一体化卫星系统架构分层图"; subtitle =
  "涵盖轨道高度 · 卫星分类 · 数据流向".

### Edges
- **Single shared arrowhead marker** (`ah`, black) for every directional edge.
- **LEO comm mesh:** left↔right connectors between consecutive comm circles, stroke
  `#2563EB`, width 1.4, **no marker** (a link mesh, not a flow).
- **Validated relay chain (the concrete data path, draw these as real edges):**
  remote-sensing source `src` → GEO relay `geo_relay` → ground control `gs3`, each
  stroke `#2563EB` width 1.8 with black arrowhead (sensing data flowing up, then down).
- **LEO↔MEO inter-satellite link:** comm4(top)↔meo3(bottom), stroke `#2563EB` width 1.3,
  **dashed**, no marker — a cross-layer constellation link.
- **Decorative (role="decoration", not real edges):** ground uplink/downlink pairs
  (solid BLUE up with arrowhead + dashed BLUE down) drawn beside each ground station;
  GEO orbital arc (gray `#A8A8A8` dashed 5,4); MEO coverage beams (dashed green
  triangles); altitude scale line + ticks (gray `#A8A8A8`).
- Routing: keep edges vertical between layers; mesh links horizontal within the LEO row;
  never let edges cross nodes.

### Design rationale
- **Pastel-fill + same-family dark-stroke per hue** keeps the four functional families
  readable while staying soft; **all text and arrowheads neutral black** eliminates any
  dark/light channel clash between the two render channels.
- **Shape encodes role, color encodes function** — so the same color (e.g. orange) reads
  differently for a sensing square vs a science triangle, and slate reads differently
  for a manned station vs a ground node (white fill).
- The **left altitude scale** is the spine that ties the stacked bands to real orbital
  altitudes (0 / 200 / 2,000 / 20,200 / 35,786 km / L1-L2), making "bottom = ground,
  top = deep space" literal rather than decorative.
- The **legend row** is mandatory: it is the only place the four hue families are named,
  so the whole diagram is self-explanatory without the footer.
- The **LEO band is the tallest** because it carries the most nodes (three sub-rows +
  the space station) and the dense comm mesh that is the diagram's structural backbone.
- Only the **relay chain and the LEO mesh** are "real" validated edges; coverage beams,
  orbital arcs, and ground up/down arrows are decoration — this keeps the evaluation
  graph small and meaningful rather than noise.
