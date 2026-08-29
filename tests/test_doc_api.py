"""Deterministic guard against SKILL.md / references doc <-> API drift.

Scans fenced code blocks in ``SKILL.md`` + ``references/*.md`` for
``drawer.<m>(`` / ``d.<m>(`` method references and asserts each exists on
``SVGDrawer``. Also asserts a curated public module/function surface stays
importable. Pure static check — no LLM, no rendering — so it runs in the
default CI gate alongside the spec and regression tests.

Catches the real drift directions:
  - docs name a method that no longer exists (API renamed/removed);
  - a core public symbol was removed entirely (curated-set safety net).

Scope is deliberately fenced code blocks only (not prose): inline backtick
spans like ``connect`` in a sentence would false-positive on common words.
"""
from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from conftest import SKILL, SCRIPTS

_CODE_FENCE_RE = re.compile(r"```[a-zA-Z0-9_]*\n(.*?)```", re.S)
# Method-call shapes inside code: drawer.rect( , d.connect( — the open paren
# excludes properties (drawer.cx) and bare attribute reads.
_METHOD_RE = re.compile(r"\b(?:drawer|d)\.([a-z_][a-z0-9_]*)\s*\(")

# Curated public module-level surface; each must stay importable from scripts/.
_MODULE_FUNCS = {
    "svg_utils": ("SVGDrawer", "save_svg", "rasterize_svg"),
    "evaluator": ("evaluate_svg", "auto_refine"),
    "svg2pptx": ("svg_to_pptx", "save_pptx", "PptxConfig", "add_svg_to_slide"),
    "semantic_qa": ("run_semantic_qa", "semantic_qa"),
}


def _doc_sources() -> list[Path]:
    files = [SKILL / "SKILL.md"]
    refs = SKILL / "references"
    if refs.is_dir():
        files.extend(sorted(refs.glob("*.md")))
    return [f for f in files if f.is_file()]


def _doc_code_text() -> str:
    chunks: list[str] = []
    for f in _doc_sources():
        chunks.extend(_CODE_FENCE_RE.findall(f.read_text(encoding="utf-8")))
    return "\n".join(chunks)


def _ensure_scripts_on_path() -> None:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))


def test_documented_drawer_methods_exist():
    """Every drawer.<m>( / d.<m>( in a fenced block must exist on SVGDrawer."""
    _ensure_scripts_on_path()
    from svg_utils import SVGDrawer

    methods = set(_METHOD_RE.findall(_doc_code_text()))
    assert methods, "no drawer.<m>( references found in docs — extraction broken"
    missing = sorted(m for m in methods if not callable(getattr(SVGDrawer, m, None)))
    assert not missing, f"docs reference drawer methods not on SVGDrawer: {missing}"


def test_core_public_api_importable():
    """The curated public module/function surface must remain importable."""
    _ensure_scripts_on_path()
    missing: list[str] = []
    for mod_name, names in _MODULE_FUNCS.items():
        mod = importlib.import_module(mod_name)
        for n in names:
            if not hasattr(mod, n):
                missing.append(f"{mod_name}.{n}")
    assert not missing, f"public API symbols missing from scripts/: {missing}"
