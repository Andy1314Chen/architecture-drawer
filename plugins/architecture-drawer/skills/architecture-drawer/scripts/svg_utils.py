import html
import math
import re as _re
import subprocess
from pathlib import Path

_INVISIBLE_PAINTS = {"none", "None", None, ""}


def _shape_visible(fill, stroke, opacity):
    """True if a shape renders ANYTHING the eye can see.

    fill=none + stroke=none, or opacity=0, produces no pixels — such a node is
    invisible and must not be used as an edge endpoint (phantom anchor).
    """
    if opacity is not None and opacity <= 0:
        return False
    has_fill = fill not in _INVISIBLE_PAINTS
    has_stroke = stroke not in _INVISIBLE_PAINTS
    return has_fill or has_stroke

def _dash_attr(dashed):
    """Convert a dashed flag/pattern to a stroke-dasharray SVG attribute.

    dashed=False/None -> "" (solid). dashed=True -> the standard "6,3" pattern
    (same as connect()). dashed="4,3" -> a custom dash pattern. This unifies
    dashed rendering across rect/circle/line/path/connect so callers never need
    the raw ``extra='stroke-dasharray="..."'`` spelling.
    """
    if dashed is True:
        return 'stroke-dasharray="6,3"'
    if isinstance(dashed, str) and dashed:
        return f'stroke-dasharray="{dashed}"'
    return ""


_NAMED_COLORS = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000",
    "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
    "cyan": "#00ffff", "magenta": "#ff00ff", "gray": "#808080",
    "grey": "#808080", "silver": "#c0c0c0", "navy": "#000080",
    "maroon": "#800000", "olive": "#808000", "purple": "#800080",
    "teal": "#008080",
}


def normalize_color(value):
    """Normalize a CSS/SVG color to '#rrggbb' (lowercase) or return None.

    Returns None for none/transparent/unparseable colors so callers can skip
    them. Supports #RGB, #RRGGBB, rgb()/rgba() ints, and common named colors.
    """
    if value in _INVISIBLE_PAINTS or value == "transparent":
        return None
    v = str(value).strip()
    if v.startswith("#"):
        h = v[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            try:
                int(h, 16)
                return "#" + h.lower()
            except ValueError:
                return None
        return None
    m = _re.match(r"rgba?\(([^)]+)\)", v)
    if m:
        parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
        nums = []
        for p in parts:
            n = p.rstrip("%")
            try:
                nums.append(float(n))
            except ValueError:
                return None
        if len(nums) >= 3:
            rgb = [min(int(round(nums[i])), 255) for i in range(3)]
            return "#%02x%02x%02x" % (rgb[0], rgb[1], rgb[2])
        return None
    named = _NAMED_COLORS.get(v.lower())
    return named.lower() if named else None


def _hex_rgb(hex_color):
    """Return (r, g, b) ints for a #rrggbb string, or None if unparseable."""
    c = hex_color.lstrip("#")
    try:
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except (ValueError, IndexError):
        return None


def is_neutral(hex_color):
    """True for white/black/grayscale colors (R==G==B) — structural, not accent."""
    rgb = _hex_rgb(hex_color)
    return bool(rgb) and rgb[0] == rgb[1] == rgb[2]


def relative_luminance(hex_color):
    """WCAG sRGB relative luminance in [0, 1]. Higher = lighter."""
    rgb = _hex_rgb(hex_color)
    if rgb is None:
        return 0.5
    r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0

    def chan(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


# Affine transform matrix helpers (matrix(a,b,c,d,e,f) = [[a c e],[b d f],[0 0 1]]).
IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def multiply_matrix(m1, m2):
    """Compose two affine matrices: result = m1 ∘ m2 (m2 applied first)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def transform_point(matrix, point):
    """Apply affine matrix (a,b,c,d,e,f) to (x, y)."""
    a, b, c, d, e, f = matrix
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def parse_transform(value):
    """Parse an SVG transform attribute into an affine matrix.

    Supports matrix()/translate()/scale()/rotate()/skewX()/skewY(), chained.
    Ported from fireworks-tech-graph validate_svg.parse_transform.
    """
    result = IDENTITY
    if not value:
        return result
    for name, raw in _re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)", str(value)):
        vals = [float(v) for v in _re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", raw)]
        name = name.lower()
        cur = IDENTITY
        if name == "matrix" and len(vals) == 6:
            cur = tuple(vals)
        elif name == "translate" and vals:
            cur = (1, 0, 0, 1, vals[0], vals[1] if len(vals) > 1 else 0)
        elif name == "scale" and vals:
            cur = (vals[0], 0, 0, vals[1] if len(vals) > 1 else vals[0], 0, 0)
        elif name == "rotate" and vals:
            ang = math.radians(vals[0])
            rot = (math.cos(ang), math.sin(ang), -math.sin(ang), math.cos(ang), 0, 0)
            if len(vals) >= 3:
                cx, cy = vals[1], vals[2]
                cur = multiply_matrix(multiply_matrix((1, 0, 0, 1, cx, cy), rot), (1, 0, 0, 1, -cx, -cy))
            else:
                cur = rot
        elif name == "skewx" and len(vals) == 1:
            cur = (1, 0, math.tan(math.radians(vals[0])), 1, 0, 0)
        elif name == "skewy" and len(vals) == 1:
            cur = (1, math.tan(math.radians(vals[0])), 0, 1, 0, 0)
        result = multiply_matrix(result, cur)
    return result


class BBox:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def intersects(self, other):
        return not (self.x + self.w <= other.x or
                    other.x + other.w <= self.x or
                    self.y + self.h <= other.y or
                    other.y + other.h <= self.y)

    def contains(self, other):
        """True if this bbox fully encloses `other` (parent-child containment)."""
        return (self.x <= other.x and self.y <= other.y and
                self.x + self.w >= other.x + other.w and
                self.y + self.h >= other.y + other.h)

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    def __repr__(self):
        return f"BBox(x={self.x}, y={self.y}, w={self.w}, h={self.h})"


class Node:
    """A connectable rectangular element (operation, layer, block, ...).

    Registered so that edges (lines/paths) can be validated against it: every
    connection endpoint should land on or near a node border.
    """

    SIDES = ("top", "bottom", "left", "right")

    def __init__(self, node_id, x, y, w, h, kind="op", visible=True, role="node"):
        self.id = node_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.kind = kind  # 'op' | 'layer' | 'block' | 'region' ...
        # Whether the node's shape actually renders anything. Invisible nodes
        # (fill=none + stroke=none, opacity=0, or zero-size) referenced by edges
        # are "phantom anchors" and get flagged by the validator.
        self.visible = visible
        # Semantic role: 'node' (business) | 'decoration' | 'legend' | 'label'
        # | 'background' | 'reserved'. Decorative/legend/background nodes are
        # excluded from business-logic checks (spacing, palette count, etc.).
        self.role = role

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    def edge_point(self, side):
        """Midpoint of a given border side."""
        if side == "top":
            return (self.cx, self.y)
        if side == "bottom":
            return (self.cx, self.y + self.h)
        if side == "left":
            return (self.x, self.cy)
        if side == "right":
            return (self.x + self.w, self.cy)
        raise ValueError(f"Unknown side: {side!r} (expected one of {Node.SIDES})")

    def border_distance(self, px, py):
        """Shortest distance from point (px, py) to the node's rectangular border.

        Returns 0 when the point lies on the border rectangle.
        """
        dx = max(self.x - px, 0.0, px - (self.x + self.w))
        dy = max(self.y - py, 0.0, py - (self.y + self.h))
        return math.hypot(dx, dy)


class Edge:
    """A semantic connection between two points (optionally arrow-terminated).

    path_d holds the actual rendered path data (the `d` attribute) when the
    edge is a curve; the evaluator samples it (bezier/arc) instead of
    approximating by the chord. For straight line edges path_d is None.
    """

    def __init__(self, start, end, edge_id=None, has_arrow=True, label=None, path_d=None, role="edge"):
        self.id = edge_id
        self.start = (start[0], start[1])
        self.end = (end[0], end[1])
        self.has_arrow = has_arrow
        self.label = label
        self.path_d = path_d
        # Semantic role: 'edge' (business) | 'decoration'. Decorative edges
        # (rail casings, echoes) are excluded from crossing/connection checks.
        self.role = role

    @property
    def length(self):
        return math.hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])


class SVGDrawer:
    def __init__(self, width=1200, height=800, bg="#FFFFFF"):
        self.width = width
        self.height = height
        self.elements = []
        self.defs = []
        self.bboxes = []
        self.canvas_bbox = BBox(0, 0, width, height)
        # Semantic registries for connection validation
        self.nodes = {}       # id -> Node
        self.edges = []       # list[Edge]
        self._node_seq = 0
        self._edge_seq = 0
        # Registered arrow markers: id -> (markerWidth, markerHeight, refX).
        # connect() derives per-edge tip retraction from the marker actually
        # used, so the arrow always kisses the target border regardless of
        # marker size. Falls back to marker_depth for unregistered markers.
        self.markers = {}
        self.marker_depth = 8.0
        # Design-system registries for typography/palette quality checks.
        # font_sizes: every font_size passed to text()/multiline_text().
        # accent_colors: distinct non-neutral fills/strokes actually used.
        self.font_sizes = []
        self.accent_colors = set()
        # Background: defaults to white (a light canvas is the sane default for
        # technical diagrams). set_background() or the bg= ctor arg overrides.
        self._bg_index = None  # element-list slot of the bg rect, if any
        self.background = "#ffffff"
        # Transform stack for group() contexts. The current accumulated matrix
        # maps local coordinates (used inside a group) to absolute canvas coords.
        # register_node/register_edge/add_element apply it so nodes/bboxes/edges
        # are stored in absolute space regardless of grouping.
        self._matrix_stack = [(1.0, 0.0, 0.0, 1.0, 0.0, 0.0)]
        self.set_background(bg)

    # ------------------------------------------------------------------
    # Low-level element emission
    # ------------------------------------------------------------------
    @property
    def _current_matrix(self):
        return self._matrix_stack[-1]

    def _transform_bbox(self, bbox):
        """Map a local-space bbox to absolute canvas coords via current matrix.

        Transforms all four corners and takes the axis-aligned bounding box of
        the result (handles rotation/skew by enlarging the AABB).
        """
        m = self._current_matrix
        if m == IDENTITY:
            return bbox
        corners = [(bbox.x, bbox.y), (bbox.x + bbox.w, bbox.y),
                   (bbox.x, bbox.y + bbox.h), (bbox.x + bbox.w, bbox.y + bbox.h)]
        pts = [transform_point(m, c) for c in corners]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    def add_element(self, element, bbox=None):
        self.elements.append(element)
        if bbox:
            bbox = self._transform_bbox(bbox)
            self.bboxes.append(bbox)
            # Check for canvas overflow
            if bbox.x < 0 or bbox.y < 0 or bbox.x + bbox.w > self.width or bbox.y + bbox.h > self.height:
                print(f"Warning: Element at ({bbox.x:.1f}, {bbox.y:.1f}) exceeds canvas boundaries.")

    def group(self, transform):
        """Open a transform context: nodes/bboxes/edges drawn inside are stored
        in absolute canvas coordinates.

        Usage:
            with drawer.group("translate(100, 50)"):
                drawer.rect(0, 0, 40, 30, node_id="a")  # registered at abs (100,50)
        Supports matrix()/translate()/scale()/rotate()/skewX()/skewY(), chained.
        """
        local = parse_transform(transform)
        parent = self._current_matrix
        self._matrix_stack.append(multiply_matrix(parent, local))
        self.elements.append(f'<g transform="{transform}">')
        return _GroupContext(self)
    def add_def(self, def_content):
        self.defs.append(def_content)

    def _record_color(self, *colors):
        """Record each color (fill/stroke) as a normalized accent color.

        Neutrals (white/black/gray) and unparseable/none values are skipped so
        the palette check only counts genuine accent colors.
        """
        for c in colors:
            norm = normalize_color(c)
            if norm is not None and not is_neutral(norm):
                self.accent_colors.add(norm)

    def set_background(self, color):
        """Set (or replace) the canvas background color.

        A full-canvas rect is kept at the bottom of the element stack so it
        always paints first. Defaults to white; pass a dark color only when the
        diagram is intentionally a dark theme (then opt in via this call so the
        palette check doesn't warn about a non-light background).
        """
        norm = normalize_color(color) or "#ffffff"
        self.background = norm
        bg_rect = (f'<rect x="0" y="0" width="{self.width}" height="{self.height}" '
                   f'fill="{norm}" stroke="none" />')
        if self._bg_index is None:
            self.elements.insert(0, bg_rect)
            self._bg_index = 0
        else:
            self.elements[self._bg_index] = bg_rect

    # ------------------------------------------------------------------
    # Semantic registration (for connection validation)
    # ------------------------------------------------------------------
    def register_node(self, node_id, x, y, w, h, kind="op", visible=True, role="node"):
        m = self._current_matrix
        if m != IDENTITY:
            corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
            pts = [transform_point(m, c) for c in corners]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y
        node = Node(node_id, x, y, w, h, kind=kind, visible=visible, role=role)
        self.nodes[node_id] = node
        return node

    def register_edge(self, start, end, edge_id=None, has_arrow=True, label=None, path_d=None, role="edge"):
        m = self._current_matrix
        if m != IDENTITY:
            start = transform_point(m, start)
            end = transform_point(m, end)
        if edge_id is None:
            edge_id = f"edge_{self._edge_seq}"
            self._edge_seq += 1
        edge = Edge(start, end, edge_id=edge_id, has_arrow=has_arrow, label=label, path_d=path_d, role=role)
        self.edges.append(edge)
        return edge
    def nearest_node(self, px, py, kinds=None):
        """Return (node, distance) for the closest registered node border."""
        best_node, best_dist = None, float("inf")
        for node in self.nodes.values():
            if kinds is not None and node.kind not in kinds:
                continue
            d = node.border_distance(px, py)
            if d < best_dist:
                best_dist, best_node = d, node
        return best_node, best_dist

    # ------------------------------------------------------------------
    # Primitives (rendering + optional semantic registration)
    # ------------------------------------------------------------------
    def rect(self, x, y, w, h, rx=5, ry=5, fill="white", stroke="black",
             stroke_width=1, opacity=1, id=None, extra="", dashed=False,
             node_id=None, node_kind="op", bbox=True, role=None):
        """Draw a rectangle.

        node_id: if given, also register a Node at these coords so edges can be
                 validated against it. No bbox collision tracking is added by
                 default for registered nodes (set bbox=True to also track it).
        role: semantic role for the validator ('node'|'decoration'|'legend'|
              'label'|'background'). When set, emitted as data-graph-role and
              stored on the node; decorative/legend roles skip business checks.
        """
        id_attr = f'id="{id}"' if id else ""
        extra = " ".join(filter(None, [_dash_attr(dashed), extra]))
        role_attr = f' data-graph-role="{role}"' if role else ""
        self.add_element(
            f'<rect {id_attr} x="{x}" y="{y}" width="{w}" height="{h}" '
            f'rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" fill-opacity="{opacity}"{role_attr} {extra} />',
            BBox(x, y, w, h) if bbox else None,
        )
        self._record_color(fill, stroke)
        if node_id:
            visible = (_shape_visible(fill, stroke, opacity) and w > 0 and h > 0)
            self.register_node(node_id, x, y, w, h, kind=node_kind, visible=visible, role=role or "node")

    def text(self, x, y, content, font_size=14, font_family="Arial, sans-serif",
             fill="black", anchor="middle", weight="normal", style="normal",
             id=None, extra="", bbox=True):
        content_esc = html.escape(content)
        id_attr = f'id="{id}"' if id else ""
        # Width estimate: 0.55em per ASCII glyph (0.62 bold), 1.0em per CJK glyph.
        # This matches evaluator._estimate_text_width so rendering & checks agree.
        coef = 0.62 if weight == "bold" else 0.55
        w = sum(font_size * (1.0 if ord(c) > 0x2E80 else coef) for c in content)
        h = font_size
        tx = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        ty = y - h / 2
        # dominant-baseline="central" vertically centers on (x,y) exactly,
        # replacing the old y+0.35*fs approximation (ink-graph convention).
        self.add_element(
            f'<text {id_attr} x="{x}" y="{y}" font-family="{font_family}" '
            f'font-size="{font_size}" fill="{fill}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-weight="{weight}" font-style="{style}" {extra}>{content_esc}</text>',
            BBox(tx, ty, w, h) if bbox else None,
        )
        self.font_sizes.append(font_size)
        self._record_color(fill)

    def multiline_text(self, x, y, lines, font_size=14, line_height=1.2,
                       font_family="Arial, sans-serif", fill="black",
                       anchor="middle", weight="normal"):
        for i, line in enumerate(lines):
            dy = i * font_size * line_height
            self.text(x, y + dy, line, font_size, font_family, fill, anchor, weight)
    def formula(self, x, y, markup, font_size=14,
                font_family="Consolas, 'Courier New', monospace", fill="black",
                anchor="middle", weight="bold", bbox=False):
        """Render a formula with real sub/superscripts via <tspan> baseline shifts.

        Markup syntax:  _{...} -> subscript,  ^{...} -> superscript.
        Example: "F_{k} = MS^{↑}_{k} + g_{k}" renders F with subscript k, etc.
        Unlike text() (which HTML-escapes content and can only show literal
        underscores/carets), this emits genuine <tspan dy=... font-size=...>
        elements so sub/superscripts display correctly (down/up-shifted,
        ~0.72x smaller). The baseline auto-resets after each token so multiple
        sub/superscripts in one formula align properly.

        bbox: when True, registers a collision bbox (width estimate strips
              tspan markup, matching evaluator._estimate_text_width). Off by
              default since formulas are usually inline annotations.
        """
        SUB = font_size * 0.30   # subscript baseline shift (down)
        SUP = -font_size * 0.38  # superscript baseline shift (up)
        SSZ = font_size * 0.72   # sub/superscript glyph size
        parts = []
        baseline = 0.0
        for tok in _re.split(r'(_\{[^}]*\}|\^\{[^}]*\})', markup):
            if not tok:
                continue
            if tok.startswith('_{'):
                content, target, fs = tok[2:-1], SUB, SSZ
            elif tok.startswith('^{'):
                content, target, fs = tok[2:-1], SUP, SSZ
            else:
                content, target, fs = tok, 0.0, font_size
            dy = target - baseline  # relative shift from current position
            baseline = target
            parts.append(
                f'<tspan dy="{dy:.2f}" font-size="{fs:.2f}">{html.escape(content)}</tspan>')
        body = ''.join(parts)
        box = None
        if bbox:
            visible = _re.sub(r'<[^>]+>', '', body)
            coef = 0.62 if weight == "bold" else 0.55
            w = sum(font_size * (1.0 if ord(c) > 0x2E80 else coef) for c in visible)
            tx = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
            box = BBox(tx, y - font_size / 2, w, font_size)
        self.add_element(
            f'<text x="{x}" y="{y}" font-family="{font_family}" font-size="{font_size}" '
            f'fill="{fill}" text-anchor="{anchor}" dominant-baseline="central" '
            f'font-weight="{weight}">{body}</text>', box)
        self.font_sizes.append(font_size)
        self._record_color(fill)

    def circle(self, cx, cy, r, fill="white", stroke="black", stroke_width=1,
               opacity=1, id=None, node_id=None, node_kind="junction", bbox=False,
               extra="", dashed=False, role=None):
        """Draw a circle. When node_id is given, also register a square Node of
        side 2r centered at (cx, cy) so edges can snap to its border (the node
        approximates the circle for connection validation; endpoints landing at
        the center register distance 0)."""
        id_attr = f'id="{id}"' if id else ""
        extra = " ".join(filter(None, [_dash_attr(dashed), extra]))
        role_attr = f' data-graph-role="{role}"' if role else ""
        self.add_element(
            f'<circle {id_attr} cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" fill-opacity="{opacity}"{role_attr} {extra} />',
            BBox(cx - r, cy - r, 2 * r, 2 * r) if bbox else None,
        )
        self._record_color(fill, stroke)
        if node_id:
            visible = (_shape_visible(fill, stroke, opacity) and r > 0)
            self.register_node(node_id, cx - r, cy - r, 2 * r, 2 * r, kind=node_kind, visible=visible, role=role or "node")

    def database(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
                 opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
                 extra="", role=None, label=None):
        """Cylinder (database) shape. Top ellipse depth = min(8, h*0.12)."""
        depth = min(8, h * 0.12)
        ra = f' data-graph-role="{role}"' if role else ""
        id_attr = f'id="{id}"' if id else ""
        body = (f'M 0,{depth} A {w/2},{depth} 0 0 1 {w},{depth} '
                f'L {w},{h-depth} A {w/2},{depth} 0 0 1 0,{h-depth} Z')
        top = f'M 0,{depth} A {w/2},{depth} 0 0 0 {w},{depth}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<path d="{body}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra} {extra}/>'
            f'<path d="{top}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}"{ra}/>'
            f'</g>', BBox(x, y, w, h) if bbox else None)
        self._record_color(fill, stroke)
        if node_id:
            self.register_node(node_id, x, y, w, h, kind=node_kind,
                               visible=_shape_visible(fill, stroke, opacity), role=role or "node")
        if label:
            self.text(x + w / 2, y + h / 2, label, 12, anchor="middle")

    def decision(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
                 opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
                 extra="", role=None, label=None):
        """Diamond (decision) shape. Four points around center."""
        ra = f' data-graph-role="{role}"' if role else ""
        id_attr = f'id="{id}"' if id else ""
        pts = f'{w/2},0 {w},{h/2} {w/2},{h} 0,{h/2}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra} {extra}/></g>',
            BBox(x, y, w, h) if bbox else None)
        self._record_color(fill, stroke)
        if node_id:
            self.register_node(node_id, x, y, w, h, kind=node_kind,
                               visible=_shape_visible(fill, stroke, opacity), role=role or "node")
        if label:
            self.text(x + w / 2, y + h / 2, label, 12, anchor="middle")

    def hexagon(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
                opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
                extra="", role=None, label=None):
        """Hexagon (gateway) with 25% corner insets."""
        ra = f' data-graph-role="{role}"' if role else ""
        id_attr = f'id="{id}"' if id else ""
        pts = f'{w*0.25},0 {w*0.75},0 {w},{h/2} {w*0.75},{h} {w*0.25},{h} 0,{h/2}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra} {extra}/></g>',
            BBox(x, y, w, h) if bbox else None)
        self._record_color(fill, stroke)
        if node_id:
            self.register_node(node_id, x, y, w, h, kind=node_kind,
                               visible=_shape_visible(fill, stroke, opacity), role=role or "node")
        if label:
            self.text(x + w / 2, y + h / 2, label, 12, anchor="middle")

    def component(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
                  opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
                  extra="", role=None, label=None):
        """Component box with two small tabs on the left edge."""
        ra = f' data-graph-role="{role}"' if role else ""
        id_attr = f'id="{id}"' if id else ""
        tab1 = f'<rect x="-8" y="{h*0.3}" width="16" height="8" rx="1" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{ra}/>'
        tab2 = f'<rect x="-8" y="{h*0.55}" width="16" height="8" rx="1" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{ra}/>'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<rect width="{w}" height="{h}" rx="4" ry="4" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" fill-opacity="{opacity}"{ra} {extra}/>'
            f'{tab1}{tab2}</g>', BBox(x, y, w, h) if bbox else None)
        self._record_color(fill, stroke)
        if node_id:
            self.register_node(node_id, x, y, w, h, kind=node_kind,
                               visible=_shape_visible(fill, stroke, opacity), role=role or "node")
        if label:
            self.text(x + w / 2, y + h / 2, label, 12, anchor="middle")

    def cloud(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
              opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
              extra="", role=None, label=None):
        """Multi-lobe cloud built from cubic curves (ink-graph shape #9)."""
        ra = f' data-graph-role="{role}"' if role else ""
        id_attr = f'id="{id}"' if id else ""
        d = (f'M {w*0.22},{h*0.68} C {w*0.10},{h*0.68} 0,{h*0.58} 0,{h*0.46} '
             f'C 0,{h*0.34} {w*0.10},{h*0.24} {w*0.22},{h*0.24} '
             f'C {w*0.27},{h*0.10} {w*0.40},0 {w*0.55},0 '
             f'C {w*0.68},0 {w*0.80},{h*0.08} {w*0.86},{h*0.20} '
             f'C {w*0.95},{h*0.20} {w},{h*0.30} {w},{h*0.40} '
             f'C {w},{h*0.54} {w*0.89},{h*0.66} {w*0.76},{h*0.66} '
             f'C {w*0.70},{h*0.76} {w*0.58},{h*0.82} {w*0.46},{h*0.80} '
             f'C {w*0.37},{h*0.84} {w*0.27},{h*0.80} {w*0.22},{h*0.68} Z')
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra} {extra}/></g>',
            BBox(x, y, w, h) if bbox else None)
        self._record_color(fill, stroke)
        if node_id:
            self.register_node(node_id, x, y, w, h, kind=node_kind,
                               visible=_shape_visible(fill, stroke, opacity), role=role or "node")
        if label:
            self.text(x + w / 2, y + h * 0.5, label, 12, anchor="middle")

    def line(self, x1, y1, x2, y2, stroke="black", stroke_width=1, marker_end=None,
             edge_id=None, register_edge=False, edge_label=None, bbox=False, extra="",
             dashed=False, role=None):
        """Draw a straight line. Register as an Edge when register_edge=True."""
        role_attr = f' data-graph-role="{role}"' if role else ""
        extra = " ".join(filter(None, [_dash_attr(dashed), extra]))
        marker = f'marker-end="url(#{marker_end})"' if marker_end else ""
        self.add_element(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" {marker}{role_attr} {extra} />',
            BBox(min(x1, x2), min(y1, y2), abs(x2 - x1) or 1, abs(y2 - y1) or 1) if bbox else None,
        )
        self._record_color(stroke)
        if register_edge:
            self.register_edge((x1, y1), (x2, y2), edge_id=edge_id,
                               has_arrow=marker_end is not None, label=edge_label, role=role or "edge")

    def path(self, d, fill="none", stroke="black", stroke_width=1, marker_end=None,
             edge_id=None, register_edge=False, start=None, end=None,
             edge_label=None, bbox=None, extra="", dashed=False, role=None):
        """Draw an SVG path.

        For connection validation pass start/end (the semantic endpoints) plus
        register_edge=True. The visible `d` may describe a curve; start/end are
        what the validator checks against node borders.
        """
        role_attr = f' data-graph-role="{role}"' if role else ""
        extra = " ".join(filter(None, [_dash_attr(dashed), extra]))
        marker = f'marker-end="url(#{marker_end})"' if marker_end else ""
        self.add_element(
            f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" {marker}{role_attr} {extra} />',
            bbox,
        )
        self._record_color(fill, stroke)
        if register_edge:
            if start is None or end is None:
                raise ValueError("register_edge=True requires start and end points")
            self.register_edge(start, end, edge_id=edge_id,
                               has_arrow=marker_end is not None, label=edge_label, path_d=d, role=role or "edge")

    # ------------------------------------------------------------------
    # Connection helpers (snap endpoints to node borders)
    def connect(self, from_id, from_side, to_id, to_side,
                stroke="black", stroke_width=1.5, marker_end="arrowhead",
                edge_id=None, edge_label=None, as_curve=False, curve_dir=None,
                dashed=False, role=None):
        """Draw a clean connection between two registered nodes.

        Endpoints are taken from the nodes' border midpoints, so the rendered
        line/arrow always lands exactly on a node edge. The connection is
        registered for validation automatically. Pass dashed=True for a
        stroke-dasharray style (e.g. lowering/bypass flows).
        """
        if from_id not in self.nodes:
            raise KeyError(f"Unknown source node: {from_id!r}")
        if to_id not in self.nodes:
            raise KeyError(f"Unknown target node: {to_id!r}")
        start = self.nodes[from_id].edge_point(from_side)
        end = self.nodes[to_id].edge_point(to_side)
        extra = _dash_attr(dashed)
        # Retract the arrow tip just outside the target border so the marker
        # sits beside the node instead of poking into its interior (the marker
        # refX aligns the tip at the path endpoint). Direction = start->end.
        if marker_end:
            depth = self.marker_tip_depth(marker_end, stroke_width)
            dx, dy = end[0] - start[0], end[1] - start[1]
            seglen = math.hypot(dx, dy) or 1.0
            ux, uy = dx / seglen, dy / seglen
            draw_end = (end[0] - ux * depth, end[1] - uy * depth)
        else:
            draw_end = end
        if as_curve:
            mx = (start[0] + end[0]) / 2.0
            if curve_dir == "left":
                mx = min(start[0], end[0]) - 60
            elif curve_dir == "right":
                mx = max(start[0], end[0]) + 60
            d = (f"M{start[0]},{start[1]} C{mx},{start[1]} {mx},{draw_end[1]} "
                 f"{draw_end[0]},{draw_end[1]}")
            self.path(d, stroke=stroke, stroke_width=stroke_width, marker_end=marker_end,
                      edge_id=edge_id, register_edge=True, start=start, end=end,
                      edge_label=edge_label, extra=extra, role=role)
        else:
            self.line(start[0], start[1], draw_end[0], draw_end[1], stroke=stroke,
                      stroke_width=stroke_width, marker_end=marker_end,
                      edge_id=edge_id, register_edge=True, edge_label=edge_label,
                      extra=extra, role=role)
        return start, end

    # ------------------------------------------------------------------
    # Arrow markers / collision / render
    # ------------------------------------------------------------------
    def arrow_head(self, id="arrowhead", color="black", marker_width=10,
                   marker_height=7, ref_x=9, ref_y=3.5):
        """Register an arrow marker and record its geometry.

        The recorded (marker_width, ref_x) lets connect() derive the exact tip
        retraction per edge so the arrow tip sits on the target border.
        """
        self.markers[id] = (marker_width, marker_height, ref_x)
        self.add_def(f'''
        <marker id="{id}" markerWidth="{marker_width}" markerHeight="{marker_height}" refX="{ref_x}" refY="{ref_y}" orient="auto">
            <polygon points="0 0, {marker_width} {ref_y}, 0 {marker_height}" fill="{color}" />
        </marker>''')
        self._record_color(color)

    def marker_tip_depth(self, marker_id, stroke_width):
        """Pixels the arrow tip protrudes beyond the line endpoint.

        With markerUnits=strokeWidth (the SVG default), the marker is scaled by
        stroke_width; the tip sits (markerWidth - refX) marker-units past the
        endpoint. Retracting the endpoint by this much lands the tip exactly on
        the target border. Falls back to self.marker_depth for unknown markers.
        """
        spec = self.markers.get(marker_id)
        if spec is None:
            return self.marker_depth
        marker_width, _marker_height, ref_x = spec
        return (marker_width - ref_x) * max(stroke_width, 0.0)

    def check_collisions(self):
        """Containment-aware overlap check.

        Two bboxes "collide" only when they intersect AND neither fully contains
        the other. Parent/child nesting (Module > Layer > Block > op) is normal
        in architecture diagrams and must NOT count as a collision.
        """
        collisions = []
        for i in range(len(self.bboxes)):
            for j in range(i + 1, len(self.bboxes)):
                a, b = self.bboxes[i], self.bboxes[j]
                if a.intersects(b) and not (a.contains(b) or b.contains(a)):
                    collisions.append((i, j))
        return collisions

    def render(self):
        defs_str = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return f'''<svg width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">
        {defs_str}
        {''.join(self.elements)}
        </svg>'''


class _GroupContext:
    """Context manager that closes a <g> opened by SVGDrawer.group().

    On exit it appends '</g>', restores the parent transform on the matrix
    stack, so registrations after the `with` block use absolute coords again.
    """

    def __init__(self, drawer):
        self._drawer = drawer

    def __enter__(self):
        return self._drawer

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._drawer.elements.append('</g>')
        if len(self._drawer._matrix_stack) > 1:
            self._drawer._matrix_stack.pop()
        return False
def save_svg(content, filename):
    """Write SVG *content* to *filename*, creating parent directories as needed.

    Returns the resolved absolute path written. The library writes wherever the
    caller asks — there is no enforced output directory. A previous version
    required an ``output/<task>/`` layout; that was removed for the public
    release because it refused legitimate temp and cross-project paths.
    """
    path = Path(filename).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(path)


def rasterize_svg(svg_path, png_path, width):
    """Rasterize an SVG to PNG via rsvg-convert.

    Equivalent to ``rsvg-convert -w <width> <svg_path> -o <png_path>``.
    Creates the parent directory if missing. Returns the resolved PNG path.
    """
    out = Path(png_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["rsvg-convert", "-w", str(width), str(svg_path), "-o", str(out)],
        check=True,
    )
    return str(out)


# ----------------------------------------------------------------------
# Layout helpers (pure geometry — compute coords BEFORE drawing)
# ----------------------------------------------------------------------
# SVGDrawer bakes coordinates into the emitted string at draw time, so layout
# must be computed up front and passed to the primitives. Mutating node
# coords after drawing (the approach auto_refine took) does NOT update the
# rendered SVG — see the layout-first pattern below.

def _angle_to_side(angle_deg):
    """Pick (neighbor_side, hub_side) for connect() from a neighbor's angle.

    Angles are SVG-space degrees (0=+x/right, 90=+y/down). Returns the side
    of the neighbor that faces the hub, and the side of the hub that faces
    the neighbor, so connect() arrows land cleanly.
    """
    a = ((angle_deg + 180) % 360) - 180  # normalize to [-180, 180)
    if -45 <= a < 45:
        return "left", "right"     # neighbor is right of hub
    if 45 <= a < 135:
        return "top", "bottom"     # neighbor is below hub
    if a >= 135 or a < -135:
        return "right", "left"     # neighbor is left of hub
    return "bottom", "top"         # neighbor is above hub (-135..-45)


def layout_radial(hub, neighbors, center, radius, start_angle=-90.0):
    """Radial (star) layout: hub at center, neighbors evenly on a circle.

    Pure geometry — returns top-left coords + connect() sides; the caller
    draws. A hub with N neighbors fanned evenly has **zero edge crossings**
    by construction (every edge is hub<->neighbor). Ideal for message-bus /
    gateway / load-balancer topologies where one central node talks to many.

    Args:
        hub: (id, w, h) of the central node.
        neighbors: list of (id, w, h) for the surrounding nodes.
        center: (cx, cy) canvas point for the hub's center.
        radius: distance from hub center to each neighbor's center.
        start_angle: degrees (0=+x, -90=up) for the first neighbor; others
            follow at 360/N spacing clockwise.
    Returns:
        (positions, sides) where
          positions = {id: (x, y, w, h)} top-left + size for every node;
          sides     = {neighbor_id: (neighbor_side, hub_side)} best
                      connect() sides, picked from each neighbor's angle.
    """
    hid, hw, hh = hub
    cx, cy = center
    positions = {hid: (cx - hw / 2, cy - hh / 2, hw, hh)}
    sides = {}
    n = len(neighbors)
    step = 360.0 / n if n else 0.0
    for i, (nid, nw, nh) in enumerate(neighbors):
        ang = start_angle + i * step
        theta = math.radians(ang)
        ncx = cx + radius * math.cos(theta)
        ncy = cy + radius * math.sin(theta)
        positions[nid] = (ncx - nw / 2, ncy - nh / 2, nw, nh)
        sides[nid] = _angle_to_side(ang)
    return positions, sides
