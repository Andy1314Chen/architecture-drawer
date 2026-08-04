"""Unit tests for the evaluator's per-dimension check functions.

The black-box regression suite (``test_regression.py``) scores whole evals but
does not isolate individual checks. These tests pin the contracts of the
``check_contrast`` and ``check_alignment`` dimensions (added 2026-08-03, mapped
from the better-colors / better-layout skill principles) so a future edit that
silently weakens either check fails here.

Contracts defended:
  - ``check_contrast`` flags a label that doesn't read on its accent fill
    (WCAG 2 ratio), and ignores accent text on a neutral canvas (a deliberate
    category/heading choice, not a fill defect).
  - ``check_alignment`` flags two SAME-SIZED same-kind peers that share neither
    a row/column edge nor a center line, and ignores differently-sized peers
    (a row of varied components legitimately staggers).
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(
    os.path.join(_HERE, "..", "plugins", "architecture-drawer",
                 "skills", "architecture-drawer", "scripts")
)
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)

from svg_utils import SVGDrawer  # noqa: E402
from evaluator import check_alignment, check_contrast  # noqa: E402


# --------------------------------------------------------------------------
# check_contrast
# --------------------------------------------------------------------------
def test_contrast_flags_low_ratio_label_on_accent_fill():
    """A near-fill-colored label on an accent card must FAIL (below 3:1)."""
    d = SVGDrawer(300, 200)
    # mid-blue card with a darker-blue label: ~1.4:1, well under the 3:1 floor
    d.rect(40, 40, 200, 60, fill="#9BB9D1", node_id="card", node_kind="op")
    d.text(140, 70, "label", 14, fill="#769EBF", anchor="middle")
    fail, warn = check_contrast(d)
    assert fail, "expected a FAIL for low-contrast label on accent fill"
    assert "label" in fail[0]
    assert all("card" not in m or "text" not in m for m in fail)


def test_contrast_passes_high_contrast_label_on_accent_fill():
    """Black text on a light accent fill passes both floors."""
    d = SVGDrawer(300, 200)
    d.rect(40, 40, 200, 60, fill="#D5E1EB", node_id="card", node_kind="op")
    d.text(140, 70, "label", 14, fill="#000000", anchor="middle")
    fail, warn = check_contrast(d)
    assert fail == [] and warn == [], "black-on-light-accent must pass"


def test_contrast_ignores_accent_text_on_neutral_canvas():
    """Accent-colored text on white/neutral is a typographic choice, skipped.

    This is the false-positive guard: category labels and muted captions use
    saturated hues on a white canvas by design, and must NOT be measured as a
    fill-contrast defect.
    """
    d = SVGDrawer(300, 200)
    d.text(150, 100, "category", 14, fill="#82b366", anchor="middle")  # green on white
    fail, warn = check_contrast(d)
    assert fail == [] and warn == [], "accent text on neutral canvas must be skipped"


def test_contrast_white_label_on_white_card_skipped():
    """Identical fill+text color is unreadable but not a contrast-measurement case."""
    d = SVGDrawer(300, 200)
    d.rect(40, 40, 120, 50, fill="#ffffff", node_id="card", node_kind="op")
    d.text(100, 65, "x", 14, fill="#ffffff", anchor="middle")
    fail, warn = check_contrast(d)
    assert fail == [] and warn == []


# --------------------------------------------------------------------------
# check_alignment
# --------------------------------------------------------------------------
def test_alignment_flags_misaligned_same_size_column_peers():
    """Two same-sized op nodes stacked but offset on every axis are flagged."""
    d = SVGDrawer(400, 400)
    d.rect(40, 40, 120, 50, node_id="a", node_kind="op")
    d.rect(70, 150, 120, 50, node_id="b", node_kind="op")  # +30px right, no shared edge
    issues = check_alignment(d)
    assert issues, "expected a misalignment issue for offset same-size peers"
    assert "a" in issues[0] and "b" in issues[0]


def test_alignment_passes_aligned_row_peers():
    """Two same-sized op nodes on a shared top edge are aligned."""
    d = SVGDrawer(400, 300)
    d.rect(40, 40, 120, 50, node_id="a", node_kind="op")
    d.rect(200, 40, 120, 50, node_id="b", node_kind="op")  # shared top (y=40)
    assert check_alignment(d) == []


def test_alignment_ignores_differently_sized_staggered_peers():
    """A column of varied-size components legitimately staggers — not flagged."""
    d = SVGDrawer(400, 400)
    d.rect(40, 40, 120, 50, node_id="a", node_kind="op")
    d.rect(200, 150, 90, 70, node_id="b", node_kind="op")  # different footprint
    assert check_alignment(d) == []


def test_alignment_ignores_decorative_nodes():
    """role=decoration nodes are not business peers and are skipped."""
    d = SVGDrawer(400, 400)
    d.rect(40, 40, 120, 50, node_id="a", node_kind="op", role="decoration")
    d.rect(70, 150, 120, 50, node_id="b", node_kind="op", role="decoration")
    assert check_alignment(d) == []
