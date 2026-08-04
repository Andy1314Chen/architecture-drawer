# CI/CD 部署流水线 — Deployment Pipeline Flowchart

A top-to-bottom **process flowchart** for a realistic CI/CD pipeline with four
quality-gate decisions. Color encodes the standard flowchart role vocabulary:
green = start/end terminator, blue = process, yellow = decision, orange = I/O,
purple = subprocess (double border). Gray junction circles mark merge points
where multiple failure branches converge.

## Pipeline stages & flow

### Trigger
1. **Start** (green terminator) — a commit is pushed to `main` or a PR merged.
2. **Webhook** (orange hexagon, I/O input) — push event received.

### Build
3. **Checkout & Build** (purple subprocess) — `git clone`, dependency install
   (`npm ci`), compile / bundle the artifact.
4. **Build OK?** (yellow decision):
   - **No** → enters the failure column (left).
   - **Yes** → continues down the spine.

### Quality gates
5. **Lint & Security Scan** (purple subprocess) — ESLint, MyPy type check, SAST
   vulnerability scan.
6. **Lint OK?** (yellow decision):
   - **No** → failure column.
   - **Yes** → continues.
7. **Test Suite** (purple subprocess) — unit, integration, and end-to-end tests.
8. **Tests Pass?** (yellow decision):
   - **No** → failure column.
   - **Yes** → continues.

### Staging & production
9. **Deploy to Staging** (blue process) — `kubectl apply`, rolling update on the
   staging cluster.
10. **Smoke Tests** (blue process) — health probes, API contract checks.
11. **Smoke OK?** (yellow decision):
    - **No** → failure column.
    - **Yes** → continues.
12. **Deploy to Prod** (blue process) — canary (10 % traffic) → blue-green
    promotion.
13. **Released** (green terminator) — happy-path end.

### Failure convergence (left column)
All four decisions branch **No** to the left. The first failure route hits
**Notify Failure** (blue process — Slack / Email alert); subsequent failure
routes merge via gray junction circles and all converge on a single **Failed**
green terminator. The **Yes** paths stay on the vertical center spine.

## Design Specification

### Canvas
- 1000 × 1520 px, background `#FFFFFF`.
- PNG export rasterized at 2× width (2000 px) for crisp high-DPI display (SVG
  is vector, so the upscale is lossless).

### Layout topology
- **Center spine** at x ≈ 500 (~50% width): the happy path runs straight down
  the middle, top-to-bottom.
- **Failure column** at x ≈ 210 (~21% width), on the LEFT of the spine.
- **Vertical center-to-center node spacing ≈ 105–120 px** on the spine; the
  84 px-tall diamond needs ≥84 px gap, so the c2c around decisions is ~118 px.
- Spine node y-centers (top→bottom): Start ≈105 → Webhook ≈207 → Checkout ≈312
  → Build-OK? ≈430 → Lint ≈548 → Lint-OK? ≈666 → Tests ≈784 → Test-OK? ≈902 →
  Staging ≈1010 → Smoke ≈1115 → Smoke-OK? ≈1233 → Deploy ≈1351 → Released ≈1456.
- Failure column aligns to **each decision's y-level**: Notify Failure at y≈430
  (Build-OK row), junction m1 at y≈666 (Lint-OK row), junction m2 at y≈902
  (Test-OK row), Failed terminator at y≈1233 (Smoke-OK row). Shared-y alignment
  lets each "No" branch travel as a clean horizontal line.
- No container/group boxes — the two columns are the only spatial grouping.

### Palette (exact hex)
Five role accents (each fill paired with a darker sibling-hue border); text
colors are neutrals.
- **Terminator (start/end)** — fill `#D5E8D4`, stroke `#82B366` (green).
- **Process** — fill `#DAE8FC`, stroke `#6C8EBF` (blue).
- **Decision** — fill `#FFF2CC`, stroke `#D6B656` (yellow).
- **I/O (hexagon)** — fill `#FFE6CC`, stroke `#D79B00` (orange).
- **Subprocess (double border)** — fill `#E1D5E7`, stroke `#9673A6` (purple).
- **Junction merge point** — fill `#B0B0B0`, stroke `#666666` (neutral gray;
  role-neutral, NOT counted as an accent).
- **Text** — main node label `#1A1A1A` (INK); subtitle / sub-label / branch flag
  `#555555` (SUB). All dark text on pastel fills → WCAG-legible.

### Shape vocabulary
- **Terminator** → circle, radius 30; stroke 1.8 px.
- **Process** → rounded rect 220 × 56, corner radius rx=7; stroke 1.4 px.
- **Decision** → diamond 170 × 84; stroke 1.6 px.
- **I/O (input)** → hexagon 240 × 56; stroke 1.4 px.
- **Subprocess** → rounded rect 220 × 56 (rx=7) PLUS a decorative inset border
  (rect inset 4 px on every side, rx=5, stroke-only, no fill) rendering the
  classic double-border subroutine symbol; outer stroke 1.4 px, inset 1.0 px.
- **Junction** → small circle, radius 6; stroke 1.2 px.

### Typography
- Font tiers (exact): **20** diagram title / **14** node label / **12** title
  subtitle / **10** node sub-label & branch flag.
- Diagram title 20 px bold `#1A1A1A`, centered at top (y≈38); English subtitle
  12 px `#555555` directly below (y≈62).
- Node labels: 14 px bold `#1A1A1A`; tool-name sub-label 10 px `#555555`, ~14 px
  below the main label, both center-anchored.
- Decision: Chinese label at cy−6, English sub-label at cy+14.
- **Bilingual**: every node carries a Chinese main label + an English/tool-name
  sub-label (e.g. "检出 & 构建" / "git clone · npm ci · compile").
- **Terminator labels are Chinese-only (开始 / 已发布 / 失败), placed OUTSIDE the
  circle** (~46 px to the side) — the r=30 circle has no room for legible CJK.

### Edges
- Color `#4D4D4D` (neutral gray), width **1.8 px**, arrowhead marker on every
  edge (single `ah` arrow head, same `#4D4D4D`).
- **All edges are solid** (no dashed lines).
- **Spine routing**: vertical, node.bottom → next node.top.
- **Failure routing**: each decision's LEFT port → failure column (horizontal to
  Notify / m1 / m2 / Failed), then converge downward Notify → m1 → m2 → Failed.
- **Yes/No flags**: every decision edge carries a perpendicular-offset label —
  "是 Yes" on the down-spine, "否 No" on the left-to-failure branch — 10 px
  `#555555`, offset clear of the line.

### Design rationale
- **Two-column flowchart, not architecture layers**: the diagram is a sequential
  pipeline, so a vertical center spine carries the happy path and a parallel
  left column collects every failure exit — failure handling never crosses the
  spine.
- **Junctions reuse decisions' y-levels** so each "No" arrow is a clean
  horizontal line; m1/m2 then chain downward so all failures funnel into one
  Failed terminator. This collapses 4 failure exits into 1 endpoint.
- **Color = flowchart role** (green/blue/yellow/orange/purple), not layer or
  team. Each border hue is the darker sibling of its fill (e.g. blue fill
  `#DAE8FC` → blue border `#6C8EBF`) — a 5-accent scheme rather than 10.
- **Subprocess vs process distinction**: build / lint / tests are purple
  double-border subprocesses (multi-step, invoke tools); staging / smoke /
  deploy are plain blue processes (single deploy actions). The decorative inset
  border is NOT a separate node — it only renders the double-line symbol.
- **Terminator text lives outside the circles** because a 30-px-radius green
  terminator is too small for legible CJK; placing 开始/已发布/失败 beside the
  node keeps the circle a pure visual start/end marker.
- **Wide process/hexagon rects (220–240 px)** accommodate bilingual labels and
  the long tool-name sub-labels (`canary → blue-green`, `kubectl rolling`).
