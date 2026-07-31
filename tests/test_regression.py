"""Regression tests for every bundled eval generator.

For each ``evals/<name>/gen.py``:
  1. Run it as a subprocess and assert its printed quality score meets the
     per-case threshold (locks in current quality; catches evaluator/layout
     regressions).
  2. Snapshot the rendered SVG against a golden copy under ``tests/golden/``.
     On first run the golden is written automatically; thereafter any
     geometry/text drift fails the test. Use ``pytest --regenerate-golden`` to
     intentionally refresh all golden snapshots after an accepted change.
"""
from __future__ import annotations

import pytest

from conftest import (
    GOLDEN, LLM_REPLAY_MIN_SCORE, SCORE_THRESHOLDS, run_gen, replay_gen,
)



@pytest.mark.regression
def test_eval_quality_and_snapshot(eval_cases, request):
    """Each eval must score >= its threshold and match its golden SVG."""
    if not eval_cases:
        pytest.skip("no eval cases discovered")

    regenerate = request.config.getoption("--regenerate-golden")
    failures = []
    checked = 0

    for name, eval_dir in sorted(eval_cases.items()):
        checked += 1
        try:
            score, svg = run_gen(eval_dir)
        except Exception as exc:  # subprocess / IO failure
            failures.append(f"[{name}] gen.py error: {exc}")
            continue

        threshold = SCORE_THRESHOLDS.get(name)
        if threshold is not None and score < threshold:
            failures.append(f"[{name}] score {score} < threshold {threshold}")

        golden_path = GOLDEN / f"{name}.svg"
        if regenerate:
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(svg, encoding="utf-8")
        elif golden_path.is_file():
            if golden_path.read_text(encoding="utf-8") != svg:
                failures.append(
                    f"[{name}] SVG snapshot drift "
                    f"(rerun with --regenerate-golden to accept)"
                )
        else:
            # First run: seed the golden so the repo is self-bootstrapping.
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(svg, encoding="utf-8")

    if failures:
        pytest.fail(
            f"{len(failures)} regression failure(s) across {checked} eval(s):\n  - "
            + "\n  - ".join(failures)
        )



@pytest.mark.llm_replay
def test_llm_replay_quality(eval_cases, request):
    """LLM replay: read each eval's input.md, regenerate via LLM, score only.

    Opt-in (``pytest --llm-replay``). Unlike the frozen-gen snapshot test, no
    golden comparison is performed — only the score must clear the floor.
    This covers the skill's core promise: "turn a text description into a
    compliant diagram". Run locally or nightly, not in the PR gate.
    """
    if not request.config.getoption("--llm-replay"):
        pytest.skip("--llm-replay not passed; deterministic gate only")

    candidates = {
        n: d for n, d in eval_cases.items() if (d / "input.md").is_file()
    }
    if not candidates:
        pytest.skip("no eval has an input.md spec to replay")

    failures = []
    checked = 0
    for name, eval_dir in sorted(candidates.items()):
        checked += 1
        try:
            score = replay_gen(eval_dir, request.config.getoption("--llm-iter"))
        except Exception as exc:
            failures.append(f"[{name}] replay error: {exc}")
            continue
        if score < LLM_REPLAY_MIN_SCORE:
            failures.append(
                f"[{name}] replay score {score} < floor {LLM_REPLAY_MIN_SCORE}"
            )

    if failures:
        pytest.fail(
            f"{len(failures)} LLM replay failure(s) across {checked} eval(s):\n  - "
            + "\n  - ".join(failures)
        )