# SVG Architecture Design Specifications

## Color Palette Library

Color encodes **information**, not decoration. This skill ships multiple preset palettes — **pick by diagram type** (see the decision guide), not by aesthetic preference. Each scheme is pre-verified against the evaluator (accent count ≤ 12, no luminance clash) and tuned for a specific visual task. Categorical palettes (Okabe-Ito etc.) are optimized for class separation in scatter/line charts and look chaotic as large fills — don't use them where a monochrome or semantic scheme fits.

### How to choose

| Diagram type | Scheme | Rationale |
| :--- | :--- | :--- |
| Multi-module framework (≥4) / general architecture / **unsure** | **S1 Monochrome Blue** | Single hue, luminance tiers — avoids "too many colors"; grayscale-safe |
| Categorical / data-flow (2–4 classes needing hue distinction) | S2 Categorical | Colorblind-safe hue separation for distinct classes |
| Cloud / system topology (component-type semantics) | S3 Semantic | Each component type has a fixed color, consistent across diagrams |
| Diagram with one focal element (innovation / core module) | S4 Duotone | Cool family + single warm focal accent |
| Grayscale print / technical report | S1 | Pure luminance ramp is inherently gray-safe |

**Default = S1.** When in doubt, a single-hue luminance ramp is always safer than multi-hue.

### Scheme 1: Monochrome Blue (default)

Single hue (Nature Blue), four luminance tiers, **unified dark stroke**. Layers are distinguished by fill lightness (ΔE 8–12, spread 3.6 — uniform), not by hue. Op cards stay white so they don't inflate the accent budget. The most克制/uniform scheme; ideal when modules ≥ 4.

| Tier | Fill | Stroke (unified) | Suggested use |
| :--- | :--- | :--- | :--- |
| L1 (lightest) | `#D5E1EB` | `#1B3A5C` | Input / frontend |
| L2 | `#BBCEDF` | `#1B3A5C` | Processing |
| L3 | `#9BB9D1` | `#1B3A5C` | I/O / transport |
| L4 (darkest) | `#769EBF` | `#1B3A5C` | Output / storage |

*Evaluator: 5 accents, no clash. ΔE(adj fill) = 8.3 / 9.7 / 11.9.*

### Scheme 2: Categorical (colorblind-safe)

Okabe-Ito (Nature Methods 2011, Bang Wong), the de-facto standard for accessible categorical figures. Use **only when distinct classes need hue separation** (2–4 groups); do not use for ≥5 side-by-side layers (switch to S1). Two fill modes: colored tint (richer, 8 accents) or white (most克制, 4 accents — color lives in the border only).

| Class | Fill (tint) | Fill (white mode) | Stroke |
| :--- | :--- | :--- | :--- |
| Orange | `#FAEED1` | `#FFFFFF` | `#E69F00` |
| Sky Blue | `#E1F2FB` | `#FFFFFF` | `#56B4E9` |
| Bluish-Green | `#D1EEE6` | `#FFFFFF` | `#009E73` |
| Deep Blue | `#D1E6F1` | `#FFFFFF` | `#0072B2` |

*Evaluator: 8 accents (tint) / 4 accents (white), no clash.*

### Scheme 3: Semantic (cloud / system architecture)

Component **type** → fixed color, consistent across every diagram (ArchiMate / AWS-diagrams convention). Op cards are white-filled; the color lives entirely in the stroke + a small type label. This keeps the accent count low even with many components.

| Component type | Stroke | Fill |
| :--- | :--- | :--- |
| Network (LB, gateway) | `#3498DB` | `#FFFFFF` |
| Compute (app, instance) | `#E67E22` | `#FFFFFF` |
| Storage | `#27AE60` | `#FFFFFF` |
| Security | `#E74C3C` | `#FFFFFF` |
| Database | `#9B59B6` | `#FFFFFF` |

*Evaluator: 5 accents, no clash. To group components into a cluster, wrap them in a near-white container (`#F7F7F7`) with a `#CCCCCC` border — neutrals, not counted.*

### Scheme 4: Duotone (focal highlight)

A tight cool family (3 hues) for the body, plus **one warm focal accent** for the single most important element. The warm color pops against the cool background without redesigning the palette. Use when the diagram has a clear "hero" (innovation point, loss module, key output).

| Role | Fill | Stroke |
| :--- | :--- | :--- |
| Cool 1 (Indigo) | `#CDD2F6` | `#5B6EE1` |
| Cool 2 (Cyan) | `#BFDFED` | `#3D9FC7` |
| Cool 3 (Teal) | `#B0DDD9` | `#2EA69A` |
| **Focal (Amber)** | `#F6D0B4` | `#E8833A` |

*Evaluator: 8 accents, no clash. Reserve the amber for exactly one element; using it on multiple nodes defeats the focal intent.*

### Structural neutrals (all schemes, not counted as accents)

| Element | Hex | Usage |
| :--- | :--- | :--- |
| Background | `#FFFFFF` | Canvas (white is the default) |
| Container / Divider | `#D5D5D5` or `#CCCCCC` | Layer frames, cluster wrappers |
| Cluster fill | `#F7F7F7` | Near-white grouping background |
| Text (Primary) | `#000000` | Main labels and headers |
| Text (Secondary) | `#333333` | Sub-labels and formulas |
| Connectors | `#4D4D4D` or `#666666` | Arrows / lines (gray, not colored) |

### Design principles (apply to all schemes)

1. **White-dominant** — ≥70% of the canvas should be white/near-white. Color is a border/label language, not a fill-everything language.
2. **Op cards stay white** — only layer/cluster containers take colored fills; individual operation cards are `fill="white"` so they don't bloat the accent count.
3. **≤3 chromatic families visible at once** (S1 has 1, S3 has up to 5 but only as strokes). If a diagram needs more, it's too complex — split it.
4. **Connectors are gray** (`#4D4D4D`), never colored. Color on a line implies data-flow semantics that belong to the node, not the edge.
5. **One focal accent max** — if highlighting, pick exactly one element (S4 amber, or a saturated stroke swap in S1). Multiple "highlights" = no highlight.

## Layout Principles

1.  **Grid-Based**: Use a 1200x800 base canvas.
2.  **Layering**: Use vertical sections (Layers) and horizontal stages (Stages).
3.  **Spacing**:
    *   Margin: 20px
    *   Section Padding: 10px
    *   Component Gap: 15px
4.  **Typography**:
    *   Main Header: 18px, Bold
    *   Sub-header: 14px, Bold
    *   Body Text: 12px, Regular
    *   Math/Formula: 13px, Monospace/Italic

## Reusable Components

### 1. Rounded Container
```svg
<rect x="x" y="y" width="w" height="h" rx="10" ry="10" fill="#HEX" stroke="#333" stroke-width="1" />
```

### 2. Arrow Marker
```svg
<defs>
  <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#333" />
  </marker>
</defs>
```
