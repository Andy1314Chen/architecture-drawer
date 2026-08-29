"""semantic_qa.py — semantic smoke-check layered on top of the geometry evaluator.

The geometric evaluator (evaluator.evaluate_svg) answers "does the picture render
correctly?" — overlaps, boundary overflow, edge endpoints landing on node borders.
It deliberately does NOT answer "does the picture mean what it should?".

This module answers the second question by parsing the *rendered SVG string* (the
same "evaluate, don't assert" philosophy) and checking semantic wiring that a
bounding-box evaluator structurally cannot see:

  1.  marker 缺省陷阱  (dangling marker references)
      connect() defaults to marker_end="arrowhead"; a generator that registers
      arrow_head("arrow", ...) but calls connect(..., marker_end="arrow") only in
      *some* places leaves other connections referencing url(#arrowhead) which is
      undefined. SVG silently renders a plain line — no arrowhead, no error. The
      geometry evaluator still sees a valid line segment, so it passes.
  2.  FIGS 尺寸漂移  (declared vs. actual figure size)
      The declared <svg width height> must actually enclose the content bbox; a
      canvas far larger than its content (or content that overflows) is a sizing
      drift the per-element boundary check won't surface holistically.
  3.  标签错位  (label / container mismatch)
      text-anchor=middle labels must sit on their containing node's horizontal
      center; every business node rect should carry a label inside it. A label
      placed inside the *wrong* box, or a node with no label, passes geometry
      checks (it is inside *some* box) yet is semantically wrong.

API
---
    run_semantic_qa(drawer_or_svg, expected_size=None) -> SemanticResult

    drawable may be an SVGDrawer (calls .render()) or a raw SVG string.
    expected_size may be (w, h) from the design spec; used for the size-drift
    check when the author knows the intended canvas dimensions.

    SemanticResult is a dataclass with: issues (list[Issue]), score (int),
    ok (bool). Use .report() to get human-readable lines mirroring evaluator's
    "[FAIL]/[WARN]" format.
"""

from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass, field
from typing import Optional

try:
    from svg_utils import BBox
except ImportError:  # allow running the module standalone for tests/debug
    class BBox:  # minimal fallback mirroring svg_utils.BBox
        def __init__(self, x, y, w, h):
            self.x, self.y, self.w, self.h = x, y, w, h

        @property
        def cx(self):
            return self.x + self.w / 2.0

        @property
        def cy(self):
            return self.y + self.h / 2.0

        def contains(self, other):
            return (self.x <= other.x <= other.x + other.w <= self.x + self.w and
                    self.y <= other.y <= other.y + other.h <= self.y + self.h)


# ---------------------------------------------------------------------------
# Issue + result containers
# ---------------------------------------------------------------------------
@dataclass
class Issue:
    severity: str            # "fail" | "warn"
    code: str                # e.g. "marker-dangling", "size-drift", "label-offcenter"
    message: str
    element: str = ""        # optional svg element snippet for debugging

    def render(self) -> str:
        tag = "[FAIL]" if self.severity == "fail" else "[WARN]"
        suffix = f"  ({self.element})" if self.element else ""
        return f"{tag} [semantic:{self.code}] {self.message}{suffix}"


@dataclass
class SemanticResult:
    issues: list = field(default_factory=list)

    @property
    def score(self) -> int:
        score = 100
        fails = sum(1 for i in self.issues if i.severity == "fail")
        warns = sum(1 for i in self.issues if i.severity == "warn")
        score -= min(fails * 15, 60)
        score -= min(warns * 3, 15)
        return max(score, 0)

    @property
    def ok(self) -> bool:
        return all(i.severity != "fail" for i in self.issues)

    @property
    def has_fail(self) -> bool:
        return any(i.severity == "fail" for i in self.issues)

    def report(self) -> list[str]:
        if not self.issues:
            return ["[PASS] semantic QA: marker refs resolve, size coherent, labels aligned."]
        return [i.render() for i in self.issues]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
import xml.etree.ElementTree as _ET

try:
    from svg_utils import (BBox, multiply_matrix, parse_transform,
                           transform_point)
except ImportError:  # standalone use without the skill on sys.path
    _I = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    def multiply_matrix(m1, m2):
        return m1 if m2 == _I else m2

    def parse_transform(value):
        return _I

    def transform_point(m, p):
        return p


def _local(tag):
    """Strip an eventual {namespace} prefix from an ElementTree tag."""
    return tag.rsplit('}', 1)[-1]


def _f(v, default=None):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _text_width(content: str, font_size: float, bold: bool) -> float:
    """Rough rendered width estimate consistent with the evaluator's metric."""
    visible = re.sub(r'<[^>]+>', '', html.unescape(content))
    coef = 0.62 if bold else 0.55
    return sum(font_size * (1.0 if ord(ch) > 0x2E80 else coef) for ch in visible)


def _abs_bbox(local_bbox, m):
    """Map a local-space BBox to absolute canvas coords under matrix m."""
    x, y, w, h = local_bbox
    if m == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0):
        return BBox(x, y, w, h)
    pts = [transform_point(m, p) for p in
           ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


_NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')
_PATH_TOKEN_RE = re.compile(r'[MmLlHhVvCcSsQqTtAaZz]|-?\d+(?:\.\d+)?')
# per-command argument counts (endpoint coords are the last pair of each)
_PATH_ARITY = {"M": 2, "m": 2, "L": 2, "l": 2, "T": 2, "t": 2,
               "H": 1, "h": 1, "V": 1, "v": 1,
               "C": 6, "c": 6, "S": 4, "s": 4, "Q": 4, "q": 4,
               "A": 7, "a": 7, "Z": 0, "z": 0}


def _path_points(d):
    """Approximate a path's geometry by tracking an absolute cursor.

    Raw-number-soup bboxes corrupt on arcs (rx/ry/flags leak into the x/y
    pairing — a database cylinder's `A 130,6.96 0 0 1 260,6.96` would grow
    the bbox to 260x260). Walking commands with a cursor and recording the
    endpoint after each gives an honest envelope; control points are ignored,
    which is fine for label-host selection.
    """
    tokens = _PATH_TOKEN_RE.findall(d)
    pts = []
    x = y = 0.0
    cmd, args = None, []

    def _apply(tok, vals):
        nonlocal x, y
        n = _PATH_ARITY.get(tok, 0)
        if n == 0 or not vals:
            return
        # SVG allows implicit coordinate repeats ("L 10,10 20,20") — the
        # number run exceeds the command arity; apply in arity-sized chunks.
        if len(vals) < n:
            vals = vals + [0.0] * (n - len(vals))
        for i in range(0, len(vals) - n + 1, n):
            chunk = vals[i:i + n]
            # curve control points bound the curve's convex hull — include
            # them in the envelope (a Q's apex lives in its control point;
            # endpoints alone can collapse a dome path to zero height)
            if tok in ("C", "S", "Q", "c", "s", "q"):
                for j in range(0, len(chunk) - 1, 2):
                    pts.append((chunk[j], chunk[j + 1]))
            if tok in ("M", "L", "T", "C", "S", "Q", "A"):
                x, y = chunk[-2], chunk[-1]
            elif tok in ("m", "l", "t", "c", "s", "q", "a"):
                x, y = x + chunk[-2], y + chunk[-1]
            elif tok == "H":
                x = chunk[-1]
            elif tok == "h":
                x += chunk[-1]
            elif tok == "V":
                y = chunk[-1]
            elif tok == "v":
                y += chunk[-1]
            else:
                continue
            pts.append((x, y))

    for tok in tokens:
        if tok in _PATH_ARITY:
            if cmd is not None:
                _apply(cmd, [float(v) for v in args])
            cmd, args = tok, []
        else:
            args.append(tok)
    if cmd is not None:
        _apply(cmd, [float(v) for v in args])
    return pts


def _shape_bbox(tag, a):
    """Local bbox for a shape element, or None. Covers every node shape the
    DSL emits: rect, polygon (decision/hexagon/component), circle, ellipse,
    and filled paths (database/cloud)."""
    if tag == "rect":
        x, y = _f(a.get("x")), _f(a.get("y"))
        w, h = _f(a.get("width")), _f(a.get("height"))
        if None in (x, y, w, h):
            return None
        return (x, y, max(w, 0.0), max(h, 0.0))
    if tag == "circle":
        cx, cy, r = _f(a.get("cx")), _f(a.get("cy")), _f(a.get("r"))
        if None in (cx, cy, r):
            return None
        return (cx - r, cy - r, 2 * r, 2 * r)
    if tag == "ellipse":
        cx, cy = _f(a.get("cx")), _f(a.get("cy"))
        rx, ry = _f(a.get("rx")), _f(a.get("ry"))
        if None in (cx, cy, rx, ry):
            return None
        return (cx - rx, cy - ry, 2 * rx, 2 * ry)
    if tag == "polygon":
        nums = [float(v) for v in _NUM_RE.findall(a.get("points", ""))]
        if len(nums) < 4:
            return None
        xs, ys = nums[0::2], nums[1::2]
        x0, y0 = min(xs), min(ys)
        return (x0, y0, max(xs) - x0, max(ys) - y0)
    if tag == "path":
        # Filled paths are node candidates (database/cloud bodies). A stroke-
        # only path is normally an edge — EXCEPT when the stroke is a thick
        # band (>= 8px): a 15px "pool" arc drawn as a fat stroke is visually
        # a shape that owns its centered label, not a connector.
        fill = a.get("fill") or "none"
        sw = _f(a.get("stroke-width"), 1.0) or 1.0
        if fill in ("none",) and sw < 8.0:
            return None
        pts = _path_points(a.get("d", ""))
        if len(pts) < 2:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, y0 = min(xs), min(ys)
        return (x0, y0, max(xs) - x0, max(ys) - y0)
    return None


def _walk(el, m, out):
    """Depth-first walk applying group transforms, filling the out dict.

    Recurses into ANY element with children (<g>, <defs>, <a>, ...) so nested
    markers and grouped shapes are all seen. <marker> returns early so its
    inner <polygon> (the arrowhead glyph) is never counted as a node box.
    """
    tag = _local(el.tag)
    a = el.attrib
    if tag == "marker":
        if a.get("id"):
            out["markers"].add(a["id"])
        return
    # marker refs live on any drawn element (line/path/polyline/...);
    # pair each ref with its own element bbox so the report can point at the
    # offending connector's location.
    ref = a.get("marker-end") or a.get("marker-start") or a.get("marker-mid")
    if ref:
        lb = _shape_bbox(tag, a)
        if tag == "line":
            x1, y1, x2, y2 = (_f(a.get(k)) for k in ("x1", "y1", "x2", "y2"))
            if None not in (x1, y1, x2, y2):
                p1, p2 = transform_point(m, (x1, y1)), transform_point(m, (x2, y2))
                lb = (min(p1[0], p2[0]), min(p1[1], p2[1]),
                      abs(p2[0] - p1[0]) or 1, abs(p2[1] - p1[1]) or 1)
        # stroke-only paths are excluded from _shape_bbox; still give the
        # report a rough location from the raw d numbers.
        if lb is None:
            pts = _path_points(a.get("d", ""))
            if len(pts) >= 2:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                lb = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            else:
                nums = [float(v) for v in _NUM_RE.findall(
                    a.get("d", "") + " " + a.get("points", ""))]
                if len(nums) >= 4:
                    xs, ys = nums[0::2], nums[1::2]
                    lb = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
        out["line_refs"].append(
            (ref, _abs_bbox(lb, m) if lb else BBox(0, 0, 1, 1)))
    if tag in ("rect", "polygon", "circle", "ellipse", "path"):
        role = a.get("data-graph-role", "")
        lb = _shape_bbox(tag, a)
        if lb is None:
            # stroked paths (edges/curves) contribute their polyline to the
            # segment inventory so near-edge label annotations are recognized
            if tag == "path" and a.get("d"):
                lpts = _path_points(a.get("d", ""))
                if len(lpts) >= 2:
                    abspts = [transform_point(m, p) for p in lpts]
                    prole = a.get("data-graph-role", "")
                    psw = _f(a.get("stroke-width"), 1.0)
                    out["segments"].extend(
                        (a_, b_, prole, psw)
                        for a_, b_ in zip(abspts, abspts[1:]))
                    # whole-edge spec (first->last point) for flow checks:
                    # an orthogonal/curved edge must count as ONE edge, not
                    # per-sub-segment (sub-segment attribution loses L-edges
                    # whose middle jog lands between bands).
                    if a.get("fill", "none") in (None, "", "none"):
                        out["edge_specs"].append((abspts[0], abspts[-1], prole))
            return
        # full-canvas / background-role shapes are never node hosts
        if role == "background":
            return
        if tag == "rect" and lb[0] <= 0.5 and lb[1] <= 0.5 \
                and lb[2] >= out["canvas"][0] - 0.5 and lb[3] >= out["canvas"][1] - 0.5:
            return
        if tag == "path" and role in ("edge",):
            return
        out["rects"].append(_abs_bbox(lb, m))
        out["rect_roles"].append(role)
        # identity + paint for the design-brief contract check (A/B/C)
        out["rect_ids"].append(a.get("data-node-id", ""))
        out["rect_paints"].append((a.get("fill", ""), a.get("stroke", "")))
        if tag == "circle":
            out["circles"].append(_abs_bbox(lb, m))
    elif tag == "text":
        x, y = _f(a.get("x")), _f(a.get("y"))
        if x is None or y is None:
            return
        px, py = transform_point(m, (x, y))
        content = "".join(el.itertext())
        fs = _f(a.get("font-size"), 12.0)
        bold = "bold" in a.get("font-weight", "")
        anchor = a.get("text-anchor", "start")
        w = _text_width(content, fs, bold)
        bx = px - w / 2 if anchor == "middle" else (px - w if anchor == "end" else px)
        out["texts"].append((BBox(bx, py - fs / 2, w, fs), anchor,
                              content.strip(), fs, px, py))
    elif tag == "line":
        x1, y1, x2, y2 = (_f(a.get(k)) for k in ("x1", "y1", "x2", "y2"))
        if None not in (x1, y1, x2, y2):
            p1, p2 = transform_point(m, (x1, y1)), transform_point(m, (x2, y2))
            out["segments"].append((p1, p2, a.get("data-graph-role", ""),
                                     _f(a.get("stroke-width"), 1.0)))
            out["edge_specs"].append((p1, p2, a.get("data-graph-role", "")))
    # recurse into any remaining container (g/defs/a/switch/...)
    if len(el):
        t = a.get("transform")
        child_m = multiply_matrix(m, parse_transform(t)) if t else m
        for child in el:
            _walk(child, child_m, out)


def _collect(svg: str):
    """Parse the rendered SVG into semantic structures (absolute coords).

    Returns a dict: markers / rects / circles / segments / line_refs / texts /
    canvas / rect_ids / rect_paints / edge_specs. rects covers every
    node-shape kind (rect / polygon / circle / ellipse / filled path) with
    group transforms applied — decision diamonds and cloud/database paths are
    label hosts exactly like rects; circles are ALSO listed separately
    (junction dots legitimately carry adjacent labels). segments holds
    absolute line endpoints for the edge-annotation exemption. rect_ids /
    rect_paints align 1:1 with rects (data-node-id + raw fill/stroke) for the
    design-brief contract check; edge_specs holds whole edges (first->last
    point) so orthogonal/curved connectors count as ONE edge in flow checks.
    """
    empty = {"markers": set(), "rects": [], "rect_roles": [], "circles": [],
             "segments": [], "line_refs": [], "texts": [],
             "rect_ids": [], "rect_paints": [], "edge_specs": [],
             "canvas": (0.0, 0.0)}
    try:
        root = _ET.fromstring(svg)
    except _ET.ParseError:
        return empty
    out = dict(empty)
    w = _f(root.get("width"))
    h = _f(root.get("height"))
    if w and h:
        out["canvas"] = (float(w), float(h))
    identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for child in root:
        _walk(child, identity, out)
    return out


def _dedup_rects(rects, rect_roles=None, eps=0.5, aligned=None):
    """Collapse rects that describe the *same* box (identical geometry) so a
    card + its own text-frame aren't double-counted. rect_roles and any
    aligned list given in ``aligned`` (name -> list, 1:1 with rects, e.g.
    rect_ids / rect_paints) are filtered in lockstep so indices stay
    aligned."""
    out, out_roles, out_aligned = [], [], {k: [] for k in (aligned or {})}
    order = sorted(range(len(rects)),
                   key=lambda i: (rects[i].w * rects[i].h, rects[i].x, rects[i].y),
                   reverse=True)
    for orig in order:
        b = rects[orig]
        dup = any(
            abs(b.x - o.x) < eps and abs(b.y - o.y) < eps
            and abs(b.w - o.w) < eps and abs(b.h - o.h) < eps
            for o in out
        )
        if not dup:
            out.append(b)
            if rect_roles is not None:
                out_roles.append(rect_roles[orig] if orig < len(rect_roles) else "")
            for k, seq in (aligned or {}).items():
                out_aligned[k].append(seq[orig] if orig < len(seq) else None)
    if aligned is not None:
        return out, out_roles, out_aligned
    if rect_roles is not None:
        return out, out_roles
    return out


# ---------------------------------------------------------------------------
# Check 1 — marker 缺省陷阱
# ---------------------------------------------------------------------------
def _ref_id(ref: Optional[str]) -> Optional[str]:
    if not ref:
        return None
    m = re.match(r'url\(#([^)]+)\)', ref)
    return m.group(1) if m else None


def check_marker_refs(markers, line_refs, errs):
    """Every marker-end/start/mid URL must resolve to a defined <marker id>.

    This is the marker 缺省陷阱: connect() defaults to marker_end='arrowhead'
    while authors register arrow_head('arrow', ...). The mismatched reference
    silently drops every arrowhead — the line renders, geometry passes, but
    the diagram shows no direction at all.
    """
    for ref, bbox in line_refs:
        rid = _ref_id(ref)
        if rid is None or rid in markers:
            continue
        cx, cy = bbox.cx, bbox.cy
        defined = sorted(markers) if markers else ["(none)"]
        errs.append(Issue(
            "fail", "marker-dangling",
            f"connector near ({cx:.0f},{cy:.0f}) references undefined marker "
            f"'#{rid}' — its arrowhead will silently not render. Defined "
            f"markers: {defined}. connect() defaults to marker_end='arrowhead'; "
            f"if you registered arrow_head('arrow', ...), pass "
            f"marker_end='arrow' explicitly on every connect() call.",
            element=f"marker-end='{ref}'",
        ))
    # Reverse direction: a marker that is defined but never referenced usually
    # means the author registered an arrowhead and then forgot to use it.
    # With zero refs at all it is even worse — every arrow may be lost — but a
    # single-marker edgeless figure is legitimate, so require either some
    # usage or more than one defined marker.
    if markers:
        used = {_ref_id(ref) for ref, _ in line_refs}
        unused = markers - used
        if unused and (line_refs or len(markers) > 1):
            errs.append(Issue(
                "warn", "marker-unused",
                f"marker(s) {sorted(unused)} defined but never referenced — "
                f"did some connect() forget marker_end=?",
            ))


# ---------------------------------------------------------------------------
# Check 2 — FIGS 尺寸漂移
# ---------------------------------------------------------------------------
def check_figure_size(canvas, rects, texts, expected_size, errs):
    """Declared canvas size vs. actual content bbox.

    - content bigger than canvas → overflow (fail).
    - content far smaller than canvas → size drift: the diagram is a small island
      in a huge canvas (warn).
    - expected_size (from the design spec) mismatching the declared canvas →
      declared-size drift (warn).
    """
    cw, ch = canvas
    if not cw or not ch:
        errs.append(Issue("fail", "size-unknown", "could not read <svg width height>."))
        return

    all_boxes = rects + [t[0] for t in texts]
    content = None
    for b in all_boxes:
        if content is None:
            content = BBox(b.x, b.y, b.w, b.h)
        else:
            x0, y0 = min(content.x, b.x), min(content.y, b.y)
            x1 = max(content.x + content.w, b.x + b.w)
            y1 = max(content.y + content.h, b.y + b.h)
            content = BBox(x0, y0, x1 - x0, y1 - y0)
    if content is None:
        errs.append(Issue("warn", "size-empty", "no drawable content found."))
        return

    # (a) overflow
    pad = 2.0
    if (content.x < 0 or content.y < 0 or
            content.x + content.w > cw + pad or content.y + content.h > ch + pad):
        errs.append(Issue(
            "fail", "size-overflow",
            f"content bbox ({content.x:.0f},{content.y:.0f} "
            f"{content.w:.0f}x{content.h:.0f}) exceeds declared canvas "
            f"{cw:.0f}x{ch:.0f}.",
        ))

    # (b) drift — content too small relative to canvas
    area_ratio = (content.w * content.h) / (cw * ch)
    if area_ratio < 0.12:
        errs.append(Issue(
            "warn", "size-drift",
            f"content occupies only {area_ratio * 100:.1f}% of the {cw:.0f}x{ch:.0f} "
            f"canvas (content {content.w:.0f}x{content.h:.0f}); diagram may be "
            f"mis-sized or misplaced.",
        ))

    # (c) declared size vs. design spec
    if expected_size:
        ew, eh = expected_size
        if abs(ew - cw) > 1 or abs(eh - ch) > 1:
            errs.append(Issue(
                "warn", "size-declared-vs-spec",
                f"declared canvas {cw:.0f}x{ch:.0f} differs from design-spec "
                f"expected {ew:.0f}x{eh:.0f}.",
            ))


def _point_rect_dist(px, py, rb):
    """Distance from a point to the nearest edge of a rect (0 when inside)."""
    dx = max(rb.x - px, 0.0, px - (rb.x + rb.w))
    dy = max(rb.y - py, 0.0, py - (rb.y + rb.h))
    return math.hypot(dx, dy)


# ---------------------------------------------------------------------------
# Check 3 — 标签错位
# ---------------------------------------------------------------------------
def _point_seg_dist(px, py, seg):
    """Distance from a point to a line segment ((x1,y1),(x2,y2))."""
    (x1, y1), (x2, y2) = seg
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def check_labels(canvas_h, rects, circles, segments, texts, errs):
    """Label / container association.

    - every text-anchor=middle label must sit centered over *its* containing
      node box — but only when the box plausibly owns the text (box width
      within 4x the estimated text width). A lane/band caption inside a wide
      container is intentionally off-center and must not be flagged.
    - every business-node rect (area above a floor) should contain at least
      one text label; circles are exempt (junction dots / start-end nodes
      legitimately carry adjacent labels).
    We deliberately do NOT flag (a) top-band centered titles/subtitles (they
    are meant to float above the grid), (b) tiny decorative squares, and
    (c) labels sitting beside an edge segment (flowchart branch labels like
    "No", bidirectional link annotations).
    """
    title_band = 0.13 * canvas_h     # top stripe reserved for the diagram title
    node_floor = 60 * 40              # min node box area to count as a business node
    circle_set = {(c.x, c.y, c.w, c.h) for c in circles}
    occupied = [False] * len(rects)

    for (tb, anchor, content, fs, tx, ty) in texts:
        if not content:
            continue
        if anchor != "middle":
            continue  # left labels are naturally caption-style
        # top-band centered titles/subtitles are expected to float — not orphans
        if ty < title_band and anchor == "middle":
            continue
        # candidate containers whose center the label should match.
        # Any size qualifies (a 52x30 KV-block chip owns its "L0" label as
        # much as a 360x124 card owns its title); the smallest containing box
        # wins. Two ownership guards keep false hosts out:
        #   - the box must hold at least half the estimated text box;
        #   - the box must not be wider than 4x the text (a 43px lane caption
        #     inside a 500px band is a band caption, not the band's title).
        cx, cy = tb.cx, tb.cy
        candidates = [
            (i, rb) for i, rb in enumerate(rects)
            if rb.w >= 0.5 * tb.w and rb.h >= 0.5 * tb.h
            and rb.w <= 4.0 * max(tb.w, 1.0)
            and rb.x <= cx <= rb.x + rb.w and rb.y - fs <= cy <= rb.y + rb.h + fs
        ]
        best = (min(candidates, key=lambda p: p[1].w * p[1].h)
                if candidates else None)
        if best is not None:
            # composite shapes: a label centered over the UNION of overlapping
            # candidates (e.g. two half-arcs forming one bracket) is centered,
            # even though it is off the single smallest candidate's centre.
            if len(candidates) >= 2:
                ux0 = min(rb.x for _, rb in candidates)
                ux1 = max(rb.x + rb.w for _, rb in candidates)
                if abs((ux0 + ux1) / 2 - cx) <= 6.0:
                    for i, _rb in candidates:
                        occupied[i] = True
                    candidates = []
                    best = None
                    continue
        if best is None:
            # centered label floating in empty space. Three legitimate
            # patterns are exempt:
            #   - near a box (~24px: icon-chip labels);
            #   - beside an edge segment (~24px: branch labels like "No",
            #     mid-link annotations between a paired up/down link);
            #   - a cluster caption: >=2 node boxes directly below (or above)
            #     within 90px and within a ±120px horizontal window — the
            #     "constellation title over its satellites" pattern.
            near_box = any(_point_rect_dist(cx, cy, rb) <= 24.0 for rb in rects)
            near_edge = any(_point_seg_dist(cx, cy, (s[0], s[1])) <= 24.0
                           for s in segments)
            cluster_below = sum(
                1 for rb in rects
                if abs(rb.cx - cx) <= 120.0 and 0 <= (rb.y - cy) <= 90.0)
            cluster_above = sum(
                1 for rb in rects
                if abs(rb.cx - cx) <= 120.0 and 0 <= (cy - (rb.y + rb.h)) <= 90.0)
            if near_box or near_edge or cluster_below >= 2 or cluster_above >= 2:
                continue
            errs.append(Issue(
                "warn", "label-orphan",
                f"middle-anchored label '{content[:20]}' at ({tx:.0f},{ty:.0f}) is "
                f"not inside (nor near) any node box.",
            ))
            continue
        i, rb = best
        occupied[i] = True
        # horizontal centering within that box
        center_dx = abs(rb.cx - cx)
        tol_center = max(6.0, 0.05 * rb.w)
        if center_dx > tol_center:
            errs.append(Issue(
                "warn", "label-offcenter",
                f"label '{content[:20]}' center x-offset {center_dx:.1f}px from its "
                f"box center ({rb.cx:.0f}); text-anchor=middle wants centering.",
            ))

    # --- unlabelled business nodes --------------------------------
    # A box only *needs* an interior label when the diagram labels its boxes
    # from the inside (the common convention). If every label in the figure sits
    # adjacent/outside (chip-style legends, side captions), boxes without an
    # interior label are legitimate layout, not a defect.
    tol = 10.0  # allow slight label overflow outside a box

    def _inside(rb, t):
        return (rb.x - tol <= t[0].cx <= rb.x + rb.w + tol and
                rb.y - tol <= t[0].cy <= rb.y + rb.h + tol)

    interior_convention = any(
        any(_inside(rb, t) for t in texts) for rb in rects
    )
    for i, rb in enumerate(rects):
        if occupied[i] or rb.w * rb.h < node_floor:
            continue
        # circles (junction dots / start-end nodes) legitimately carry
        # adjacent labels instead of interior ones
        if (rb.x, rb.y, rb.w, rb.h) in circle_set:
            continue
        if not (interior_convention and not any(_inside(rb, t) for t in texts)):
            continue
        errs.append(Issue(
            "warn", "label-missing",
            f"node box at ({rb.x:.0f},{rb.y:.0f} {rb.w:.0f}x{rb.h:.0f}) "
            f"contains no text label.",
        ))


# ---------------------------------------------------------------------------
# Check 4 — connector route vs filled shapes（箭头线盖在组件上）
# ---------------------------------------------------------------------------
def _interior_samples(p1, p2, rect, margin=3.0, endpoint_skip=0.0, steps=60):
    """Sampled points of segment p1→p2 strictly inside rect (with margin).

    endpoint_skip drops samples within that many px of either endpoint — a
    connector legitimately touching a shape's border at its anchor should not
    count as passing through the interior.
    """
    seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    inside = []
    for i in range(steps + 1):
        t = i / steps
        px, py = p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t
        if endpoint_skip:
            if math.hypot(px - p1[0], py - p1[1]) < endpoint_skip:
                continue
            if math.hypot(px - p2[0], py - p2[1]) < endpoint_skip:
                continue
        if rect.x + margin < px < rect.x + rect.w - margin \
                and rect.y + margin < py < rect.y + rect.h - margin:
            inside.append((px, py))
    return inside, seg_len


def check_connector_routes(rects, rect_roles, circles, segments, errs,
                           card_min_w=40.0, card_max_w=320.0, card_min_h=24.0,
                           card_max_h=180.0,
                           container_min_w=400.0, container_min_area=40000.0,
                           anchor_tol=14.0, min_rail_len=60.0):
    """Raw-SVG route check: connectors vs filled shapes, role-aware.

    The registry-based evaluator cannot see this defect class: bus rails are
    drawn as raw line() calls (never registered as edges), and band containers
    are role='layer' (never registered as nodes) — so "edge routes through
    node" is structurally blind to a spine slicing through colored bands.
    This check parses the rendered geometry instead:

    - connector-through-card (FAIL): a segment crosses a business card's
      interior (cards = unmarked shapes 40–320px wide; anything wider is a
      container — arrows legitimately live inside white layer containers).
    - rail-slices-container (WARN): a >=60px connector whose NEITHER endpoint
      is anchored to any card/circle crosses a wide filled band/container
      interior for >=24px — the classic "right-side AgentEvent spine drawn
      at x=776 inside the band rect (right edge 790) instead of outside it",
      painting over the component bands it was meant to route around.
    Legend/decoration shapes are exempt on both sides.
    """
    skip_roles = ("legend", "decoration", "background")
    cards = [r for r, role in zip(rects, rect_roles)
             if role not in skip_roles
             and card_min_w <= r.w <= card_max_w and card_min_h <= r.h <= card_max_h]
    containers = [r for r, role in zip(rects, rect_roles)
                  if role not in skip_roles
                  and r.w >= container_min_w and r.w * r.h >= container_min_area]
    # Anchoring recognizes business shapes that are NOT wide containers — an
    # edge landing on a wide card's border is anchored, but a rail endpoint
    # merely floating inside a big band's interior (or a wide strip) is not.
    anchors = [r for r, role in zip(rects, rect_roles)
               if role not in skip_roles and r.w < container_min_w] \
        + list(circles)

    def anchored(p):
        return any(_point_rect_dist(p[0], p[1], c) <= anchor_tol for c in anchors)

    warned = 0
    for seg in segments:
        p1, p2 = seg[0], seg[1]
        role = seg[2] if len(seg) > 2 else ""
        sw = seg[3] if len(seg) > 3 else 1.0
        if role in skip_roles or sw <= 1.0:
            continue  # legend/decoration lines and hairline dividers are not rails
        # (a) through a business card interior → FAIL
        for c in cards:
            inside, _ = _interior_samples(p1, p2, c,
                                          margin=3.0, endpoint_skip=10.0)
            if len(inside) >= 8:
                errs.append(Issue(
                    "fail", "connector-through-card",
                    f"connector ({p1[0]:.0f},{p1[1]:.0f})->({p2[0]:.0f},{p2[1]:.0f}) "
                    f"runs through the interior of card "
                    f"({c.x:.0f},{c.y:.0f} {c.w:.0f}x{c.h:.0f}) — reroute it "
                    f"around the card or anchor it on the card border.",
                ))
                break
        # (b) floating rail slicing a filled band/container → WARN
        if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 30.0:
            continue
        if anchored(p1) or anchored(p2):
            continue
        slicing = []
        for c in containers:
            inside, seg_len = _interior_samples(p1, p2, c, margin=3.0)
            # crossing DEPTH in px (sample fraction × length) — count-based
            # thresholds dilute for long rails (a 616px spine spends ~110px
            # per band but only ~12 raw samples of 61).
            if seg_len <= 0 or len(inside) / 61.0 * seg_len < 24.0:
                continue
            # only a pass-through / edge-entry counts: at least one endpoint
            # must lie OUTSIDE the container — a rail that lives wholly inside
            # one band (legend arrows between chips) is that band's business.
            outside = [
                not (c.x + 3.0 < pt[0] < c.x + c.w - 3.0
                     and c.y + 3.0 < pt[1] < c.y + c.h - 3.0)
                for pt in (p1, p2)
            ]
            if not any(outside):
                continue
            slicing.append(c)
        if slicing and warned < 6:
            warned += 1
            names = ", ".join(f"({c.x:.0f},{c.y:.0f} {c.w:.0f}x{c.h:.0f})"
                            for c in slicing[:3])
            errs.append(Issue(
                "warn", "rail-slices-container",
                f"connector ({p1[0]:.0f},{p1[1]:.0f})->({p2[0]:.0f},{p2[1]:.0f}) "
                f"with no node-anchored endpoint slices through filled "
                f"container(s) {names} — move the rail outside the containers "
                f"(or register it as a business edge). (箭头线盖在组件上)",
            ))


# ---------------------------------------------------------------------------
# Check 5 — text semantics vs the spec（文本语义）
# ---------------------------------------------------------------------------
_DESIGN_STOPWORDS = frozenset(
    "w left right top bottom up down solid dashed arrow arrows spine band layer"
    " layers title subtitle legend canvas fill stroke px width height exact hex"
    " accents tier tiers bold italic box line lines row rows col cols".split())


def _norm_entity(s):
    """Normalize a spec term for matching: keep alnum + CJK, lowercase."""
    return "".join(ch.lower() for ch in s
                   if ch.isalnum() or ord(ch) > 0x2E80)


def _spec_entities(spec_text):
    """Extract component-name entities from a spec's **bold** / `backtick`
    spans. Long phrases are split on separators; hex colors, pure numbers and
    design vocabulary are dropped — they describe style, not diagram text."""
    ents = set()
    spans = re.findall(r"\*\*([^*]+)\*\*", spec_text or "")
    spans += re.findall(r"`([^`]+)`", spec_text or "")
    for span in spans:
        for term in re.split(r"[（(·—/:;、,，。\|\s]+|\s+to\s+", span):
            t = term.strip()
            n = _norm_entity(t)
            if not n:
                continue
            if re.fullmatch(r"[0-9a-f]{6}|[0-9a-f]{3}|\d+", n):
                continue
            # design directives, not component names
            if n[0].isdigit() or "=" in t:
                continue
            has_cjk = any(ord(c) > 0x2E80 for c in t)
            if not has_cjk:
                # ASCII entities must LOOK like identifiers (camelCase,
                # ALLCAPS, or hyphen/underscore-joined) — plain words and
                # bolded design sentences ("All edges are solid") drop out
                camel = re.search(r"[a-z][A-Z]", t)
                caps = re.fullmatch(r"[A-Z][A-Za-z]*[A-Z]|[A-Z]{2,}", t)
                joined = re.search(r"[A-Za-z0-9][-_][A-Za-z0-9]", t) and len(n) >= 4
                if not (camel or caps or joined):
                    continue
            if len(n) < (2 if has_cjk else 3):
                continue
            if n in _DESIGN_STOPWORDS:
                continue
            ents.add(n)
    return ents


def check_text_semantics(texts, spec_text, errs, min_coverage=0.4, warn_coverage=0.85):
    """Text-level semantic checks (content, not geometry).

    - placeholder/garbled text (TODO/TBD/mojibake/empty) → FAIL
    - spec entities missing from the diagram: coverage below min_coverage →
      FAIL (forces regeneration or text correction); individual misses above
      the floor are tolerated (synonym rewording like 事件序列 vs 事件流).
    """
    for (tb, anchor, content, fs, tx, ty) in texts:
        if not content:
            errs.append(Issue(
                "fail", "text-empty",
                f"empty <text> element at ({tx:.0f},{ty:.0f})."))
            continue
        if re.search(r"\bTODO\b|\bTBD\b|\bFIXME\b|\bXXX+\b|lorem ipsum"
                    r"|\bundefined\b|\bNaN\b", content) \
                or re.search(r"Ã|â€", content):
            errs.append(Issue(
                "fail", "text-placeholder",
                f"placeholder/garbled text '{content[:24]}' at ({tx:.0f},{ty:.0f})."))
    if not spec_text:
        return
    ents = _spec_entities(spec_text)
    if not ents:
        return
    blob = _norm_entity(" ".join(t[2] for t in texts))
    missing = [e for e in sorted(ents) if e not in blob]
    coverage = 1.0 - len(missing) / len(ents)
    if coverage < min_coverage:
        errs.append(Issue(
            "fail", "spec-entities-missing",
            f"only {coverage * 100:.0f}% of the spec's component names appear in "
            f"the diagram (< {min_coverage * 100:.0f}%) — whole components may "
            f"be missing. Missing: {', '.join(missing[:10])}",
        ))
    elif coverage < warn_coverage:
        errs.append(Issue(
            "warn", "spec-entities-partial",
            f"{coverage * 100:.0f}% of the spec's component names appear in the "
            f"diagram — consider adding: {', '.join(missing[:8])}",
        ))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_semantic_qa(drawable, expected_size: Optional[tuple] = None,
                   spec_text: Optional[str] = None) -> SemanticResult:
    """Analyze a drawer (.render()) or a raw SVG string.

    spec_text: the original requirement text (e.g. input.md). When given,
    text-semantics checks entity coverage of the diagram against the spec.
    """
    svg = drawable.render() if hasattr(drawable, "render") else str(drawable)
    doc = _collect(svg)
    rects, rect_roles = _dedup_rects(doc["rects"], doc.get("rect_roles"), eps=0.75)
    errs = []
    check_marker_refs(doc["markers"], doc["line_refs"], errs)
    cw, ch = doc["canvas"]
    check_figure_size((cw, ch), rects, doc["texts"], expected_size, errs)
    check_labels(ch, rects, doc["circles"], doc["segments"], doc["texts"], errs)
    check_connector_routes(rects, rect_roles, doc["circles"], doc["segments"], errs)
    check_text_semantics(doc["texts"], spec_text, errs)
    return SemanticResult(issues=errs)


def semantic_qa(drawable, expected_size=None, spec_text=None):
    """Alias matching the evaluator's public-function style."""
    return run_semantic_qa(drawable, expected_size, spec_text)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            svg = fh.read()
        res = run_semantic_qa(svg)
        print("\n".join(res.report()))
        print(f"semantic-qa score: {res.score}  ok={res.ok}")
    else:
        print("usage: python semantic_qa.py <diagram.svg> [expected_w expected_h]")