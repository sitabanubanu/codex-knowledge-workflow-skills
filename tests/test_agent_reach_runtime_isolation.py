#!/usr/bin/env python
"""Regression tests for the shared Agent-Reach runtime boundary."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from kw_cli import agent_reach_adapter, agent_reach_runtime


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def test_default_layout(failures: list[str]) -> None:
    assert_true(
        "Agent-Reach source is pinned to v1.5.0",
        agent_reach_runtime.AGENT_REACH_GIT_SOURCE.endswith("@v1.5.0"),
        failures,
    )
    assert_true(
        "Agent-Reach source layout uses github-tools",
        agent_reach_runtime.agent_reach_source_root().name == "Agent-Reach",
        failures,
    )
    assert_true(
        "Agent-Reach runtime layout is separate from source",
        agent_reach_runtime.agent_reach_source_root() != agent_reach_runtime.agent_reach_runtime_root(),
        failures,
    )


def test_hermes_path_is_rejected(failures: list[str]) -> None:
    hermes = r"C:\Users\Socrates\.hermes\hermes-agent\venv\Scripts\agent-reach.exe"
    with tempfile.TemporaryDirectory(prefix="kw-agent-reach-hermes-") as tmp:
        old_root = os.environ.get(agent_reach_runtime.TOOLS_ROOT_ENV)
        os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = tmp
        try:
            try:
                agent_reach_runtime.resolve_agent_reach_executable(
                    require_exists=False,
                    path_lookup=lambda _name: hermes,
                )
            except agent_reach_runtime.AgentReachRuntimeError:
                rejected = True
            else:
                rejected = False
        finally:
            if old_root is None:
                os.environ.pop(agent_reach_runtime.TOOLS_ROOT_ENV, None)
            else:
                os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = old_root
    assert_true("Hermes Agent-Reach executable is rejected", rejected, failures)


def test_adapter_uses_explicit_runtime(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-agent-reach-runtime-") as tmp:
        root = Path(tmp)
        executable = root / "runtimes" / "agent-reach" / "venv" / "Scripts" / "agent-reach.exe"
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_bytes(b"placeholder")
        old_root = os.environ.get(agent_reach_runtime.TOOLS_ROOT_ENV)
        os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = str(root)
        try:
            command = agent_reach_adapter.standalone_agent_reach_command("doctor", "--json")
        finally:
            if old_root is None:
                os.environ.pop(agent_reach_runtime.TOOLS_ROOT_ENV, None)
            else:
                os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = old_root
        assert_true("adapter command uses explicit runtime executable", command[0] == str(executable), failures)


def test_manifest_declares_isolation(failures: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="kw-agent-reach-manifest-") as tmp:
        root = Path(tmp)
        executable = root / "runtimes" / "agent-reach" / "venv" / "Scripts" / "agent-reach.exe"
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_bytes(b"placeholder")
        old_root = os.environ.get(agent_reach_runtime.TOOLS_ROOT_ENV)
        os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = str(root)
        try:
            metadata = agent_reach_runtime.runtime_metadata(path_lookup=lambda _name: None)
        finally:
            if old_root is None:
                os.environ.pop(agent_reach_runtime.TOOLS_ROOT_ENV, None)
            else:
                os.environ[agent_reach_runtime.TOOLS_ROOT_ENV] = old_root
        assert_true("runtime metadata is ready", metadata.get("status") == "ready", failures)
        assert_true("runtime metadata declares Hermes isolation", metadata.get("hermes_isolation") is True, failures)


def main() -> int:
    failures: list[str] = []
    test_default_layout(failures)
    test_hermes_path_is_rejected(failures)
    test_adapter_uses_explicit_runtime(failures)
    test_manifest_declares_isolation(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_agent_reach_runtime_isolation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
