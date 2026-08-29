"""Real-agent backends for the opt-in ``--agent-replay`` regression layer.

Each backend installs the skill into a **leak-free sandbox** and lets a real
coding agent author ``gen.py`` from the eval's ``input.md``. The harness — not
the agent — is the deterministic gate: it re-runs the produced ``gen.py`` and
asserts both score and artifacts (see ``tests/test_agent_replay.py``).

The default backend is the **Pi coding agent** (pi.dev,
``@earendil-works/pi-coding-agent``). The ``AgentBackend`` ABC leaves room for
other harnesses; adding one means implementing ``run()`` and, optionally,
``continue_run()``.

Leak-free sandbox shape (every backend):

    <sandbox>/                       # git-init'd so project detection is sane
      .pi/skills/architecture-drawer/
        SKILL.md
        scripts/                     # svg_utils.py · evaluator.py · svg2pptx.py
        references/                  # design_specs.md · diagram_types.md
        assets/
      AGENTS.md                      # scripts-path hint + output convention
      input.md                       # the TARGET eval's spec only

The skill's ``evals/`` directory is NEVER copied. Feeding the golden
``gen.py`` to the agent would turn the replay into a reverse-transcription
exercise (it copies coordinates verbatim, defeats the purpose of testing
text->diagram understanding, and propagates any golden defects).

References (Pi CLI + skills, retrieved 2026-08-02):
  - Print mode: ``pi -p "<prompt>"`` (non-interactive, prints response, exits)
  - Skill load: ``--skill <path>`` (repeatable, additive even with --no-skills,
    bypasses the project-trust gate)
  - Trust: ``-a``/``--approve`` trusts project-local files (AGENTS.md context,
    ``.pi/skills/`` discovery) for this run
  - Skills doc: pi loads ``.pi/skills/<name>/SKILL.md`` (project, post-trust)
  - Default tools: read, write, edit, bash, grep, find, ls (auto-approved,
    no permission pop-ups)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

# Skill install layout, relative to the sandbox root. Pi discovers project
# skills at ``.pi/skills/<name>/SKILL.md`` (only after the project is trusted,
# so the backend also passes ``--skill`` explicitly to guarantee the load).
_SANDBOX_SKILL_REL = Path(".pi") / "skills" / "architecture-drawer"

# Subdirs of the skill that constitute its PUBLIC surface. ``evals/`` is
# intentionally excluded to keep the golden generators out of the sandbox.
_PUBLIC_SUBDIRS = ("scripts", "references", "assets")

# Context-file hint dropped at the sandbox root. Pi discovers ``AGENTS.md`` as a
# context file (disable with ``-nc``), so this reaches the agent's system prompt
# without being inlined into the run prompt (which would defeat skill discovery).
_AGENTS_HINT = """\
# Sandbox — architecture-drawer agent replay

You are drawing a diagram with the **architecture-drawer** skill. It is
installed for you (loaded via `--skill`) at:

    .pi/skills/architecture-drawer/

Its Python modules live at `.pi/skills/architecture-drawer/scripts`. Resolve
that directory from your script's own location — never hard-code an absolute
path:

```python
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL = os.path.normpath(os.path.join(
    _HERE, ".pi", "skills", "architecture-drawer", "scripts"))
if _SKILL not in sys.path:
    sys.path.insert(0, _SKILL)
```

Write `gen.py` and all of its artifacts (SVG / PNG / PPTX) next to `gen.py` in
this directory. The architecture to draw is in `input.md`.
"""


def _skill_root() -> Path:
    """Lazily resolve the skill root via conftest (avoids a load-time cycle)."""
    from conftest import SKILL
    return SKILL


def prepare_sandbox(eval_dir: Path, skill_root: Path | None = None) -> Path:
    """Build a leak-free sandbox for *eval_dir* and return its path.

    Copies the skill's public surface (no ``evals/``) to
    ``<sandbox>/.pi/skills/architecture-drawer/``, drops the target eval's
    ``input.md`` at the sandbox root, writes an ``AGENTS.md`` path hint, and
    ``git init``s the sandbox so the agent's project detection (session storage,
    worktree root) is well-defined.
    """
    skill_root = skill_root or _skill_root()
    sandbox = Path(tempfile.mkdtemp(prefix="agent_replay_"))
    skill_dst = sandbox / _SANDBOX_SKILL_REL
    skill_dst.mkdir(parents=True, exist_ok=True)
    # SKILL.md + public subdirs only — never evals/.
    shutil.copy2(skill_root / "SKILL.md", skill_dst / "SKILL.md")
    for sub in _PUBLIC_SUBDIRS:
        src = skill_root / sub
        if src.is_dir():
            # Skip __pycache__/*.pyc so stale bytecode never enters the
            # leak-free sandbox (copytree copies everything by default).
            shutil.copytree(src, skill_dst / sub,
                            ignore=shutil.ignore_patterns("__pycache__"))
    # Target eval spec only — not its gen.py, not sibling evals.
    shutil.copy2(eval_dir / "input.md", sandbox / "input.md")
    (sandbox / "AGENTS.md").write_text(_AGENTS_HINT, encoding="utf-8")
    # git-init so project-relative detection / session storage is scoped here.
    # Non-fatal: --skill + -a make the load work even without a worktree root.
    for cmd in (["git", "init", "-q"], ["git", "config", "commit.gpgsign", "false"]):
        subprocess.run(cmd, cwd=str(sandbox), capture_output=True, check=False)
    return sandbox


class AgentBackend(ABC):
    """Abstract real-agent backend for the ``--agent-replay`` layer.

    Implementations install the skill into a sandbox (``prepare_sandbox``) and
    drive a headless coding agent to author ``gen.py``. The deterministic score
    gate lives in the test (``conftest.score_gen_script``); the backend only has
    to make the agent produce ``gen.py`` (and, ideally, the full SVG/PNG/PPTX
    triplet).
    """

    name: str = "agent"
    cli: str = ""            # executable name checked on PATH
    timeout: int = 1800      # per-run seconds (covers ~912s worst observed + variance)

    @abstractmethod
    def run(self, prompt: str, cwd: Path) -> subprocess.CompletedProcess:
        """First-round run: send *prompt* in *cwd*, return the completed process."""

    def continue_run(self, message: str, cwd: Path) -> subprocess.CompletedProcess:
        """Refine round. Stateless default: re-run *message* in *cwd*.

        Pi's tools (read/edit/bash) read the current ``gen.py`` from disk, so
        each round is self-contained — no session-continuity bookkeeping is
        required. Backends with cheap session continuation may override this.
        """
        return self.run(message, cwd)

    @staticmethod
    def available() -> bool:  # pragma: no cover - overridden by concrete backends
        return False


class PiAgentBackend(AgentBackend):
    """Pi coding agent (pi.dev) backend.

    Headless invocation: ``pi -p --skill <path> -a --no-session "<prompt>"``.

    - ``-p``/``--print``: non-interactive; print the response and exit.
    - ``--skill <path>``: load the skill explicitly. Additive and bypasses the
      project-trust gate, so the skill loads even in a fresh untrusted sandbox.
    - ``-a``/``--approve``: trust project-local files (``AGENTS.md`` context,
      ``.pi/skills/`` discovery) for this run.
    - ``--no-session``: ephemeral — no session files are written; refine rounds
      re-read ``gen.py`` from disk instead of resuming a session.
    - The prompt is one trailing argv element. It is crafted to NOT start with
      ``-`` (we do not inline SKILL.md, whose ``---`` YAML frontmatter would be
      mis-parsed as a flag), so it is safe as a bare positional.

    Auth is the caller's responsibility: set ``ANTHROPIC_API_KEY`` (or another
    provider key / a prior ``pi /login``) before running the suite. Optionally
    pin a model via the ``PI_AGENT_MODEL`` env var or the *model* argument.
    """

    name = "pi"
    cli = "pi"

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("PI_AGENT_MODEL")

    def _base_args(self, cwd: Path) -> list[str]:
        args = [self.cli, "-p", "--no-session"]
        skill = cwd / _SANDBOX_SKILL_REL
        if skill.is_dir():
            args += ["--skill", str(skill)]   # bypass the project-trust gate
        args += ["-a"]                         # trust project-local files (AGENTS.md)
        if self.model:
            args += ["--model", self.model]
        return args

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        # Skip the startup version check so a run never depends on pi.dev being
        # reachable, and never auto-updates mid-suite. (PI_OFFLINE is NOT set:
        # agent-replay is local/nightly only, never CI, and PI_OFFLINE would
        # also block the provider model-catalog fetch the run needs.)
        env.setdefault("PI_SKIP_VERSION_CHECK", "1")
        return env

    def run(self, prompt: str, cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            self._base_args(cwd) + [prompt],
            cwd=str(cwd), capture_output=True, text=True,
            timeout=self.timeout, env=self._env(),
        )

    @staticmethod
    def available() -> bool:
        return shutil.which("pi") is not None


__all__ = ["AgentBackend", "PiAgentBackend", "prepare_sandbox"]
