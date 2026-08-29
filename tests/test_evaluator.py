"""Evaluator palette-floor tests — the 无配色 (colorless-diagram) defect class.

Observed in the wild (2026-08-29 coarse-spec agent-replay pilot): an agent
"fixed" its text-contrast WARN by de-coloring the whole diagram — the final
100-score output carried only desaturated slate tones (#546E7A / #37474F /
#78909C), which pass the R==G==B neutral filter yet read as colorless. The
palette cap is meaningless without a floor, so ``check_palette`` now FAILs any
business diagram whose accents carry no readable hue (HSL saturation < 0.25).
"""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / (
    "plugins/architecture-drawer/skills/architecture-drawer/scripts")
sys.path.insert(0, str(SCRIPTS))

from svg_utils import SVGDrawer                    # noqa: E402
from evaluator import check_palette, _is_chromatic  # noqa: E402


def _wrap(svg_body, w=600, h=400):
    class D:
        pass
    d = D()
    d._s = svg_body
    d.width, d.height = w, h
    d.render = lambda: svg_body
    return d


def test_chromatic_classification():
    """Slate pseudo-accents are achromatic; pastel tints are chromatic."""
    assert not _is_chromatic("#546e7a")   # slate, S≈0.18 — the pilot's only "colors"
    assert not _is_chromatic("#37474f")
    assert not _is_chromatic("#999999")   # pure gray
    assert _is_chromatic("#dae8fc")       # pastel blue tint, S≈0.85
    assert _is_chromatic("#d47130")       # saturated orange
    assert _is_chromatic("#1b3a5c")       # dark navy accent


def test_decolored_diagram_fails_the_floor():
    """The exact pilot regression: slate-only 'accents' → no-chromatic FAIL."""
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="200" height="80" fill="#ffffff" '
           'stroke="#546e7a" stroke-width="2"/>'
           '<rect x="50" y="200" width="500" height="60" fill="#546e7a" '
           'stroke="#37474f" stroke-width="1"/>'
           '<rect x="300" y="50" width="200" height="80" fill="#f5f5f5" '
           'stroke="#78909c" stroke-width="1"/></svg>')
    issues = check_palette(_wrap(svg))
    assert any("no chromatic accent" in s for s in issues)


def test_neutral_only_diagram_fails_the_floor():
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="200" height="80" fill="#ffffff" '
           'stroke="#999999" stroke-width="1"/>'
           '<rect x="300" y="50" width="200" height="80" fill="#eeeeee" '
           'stroke="#cccccc" stroke-width="1"/></svg>')
    issues = check_palette(_wrap(svg))
    assert any("no chromatic accent" in s for s in issues)


def test_tinted_diagram_passes_the_floor():
    """Golden-style layering — light tint fills + dark accent stroke — is the
    sanctioned way to carry color (and the documented contrast fix)."""
    svg = ('<svg width="600" height="400">'
           '<rect x="0" y="0" width="600" height="400" fill="#ffffff"/>'
           '<rect x="50" y="50" width="500" height="120" fill="#dae8fc" '
           'stroke="#1b3a5c" stroke-width="1.5"/>'
           '<rect x="50" y="220" width="500" height="120" fill="#d5e1eb" '
           'stroke="#1b3a5c" stroke-width="1.5"/></svg>')
    issues = check_palette(_wrap(svg))
    assert not any("no chromatic accent" in s for s in issues)


def test_gray_dominant_structure_fails():
    """The agent_infra replay defect: color present but marginal — neutral
    bands/cards everywhere, chromatic color confined to two small chips.
    Low on BOTH axes (elements AND area) -> FAIL."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(6):  # the gray skeleton
        parts.append(f'<rect x="50" y="{40 + i * 140}" width="1000" height="100" '
                     f'fill="#f2f2f2" stroke="#b0b0b0" stroke-width="1"/>')
    for i in range(3):  # white cards on top
        parts.append(f'<rect x="80" y="{60 + i * 140}" width="200" height="60" '
                     f'fill="#ffffff" stroke="#bebebe" stroke-width="1"/>')
    # the only color: two tiny chips
    parts.append('<rect x="400" y="60" width="60" height="30" fill="#dbeafe" stroke="#2563eb"/>')
    parts.append('<rect x="400" y="200" width="60" height="30" fill="#fee2e2" stroke="#dc2626"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert any("gray-dominant" in s for s in issues)


def test_tinted_bands_are_not_gray_dominant():
    """Band-style scheme: tinted band fills ride the AREA axis."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(6):
        parts.append(f'<rect x="50" y="{40 + i * 140}" width="1000" height="100" '
                     f'fill="#dae8fc" stroke="#1b3a5c" stroke-width="1.5"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert not any("gray-dominant" in s for s in issues)


def test_node_style_colors_ride_the_element_axis():
    """Node-style scheme (constellation/flowchart): neutral bands are fine
    when the primary NODES carry the color."""
    parts = ['<svg width="1200" height="900" xmlns="http://www.w3.org/2000/svg">',
             '<rect x="0" y="0" width="1200" height="900" fill="#ffffff"/>']
    for i in range(5):  # neutral layer bands
        parts.append(f'<rect x="100" y="{40 + i * 170}" width="1000" height="120" '
                     f'fill="#f7f7f7" stroke="none"/>')
    for i in range(20):  # colored constellation nodes
        parts.append(f'<circle cx="{150 + (i % 5) * 200}" cy="{100 + (i // 5) * 170}" '
                     f'r="15" fill="#dbeafe" stroke="#2563eb" stroke-width="1.4"/>')
    parts.append('</svg>')
    issues = check_palette(_wrap("".join(parts), 1200, 900))
    assert not any("gray-dominant" in s for s in issues)

def test_floor_survives_the_real_drawer():
    """End-to-end through SVGDrawer: a colored diagram keeps its palette PASS,
    a slate-only one draws the FAIL inside the full evaluate_svg report."""
    d = SVGDrawer(600, 400)
    d.rect(50, 50, 500, 120, fill="#dae8fc", stroke="#1b3a5c", stroke_width=1.5)
    issues = check_palette(d)
    assert not any("no chromatic accent" in s for s in issues)

    d2 = SVGDrawer(600, 400)
    d2.rect(50, 50, 500, 120, fill="#ffffff", stroke="#546e7a", stroke_width=2)
    issues2 = check_palette(d2)
    assert any("no chromatic accent" in s for s in issues2)
