# Evaluator Cheatsheet — 16 checks × threshold × trigger

Single-page reference for the quality gate in `scripts/evaluator.py`
(`evaluate_svg`). **Read this instead of the evaluator source code**: every
number below is the exact default the shipped evaluator enforces, and the
repair column is what the `[FAIL]`/`[WARN]` report line expects you to do.
All checks are **render-then-parse** — they re-read the actual SVG markup, so
`add_element`/`bbox=False` content is measured too.

**Do not pre-verify these by hand.** `evaluate_svg` runs in under a second on
a finished `gen.py`; it is the cheap oracle. Sketch an approximate layout,
run the script, read the report lines, and fix exactly what they name. The
table exists so a report line can be mapped to a threshold and a repair
without reading the check's implementation.

## Score model

Start at 100. Each failing check subtracts its penalty (see table; multiple
issues in one check multiply per-issue cost up to that check's cap). Score
floors at 0. `[FAIL]` vs `[WARN]`: both cost points; `[FAIL]` classes are
defects that must be fixed (ship gate: no `[FAIL]`), `[WARN]` classes are
quality polish — fix when cheap, never suppress.

## The 16 checks

| 1 | Collisions | Any two registered bboxes overlap | 10/issue | Move one node clear of the other; never layer business shapes |
| 2 | Canvas boundary | Any bbox outside `0,0–W,H` | 15/issue | Pull coordinates inside; enlarge canvas only via the brief |
| 3 | Text overflow (canvas) | `<text>` bbox outside canvas (pad 2) | 6/issue, cap 24 | Shorten the label or move the text inside |
| 4 | Text overflow (container) | `<text>` bbox outside its nearest containing rect (pad 6) | 3/issue, cap 18 | Widen the node/container or shorten the label |
| 5 | Text overlaps | `<text>` bbox hits a visible shape or another `<text>` (+pad 1) | 4/issue, cap 24 | Nudge the label or the shape; never stack labels |
| 6 | Coverage | Union of bboxes <5% or >60% of canvas | −20 / −10 | Repack to fill the canvas better (denser or sparser) |
| 7 | Dangling / degenerate edges | Edge endpoint >12px from any node border, or length <4px | 8/issue, cap 40 | Re-anchor with `connect(a, side, b, side)` — auto-snap |
| 8 | Duplicate edges | Same endpoint pair within 6px | 8/issue (with #7, cap 40) | Delete the duplicate; or offset via port spread (automatic when ≥2 edges share a side) |
| 9 | Phantom anchors | Invisible node (no fill/stroke/size) used as edge endpoint | 15/issue, cap 45 | Give the anchor a visible shape, or connect to a real node |
| 10 | Route-through | Edge polyline passes through an unrelated node interior (+3px margin) | 10/issue, cap 40 | Reroute: connect side-to-side so the segment misses nodes |
| 11 | Edge crossings | Two edge polylines cross in their interiors | 8/pair, cap 40 | Reroute one edge; a hub junction node often kills crossings |
| 12 | Composition budget | >2 bends, >1.35× route stretch, gutter <20px, segment <16px | 2/issue (WARN), cap 12 | Straighten the route; widen the container gutter |
| 12b | Edge-through-text | Edge segment passes through a `<text>` bbox | 8/issue, cap 24 | Reroute the edge around the label |
| 13 | Same-kind spacing | Two `op`/`junction` nodes <14px apart (Euclidean gap); a chip fully inside its card is exempt (gutter rule owns it) | 4/issue, cap 20 | Spread nodes; `auto_refine` fixes this automatically |
| 14 | Peer alignment | Same-sized same-kind peers in a row/column sharing no edge/center line (5px / 15%) | 3/issue, cap 15 | Snap the row/column to shared edges |
| 15 | Type scale | >4 distinct font sizes, or adjacent tiers <1.15× apart | 4/issue, cap 8 | Use 3–4 tiers (e.g. 20/14/12/10); merge near-duplicate sizes |
| 16 | Palette | >8 accents (hard 12); zero chromatic accents; gray-dominance (<35% business elements chromatic AND <15% painted area) | 4/issue; FAIL beyond hard cap / colorless / gray-dominant | Use a preset from `design_specs.md`; color must own bands or nodes, not just chips |
| 17 | Contrast | `<text>` on an accent fill <3:1 FAIL (<4.5:1 WARN; large text ≥24px or bold ≥18.5px → 3:1) | 6/issue, cap 18; WARN 3/issue cap 12 | Darken text on light tints / lighten on dark fills (preset tiers are pre-verified) |

> Rows 15–17 involve the semantic layer (palette / type scale / contrast are
> asserted in the brief contract too): a preset from `design_specs.md` plus
> brief palette_role keys keeps all three green without measurement.

## Report line → repair mapping (quick decode)

```
"[FAIL] N element collisions"                       → check 1: separate the shapes
"[FAIL] N elements exceed canvas boundaries"        → check 2: pull inside / resize canvas
"[FAIL] N text element(s) overflow the canvas"      → check 3: shorten/move text
"[FAIL] N edge(s) route through unrelated node"     → check 10: reroute
"[FAIL] N text overlap(s) with shapes/other text"   → check 5: nudge labels
"[WARN] Canvas coverage very low/high"              → check 6: repack density
"[FAIL] Connection check … dangling … duplicate"    → check 7/8: re-anchor / dedupe
"[FAIL] N phantom anchor(s)"                        → check 9: visible anchor
"[FAIL] N edge pair(s) cross"                       → check 11: reroute / hub
"[FAIL] N edge(s) pass through text"                → check 12b: route around text
"[WARN] composition budget violation(s)"            → check 12: straighten/gutter
"[WARN] N same-kind node pair(s) too close"         → check 13: spread / auto_refine
"[WARN] N misaligned same-kind peer pair(s)"        → check 14: snap to shared edge
"[WARN/FAIL] Typography …"                          → check 15: 3–4 tiers, ≥1.15×
"[WARN/FAIL] Palette …"                             → check 16: preset + brief keys
"[FAIL] N text element(s) below 3:1 contrast"       → check 17: contrast-safe text
```

## Anti-simulation guidance

The two most expensive mistakes an agent makes with this skill (measured:
~84% of wall-clock on a clean run): reading the evaluator source to
understand every threshold, then mentally verifying the layout against all
16 checks before writing anything. Both are wasted effort:

- The evaluator **is** the oracle and runs in <1s. Write an approximate
  layout, run, read report lines, fix what they name. Two bounded rounds
  converge on every shipped eval.
- This cheatsheet replaces source-reading for check semantics. If a report
  line's vocabulary is unclear, read this table's row, not the check's
  implementation.

## Notes on auto-fix vs manual

`auto_refine(drawer)` (in `evaluator.py`) handles checks 12 (gutter part),
13, and the spacing part of the budget automatically — call it before any
manual repair. It deliberately refuses two cases: containment pairs (a chip
inside its card is the gutter rule's business) and equal-pitch grid arrays
(>=3 aligned nodes — move the whole array instead; centering one member
breaks the alignment). Checks 7/10/11/12b (dangles, route-through, crossings,
edge-through-text) need manual rerouting: `connect()` side-to-side snapping
plus junction nodes for fan-outs. Differently-sized peers are exempt from
check 14; legend/background shapes and intentional in-box labels are exempt
from check 5.
