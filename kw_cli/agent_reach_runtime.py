"""Resolve and install the shared Agent-Reach runtime.

Agent-Reach is an external acquisition tool. Its Python environment must not
depend on whichever agent happened to launch Knowledge Workflow.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


AGENT_REACH_VERSION = "1.5.0"
AGENT_REACH_GIT_SOURCE = "git+https://github.com/Panniantong/Agent-Reach.git@v1.5.0"
TOOLS_ROOT_ENV = "KW_GITHUB_TOOLS_ROOT"
RUNTIME_EXE_ENV = "KW_AGENT_REACH_EXE"
BASE_PYTHON_ENV = "KW_AGENT_REACH_BASE_PYTHON"


class AgentReachRuntimeError(RuntimeError):
    """Raised when the shared Agent-Reach runtime is missing or unsafe."""


def github_tools_root() -> Path:
    configured = os.environ.get(TOOLS_ROOT_ENV, "").strip()
    if configured:
        return Path(os.path.expandvars(configured)).expanduser().resolve()
    return (Path.home() / "github-tools").resolve()


def sources_root() -> Path:
    return github_tools_root() / "sources"


def agent_reach_source_root() -> Path:
    return sources_root() / "Agent-Reach"


def runtimes_root() -> Path:
    return github_tools_root() / "runtimes"


def agent_reach_runtime_root() -> Path:
    return runtimes_root() / "agent-reach"


def agent_reach_venv_root() -> Path:
    return agent_reach_runtime_root() / "venv"


def agent_reach_python() -> Path:
    if os.name == "nt":
        return agent_reach_venv_root() / "Scripts" / "python.exe"
    return agent_reach_venv_root() / "bin" / "python"


def agent_reach_executable_path() -> Path:
    if os.name == "nt":
        return agent_reach_venv_root() / "Scripts" / "agent-reach.exe"
    return agent_reach_venv_root() / "bin" / "agent-reach"


def runtime_manifest_path() -> Path:
    return github_tools_root() / "manifests" / "agent-reach.json"


def external_tool_environment() -> dict[str, str]:
    """Keep optional uv/pipx caches and tool environments outside agent homes."""

    root = github_tools_root()
    environment = os.environ.copy()
    environment["UV_TOOL_DIR"] = str(root / "runtimes" / "uv-tools")
    environment["UV_CACHE_DIR"] = str(root / "cache" / "uv")
    environment["PIP_CACHE_DIR"] = str(root / "cache" / "pip")
    environment["PIPX_HOME"] = str(root / "runtimes" / "pipx")
    environment["PIPX_BIN_DIR"] = str(root / "bin")
    return environment


def is_hermes_path(value: str | Path) -> bool:
    normalized = str(Path(value).expanduser().resolve(strict=False)).replace("\\", "/").lower()
    return "/.hermes/" in normalized or "/hermes-agent/venv/" in normalized


def _validate_candidate(candidate: str | Path, *, require_exists: bool) -> Path:
    path = Path(candidate).expanduser()
    if is_hermes_path(path):
        raise AgentReachRuntimeError(
            "Agent-Reach resolved to a Hermes-private environment: "
            f"{path}. Configure the standalone runtime under github-tools."
        )
    if require_exists and not path.exists() and (path.is_absolute() or "/" in str(path) or "\\" in str(path)):
        raise AgentReachRuntimeError(f"Agent-Reach executable does not exist: {path}")
    return path


def _manifest_executable() -> Path | None:
    path = runtime_manifest_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = payload.get("executable") if isinstance(payload, dict) else None
    return Path(value).expanduser() if value else None


def resolve_agent_reach_executable(
    *,
    require_exists: bool = True,
    path_lookup: Callable[[str], str | None] = shutil.which,
) -> Path:
    """Return the standalone executable, rejecting Hermes and unsafe fallback paths."""

    configured = os.environ.get(RUNTIME_EXE_ENV, "").strip()
    if configured:
        return _validate_candidate(configured, require_exists=require_exists)

    manifest_candidate = _manifest_executable()
    if manifest_candidate:
        return _validate_candidate(manifest_candidate, require_exists=require_exists)

    default_candidate = agent_reach_executable_path()
    if default_candidate.exists():
        return _validate_candidate(default_candidate, require_exists=True)

    path_candidate = path_lookup("agent-reach")
    if path_candidate:
        return _validate_candidate(path_candidate, require_exists=require_exists)

    if require_exists:
        raise AgentReachRuntimeError(
            "Standalone Agent-Reach is not installed. Expected: "
            f"{default_candidate}"
        )
    return default_candidate


def agent_reach_command(
    *arguments: str,
    require_exists: bool = True,
    path_lookup: Callable[[str], str | None] = shutil.which,
) -> list[str]:
    executable = resolve_agent_reach_executable(require_exists=require_exists, path_lookup=path_lookup)
    return [str(executable), *arguments]


def runtime_metadata(*, path_lookup: Callable[[str], str | None] = shutil.which) -> dict[str, object]:
    executable = agent_reach_executable_path()
    try:
        resolved = resolve_agent_reach_executable(require_exists=False, path_lookup=path_lookup)
        status = "ready" if resolved.exists() or (not Path(resolved).is_absolute() and str(resolved) != str(executable)) else "missing"
        error = ""
    except AgentReachRuntimeError as exc:
        resolved = executable
        status = "blocked"
        error = str(exc)
    return {
        "status": status,
        "version": AGENT_REACH_VERSION,
        "tools_root": str(github_tools_root()),
        "source_root": str(agent_reach_source_root()),
        "runtime_root": str(agent_reach_runtime_root()),
        "python_executable": str(agent_reach_python()),
        "executable": str(resolved),
        "manifest": str(runtime_manifest_path()),
        "hermes_isolation": not is_hermes_path(resolved),
        "error": error,
    }


def _candidate_base_python() -> Path:
    configured = os.environ.get(BASE_PYTHON_ENV, "").strip()
    if configured:
        candidate = Path(os.path.expandvars(configured)).expanduser()
        if is_hermes_path(candidate):
            raise AgentReachRuntimeError(f"{BASE_PYTHON_ENV} points into Hermes: {candidate}")
        if candidate.exists():
            return candidate.resolve()
        raise AgentReachRuntimeError(f"Configured base Python does not exist: {candidate}")

    if os.name == "nt":
        launcher = shutil.which("py")
        if launcher:
            completed = subprocess.run(
                [launcher, "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode == 0:
                candidate = Path(completed.stdout.strip())
                if candidate.exists() and not is_hermes_path(candidate):
                    return candidate.resolve()

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python312" / "python.exe",
        Path("/usr/bin/python3"),
        Path("/usr/local/bin/python3"),
    ]
    if sys.executable and not is_hermes_path(sys.executable) and sys.prefix == sys.base_prefix:
        candidates.insert(0, Path(sys.executable))
    path_python = shutil.which("python3") or shutil.which("python")
    if path_python:
        candidates.append(Path(path_python))
    for candidate in candidates:
        if candidate and candidate.exists() and not is_hermes_path(candidate):
            return candidate.resolve()
    raise AgentReachRuntimeError(
        "No standalone base Python was found. Install Python 3.12 or set "
        f"{BASE_PYTHON_ENV}."
    )


def install_source() -> str:
    source_root = agent_reach_source_root()
    if (source_root / "pyproject.toml").exists() or (source_root / "setup.py").exists():
        return str(source_root)
    return AGENT_REACH_GIT_SOURCE


def install_plan() -> list[list[str]]:
    base_python = _candidate_base_python()
    return [
        [str(base_python), "-m", "venv", str(agent_reach_venv_root())],
        [str(agent_reach_python()), "-m", "pip", "install", "--upgrade", install_source()],
    ]


def _write_runtime_manifest() -> None:
    path = runtime_manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "tool": "agent-reach",
        "version": AGENT_REACH_VERSION,
        "source_project": str(agent_reach_source_root()),
        "install_source": install_source(),
        "runtime_root": str(agent_reach_runtime_root()),
        "python_executable": str(agent_reach_python()),
        "executable": str(agent_reach_executable_path()),
        "owner": "knowledge-workflow-shared-runtime",
        "hermes_isolation": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ensure_runtime(*, dry_run: bool = False) -> Path:
    """Create the shared venv and install the pinned upstream package."""

    target_python = agent_reach_python()
    target_executable = agent_reach_executable_path()
    if target_executable.exists() and target_python.exists():
        if dry_run:
            print("[dry-run] Agent-Reach standalone runtime already exists:")
            print(f"  {agent_reach_runtime_root()}")
            print("  " + " ".join([str(target_python), "-m", "pip", "install", "--upgrade", install_source()]))
            return target_executable
        completed = subprocess.run(
            [str(target_python), "-m", "pip", "install", "--upgrade", install_source()],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=external_tool_environment(),
        )
        if completed.returncode != 0:
            raise AgentReachRuntimeError(completed.stderr[-3000:] or "Failed to update Agent-Reach.")
        _write_runtime_manifest()
        return target_executable

    plan = install_plan()
    if dry_run:
        print("[dry-run] Agent-Reach standalone runtime target:")
        print(f"  {agent_reach_runtime_root()}")
        for command in plan:
            print("  " + " ".join(command))
        return target_executable

    agent_reach_runtime_root().mkdir(parents=True, exist_ok=True)
    if not target_python.exists():
        completed = subprocess.run(
            plan[0],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=external_tool_environment(),
        )
        if completed.returncode != 0:
            raise AgentReachRuntimeError(completed.stderr[-2000:] or "Failed to create Agent-Reach venv.")

    completed = subprocess.run(
        plan[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=external_tool_environment(),
    )
    if completed.returncode != 0:
        raise AgentReachRuntimeError(completed.stderr[-3000:] or "Failed to install Agent-Reach.")
    if not target_executable.exists():
        raise AgentReachRuntimeError(f"Agent-Reach installation completed without executable: {target_executable}")
    _write_runtime_manifest()
    return target_executable
