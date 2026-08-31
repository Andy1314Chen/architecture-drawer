"""Agent-replay session recorder (pytest plugin).

Adds ``--record-sessions <dir>``: when set, every ``pi`` invocation the
replay harness makes is patched to pass ``--session-dir <dir>`` so full
session .jsonl files (message history incl. thinking) are persisted outside
the sandbox for offline timing/behavior analysis. Leak-free property is
preserved: nothing extra lands inside any sandbox.

Load with ``-p replay_recorder`` (PYTHONPATH=tests or run from tests/).
"""
from __future__ import annotations

import os
import sys

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--record-sessions", action="store", default=None,
        help="pi --session-dir root for agent-replay session capture",
    )


def pytest_configure(config):
    root = config.getoption("--record-sessions")
    if not root:
        return
    os.makedirs(root, exist_ok=True)
    # Force module identity with the harness's import: insert tests/ at
    # sys.path[0] BEFORE importing, so agent_backends resolves to the same
    # module object test_agent_replay.py will later import and patch.
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import agent_backends  # noqa: E402
    original = agent_backends.PiAgentBackend._base_args

    def patched(self, cwd):
        args = original(self, cwd)
        # The harness pins --no-session (ephemeral); recording needs it OFF.
        # pi lets the last flag win, so swap instead of appending.
        args = [a for a in args if a != "--no-session"]
        return args + ["--session-dir", root]

    agent_backends.PiAgentBackend._base_args = patched
