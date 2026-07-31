"""Shared fixtures and helpers for the architecture-drawer test suite.

Each eval case is a self-contained directory under the skill's ``evals/``
folder containing a ``gen.py`` generator script. Tests treat ``gen.py`` as a
black box: run it as a subprocess and capture the quality score it prints, then
read back the SVG it wrote for a snapshot diff. This avoids coupling to the
variable names or post-build reassignments (e.g. ``auto_refine``) inside any
generator and never re-derives geometry from a bare SVG string.
"""
from __future__ import annotations

import re
import subprocess
import sys
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
    "20250728_space_opt_framework": 100,
    "20260728_120000_mlir_pipeline": 76,
    "20260728_153000_agent_infra_architecture": 90,
    "20260728_153000_agent_infra_tracks": 90,
    "20260728_183101_satellite_arch": 100,
    "20260728_190000_opt_framework": 76,
    "20260728_203836_llm_inference_arch": 84,
    "20260728_205612_llm_inference_arch_dawn": 84,
    "20260728_2157_satellite_arch": 100,
    "20260729_llama_cpp_arch": 90,
    "20260729_pansharpening_cs_mra": 96,
    "20260729_pi_agent_architecture": 100,
    "20260730_vllm_arch": 90,
}

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


def pytest_configure(config):
    config.addinivalue_line("markers", "regression: eval-case quality + snapshot test")

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


__all__ = [
    "ROOT", "SKILL", "SCRIPTS", "EVALS", "GOLDEN",
    "SCORE_THRESHOLDS", "run_gen",
]
