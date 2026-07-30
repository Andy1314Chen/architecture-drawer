"""Validate the skill against the Agent Skills specification.

Checks enforced by agentskills.io/specification:
  - SKILL.md has YAML frontmatter with required `name` and `description`.
  - `name` is lowercase, 1-64 chars, only [a-z0-9-], no leading/trailing or
    consecutive hyphens, and matches the parent directory name.
  - `description` is non-empty and <= 1024 chars.
  - File references in SKILL.md use relative paths from the skill root.
  - The three core scripts and the references dir are present.
"""
from __future__ import annotations

import re
REF_RE = re.compile(r"`((?:scripts|references|assets|evals)/[\w./-]+\.(?:py|md|json))`")

from conftest import SKILL

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)
NAME_FIELD_RE = re.compile(r"^name:\s*(\S+)\s*$", re.M)
DESC_FIELD_RE = re.compile(r"^description:\s*>\s*\n((?:\s+.*\n)+)|^description:\s*(.+?)\s*$", re.M)
VALID_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _read_skill_md():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    assert m, "SKILL.md must start with '---' YAML frontmatter closed by '---'"
    return m.group(1), m.group(2), text


def test_frontmatter_present_and_parseable():
    fm, _body, _ = _read_skill_md()
    assert "name:" in fm, "frontmatter missing required 'name' field"
    assert "description:" in fm, "frontmatter missing required 'description' field"


def test_name_matches_spec_and_directory():
    fm, _body, _ = _read_skill_md()
    m = NAME_FIELD_RE.search(fm)
    assert m, "no 'name:' field in frontmatter"
    name = m.group(1).strip().strip('"\'')
    assert VALID_NAME_RE.match(name), (
        f"name {name!r} violates spec: lowercase, [a-z0-9-], no leading/trailing/"
        f"consecutive hyphens, 1-64 chars"
    )
    assert name == SKILL.name, f"name {name!r} must equal directory name {SKILL.name!r}"


def test_description_nonempty_and_bounded():
    fm, _body, _ = _read_skill_md()
    m = DESC_FIELD_RE.search(fm)
    assert m, "no 'description:' field in frontmatter"
    desc = (m.group(1) or m.group(2) or "").strip().strip('"\'')
    assert 1 <= len(desc) <= 1024, f"description length {len(desc)} outside 1-1024"
    assert "svg" in desc.lower() or "diagram" in desc.lower(), (
        "description should mention SVG/diagrams for discoverability"
    )


def test_file_references_are_relative():
    _fm, body, _ = _read_skill_md()
    # No absolute paths in backtick-quoted code/path spans (real usage).
    abs_refs = re.findall(r"`(/[^\s`]+)`|file:///", body)
    assert not abs_refs, (
        f"SKILL.md references absolute paths in code spans (must be relative): {abs_refs}"
    )
    # Every backtick-quoted local file ref must resolve under the skill.
    for ref in REF_RE.findall(body):
        assert (SKILL / ref).exists(), f"SKILL.md references missing file: {ref}"


def test_core_scripts_and_references_present():
    for script in ("svg_utils.py", "evaluator.py", "svg2pptx.py"):
        assert (SKILL / "scripts" / script).is_file(), f"missing core script: {script}"
    assert (SKILL / "references" / "design_specs.md").is_file(), "missing design_specs.md"
    assert (SKILL / "evals").is_dir(), "missing evals/ directory"


def test_no_hardcoded_absolute_paths_in_scripts():
    """No leftover /home/... or ppt-agent paths in the shipped scripts."""
    leak = re.compile(r"/home/|/Users/|ppt-agent")
    for script in ("svg_utils.py", "evaluator.py", "svg2pptx.py"):
        text = (SKILL / "scripts" / script).read_text(encoding="utf-8")
        hits = leak.findall(text)
        assert not hits, f"{script} contains absolute/home paths: {hits[:3]}"
