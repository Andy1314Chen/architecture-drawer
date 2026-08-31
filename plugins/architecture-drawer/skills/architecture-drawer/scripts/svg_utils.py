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
    """Normalize the ``dashed`` flag/pattern into a stroke-dasharray attribute.

    ``dashed=True`` means the standard "6,3" pattern; a non-empty string is
    taken verbatim. Centralizing it gives one spelling for consistent
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
        # Relocate support: a node drawn outside any group (matrix == identity)
        # remembers where its emitted XML sits in drawer.elements and how to
        # regenerate it at new coords, so relocate_node() can move it post-emit.
        # Mutating x/y directly does NOT update the baked-in emit — this does.
        self._emit_range = None    # (start, end) indices into drawer.elements
        self._bbox_index = None    # index into drawer.bboxes (None if bbox=False)
        self._rebuild_xml = None   # callable(nx, ny) -> list[str]
        self._rebuild_bbox = None  # callable(nx, ny) -> BBox

    @property
    def cx(self):
        return self.x + self.w / 2.0

    @property
    def cy(self):
        return self.y + self.h / 2.0

    def edge_point(self, side, offset=0.0):
        """Midpoint of a given border side, optionally shifted along the
        border by ``offset`` px (positive = down/right along the border;
        used by automatic port spreading so same-side edges fan out).
        """
        if side == "top":
            return (self.cx + offset, self.y)
        if side == "bottom":
            return (self.cx + offset, self.y + self.h)
        if side == "left":
            return (self.x, self.cy + offset)
        if side == "right":
            return (self.x + self.w, self.cy + offset)
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
        # Relocate support: connect()-built edges remember their node anchors +
        # emit range so relocate_node() can re-route them when an endpoint node
        # moves. None for raw line()/path() edges (not auto-rerouted).
        self.from_id = None
        self.from_side = None
        self.to_id = None
        self.to_side = None
        self._emit_range = None    # (start, end) indices into drawer.elements
        self._rebuild_xml = None   # callable() -> list[str] (reads live node coords)
        # Deterministic same-port spread offset for this edge's endpoints,
        # keyed {(node_id, side): px_along_border}; assigned by
        # SVGDrawer._spread_ports() when several connect() edges share one
        # node side so they fan out symmetrically instead of stacking on the
        # border midpoint (which reads as one thick line). See
        # PORT_SPREAD_* constants near SVGDrawer.
        self._spread_offsets = {}

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
    def _record_rebuild(self, node, start, bbox_idx, had_bbox,
                        rebuild_xml, rebuild_bbox):
        """Register post-emit relocation for a node drawn outside any group.

        Only when the current transform is identity (a top-level node): inside
        a group() coords are local, so absolute-xy relocation is meaningless.
        """
        if self._current_matrix != IDENTITY:
            return
        node._emit_range = (start, len(self.elements))
        node._bbox_index = bbox_idx if had_bbox else None
        node._rebuild_xml = rebuild_xml
        node._rebuild_bbox = rebuild_bbox

    def relocate_node(self, node_id, new_x, new_y):
        """Move an already-drawn node to new top-left coords.

        Re-emits the node's shape XML, updates its collision bbox, and
        re-routes every connect()-built edge anchored on it. Critically, it
        also refreshes each re-routed edge's registry fields (start/end/
        path_d): the evaluator's connection/crossing/routing checks read
        `drawer.edges[*]`, NOT the re-parsed SVG, so a re-emit that left the
        registry stale would report phantom dangles and undermine the fix.

        Returns True if relocated, False if the node is unknown, was drawn
        inside a group, belongs to a shape without rebuild support, OR has a
        connect()-built edge that cannot be re-routed (e.g. the edge was
        drawn inside a group, so its `_rebuild_xml` is None). The check is
        atomic: if ANY anchored edge can't follow the node, the whole move is
        refused rather than leaving the node moved and its edges stale (a
        half-applied relocate would dangle).

        Unlike mutating node.x/y directly (which the baked-in emit ignores),
        this updates the actual rendered SVG — use it from auto_refine or any
        post-emit layout adjustment.
        """
        node = self.nodes.get(node_id)
        if node is None or node._rebuild_xml is None:
            return False
        # Atomicity guard: refuse if any edge anchored here can't be re-routed.
        for edge in self.edges:
            if node_id in (edge.from_id, edge.to_id) and edge._rebuild_xml is None:
                return False
        s, e = node._emit_range
        new_elems = node._rebuild_xml(new_x, new_y)
        # A rebuild MUST emit exactly as many elements as it replaces, or every
        # later _emit_range index (other nodes', edges') silently shifts and
        # corrupts the element list.
        if len(new_elems) != e - s:
            raise RuntimeError(
                f"relocate_node('{node_id}'): node rebuild emitted "
                f"{len(new_elems)} elements, expected {e - s}")
        self.elements[s:e] = new_elems
        if node._bbox_index is not None:
            self.bboxes[node._bbox_index] = node._rebuild_bbox(new_x, new_y)
        node.x, node.y = new_x, new_y
        # Re-route edges anchored on this node: re-emit their XML AND refresh
        # the registry so evaluate_svg's connection checks see the new coords.
        for edge in self.edges:
            if edge._rebuild_xml is None:
                continue
            if node_id in (edge.from_id, edge.to_id):
                es, ee = edge._emit_range
                new_xmls, (nstart, nend, npath_d) = edge._rebuild_xml()
                if len(new_xmls) != ee - es:
                    raise RuntimeError(
                        f"relocate_node('{node_id}'): edge '{edge.id}' rebuild "
                        f"emitted {len(new_xmls)} elements, expected {ee - es}")
                self.elements[es:ee] = new_xmls
                edge.start, edge.end, edge.path_d = nstart, nend, npath_d
        return True

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
    def _rect_xml(self, x, y, w, h, rx, ry, fill, stroke, stroke_width,
                  opacity, id_attr, extra, attrs):
        return (f'<rect {id_attr} x="{x}" y="{y}" width="{w}" height="{h}" '
                f'rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{stroke_width}" fill-opacity="{opacity}"{attrs} {extra} />')

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
        # Semantic identity emitted into the SVG so downstream checkers can
        # map rendered geometry back to declared roles (data-graph-role for
        # check filtering, data-node-id for brief-contract attribution).
        attrs = (f' data-graph-role="{role}"' if role else "") + \
                (f' data-node-id="{node_id}"' if node_id else "")
        start, bbox_idx = len(self.elements), len(self.bboxes)
        self.add_element(
            self._rect_xml(x, y, w, h, rx, ry, fill, stroke, stroke_width,
                           opacity, id_attr, extra, attrs),
            BBox(x, y, w, h) if bbox else None,
        )
        self._record_color(fill, stroke)
        if node_id:
            visible = (_shape_visible(fill, stroke, opacity) and w > 0 and h > 0)
            node = self.register_node(node_id, x, y, w, h, kind=node_kind, visible=visible, role=role or "node")
            self._record_rebuild(
                node, start, bbox_idx, bbox,
                lambda nx, ny: [self._rect_xml(
                    nx, ny, w, h, rx, ry, fill, stroke, stroke_width,
                    opacity, id_attr, extra, attrs)],
                lambda nx, ny: BBox(nx, ny, w, h))

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

    def _circle_xml(self, cx, cy, r, fill, stroke, stroke_width,
                    opacity, id_attr, extra, attrs):
        return (f'<circle {id_attr} cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="{stroke_width}" fill-opacity="{opacity}"{attrs} {extra} />')

    def circle(self, cx, cy, r, fill="white", stroke="black", stroke_width=1,
               opacity=1, id=None, node_id=None, node_kind="junction", bbox=False,
               extra="", dashed=False, role=None):
        """Draw a circle. When node_id is given, also register a square Node of
        side 2r centered at (cx, cy) so edges can snap to its border (the node
        approximates the circle for connection validation; endpoints landing at
        the center register distance 0)."""
        id_attr = f'id="{id}"' if id else ""
        extra = " ".join(filter(None, [_dash_attr(dashed), extra]))
        attrs = (f' data-graph-role="{role}"' if role else "") + \
                (f' data-node-id="{node_id}"' if node_id else "")
        start, bbox_idx = len(self.elements), len(self.bboxes)
        self.add_element(
            self._circle_xml(cx, cy, r, fill, stroke, stroke_width,
                             opacity, id_attr, extra, attrs),
            BBox(cx - r, cy - r, 2 * r, 2 * r) if bbox else None,
        )
        self._record_color(fill, stroke)
        if node_id:
            visible = (_shape_visible(fill, stroke, opacity) and r > 0)
            node = self.register_node(node_id, cx - r, cy - r, 2 * r, 2 * r, kind=node_kind, visible=visible, role=role or "node")
            self._record_rebuild(
                node, start, bbox_idx, bbox,
                lambda nx, ny: [self._circle_xml(
                    nx + r, ny + r, r, fill, stroke, stroke_width,
                    opacity, id_attr, extra, attrs)],
                lambda nx, ny: BBox(nx, ny, 2 * r, 2 * r))

    def database(self, x, y, w, h, fill="white", stroke="black", stroke_width=1,
                 opacity=1, id=None, node_id=None, node_kind="op", bbox=False,
                 extra="", role=None, label=None):
        """Cylinder (database) shape. Top ellipse depth = min(8, h*0.12)."""
        depth = min(8, h * 0.12)
        ra = f' data-graph-role="{role}"' if role else ""
        na = f' data-node-id="{node_id}"' if node_id else ""
        id_attr = f'id="{id}"' if id else ""
        body = (f'M 0,{depth} A {w/2},{depth} 0 0 1 {w},{depth} '
                f'L {w},{h-depth} A {w/2},{depth} 0 0 1 0,{h-depth} Z')
        top = f'M 0,{depth} A {w/2},{depth} 0 0 0 {w},{depth}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<path d="{body}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra}{na} {extra}/>'
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
        na = f' data-node-id="{node_id}"' if node_id else ""
        id_attr = f'id="{id}"' if id else ""
        pts = f'{w/2},0 {w},{h/2} {w/2},{h} 0,{h/2}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra}{na} {extra}/></g>',
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
        na = f' data-node-id="{node_id}"' if node_id else ""
        id_attr = f'id="{id}"' if id else ""
        pts = f'{w*0.25},0 {w*0.75},0 {w},{h/2} {w*0.75},{h} {w*0.25},{h} 0,{h/2}'
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" '
            f'fill-opacity="{opacity}"{ra}{na} {extra}/></g>',
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
        na = f' data-node-id="{node_id}"' if node_id else ""
        id_attr = f'id="{id}"' if id else ""
        tab1 = f'<rect x="-8" y="{h*0.3}" width="16" height="8" rx="1" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{ra}/>'
        tab2 = f'<rect x="-8" y="{h*0.55}" width="16" height="8" rx="1" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{ra}/>'
        # Tabs protrude 8px LEFT of the box (x="-8" inside the translate group),
        # so the collision bbox must extend left by 8 to catch a left-side
        # neighbor — otherwise a component abutting another node on its left
        # would skip the collision check.
        self.add_element(
            f'<g transform="translate({x},{y})" {id_attr}>'
            f'<rect width="{w}" height="{h}" rx="4" ry="4" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" fill-opacity="{opacity}"{ra}{na} {extra}/>'
            f'{tab1}{tab2}</g>', BBox(x - 8, y, w + 8, h) if bbox else None)
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
        na = f' data-node-id="{node_id}"' if node_id else ""
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
            f'fill-opacity="{opacity}"{ra}{na} {extra}/></g>',
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
    def _edge_xml(self, start, end, stroke, stroke_width, marker_end,
                  dashed, as_curve, curve_dir, role):
        """Generate a connect()-built edge's line/path XML (no side effects).

        Shared by connect() and edge relocate-rebuild so a re-routed edge is
        byte-identical to a freshly drawn one. Returns (xml, path_d_or_None).
        """
        extra = _dash_attr(dashed)
        role_attr = f' data-graph-role="{role}"' if role else ""
        marker = f'marker-end="url(#{marker_end})"' if marker_end else ""
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
            xml = (f'<path d="{d}" fill="none" stroke="{stroke}" '
                   f'stroke-width="{stroke_width}" {marker}{role_attr} {extra} />')
            return xml, d
        xml = (f'<line x1="{start[0]}" y1="{start[1]}" x2="{draw_end[0]}" '
               f'y2="{draw_end[1]}" stroke="{stroke}" stroke-width="{stroke_width}" '
               f'{marker}{role_attr} {extra} />')
        return xml, None

    # Port-spread constants (see _apply_port_spread): deterministic fan-out
    # of same-side connect() endpoints, so N edges leaving one node side do
    # not stack on the single border midpoint.
    PORT_SPREAD_GUTTER = 16.0     # px reserved at each end of a border side
    PORT_SPREAD_MAX_SPACING = 14.0  # px cap between adjacent spread ports

    def _port_group(self, node_id, side):
        """All top-level connect() edges attached to (node_id, side)."""
        return [e for e in self.edges
                if e._rebuild_xml is not None
                and ((e.from_id == node_id and e.from_side == side)
                     or (e.to_id == node_id and e.to_side == side))]

    def _apply_port_spread(self, node_id, side):
        """Deterministically spread same-side edge endpoints along a border.

        When several connect() edges share one node side, their endpoints
        would all land on the border midpoint and render as one stacked
        line (flagged downstream as duplicate edges). Instead, order the
        edges by their counterpart node's position along the border, then
        offset each endpoint symmetrically around the midpoint:

            usable  = side_length - 2*PORT_SPREAD_GUTTER
            spacing = min(PORT_SPREAD_MAX_SPACING, usable / (n - 1))
            offset_i = (i - (n-1)/2) * spacing

        Edges on a side shorter than 2*gutter (spacing <= 0) keep midpoints.
        Each affected edge is re-emitted through its own _rebuild_xml (the
        same mechanism relocate_node uses), so the rendered SVG and the
        Edge registry stay in sync. Group-drawn edges are skipped (their
        coordinates are local; same capability boundary as relocate_node).
        """
        group = self._port_group(node_id, side)
        if len(group) < 2:
            return
        node = self.nodes[node_id]
        vertical = side in ("left", "right")   # offset runs along y
        extent = node.h if vertical else node.w

        def sort_key(e):
            other_id = e.to_id if e.from_id == node_id else e.from_id
            other = self.nodes.get(other_id)
            along = (other.cy if vertical else other.cx) if other else 0.0
            return (along, e.id or "")

        group.sort(key=sort_key)
        usable = extent - 2.0 * self.PORT_SPREAD_GUTTER
        if len(group) > 1:
            spacing = min(self.PORT_SPREAD_MAX_SPACING, usable / (len(group) - 1))
        else:
            spacing = 0.0
        if spacing <= 0:
            return
        for i, e in enumerate(group):
            e._spread_offsets = {**e._spread_offsets,
                                 (node_id, side): (i - (len(group) - 1) / 2.0) * spacing}
            self._reemit_edge(e)

    def _reemit_edge(self, edge):
        """Re-run an edge's _rebuild_xml and splice the result in place."""
        if edge._rebuild_xml is None or edge._emit_range is None:
            return
        s, t = edge._emit_range
        xmls, (nstart, nend, npath_d) = edge._rebuild_xml()
        if len(xmls) != t - s:
            raise RuntimeError(
                f"_reemit_edge('{edge.id}'): rebuild emitted {len(xmls)} "
                f"elements, expected {t - s}")
        self.elements[s:t] = xmls
        edge.start, edge.end, edge.path_d = nstart, nend, npath_d
    def connect(self, from_id, from_side, to_id, to_side,
                stroke="black", stroke_width=1.5, marker_end="arrowhead",
                edge_id=None, edge_label=None, as_curve=False, curve_dir=None,
                dashed=False, role=None):
        """Draw a clean connection between two registered nodes.

        Endpoints are taken from the nodes' border midpoints, so the rendered
        line/arrow always lands exactly on a node edge. The connection is
        registered for validation automatically. Pass dashed=True for a
        stroke-dasharray style (e.g. lowering/bypass flows).

        Returns ``(start, end)`` — the two border-midpoint coords the edge was
        drawn between (useful for placing edge labels or chaining geometry).
        Edges drawn outside any group() are re-routable by relocate_node();
        edges drawn inside a group are not (their coords are local).
        """
        if from_id not in self.nodes:
            raise KeyError(f"Unknown source node: {from_id!r}")
        if to_id not in self.nodes:
            raise KeyError(f"Unknown target node: {to_id!r}")
        start = self.nodes[from_id].edge_point(from_side)
        end = self.nodes[to_id].edge_point(to_side)
        estart = len(self.elements)
        xml, path_d = self._edge_xml(start, end, stroke, stroke_width,
                                     marker_end, dashed, as_curve, curve_dir, role)
        self.add_element(xml, None)
        self._record_color(stroke)
        edge = self.register_edge(start, end, edge_id=edge_id,
                                  has_arrow=marker_end is not None,
                                  label=edge_label, path_d=path_d, role=role or "edge")
        edge.from_id, edge.from_side = from_id, from_side
        edge.to_id, edge.to_side = to_id, to_side
        if self._current_matrix == IDENTITY:
            edge._emit_range = (estart, len(self.elements))

            def _edge_rebuild():
                # Recompute endpoints from the nodes' live border midpoints so
                # a re-route after relocate_node() lands on the moved border.
                # Same-port spread offsets (assigned by _apply_port_spread)
                # are folded in so rebuilds preserve the fan-out.
                # Returns (xml_list, (start, end, path_d)) so the caller can
                # refresh both the rendered SVG and the Edge registry.
                rs = self.nodes[from_id].edge_point(
                    from_side, edge._spread_offsets.get((from_id, from_side), 0.0))
                re_ = self.nodes[to_id].edge_point(
                    to_side, edge._spread_offsets.get((to_id, to_side), 0.0))
                rxml, rpath_d = self._edge_xml(
                    rs, re_, stroke, stroke_width, marker_end, dashed,
                    as_curve, curve_dir, role)
                return [rxml], (rs, re_, rpath_d)

            edge._rebuild_xml = _edge_rebuild
            # Same-port spread: recompute the fan-out for both endpoint
            # groups this edge joined, so every sibling edge is re-emitted
            # with its assigned offset. No-op for the first edge on a side.
            self._apply_port_spread(from_id, from_side)
            self._apply_port_spread(to_id, to_side)
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
    # Reject duplicate ids up front: a neighbor sharing the hub id (or another
    # neighbor's id) would silently overwrite positions[hid] / a prior neighbor,
    # yielding a wrong layout with no diagnostic.
    nids = [nid for nid, _w, _h in neighbors]
    dupes = {hid, }  # hub id is reserved
    for nid in nids:
        if nid in dupes:
            raise ValueError(
                f"layout_radial: duplicate node id {nid!r} (a neighbor cannot "
                f"share the hub id or another neighbor's id)")
        dupes.add(nid)
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

def layout_grid(n, x0, y0, cols, w, h, gx, gy):
    """Rectangular grid: n cells in `cols` columns, left-to-right then
    top-to-bottom. Pure geometry — returns [(x, y), ...] top-left coords;
    the caller draws. Handles the common card-array arithmetic (chips in a
    band, station rows) so the caller states the array, not 40 coordinates.
    """
    if cols < 1:
        raise ValueError("layout_grid: cols must be >= 1")
    return [(x0 + (i % cols) * (w + gx), y0 + (i // cols) * (h + gy))
            for i in range(n)]


def layout_row(items, x0, y0, gx):
    """Single row of variable-size items along x.

    items: list of widths. Returns [(x, y0, w), ...] left-to-right with `gx`
    gutters — the arithmetic-free way to lay out a labelled flow
    (source -> queue -> engine -> sink) or a chip row.
    """
    out, x = [], x0
    for wd in items:
        out.append((x, y0, wd))
        x += wd + gx
    return out

def layout_band(title, x, y, w, h, pad=24, title_h=28):
    """Band container geometry with a title slot reserved at the top.

    Returns (body_x, body_y, body_w, body_h) — the drawable interior after
    the title strip and padding, so contents laid out inside never collide
    with the band title or edges. Pure geometry; the caller draws the rect.
    `title` is accepted for self-documenting call sites; geometry does not
    depend on it.
    """
    body_x = x + pad
    body_y = y + title_h
    body_w = w - 2 * pad
    body_h = h - title_h - pad
    return body_x, body_y, body_w, body_h
