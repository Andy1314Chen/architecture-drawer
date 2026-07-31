"""Shared fixtures and helpers for the architecture-drawer test suite.

Each eval case is a self-contained directory under the skill's ``evals/``
folder containing a ``gen.py`` generator script. Tests treat ``gen.py`` as a
black box: run it as a subprocess and capture the quality score it prints, then
read back the SVG it wrote for a snapshot diff. This avoids coupling to the
variable names or post-build reassignments (e.g. ``auto_refine``) inside any
generator and never re-derives geometry from a bare SVG string.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Skill layout:  tests/  ->  ../plugins/<plugin>/skills/architecture-drawer/
ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins" / "architecture-drawer" / "skills" / "architecture-drawer"
SCRIPTS = SKILL / "scripts"
EVALS = SKILL / "evals"
GOLDEN = ROOT / "tests" / "golden"

# Per-eval score thresholds. A regression suite locks in *current* quality so
# it catches degradation; it does not retro-raise the bar on legacy generators
# written before later-added checks (text-overlap, etc.). Each value is the
# observed baseline (2026-07-30). Bump a threshold only after intentionally
# improving that generator; the snapshot test will also flag the SVG change.
SCORE_THRESHOLDS = {
    "20260728_120000_mlir_pipeline": 76,
    "20260728_153000_agent_infra_architecture": 90,
    "20260728_203836_llm_inference_arch": 84,
    "20260728_2157_satellite_arch": 100,
    "20260729_llama_cpp_arch": 90,
    "20260729_pi_agent_architecture": 100,
    "20260730_vllm_arch": 90,
}

# Minimum acceptable score for LLM-replayed diagrams. One-shot LLM output has
# more geometric variance than hand-tuned gen.py, so the bar is a flat "no
# major evaluator violations" rather than matching each frozen baseline.
LLM_REPLAY_MIN_SCORE = 80

# Generators print the score under several labels ("Quality Score", "SCORE",
# "Final score", "Initial score", "Score"). Match the last integer following
# any of them — that is the final reported score for every generator.
_SCORE_RE = re.compile(
    r"(?:Quality Score|Final score|Initial score|SCORE|Score)\D+(\d+)", re.I
)


def _eval_dirs():
    """All eval case directories (those containing a gen.py)."""
    if not EVALS.is_dir():
        return []
    return sorted(p for p in EVALS.iterdir() if (p / "gen.py").is_file())


def pytest_addoption(parser):
    parser.addoption(
        "--regenerate-golden", action="store_true", default=False,
        help="Refresh golden SVG snapshots instead of comparing.",
    )
    parser.addoption(
        "--llm-replay", action="store_true", default=False,
        help="Replay evals via LLM: read input.md, regenerate gen.py, "
             "iterate generate->evaluate->correct, score only. Needs 'claude' CLI.",
    )
    parser.addoption(
        "--llm-iter", action="store", type=int, default=3,
        help="Max LLM correction rounds (generate + N fix iterations). Default 3.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "regression: eval-case quality + snapshot test")
    config.addinivalue_line("markers", "llm_replay: LLM-replayed quality (opt-in via --llm-replay)")

@pytest.fixture(scope="session")
def eval_cases():
    """Map of eval-name -> directory, discovered once per session."""
    return {p.name: p for p in _eval_dirs()}


def run_gen(eval_dir: Path):
    """Execute a case's gen.py in its own directory.

    Runs as a subprocess so module-level side effects (prints, file writes)
    cannot pollute the test process. Returns ``(score, svg_text)`` where the
    score is parsed from stdout and svg_text is read back from the file the
    generator wrote next to itself.

    Raises RuntimeError if the run fails, no score is printed, or no SVG is
    emitted.
    """
    proc = subprocess.run(
        [sys.executable, "gen.py"],
        cwd=str(eval_dir),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gen.py failed (exit {proc.returncode}) in {eval_dir.name}:\n"
            f"{proc.stderr[-2000:]}"
        )
    combined = proc.stdout + "\n" + proc.stderr
    matches = _SCORE_RE.findall(combined)
    if not matches:
        raise RuntimeError(
            f"No score printed by gen.py in {eval_dir.name}.\n"
            f"stdout:\n{proc.stdout[-1500:]}"
        )
    score = int(matches[-1])
    svgs = sorted(eval_dir.glob("*.svg"))
    if not svgs:
        raise RuntimeError(
            f"gen.py produced no .svg in {eval_dir.name}.\nstdout:\n{proc.stdout[-1000:]}"
        )
    return score, svgs[0].read_text(encoding="utf-8")


def _extract_code(text: str) -> str:
    """Pull the largest Python code block out of an LLM response."""
    for pat in (r"```python\n(.*?)```", r"```\n(.*?)```"):
        blocks = re.findall(pat, text, re.S)
        if blocks:
            return max(blocks, key=len)
    return text


def _build_replay_prompt(skill_md: str, input_md: str) -> str:
    """Assemble the prompt that asks the LLM to produce an initial gen.py.

    IMPORTANT — anti-leakage: the prompt contains ONLY the skill's public
    documentation (SKILL.md) and the natural-language input spec (input.md).
    The golden SVG is intentionally NOT included: feeding the rendered output
    turns the replay into a reverse-transcription exercise (the LLM copies
    coordinates verbatim, defeats the purpose of testing text->diagram
    understanding, and propagates any golden defects into the replay).
    """
    return (
        f"{skill_md}\n\n---\n\n## Task\n\n"
        "Using the SVGDrawer DSL documented above, write a COMPLETE, "
        "self-contained Python script that draws the architecture described "
        "below and evaluates it with evaluate_svg.\n\n"
        "Requirements:\n"
        "- Resolve the scripts dir relative to `__file__` via "
        "`os.path.join(os.path.dirname(os.path.abspath(__file__)), \"..\", \"..\", \"scripts\")`.\n"
        "- Import from svg_utils, evaluator, and optionally svg2pptx.\n"
        "- Print the score: `print(f\"Score: {score}\")`.\n"
        "- Save the SVG next to the script.\n"
        "- Output ONLY the Python code in a single ```python block.\n\n"
        "## Architecture to draw\n\n"
        f"{input_md}"
    )


def _build_refine_prompt(code: str, score: int, report: str) -> str:
    """Feed the current gen.py + evaluator report back to the LLM for fixing.

    This mirrors the skill's Generate->Evaluate->Correct loop: the LLM sees
    its own code and the concrete FAIL lines, then must adjust coordinates
    (auto_refine cannot fix text overlaps / dangles / crossings — those are
    semantic layout decisions only the LLM can make).
    """
    return (
        "Your generated diagram scored below target. Here is the current "
        "gen.py and the evaluator report. Fix the [FAIL] and [WARN] items "
        "(especially text overlaps, dangling edges, crossings) by adjusting "
        "coordinates/layout — do NOT just add suppressions. Return the FULL "
        "corrected script in a single ```python block.\n\n"
        f"## Current code\n\n```python\n{code}\n```\n\n"
        f"## Score: {score}\n\n## Report\n\n```\n{report}\n```\n"
    )


def _llm_generate(prompt: str) -> str:
    """Call the ``claude`` CLI in headless mode to produce gen.py source.

    Raises ``RuntimeError`` if the CLI is missing or the call fails.
    """
    if not shutil.which("claude"):
        raise RuntimeError(
            "'claude' CLI not found on PATH. Install Claude Code to run LLM "
            "replay, or omit --llm-replay for a normal deterministic gate."
        )
    proc = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (exit {proc.returncode}):\n{proc.stderr[-1500:]}"
        )
    return _extract_code(proc.stdout)


def _run_and_score(code: str) -> tuple[int | None, str, str]:
    """Execute a gen.py in a sandboxed tempdir and return (score, report, stdout).

    score is None when the code fails to run or prints no score; in that case
    report carries the error/stderr for feedback to the LLM.
    """
    with tempfile.TemporaryDirectory(prefix="llm_replay_") as tmp:
        gen_path = Path(tmp) / "gen.py"
        gen_path.write_text(code, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = (
            str(SCRIPTS) + os.pathsep + env.get("PYTHONPATH", "")
        )
        proc = subprocess.run(
            [sys.executable, str(gen_path)],
            cwd=tmp, capture_output=True, text=True, timeout=180, env=env,
        )
    combined = proc.stdout + "\n" + proc.stderr
    if proc.returncode != 0:
        return None, combined[-2000:], proc.stdout
    matches = _SCORE_RE.findall(combined)
    if not matches:
        return None, "no score printed\n" + proc.stdout[-1500:], proc.stdout
    return int(matches[-1]), combined, proc.stdout


def replay_gen(eval_dir: Path, max_iter: int = 3) -> int:
    """Regenerate a diagram via an LLM generate->evaluate->correct loop.

    Mirrors a real Claude Code session using the skill: generate an initial
    gen.py from ``input.md``, run it, and if it scores below target or has
    [FAIL] items, feed the report back to the LLM for a fix (up to *max_iter*
    correction rounds). Returns the best score achieved.

    Anti-leakage: only ``SKILL.md`` + ``input.md`` enter the prompt; the golden
    SVG is never provided. The generated code runs sandboxed in a tempdir.

    Raises ``RuntimeError`` if the LLM backend is unavailable.
    """
    input_md = (eval_dir / "input.md").read_text(encoding="utf-8")
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    code = _llm_generate(_build_replay_prompt(skill_md, input_md))
    best_score, best_code = None, code

    for iteration in range(max_iter + 1):  # 1 generate + max_iter fixes
        score, report, _ = _run_and_score(code)
        if score is None:
            # Runtime/syntax error: let the LLM try to fix it.
            report_text = report
        else:
            if best_score is None or score > best_score:
                best_score, best_code = score, code
            # Target met and no FAIL lines -> done.
            fail_lines = [ln for ln in report.splitlines() if "[FAIL]" in ln]
            if score >= 100 and not fail_lines:
                break
            report_text = report
        if iteration == max_iter:
            break
        # Correction round: feed code + report back to the LLM.
        code = _llm_generate(_build_refine_prompt(code, score or 0, report_text))

    return best_score if best_score is not None else 0


__all__ = [
    "ROOT", "SKILL", "SCRIPTS", "EVALS", "GOLDEN",
    "SCORE_THRESHOLDS", "LLM_REPLAY_MIN_SCORE", "run_gen", "replay_gen",
]
