import sys
import os
import math
import re as _re
import html

# Add the scripts directory to path to import BBox. insert(0) so this dir wins
# over any same-named module elsewhere on sys.path (matches eval-gen convention).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svg_utils import BBox


def bbox_union_area(bboxes):
    """Area of the union of rectangles (scanline / sweep algorithm).

    Unlike summing individual areas, nested/overlapping bboxes are counted once,
    so a parent container + its children don't inflate coverage. Ported concept
    from standard rectangle-union sweep: collect x-edges, for each strip sum the
    active y-coverage.
    """
    if not bboxes:
        return 0.0
    xs = sorted(set(b.x for b in bboxes) | set(b.x + b.w for b in bboxes))
    total = 0.0
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        width = x1 - x0
        if width <= 0:
            continue
        # active intervals on y for bboxes spanning this x-strip
        intervals = sorted((b.y, b.y + b.h) for b in bboxes if b.x <= x0 and b.x + b.w >= x1)
        merged = 0.0
        cur_start = None
        cur_end = None
        for lo, hi in intervals:
            if cur_end is None:
                cur_start, cur_end = lo, hi
            elif lo <= cur_end:
                cur_end = max(cur_end, hi)
            else:
                merged += cur_end - cur_start
                cur_start, cur_end = lo, hi
        if cur_end is not None:
            merged += cur_end - cur_start
        total += width * merged
    return total


def _estimate_text_width(content, font_size, bold=False):
    """Approximate rendered text width in px (Arial-like metric).

    ASCII glyphs average ~0.55em (bold ~0.62em); CJK/full-width glyphs occupy
    ~1.0em. Independent of the API's own estimate so it works on raw <text>.

    Strips SVG/HTML markup (e.g. <tspan ...>..</tspan>) so inline formatting
    tags — standard SVG for subscripts/superscripts — are not counted as
    visible glyphs (which would massively inflate the estimate). Stripping
    happens BEFORE unescaping entities (&amp; -> &): the reverse order would
    turn a user's literal '<b>' (emitted as '&lt;b&gt;') back into a real tag
    and swallow it, undercounting the width. The input is parsed from the
    *rendered* SVG, where svg_utils.text() has already html.escape()d content.
    """
    visible = html.unescape(_re.sub(r'<[^>]+>', '', content))
    coef = 0.62 if bold else 0.55
    return sum(font_size * (1.0 if ord(ch) > 0x2E80 else coef) for ch in visible)


def check_text_overflow(drawer, canvas_pad=2, container_pad=6):
    """Detect <text> elements that overflow the canvas or their container rect.

    Parses the rendered SVG (not the registry) so raw add_element text is caught.
    Two failure modes:
      (a) canvas overflow — text bbox exceeds the canvas (FAIL-grade);
      (b) container overflow — text center lies inside a <rect> but the text is
          wider than (rect.width - container_pad), i.e. it spills past the box
          that visually owns it (WARN-grade). The most specific (smallest-area)
          containing rect is chosen, so a card inside a band is judged against
          the card, not the band.
    """
    issues_fail, issues_warn = [], []
    svg = drawer.render()
    W, H = drawer.width, drawer.height
    # collect rects with role
    rects = []
    for attrs in _re.findall(r'<rect ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            rx, ry = float(p['x']), float(p['y'])
            rw, rh = float(p['width']), float(p['height'])
        except (KeyError, ValueError):
            continue
        rects.append((rx, ry, rw, rh, p.get('data-graph-role', '')))
    # collect texts
    for attrs, content in _re.findall(r'<text ([^>]*)>(.*?)</text>', svg, _re.DOTALL):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            tx, ty = float(p['x']), float(p['y'])
        except (KeyError, ValueError):
            continue
        if not content.strip():
            continue
        fs = float(p.get('font-size', '12'))
        anchor = p.get('text-anchor', 'start')
        bold = 'bold' in p.get('font-weight', 'normal')
        w = _estimate_text_width(content, fs, bold)
        if anchor == 'middle':
            lx = tx - w / 2
        elif anchor == 'end':
            lx = tx - w
        else:
            lx = tx
        rx = lx + w
        asc, desc = ty - fs * 0.5, ty + fs * 0.5  # dominant-baseline="central" -> (x,y) is the vertical center
        snippet = content.strip()[:32]
        # (a) canvas overflow
        if lx < -canvas_pad or rx > W + canvas_pad or asc < -canvas_pad or desc > H + canvas_pad:
            issues_fail.append(
                f"[text] '{snippet}' overflows canvas (x {lx:.0f}-{rx:.0f}, y {asc:.0f}-{desc:.0f})."
            )
            continue
        # (b) container overflow vs the smallest rect containing the text anchor.
        # Use the anchor point (tx, baseline ty) — the text's (x,y) normally sits
        # inside its owning box even when the rendered glyphs spill past the edge.
        cx, cy = tx, ty
        containing = [(a, b, c, e, role) for (a, b, c, e, role) in rects
                      if c >= 4 and e >= 4 and a <= cx <= a + c and b <= cy <= b + e]
        if containing:
            a, b, c, e, role = min(containing, key=lambda r: r[2] * r[3])
            if lx < a + container_pad or rx > a + c - container_pad:
                issues_warn.append(
                    f"[text] '{snippet}' overflows container "
                    f"({c:.0f}x{e:.0f}, role={role or 'node'}): text w={w:.0f}."
                )
    return issues_fail, issues_warn


def _seg_rect_intersect(x1, y1, x2, y2, rx, ry, rw, rh):
    """Liang-Barsky: does segment (x1,y1)-(x2,y2) meet rect [rx,ry,rw,rh]?"""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx), (dx, rx + rw - x1), (-dy, y1 - ry), (dy, ry + rh - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return t0 <= t1


def _point_in_poly(px, py, pts):
    """Ray-casting point-in-polygon test (pts = list of (x, y))."""
    n = len(pts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _rects_overlap(a, b):
    """AABB overlap test for (x, y, w, h) tuples; touching edges do not count."""
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0]
                or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def check_text_overlaps(drawer, pad=1.0):
    """Detect <text> elements overlapping visible shapes OR other text.

    Parses the rendered SVG (registry-blind) — closes the gap left by
    check_collisions() (which only sees bbox-registered elements) and
    check_text_overflow() (which only compares text vs <rect> containers).
    Two failure modes:
      (a) text-vs-shape: a <text> bbox intersects a visible circle/rect/
          polygon/line/path. Legend/background shapes and rects fully
          containing the text (intentional in-box labels) are exempt.
      (b) text-vs-text: two <text> bboxes intersect.

    Text bbox uses the center model (dominant-baseline="central"): (x,y) is
    the vertical center and height = font_size. Shapes drawn inside a
    <g transform> (database/cloud/component/...) are in local coords here;
    those are already covered by check_collisions() via the node registry
    (register_node maps group-local coords to absolute). This check targets
    raw add_element shapes and text that bypass the registry — the documented
    blind spot where text/labels drawn with bbox=False are invisible to the
    collision registry.
    """
    issues = []
    svg = drawer.render()
    W, H = drawer.width, drawer.height

    # ---- collect text bboxes (center model) ----
    texts = []  # (x, y, w, h, content)
    for attrs, content in _re.findall(r'<text ([^>]*)>(.*?)</text>', svg, _re.DOTALL):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            tx, ty = float(p['x']), float(p['y'])
        except (KeyError, ValueError):
            continue
        if not content.strip():
            continue
        fs = float(p.get('font-size', '12'))
        bold = 'bold' in p.get('font-weight', 'normal')
        w = _estimate_text_width(content, fs, bold)
        anchor = p.get('text-anchor', 'start')
        lx = tx - w / 2 if anchor == 'middle' else (tx - w if anchor == 'end' else tx)
        texts.append((lx, ty - fs / 2, w, fs, content.strip()))

    # ---- collect visible shapes (skip role=legend/background for shapes) ----
    def _visible(p):
        return not (p.get('fill', 'none') == 'none' and p.get('stroke', 'none') == 'none')

    circles = []
    for attrs in _re.findall(r'<circle ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        if not _visible(p):
            continue
        try:
            circles.append((float(p['cx']), float(p['cy']), float(p['r']), p.get('data-graph-role', '')))
        except (KeyError, ValueError):
            pass
    rects = []
    for attrs in _re.findall(r'<rect ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        if not _visible(p):
            continue
        try:
            rects.append((float(p['x']), float(p['y']), float(p['width']), float(p['height']), p.get('data-graph-role', '')))
        except (KeyError, ValueError):
            pass
    polys = []
    for attrs in _re.findall(r'<polygon ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        if not _visible(p):
            continue
        try:
            pts = [tuple(map(float, c.split(','))) for c in p['points'].split()]
            polys.append((pts, p.get('data-graph-role', '')))
        except (KeyError, ValueError):
            pass
    lines = []
    for attrs in _re.findall(r'<line ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            lines.append((float(p['x1']), float(p['y1']), float(p['x2']), float(p['y2']), p.get('data-graph-role', '')))
        except (KeyError, ValueError):
            pass
    paths = []
    for m in _re.findall(r'<path d="([^"]*)"[^>]*/>', svg):
        sampled = sample_path(m)
        if sampled:
            paths.append(sampled)

    def _shape_hits(tx, ty, tw, th):
        """Yield (kind, desc) for each visible shape overlapping the text bbox."""
        tb = (tx, ty, tw, th)
        for cx, cy, r, role in circles:
            if role in ('legend',):
                continue
            nx = max(tx, min(cx, tx + tw))
            ny = max(ty, min(cy, ty + th))
            if (cx - nx) ** 2 + (cy - ny) ** 2 < (r - pad) ** 2:
                yield ('circle', 'circle (%.0f,%.0f) r=%.0f' % (cx, cy, r))
        for rx, ry, rw, rh, role in rects:
            # skip legend/background shapes and the full-canvas bg rect
            if role in ('legend', 'background'):
                continue
            if rx <= 1 and ry <= 1 and rx + rw >= W - 1 and ry + rh >= H - 1:
                continue
            if _rects_overlap(tb, (rx, ry, rw, rh)):
                # exempt: rect fully contains the text (intentional in-box label)
                if rx <= tx and ty >= ry and tx + tw <= rx + rw and ty + th <= ry + rh:
                    continue
                yield ('rect', 'rect (%.0f,%.0f,%.0f,%.0f)' % (rx, ry, rw, rh))
        for pts, role in polys:
            if role in ('legend', 'background'):
                continue
            pxs = [pt[0] for pt in pts]
            pys = [pt[1] for pt in pts]
            pb = (min(pxs), min(pys), max(pxs) - min(pxs), max(pys) - min(pys))
            if not _rects_overlap(tb, pb):
                continue
            samples = [(tx, ty), (tx + tw, ty), (tx, ty + th), (tx + tw, ty + th), (tx + tw / 2, ty + th / 2)]
            if any(_point_in_poly(sx, sy, pts) for sx, sy in samples):
                yield ('polygon', 'polygon near (%.0f,%.0f)' % (tx + tw / 2, ty + th / 2))
        for x1, y1, x2, y2, role in lines:
            if role in ('legend',):
                continue
            if _seg_rect_intersect(x1, y1, x2, y2, tx - pad, ty - pad, tw + 2 * pad, th + 2 * pad):
                yield ('line', 'line (%.0f,%.0f)-(%.0f,%.0f)' % (x1, y1, x2, y2))
        for sp in paths:
            hit = False
            for k in range(len(sp) - 1):
                if _seg_rect_intersect(sp[k][0], sp[k][1], sp[k + 1][0], sp[k + 1][1],
                                  tx - pad, ty - pad, tw + 2 * pad, th + 2 * pad):
                    hit = True
                    break
            if hit:
                yield ('path', 'path near (%.0f,%.0f)' % (tx + tw / 2, ty + th / 2))

    # (a) text vs shape
    for tx, ty, tw, th, content in texts:
        snippet = content[:32]
        for kind, desc in _shape_hits(tx, ty, tw, th):
            issues.append("[text] '%s' overlaps %s (%s)." % (snippet, kind, desc))

    # (b) text vs text
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a = texts[i]
            b = texts[j]
            if _rects_overlap(a[:4], b[:4]):
                issues.append("[text] '%s' overlaps text '%s'." % (a[4][:32], b[4][:32]))
    return issues


def check_connections(drawer, tolerance=12.0, min_length=4.0):
    """Validate that every registered Edge actually lands on a Node border.

    Returns a list of human-readable issue strings. An edge endpoint is
    "dangling" when its nearest registered node border is farther than
    `tolerance` pixels away. Edges shorter than `min_length` are degenerate.

    Args:
        drawer: SVGDrawer with .nodes and .edges populated.
        tolerance: max allowed distance (px) from an endpoint to a node border.
        min_length: edges shorter than this (px) are flagged as degenerate.
    """
    issues = []
    if not drawer.nodes:
        # Nothing to connect to; skip silently.
        return issues

    for edge in drawer.edges:
        # Degenerate / zero-length edges.
        if edge.length < min_length:
            issues.append(
                f"[edge:{edge.id}] Degenerate edge length {edge.length:.1f}px "
                f"(< {min_length}); from {edge.start} to {edge.end}."
            )
            continue

        for ep_name, pt in (("start", edge.start), ("end", edge.end)):
            node, dist = drawer.nearest_node(pt[0], pt[1])
            if node is None:
                issues.append(
                    f"[edge:{edge.id}] {ep_name} at ({pt[0]:.0f},{pt[1]:.0f}) "
                    f"has no registered node to connect to."
                )
            elif dist > tolerance:
                issues.append(
                    f"[edge:{edge.id}] {ep_name} at ({pt[0]:.0f},{pt[1]:.0f}) "
                    f"dangles: nearest node '{node.id}' is {dist:.1f}px away "
                    f"(tol={tolerance:.0f})."
                )
    return issues


def check_duplicate_edges(drawer, tol=6.0):
    """Flag near-duplicate edges (same endpoints within `tol` px)."""
    issues = []
    edges = drawer.edges
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            a, b = edges[i], edges[j]
            d_start = math.hypot(a.start[0] - b.start[0], a.start[1] - b.start[1])
            d_end = math.hypot(a.end[0] - b.end[0], a.end[1] - b.end[1])
            if d_start < tol and d_end < tol:
                issues.append(
                    f"[edge:{a.id}] overlaps [edge:{b.id}] "
                    f"(start Δ{d_start:.1f}px, end Δ{d_end:.1f}px)."
                )
    return issues


PATH_TOKEN_RE = _re.compile(r"[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _sample_cubic(p0, p1, p2, p3, steps=16):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _sample_quadratic(p0, p1, p2, steps=12):
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0]
        y = mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1]
        pts.append((x, y))
    return pts


def sample_path(path_d):
    """Flatten an SVG path `d` into a polyline of (x, y) points.

    Supports M/L/H/V/C/S/Q/T/Z (absolute & relative). Arcs (A) are approximated
    by their chord (endpoints only) — adequate for collision/crossing checks.
    Ported from fireworks-tech-graph path_routes.
    """
    if not path_d:
        return []
    tokens = PATH_TOKEN_RE.findall(path_d)
    routes = []
    points = []
    idx = 0
    cmd = ""
    cur = (0.0, 0.0)
    start = cur
    prev_c = None
    prev_q = None

    def read(n):
        nonlocal idx
        if idx + n > len(tokens) or any(_re.fullmatch(r"[A-Za-z]", t) for t in tokens[idx:idx + n]):
            return None
        vals = [float(t) for t in tokens[idx:idx + n]]
        idx += n
        return vals

    def abspt(x, y, rel):
        return (cur[0] + x, cur[1] + y) if rel else (x, y)

    while idx < len(tokens):
        if _re.fullmatch(r"[A-Za-z]", tokens[idx]):
            cmd = tokens[idx]; idx += 1
        if not cmd:
            return []
        rel = cmd.islower()
        op = cmd.upper()
        if op == "Z":
            if cur != start:
                points.append(start)
            cur = start; prev_c = prev_q = None; cmd = ""
            continue
        count = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}.get(op)
        if count is None:
            return []
        vals = read(count)
        if vals is None:
            return []
        if op == "M":
            if points:
                routes.append(points)
            cur = abspt(vals[0], vals[1], rel); start = cur; points = [cur]
            cmd = "l" if rel else "L"
        elif op == "L":
            cur = abspt(vals[0], vals[1], rel); points.append(cur)
        elif op == "H":
            cur = (cur[0] + vals[0], cur[1]) if rel else (vals[0], cur[1]); points.append(cur)
        elif op == "V":
            cur = (cur[0], cur[1] + vals[0]) if rel else (cur[0], vals[0]); points.append(cur)
        elif op == "C":
            c1 = abspt(vals[0], vals[1], rel); c2 = abspt(vals[2], vals[3], rel); e = abspt(vals[4], vals[5], rel)
            points.extend(_sample_cubic(cur, c1, c2, e))
            cur, prev_c = e, c2; prev_q = None
        elif op == "S":
            c1 = (2 * cur[0] - prev_c[0], 2 * cur[1] - prev_c[1]) if prev_c else cur
            c2 = abspt(vals[0], vals[1], rel); e = abspt(vals[2], vals[3], rel)
            points.extend(_sample_cubic(cur, c1, c2, e))
            cur, prev_c = e, c2; prev_q = None
        elif op == "Q":
            c = abspt(vals[0], vals[1], rel); e = abspt(vals[2], vals[3], rel)
            points.extend(_sample_quadratic(cur, c, e))
            cur, prev_q = e, c; prev_c = None
        elif op == "T":
            c = (2 * cur[0] - prev_q[0], 2 * cur[1] - prev_q[1]) if prev_q else cur
            e = abspt(vals[0], vals[1], rel)
            points.extend(_sample_quadratic(cur, c, e))
            cur, prev_q = e, c; prev_c = None
        elif op == "A":
            e = abspt(vals[5], vals[6], rel)
            points.append(e)  # chord approximation
            cur = e; prev_c = prev_q = None
        if op not in {"C", "S", "Q", "T"}:
            prev_c = prev_q = None
    if points:
        routes.append(points)
    return routes[0] if len(routes) == 1 else [p for r in routes for p in r]


def edge_polyline(edge):
    """Return the edge as a list of (x,y) vertices, sampling curves if present.

    Falls back to [start, end] for straight-line edges (no path_d).
    """
    if getattr(edge, "path_d", None):
        sampled = sample_path(edge.path_d)
        if sampled:
            return sampled
    return [edge.start, edge.end]

def _segment_core_hit(p1, p2, rect, samples=24):
    """True if the segment p1->p2 passes through the *core* of `rect`.

    `rect` is a (x, y, w, h) tuple already shrunk to the "interior core" (a
    margin inset from the true border), so lines that merely graze the edge do
    not register. Straight-line sampling is sufficient for connect() straight
    edges; curved edges are approximated by their chord (under-detects).
    """
    x0, y0, x1, y1 = p1[0], p1[1], p2[0], p2[1]
    rx, ry, rw, rh = rect
    for i in range(samples + 1):
        t = i / samples
        px = x0 + (x1 - x0) * t
        py = y0 + (y1 - y0) * t
        if rx < px < rx + rw and ry < py < ry + rh:
            return True
    return False


def check_edge_node_collisions(drawer, interior_margin=3.0, conn_tolerance=12.0):
    """Detect edges that cut through nodes they are not connected to.

    Each edge is flattened to a polyline (curves sampled via sample_path) and
    every segment is tested against each registered node whose border is NOT
    the edge's own endpoint owner. A hit means the line crosses the node's
    interior core (inset by `interior_margin`), i.e. it routes *through* an
    unrelated component. Inspired by ink-graph pitfall #3 and fireworks-tech-graph
    find_collisions + segment_hits_bounds.
    """
    issues = []
    if not drawer.nodes or not drawer.edges:
        return issues
    for edge in drawer.edges:
        if getattr(edge, "role", "edge") != "edge":
            continue  # decorative edges (rail casings) don't count
        owner_start, _ = drawer.nearest_node(*edge.start)
        owner_end, _ = drawer.nearest_node(*edge.end)
        owners = {n.id for n in (owner_start, owner_end) if n is not None}
        poly = edge_polyline(edge)
        for nid, node in drawer.nodes.items():
            if nid in owners or getattr(node, "role", "node") != "node":
                continue  # decorative/legend nodes aren't routing obstacles
            core = (node.x + interior_margin, node.y + interior_margin,
                    max(node.w - 2 * interior_margin, 1.0),
                    max(node.h - 2 * interior_margin, 1.0))
            if any(_segment_core_hit(a, b, core) for a, b in zip(poly, poly[1:])):
                issues.append(
                    f"[edge:{edge.id}] routes through node '{nid}' interior "
                    f"({edge.start}->{edge.end})."
                )
    return issues


def check_spacing(drawer, min_gap=14.0, kinds=("op", "junction")):
    """Flag same-kind nodes closer than `min_gap` px (Euclidean gap).

    Container/containment pairs are excluded by restricting to sibling kinds
    (op-vs-op, junction-vs-junction), so an op inside a layer is not penalised.
    """
    issues = []
    nodes = [n for n in drawer.nodes.values() if n.kind in kinds and getattr(n, "role", "node") == "node"]
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            dx = max(a.x - (b.x + b.w), b.x - (a.x + a.w), 0.0)
            dy = max(a.y - (b.y + b.h), b.y - (a.y + a.h), 0.0)
            gap = math.hypot(dx, dy)
            if gap < min_gap:
                issues.append(
                    f"[spacing] '{a.id}' and '{b.id}' only {gap:.1f}px apart "
                    f"(< {min_gap})."
                )
    return issues


def _overlap_len(a0, a1, b0, b1):
    """Length of the overlap of intervals [a0,a1] and [b0,b1]; 0 if disjoint."""
    return max(0.0, min(a1, b1) - max(a0, b0))


def check_alignment(drawer, edge_tol=5.0, center_frac=0.15,
                    overlap_frac=0.5, size_tol=6.0, kinds=("op",)):
    """Flag same-kind nodes that read as a row/column yet share no edge.

    Two same-kind visible nodes are "row peers" when their vertical extents
    overlap strongly (>= overlap_frac of the shorter height) while their
    horizontal extents do not overlap (side-by-side) — the eye then expects a
    shared top, bottom, or vertical-center line. "Column peers" mirror this on
    the other axis. A pair is flagged only when it shares NEITHER an edge
    (within edge_tol) NOR a center line (within center_frac * the shorter
    side), which keeps false positives low. Only SAME-SIZED peers (w/h within
    size_tol) are compared: a row/column of differently-sized components
    legitimately staggers, and "should align" only applies to peer modules of
    the same footprint. Encodes the "align to shared edges" layout principle.
    """
    issues = []
    nodes = [n for n in drawer.nodes.values()
             if n.kind in kinds and getattr(n, "role", "node") == "node" and n.visible]
    for i in range(len(nodes)):
        a = nodes[i]
        ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.w, a.y + a.h
        for j in range(i + 1, len(nodes)):
            b = nodes[j]
            bx0, by0, bx1, by1 = b.x, b.y, b.x + b.w, b.y + b.h
            # Only same-sized peers are expected to share an alignment edge;
            # a row/column of differently-sized components legitimately staggers.
            if abs(a.w - b.w) > size_tol or abs(a.h - b.h) > size_tol:
                continue
            vov = _overlap_len(ay0, ay1, by0, by1)
            hov = _overlap_len(ax0, ax1, bx0, bx1)
            # row peers: strong vertical overlap, side by side (no h-overlap)
            min_h = min(a.h, b.h)
            if min_h > 0 and vov >= overlap_frac * min_h and hov <= 0:
                acy, bcy = (ay0 + ay1) * 0.5, (by0 + by1) * 0.5
                if not (abs(ay0 - by0) <= edge_tol            # top edge
                        or abs(ay1 - by1) <= edge_tol          # bottom edge
                        or abs(acy - bcy) <= center_frac * min_h):
                    issues.append(
                        f"[alignment] row peers '{a.id}' and '{b.id}' share no "
                        f"top/bottom/center line (top Δ{abs(ay0-by0):.0f}px, "
                        f"bottom Δ{abs(ay1-by1):.0f}px)."
                    )
                continue
            # column peers: strong horizontal overlap, stacked (no v-overlap)
            min_w = min(a.w, b.w)
            if min_w > 0 and hov >= overlap_frac * min_w and vov <= 0:
                acx, bcx = (ax0 + ax1) * 0.5, (bx0 + bx1) * 0.5
                if not (abs(ax0 - bx0) <= edge_tol            # left edge
                        or abs(ax1 - bx1) <= edge_tol          # right edge
                        or abs(acx - bcx) <= center_frac * min_w):
                    issues.append(
                        f"[alignment] column peers '{a.id}' and '{b.id}' share "
                        f"no left/right/center line (left Δ{abs(ax0-bx0):.0f}px, "
                        f"right Δ{abs(ax1-bx1):.0f}px)."
                    )
    return issues

def check_phantom_anchors(drawer):
    """Detect invisible nodes used as edge endpoints (phantom anchors).

    A node registered with fill=none + stroke=none (or opacity=0 / zero size)
    renders nothing, so any edge that lands on it is visually dangling even
    though the geometric connection check passes. This catches the "add an
    invisible box to fool the validator" anti-pattern. Only nodes that are
    actually referenced by at least one edge are reported.
    """
    issues = []
    if not drawer.edges:
        return issues
    referenced = set()
    for edge in drawer.edges:
        for pt in (edge.start, edge.end):
            node, _ = drawer.nearest_node(*pt)
            if node is not None:
                referenced.add(node.id)
    for nid in sorted(referenced):
        node = drawer.nodes.get(nid)
        if node is not None and not node.visible:
            issues.append(
                f"[phantom] node '{nid}' is invisible (no fill/stroke or zero "
                f"opacity/size) but is used as an edge endpoint."
            )
    return issues


def _orient(a, b, c):
    """Sign of the cross product (b-a) x (c-a): >0 ccw, <0 cw, 0 collinear."""
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_properly_cross(p1, p2, p3, p4):
    """True iff segment p1p2 and p3p4 cross strictly in their interiors.

    Excludes touching endpoints/collinear overlap, so edges sharing a node
    (fan-out) are not flagged. Uses the standard orientation test.
    """
    d1 = _orient(p3, p4, p1)
    d2 = _orient(p3, p4, p2)
    d3 = _orient(p1, p2, p3)
    d4 = _orient(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def check_edge_crossings(drawer):
    """Detect pairs of edges whose polylines cross in their interiors.

    A zero-crossing budget is a standard diagram quality gate (see
    fireworks-tech-graph composition contract). Edges are flattened to
    polylines (curves sampled via sample_path) and every segment pair is tested
    with the orientation test; touching endpoints/collinear overlap are excluded
    so edges sharing a node (fan-out) are not flagged.
    """
    issues = []
    edges = [e for e in drawer.edges if getattr(e, "role", "edge") == "edge"]
    polylines = [edge_polyline(e) for e in edges]
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            pa, pb = polylines[i], polylines[j]
            crossed = False
            for a1, a2 in zip(pa, pa[1:]):
                if crossed:
                    break
                for b1, b2 in zip(pb, pb[1:]):
                    if _segments_properly_cross(a1, a2, b1, b2):
                        crossed = True
                        break
            if crossed:
                issues.append(f"[cross] edge '{edges[i].id}' crosses edge '{edges[j].id}'.")
    return issues




def _text_bboxes(svg):
    """Parse all <text> elements into (lx, ty, rx, by) bboxes (registry-blind).

    Used so text counts as a measurable obstacle for edge/label collision —
    fireworks contract rule 7: "every title/label/legend is an obstacle with
    measurable bounds". Width via the same font-metric estimate as
    check_text_overflow.
    """
    out = []
    for attrs, content in _re.findall(r'<text ([^>]*)>(.*?)</text>', svg, _re.DOTALL):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            tx, ty = float(p['x']), float(p['y'])
        except (KeyError, ValueError):
            continue
        if not content.strip():
            continue
        fs = float(p.get('font-size', '12'))
        anchor = p.get('text-anchor', 'start')
        bold = 'bold' in p.get('font-weight', 'normal')
        w = _estimate_text_width(content, fs, bold)
        if anchor == 'middle':
            lx = tx - w / 2
        elif anchor == 'end':
            lx = tx - w
        else:
            lx = tx
        out.append((lx, ty - fs * 0.5, lx + w, ty + fs * 0.5))
    return out


def _seg_hits_rect(p1, p2, rect, samples=12):
    """True if segment p1->p2 passes through rect interior (sampled)."""
    x0, y0, x1, y1 = p1[0], p1[1], p2[0], p2[1]
    rx, ry, rw, rh = rect
    for i in range(samples + 1):
        t = i / samples
        if rx < x0 + (x1 - x0) * t < rx + rw and ry < y0 + (y1 - y0) * t < ry + rh:
            return True
    return False


def check_composition(drawer, max_bends=2, max_route_stretch=1.35,
                      min_gutter=20.0, min_segment=16.0):
    """Composition-quality budget (ported from fireworks assess_composition).

    Quantifies "looks clean" into enforceable thresholds on edges and layout:
      - bends per edge (orthogonal turns in the sampled polyline);
      - route stretch (path length / manhattan distance start->end);
      - shortest segment (micro-segments look like rendering bugs);
      - container gutter (node floating inside its container too close to edge);
      - text as obstacle (edge segment passes through a <text> bbox — rule 7).
    Returns (fail_issues, warn_issues) lists.
    """
    fail, warn = [], []
    edges = [e for e in drawer.edges if getattr(e, "role", "edge") == "edge"]
    for edge in edges:
        poly = edge_polyline(edge)
        eid = edge.id or "edge"
        length = sum(math.hypot(poly[k+1][0]-poly[k][0], poly[k+1][1]-poly[k][1])
                     for k in range(len(poly)-1))
        direct = math.hypot(poly[-1][0]-poly[0][0], poly[-1][1]-poly[0][1])
        stretch = length / direct if direct > 1e-9 else 1.0
        if stretch > max_route_stretch + 1e-6:
            warn.append(f"[composition] edge '{eid}' stretch {stretch:.2f} > {max_route_stretch}.")
        # Curves (path_d with a curve command C/S/Q/T/A) are continuous-curvature
        # by design — sampling one into a polyline yields many tiny non-collinear
        # segments that are NOT orthogonal bends, and the micro-segments are
        # tessellation artifacts, not layout bugs. So bend/shortest-segment checks
        # apply to straight-line edges (raw line() or M/L/H/V-only paths) only.
        # A curve that loops too far is still caught by the stretch check above.
        # (A polyline path_d with only M/L/H/V/Z is straight-line routing and
        # MUST still be checked — it has genuine orthogonal bends.)
        pd = getattr(edge, "path_d", None)
        is_curve = bool(pd) and bool(_re.search(r"[cCqQtTaAsS]", pd))
        if is_curve:
            continue
        # Straight edge: count discrete turns. A real bend is a direction change
        # above an angle threshold (>15 deg), robust to sub-pixel jitter that
        # made the old exact `cross != 0` test fire on every sample.
        bends = 0
        BEND_ANGLE = math.radians(15)
        for i in range(1, len(poly) - 1):
            dx1, dy1 = poly[i][0] - poly[i-1][0], poly[i][1] - poly[i-1][1]
            dx2, dy2 = poly[i+1][0] - poly[i][0], poly[i+1][1] - poly[i][1]
            if (abs(dx1) > 0.5 or abs(dy1) > 0.5) and (abs(dx2) > 0.5 or abs(dy2) > 0.5):
                cross = dx1 * dy2 - dy1 * dx2
                dot = dx1 * dx2 + dy1 * dy2
                if abs(math.atan2(abs(cross), dot)) > BEND_ANGLE:
                    bends += 1
        if bends > max_bends:
            warn.append(f"[composition] edge '{eid}' has {bends} bends (limit {max_bends}).")
        segs = [math.hypot(poly[k+1][0]-poly[k][0], poly[k+1][1]-poly[k][1])
                for k in range(len(poly)-1)]
        shortest = min(segs) if segs else None
        if shortest is not None and shortest < min_segment:
            warn.append(f"[composition] edge '{eid}' shortest segment {shortest:.1f}px < {min_segment}.")

    # container gutter: node vs its smallest containing rect (role=background/layer)
    svg = drawer.render()
    rects = []
    for attrs in _re.findall(r'<rect ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            rx, ry = float(p['x']), float(p['y'])
            rw, rh = float(p['width']), float(p['height'])
        except (KeyError, ValueError):
            continue
        role = p.get('data-graph-role', '')
        if role in ('background', 'layer') and rw > 10 and rh > 10:
            rects.append((rx, ry, rw, rh, role))
    for nid, node in drawer.nodes.items():
        if getattr(node, "role", "node") != "node":
            continue
        # Only judge gutter when the node is FULLY inside the container
        # (all four edges within) — center-only containment misflags legitimate
        # cross-band nodes that intentionally straddle a boundary.
        nx0, ny0, nx1, ny1 = node.x, node.y, node.x + node.w, node.y + node.h
        containing = [r for r in rects
                      if r[0] <= nx0 and nx1 <= r[0]+r[2] and r[1] <= ny0 and ny1 <= r[1]+r[3]]
        if not containing:
            continue
        c = min(containing, key=lambda r: r[2]*r[3])
        gutter = min(node.x - c[0], c[0]+c[2]-(node.x+node.w),
                     node.y - c[1], c[1]+c[3]-(node.y+node.h))
        if gutter < min_gutter:
            warn.append(f"[composition] node '{nid}' gutter {gutter:.1f}px < {min_gutter} in container.")

    # text as obstacle: any edge segment passes through a <text> bbox
    tboxes = _text_bboxes(svg)
    if tboxes and edges:
        for edge in edges:
            poly = edge_polyline(edge)
            for a, b in zip(poly, poly[1:]):
                for (tlx, tty, trx, tby) in tboxes:
                    if _seg_hits_rect(a, b, (tlx, tty, trx-tlx, tby-tty)):
                        eid = edge.id or "edge"
                        fail.append(f"[composition] edge '{eid}' passes through text bbox.")
                        break
                else:
                    continue
                break
    return fail, warn

def _extract_font_sizes(svg):
    """Primary font-size values used in the rendered SVG (float list).

    Counts font-size on <text> elements only — subscript/superscript
    <tspan> modifiers are derivative of their parent text size and are NOT
    independent typographic tiers, so they are excluded from the tier count.
    """
    sizes = []
    for attrs in _re.findall(r'<text\s+([^>]*)>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        val = p.get('font-size')
        if val is None:
            continue
        try:
            sizes.append(float(val))
        except ValueError:
            pass
    return sizes


def _extract_colors(svg):
    """All non-neutral accent fill/stroke colors in the rendered SVG (#rrggbb set)."""
    from svg_utils import normalize_color, is_neutral
    accents = set()
    for raw in _re.findall(r'(?:fill|stroke)="([^"]+)"', svg):
        norm = normalize_color(raw)
        if norm is not None and not is_neutral(norm):
            accents.add(norm)
    return accents


def _extract_fill_stroke(svg):
    """Return (fills, strokes) sets of non-neutral accent colors.

    Needed because luminance clash should compare within a channel: a pastel
    fill (L>0.8) paired with a same-family dark stroke (L<0.2) is intentional
    contrast, NOT a clash. Only a dark fill AND a light fill (or dark stroke
    AND light stroke) is a genuine inconsistency.
    """
    from svg_utils import normalize_color, is_neutral
    fills, strokes = set(), set()
    for raw in _re.findall(r'fill="([^"]+)"', svg):
        norm = normalize_color(raw)
        if norm is not None and not is_neutral(norm):
            fills.add(norm)
    for raw in _re.findall(r'stroke="([^"]+)"', svg):
        norm = normalize_color(raw)
        if norm is not None and not is_neutral(norm):
            strokes.add(norm)
    return fills, strokes


def _extract_background(svg, width, height):
    """Fill of a full-canvas rect at (0,0), else None."""
    from svg_utils import normalize_color
    pat = (r'<rect[^>]*\bx="0"[^>]*\by="0"[^>]*\bwidth="%d"[^>]*\bheight="%d"[^>]*\bfill="([^"]+)"'
           % (width, height))
    m = _re.search(pat, svg)
    if m:
        return normalize_color(m.group(1))
    return None


def check_font_scale(drawer, max_sizes=4, min_step=1.15):
    """Enforce a limited, well-separated type scale (parses the rendered SVG).

    A diagram should use a small number of font sizes (professional styles
    empirically use 3-4: title / body / caption). Two failure modes:
      - too many distinct sizes (chaotic typography);
      - near-duplicate sizes (e.g. 11/12/13/14) that should be consolidated
        into one — adjacent sizes should differ by >= min_step ratio (a
        modular type scale; 1.15 ~ major-second/minor-third).
    Parses the actual SVG so it works regardless of how text was drawn.
    """
    issues = []
    sizes = sorted(set(_extract_font_sizes(drawer.render())))
    if len(sizes) > max_sizes:
        issues.append(
            f"[font] {len(sizes)} distinct font sizes used ({sizes}); cap is "
            f"{max_sizes}. Consolidate into a title/body/caption scale."
        )
    near_dup = []
    for a, b in zip(sizes, sizes[1:]):
        if a > 0 and b / a < min_step:
            near_dup.append(f"{a}/{b} (ratio {b/a:.2f} < {min_step})")
    if near_dup:
        issues.append(
            f"[font] near-duplicate font sizes: {'; '.join(near_dup)}. Merge "
            f"them (adjacent sizes should differ by >= {min_step}x)."
        )


def _is_chromatic(color):
    """True when a color carries a usable hue (HSL saturation >= 0.25).

    Desaturated blue-grays (slate tones like #546E7A, S≈0.18) pass
    ``is_neutral``'s R==G==B filter yet read as colorless; pastel tints
    (#DAE8FC, S≈0.85) read as colored despite their lightness. The palette
    floor below keys on this distinction, not on the neutral filter.
    """
    h = color.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    if len(h) != 6:
        return False
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return False
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2.0
    if mx == mn:
        return False                       # pure gray
    s = (mx - mn) / (2 - 2 * l) if l > 0.5 else (mx - mn) / (2 * l)
    return s >= 0.25


def check_palette(drawer, max_colors=8, hard_max=12):
    """Enforce a constrained, coherent color palette (parses the rendered SVG).

    Counts accent colors (non-neutral fills/strokes) actually drawn. Flags:
      - too many accents (cluttered; warn > max_colors, fail > hard_max);
      - extreme luminance clash WITHIN a channel: very dark (L<0.2) and very
        light (L>0.8) accents coexist among fills, or among strokes. A pastel
        fill paired with a same-family dark stroke is intentional contrast and
        is NOT flagged — only a dark+light mix in the same channel is chaos;
      - non-light background without an explicit dark-theme opt-in.
    Neutral colors (white/black/grays) are structural and excluded from count.
    """
    from svg_utils import relative_luminance
    issues = []
    svg = drawer.render()
    bg = _extract_background(svg, drawer.width, drawer.height)
    accents = sorted(_extract_colors(svg))
    if bg:
        accents = [c for c in accents if c != bg]  # bg is judged separately

    # Count.
    if len(accents) > hard_max:
        issues.append(
            f"[palette] {len(accents)} accent colors used ({accents}); hard cap "
            f"is {hard_max}. Reduce the palette."
        )
    elif len(accents) > max_colors:
        issues.append(
            f"[palette] {len(accents)} accent colors used ({accents}); recommend "
            f"<= {max_colors} for a coherent look."
        )

    # Chromatic floor (无配色): at least one accent must carry a real hue.
    # The observed end-state of "fix contrast by de-coloring" is a diagram
    # whose only accents are desaturated slate tones (#546E7A et al.) or none
    # at all — technically not neutral, visually colorless. That is a defect,
    # not a safe palette: the cap above is meaningless without a floor.
    chroma = [c for c in accents if _is_chromatic(c)]
    if not chroma:
        shown = sorted(accents) if accents else ["(none)"]
        issues.append(
            f"[palette] no chromatic accent color (无配色): accents {shown} "
            f"carry no readable hue - the diagram is effectively colorless. "
            f"Pick a preset scheme from references/design_specs.md "
            f"(S1-S4) and put color into tinted layer fills + accent strokes. "
            f"Do NOT fix text contrast by de-coloring: pair a light tint fill "
            f"with its dark accent stroke instead (clears WCAG AA)."
        )

    # Extreme luminance clash, compared WITHIN each channel (fill vs fill,
    # stroke vs stroke). A pastel fill paired with a same-family dark stroke is
    # intentional contrast, not a clash — only a dark+light mix in the SAME
    # channel signals a neon/pastel inconsistency.
    fills, strokes = _extract_fill_stroke(svg)
    if bg:
        fills = {c for c in fills if c != bg}
    for channel, colors in (("fill", fills), ("stroke", strokes)):
        if len(colors) < 2:
            continue
        lums = {c: relative_luminance(c) for c in colors}
        dark = sorted(c for c, l in lums.items() if l < 0.2)
        light = sorted(c for c, l in lums.items() if l > 0.8)
        if dark and light:
            issues.append(
                f"[palette] extreme luminance clash in {channel}s: very dark "
                f"{dark} and very light {light} coexist; pick one brightness family."
            )
    # Background: light is the default for technical diagrams.
    bg = bg or getattr(drawer, "background", "#ffffff")
    if relative_luminance(bg) < 0.3:
        issues.append(
            f"[palette] background '{bg}' is dark; light backgrounds are the "
            f"default. Use set_background()/bg= only for an intended dark theme."
        )
    return issues


def _contrast_ratio(fg, bg):
    """WCAG 2 contrast ratio (>=1.0) between two '#rrggbb' colors."""
    from svg_utils import relative_luminance
    lf, lb = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(lf, lb), min(lf, lb)
    return (hi + 0.05) / (lo + 0.05)


def check_contrast(drawer, normal_ratio=4.5, large_ratio=3.0,
                   large_px=24.0, large_bold_px=18.5):
    """WCAG 2 text-on-fill contrast (parses the rendered SVG).

    Pairs each <text> with the fill of the smallest <rect> containing its
    anchor point, falling back to the canvas background when no rect owns it,
    and measures the WCAG 2 contrast ratio against the text's own fill.
    Thresholds track WCAG 2 AA: 4.5:1 for normal text, 3:1 for large text
    (>=24px, or >=18.5px bold). Only text sitting on a non-neutral (accent)
    fill is measured: the defect this catches is a label that doesn't read on
    its colored card. Accent-colored text on a white/neutral canvas (category
    labels, muted captions) is a typographic choice, not a fill-contrast
    defect, and is skipped. Stroke-only (fill=none) containers are also
    skipped so the text is judged against the concrete fill painted behind it.
    Returns (fail_issues, warn_issues):
      - FAIL: below the large-text floor (large_ratio) — effectively unreadable;
      - WARN: large_ratio..normal_ratio — readable but below AA for labels.
    """
    from svg_utils import normalize_color, is_neutral
    fail, warn = [], []
    svg = drawer.render()
    W, H = drawer.width, drawer.height

    # rects that actually paint a background (skip fill=none containers)
    rects = []
    for attrs in _re.findall(r'<rect ([^>]*)/>', svg):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            rx, ry = float(p['x']), float(p['y'])
            rw, rh = float(p['width']), float(p['height'])
        except (KeyError, ValueError):
            continue
        fill = normalize_color(p.get('fill', ''))
        if fill is None:
            continue
        rects.append((rx, ry, rw, rh, fill))

    bg = _extract_background(svg, W, H) or getattr(drawer, "background", "#ffffff")
    bg = normalize_color(bg) or "#ffffff"

    for attrs, content in _re.findall(r'<text ([^>]*)>(.*?)</text>', svg, _re.DOTALL):
        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
        try:
            tx, ty = float(p['x']), float(p['y'])
        except (KeyError, ValueError):
            continue
        if not content.strip():
            continue
        fg = normalize_color(p.get('fill', 'black'))
        if fg is None:
            continue  # gradient/none text color — can't measure
        fs = float(p.get('font-size', '12'))
        bold = 'bold' in p.get('font-weight', 'normal')
        # background = smallest containing rect with a concrete fill, else canvas
        owners = [r for r in rects if r[0] <= tx <= r[0] + r[2] and r[1] <= ty <= r[1] + r[3]]
        owner_fill = min(owners, key=lambda r: r[2] * r[3])[4] if owners else bg
        if owner_fill == fg or is_neutral(owner_fill):
            continue  # identical fill, or neutral bg (canvas/white card) — the
                      # text color there is a typographic choice, not a fill defect
        ratio = _contrast_ratio(fg, owner_fill)
        threshold = large_ratio if (fs >= large_px or (bold and fs >= large_bold_px)) else normal_ratio
        snippet = content.strip()[:32]
        if ratio < large_ratio:
            fail.append(
                f"[contrast] '{snippet}' {ratio:.2f}:1 < {large_ratio}:1 "
                f"(text {fg} on {owner_fill}, {fs:.0f}px)."
            )
        elif ratio < threshold:
            warn.append(
                f"[contrast] '{snippet}' {ratio:.2f}:1 < {threshold}:1 "
                f"(text {fg} on {owner_fill}, {fs:.0f}px)."
            )
    return fail, warn

def evaluate_svg(drawer, conn_tolerance=12.0):
    report = []
    score = 100

    # 1. Collision Check (rect-level bounding-box overlap)
    collisions = drawer.check_collisions()
    if collisions:
        collision_penalty = len(collisions) * 10
        score -= collision_penalty
        report.append(f"[FAIL] Detected {len(collisions)} element collisions. Penalty: -{collision_penalty}")
    else:
        report.append("[PASS] No element collisions detected.")

    # 2. Boundary Check
    overflow_count = 0
    for bbox in drawer.bboxes:
        if bbox.x < 0 or bbox.y < 0 or bbox.x + bbox.w > drawer.width or bbox.y + bbox.h > drawer.height:
            overflow_count += 1

    if overflow_count > 0:
        overflow_penalty = overflow_count * 15
        score -= overflow_penalty
        report.append(f"[FAIL] {overflow_count} elements exceed canvas boundaries. Penalty: -{overflow_penalty}")
    else:
        report.append("[PASS] All elements are within canvas boundaries.")
    # 2b. Text overflow check — parses <text> geometry (registry-blind otherwise).
    t_fail, t_warn = check_text_overflow(drawer)
    if t_fail:
        score -= min(len(t_fail) * 6, 24)
        report.append(f"[FAIL] {len(t_fail)} text element(s) overflow the canvas. Penalty: -{min(len(t_fail) * 6, 24)}")
        for line in t_fail[:8]:
            report.append(f"        - {line}")
    if t_warn:
        score -= min(len(t_warn) * 3, 18)
        report.append(f"[WARN] {len(t_warn)} text element(s) overflow their container. Penalty: -{min(len(t_warn) * 3, 18)}")
        for line in t_warn[:8]:
            report.append(f"        - {line}")
    if not t_fail and not t_warn:
        report.append("[PASS] All text fits within canvas and containers.")

    # 2c. Text overlap check — text vs shapes AND text vs text (parses the
    #     rendered SVG, registry-blind). Closes the gap left by bbox-registered
    #     check_collisions for elements drawn with bbox=False / add_element.
    overlap_issues = check_text_overlaps(drawer)
    if overlap_issues:
        penalty = min(len(overlap_issues) * 4, 24)
        score -= penalty
        report.append(f"[FAIL] {len(overlap_issues)} text overlap(s) with shapes/other text. Penalty: -{penalty}")
        for line in overlap_issues[:12]:
            report.append(f"        - {line}")
        if len(overlap_issues) > 12:
            report.append(f"        - ... and {len(overlap_issues) - 12} more.")
    else:
        report.append("[PASS] No text overlaps shapes or other text.")

    # 3. Coverage Analysis
    total_area = drawer.width * drawer.height
    occupied_area = bbox_union_area(drawer.bboxes)
    coverage = (occupied_area / total_area) * 100 if total_area else 0

    if coverage < 5:
        score -= 20
        report.append(f"[WARN] Canvas coverage is very low ({coverage:.2f}%). The diagram might look empty.")
    elif coverage > 60:
        score -= 10
        report.append(f"[WARN] Canvas coverage is very high ({coverage:.2f}%). The diagram might look cluttered.")
    else:
        report.append(f"[PASS] Canvas coverage is optimal ({coverage:.2f}%).")

    # 4. Connection / Arrow Check (NEW)
    conn_issues = check_connections(drawer, tolerance=conn_tolerance)
    dup_issues = check_duplicate_edges(drawer)
    total_conn = len(conn_issues) + len(dup_issues)
    if total_conn:
        # Cap the penalty so a busy diagram isn't catastrophically punished,
        # but each issue still hurts.
        penalty = min(total_conn * 8, 40)
        score -= penalty
        report.append(
            f"[FAIL] Connection check found {len(conn_issues)} dangling/degenerate "
            f"endpoint(s) and {len(dup_issues)} duplicate edge(s). Penalty: -{penalty}"
        )
        for line in (conn_issues + dup_issues)[:12]:
            report.append(f"        - {line}")
        if total_conn > 12:
            report.append(f"        - ... and {total_conn - 12} more.")
    elif drawer.edges:
        n_checked = len(drawer.edges)
        report.append(f"[PASS] All {n_checked} connection(s) land on node borders (tol={conn_tolerance}px).")
    else:
        report.append("[INFO] No registered edges; connection check skipped.")
    # 4b. Phantom-anchor check: invisible nodes used as edge endpoints.
    phantom_issues = check_phantom_anchors(drawer)
    if phantom_issues:
        penalty = min(len(phantom_issues) * 15, 45)
        score -= penalty
        report.append(
            f"[FAIL] {len(phantom_issues)} phantom anchor(s): invisible node(s) "
            f"used as edge endpoint(s). Penalty: -{penalty}"
        )
        for line in phantom_issues[:12]:
            report.append(f"        - {line}")
    elif drawer.edges:
        report.append("[PASS] No phantom (invisible) anchor nodes.")
    # 5. Edge-through-node routing check (NEW)
    route_issues = check_edge_node_collisions(drawer)
    if route_issues:
        penalty = min(len(route_issues) * 10, 40)
        score -= penalty
        report.append(
            f"[FAIL] {len(route_issues)} edge(s) route through unrelated node "
            f"interior(s). Penalty: -{penalty}"
        )
        for line in route_issues[:12]:
            report.append(f"        - {line}")
        if len(route_issues) > 12:
            report.append(f"        - ... and {len(route_issues) - 12} more.")
    elif drawer.edges:
        report.append(f"[PASS] No edge routes through an unrelated node interior.")

    # 5b. Edge x edge crossing check
    cross_issues = check_edge_crossings(drawer)
    if cross_issues:
        penalty = min(len(cross_issues) * 8, 40)
        score -= penalty
        report.append(
            f"[FAIL] {len(cross_issues)} edge pair(s) cross. Penalty: -{penalty}"
        )
        for line in cross_issues[:12]:
            report.append(f"        - {line}")
        if len(cross_issues) > 12:
            report.append(f"        - ... and {len(cross_issues) - 12} more.")
    elif len(drawer.edges) > 1:
        report.append("[PASS] No edge crossings.")
    # 5c. Composition-quality budget (bends/stretch/gutter/text-obstacle)
    comp_fail, comp_warn = check_composition(drawer)
    if comp_fail:
        penalty = min(len(comp_fail) * 8, 24)
        score -= penalty
        report.append(f"[FAIL] {len(comp_fail)} edge(s) pass through text. Penalty: -{penalty}")
        for line in comp_fail[:8]:
            report.append(f"        - {line}")
    if comp_warn:
        penalty = min(len(comp_warn) * 2, 12)
        score -= penalty
        report.append(f"[WARN] {len(comp_warn)} composition budget violation(s). Penalty: -{penalty}")
        for line in comp_warn[:8]:
            report.append(f"        - {line}")
    if not comp_fail and not comp_warn and drawer.edges:
        report.append("[PASS] Composition budget met (bends/stretch/gutter/text-obstacle).")

    # 6. Node spacing check (NEW)
    space_issues = check_spacing(drawer)
    if space_issues:
        penalty = min(len(space_issues) * 4, 20)
        score -= penalty
        report.append(
            f"[WARN] {len(space_issues)} same-kind node pair(s) too close. Penalty: -{penalty}"
        )
        for line in space_issues[:12]:
            report.append(f"        - {line}")
    else:
        report.append("[PASS] Same-kind node spacing meets minimum gap.")
    # 6b. Alignment check (same-kind peers share a row/column edge)
    align_issues = check_alignment(drawer)
    if align_issues:
        penalty = min(len(align_issues) * 3, 15)
        score -= penalty
        report.append(
            f"[WARN] {len(align_issues)} misaligned same-kind peer pair(s). Penalty: -{penalty}"
        )
        for line in align_issues[:12]:
            report.append(f"        - {line}")
    else:
        report.append("[PASS] Same-kind peers share a row/column alignment edge.")

    # 7. Typography scale check
    font_issues = check_font_scale(drawer)
    if font_issues:
        # The count-exceed issue is the harder violation (-6); near-dup softer.
        penalty = min(len(font_issues) * 4, 8)
        score -= penalty
        tag = "FAIL" if any("distinct font sizes" in s for s in font_issues) else "WARN"
        report.append(f"[{tag}] Typography: {len(font_issues)} issue(s). Penalty: -{penalty}")
        for line in font_issues:
            report.append(f"        - {line}")
    else:
        uniq = sorted(set(_extract_font_sizes(drawer.render())))
        if uniq:
            report.append(f"[PASS] Type scale: {len(uniq)} size(s) {uniq} (<=4, well-separated).")
        else:
            report.append("[INFO] Type scale: no text in this diagram; check skipped.")

    # 8. Color palette check
    palette_issues = check_palette(drawer)
    if palette_issues:
        hard = any(("hard cap" in s) or ("no chromatic accent" in s)
                   for s in palette_issues)
        penalty = min(len(palette_issues) * 4, 8 if hard else 4)
        score -= penalty
        tag = "FAIL" if hard else "WARN"
        report.append(f"[{tag}] Palette: {len(palette_issues)} issue(s). Penalty: -{penalty}")
        for line in palette_issues:
            report.append(f"        - {line}")
    else:
        n_chroma = sum(1 for c in drawer.accent_colors if _is_chromatic(c))
        report.append(f"[PASS] Palette: {len(drawer.accent_colors)} accent color(s) "
                      f"({n_chroma} chromatic), light background, no luminance clash.")

    # 9. Color contrast (WCAG 2 text-on-fill) — replaces former manual-review placeholder
    if _re.search(r'<text\b', drawer.render()):
        c_fail, c_warn = check_contrast(drawer)
        if c_fail:
            penalty = min(len(c_fail) * 6, 18)
            score -= penalty
            report.append(f"[FAIL] {len(c_fail)} text element(s) below 3:1 contrast. Penalty: -{penalty}")
            for line in c_fail[:8]:
                report.append(f"        - {line}")
        if c_warn:
            penalty = min(len(c_warn) * 3, 12)
            score -= penalty
            report.append(f"[WARN] {len(c_warn)} text element(s) below AA (4.5:1) contrast. Penalty: -{penalty}")
            for line in c_warn[:8]:
                report.append(f"        - {line}")
        if not c_fail and not c_warn:
            report.append("[PASS] Text meets WCAG AA contrast against its fill.")
    else:
        report.append("[INFO] Color contrast: no text in this diagram; check skipped.")

    final_score = max(0, score)
    return final_score, report


def auto_refine(drawer, target_score=100, max_iter=3, conn_tolerance=12.0, verbose=False):
    """Iteratively evaluate + auto-fix common issues until target or max_iter.

    Fixes are applied via drawer.relocate_node(), which re-emits the node's
    shape XML and re-routes any connect()-built edges anchored on it — so the
    fixes actually change the rendered SVG (mutating node.x/y directly does
    not, since coordinates are baked into emitted strings at draw time). Only
    rect/circle nodes currently support relocation; other shapes return False
    and are skipped (reported, not silently ignored).

    Auto-fixable categories (programmatic; complex routing left to the caller):
      - text overflow container: cannot auto-fix raw add_element text (no handle);
        reports it instead. Only d.text()-drawn labels with known geometry can wrap.
      - gutter too small: nudge the node toward its container center.
      - too close (spacing): push the second node along the major axis by min_gap.
    Returns (final_score, report, fixes_applied) where fixes_applied is a list of
    human-readable actions taken. Non-fixable issues remain in the report.
    """
    fixes = []
    for iteration in range(max_iter):
        score, report = evaluate_svg(drawer, conn_tolerance=conn_tolerance)
        if score >= target_score:
            break
        changed = False
        for line in report:
            # gutter: "node 'X' gutter Npx < M in container" -> nudge node inward
            m = _re.search(r"\[composition\] node '([^']+)' gutter ([\-\d.]+)px < ([\d.]+) in container", line)
            if m:
                nid, gap_str, need_str = m.group(1), float(m.group(2)), float(m.group(3))
                if nid in drawer.nodes:
                    node = drawer.nodes[nid]
                    # find the container rect (smallest containing background/layer)
                    svg = drawer.render()
                    ncx, ncy = node.cx, node.cy
                    rects = []
                    for attrs in _re.findall(r'<rect ([^>]*)/>', svg):
                        p = dict(_re.findall(r'([\w-]+)="([^"]*)"', attrs))
                        try:
                            rx, ry = float(p['x']), float(p['y'])
                            rw, rh = float(p['width']), float(p['height'])
                        except (KeyError, ValueError):
                            continue
                        if p.get('data-graph-role', '') in ('background', 'layer') and rx <= ncx <= rx+rw and ry <= ncy <= ry+rh:
                            rects.append((rx, ry, rw, rh))
                    if rects:
                        c = min(rects, key=lambda r: r[2]*r[3])
                        # nudge toward container center by the deficit
                        ccx, ccy = c[0]+c[2]/2, c[1]+c[3]/2
                        dx = (ccx - ncx) * 0.3
                        dy = (ccy - ncy) * 0.3
                        if drawer.relocate_node(nid, node.x + dx, node.y + dy):
                            fixes.append(f"iter{iteration}: nudged '{nid}' by ({dx:.1f},{dy:.1f}) toward container center")
                            changed = True
                        else:
                            fixes.append(f"iter{iteration}: SKIP gutter fix for '{nid}' — non-relocatable shape (drawn in a group, or database/decision/hexagon/component/cloud)")
            # too close: "spacing ... 'A' and 'B' only Npx apart" -> push B along x
            m = _re.search(r"\[spacing\] '([^']+)' and '([^']+)' only ([\d.]+)px", line)
            if m:
                a, b, gap = m.group(1), m.group(2), float(m.group(3))
                if a in drawer.nodes and b in drawer.nodes:
                    nb = drawer.nodes[b]
                    if drawer.relocate_node(b, nb.x + 20, nb.y):  # push right by a gap increment
                        fixes.append(f"iter{iteration}: pushed '{b}' +20px to clear '{a}'")
                        changed = True
                    else:
                        fixes.append(f"iter{iteration}: SKIP spacing fix for '{b}' — non-relocatable shape (drawn in a group, or database/decision/hexagon/component/cloud)")
        if not changed:
            break
        if verbose:
            print(f"auto_refine iter {iteration}: score {score} -> retrying")
    final_score, final_report = evaluate_svg(drawer, conn_tolerance=conn_tolerance)
    return final_score, final_report, fixes


if __name__ == "__main__":
    pass
