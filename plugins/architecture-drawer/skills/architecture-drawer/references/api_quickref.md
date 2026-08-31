# API Quickref — SVGDrawer & layout helpers

One-page signatures + the known traps. Read this instead of grepping
`scripts/svg_utils.py` for signatures (each source grep costs a model turn;
this page answers the same questions without one).

## Layout helpers (pure geometry — they compute, you draw)

```python
from svg_utils import layout_grid, layout_row, layout_band, layout_radial

layout_grid(n, x0, y0, cols, w, h, gx, gy) -> [(x, y), ...]
    # n cells, cols per row, left-to-right then down; (w+gx)/(h+gy) pitch.
    # The card-array primitive: chips in a band, station rows, pipeline stages.

layout_row(items, x0, y0, gx) -> [(x, y0, w), ...]
    # items = list of widths. Variable-width flow: source -> queue -> engine.

layout_band(title, x, y, w, h, pad=24, title_h=28) -> (bx, by, bw, bh)
    # Drawable interior of a titled container — contents placed inside
    # never collide with the title strip or band edges.

    # ZERO crossings by construction. positions: {id: (x,y,w,h)};
    # sides: {nid: (neighbor_side, hub_side)} ready for connect().
```

State the array, not the coordinates: `for (x, y) in layout_grid(6, bx, by, 3, 120, 40, 30, 24)` replaces
six hand-computed positions and the gutter/slope arithmetic that places them.

## Drawing (register node_id so connections validate)

```python
d.rect(x, y, w, h, rx=5, fill=, stroke=, node_id=, node_kind="op", role=, bbox=)
d.circle(cx, cy, r, fill=, node_id=, node_kind="junction")
d.text(x, y, s, font_size=, anchor="middle", fill=, weight=)   # y is the CENTER line
d.line(x1, y1, x2, y2, stroke=, marker_end=, role="decoration")
d.connect(from_id, from_side, to_id, to_side, stroke=, dashed=, marker_end="arrowhead")
```

## Traps (each has cost a replay session a repair round)

- **`connect()` draws `marker_end="arrowhead"` by default** — pass `marker_end=None` explicitly for a plain
  connector. (`d.line` defaults to no arrow; ask only if you want one.)
- **Container cards**: give them `node_kind="layer"` (or `role="layer"`) when they are pure containers; use
  `node_kind="op"` only when something must `connect()` to them. Contained chips are exempt from the
  spacing check; equal-pitch arrays are protected from `auto_refine`.
- **`d.text` y is the CENTER line** (`dominant-baseline`), not the top — `y = box_y + h/2` for in-box labels.
- **Deep literals (>3 nesting) belong in named constants** — inline nested tuples/tuples-in-lists cause
  bracket-mismatch edits (observed: 3 wasted edit rounds counting parens).
- **`auto_refine(drawer)`** fixes gutter + spacing; it refuses containment pairs and grid arrays on
  purpose. Route/dangle/crossing fixes are always manual.
