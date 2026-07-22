#!/usr/bin/env python
"""Prove that acquisition capability discovery has no intermediary runtime dependency."""

from __future__ import annotations

import subprocess
from pathlib import Path

from kw_cli import acquisition_providers, main as kw_main


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TOKEN = "agent" + "-reach"
FORBIDDEN_IMPORT = "agent" + "_reach"


def assert_true(name: str, condition: bool, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def test_native_probe_registry(failures: list[str]) -> None:
    calls: list[list[str]] = []
    available = {name: name for name in ("curl", "yt-dlp", "gh", "bili", "twitter", "mcporter")}

    def path_lookup(name: str) -> str | None:
        return available.get(name)

    def runner(command: list[str], **_kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = "exa configured" if command and command[0] == "mcporter" else "fixture version"
        return subprocess.CompletedProcess(command, 0, stdout, "")

    report = acquisition_providers.build_capability_report(path_lookup=path_lookup, runner=runner)
    metadata = acquisition_providers.runtime_metadata(path_lookup=path_lookup)
    assert_true("provider report is project-owned", report.get("owner") == "knowledge-workflow", failures)
    assert_true("provider runtime has no intermediary dependency", metadata.get("runtime_dependency") == "none", failures)
    assert_true("native providers are probed directly", report.get("youtube", {}).get("active_backend") == "yt-dlp", failures)
    assert_true("all 15 channels are reported", len([name for name in acquisition_providers.CHANNEL_CATALOG if name in report]) == 15, failures)
    assert_true("no forbidden runtime command is probed", all(FORBIDDEN_TOKEN not in " ".join(command).lower() for command in calls), failures)


def test_active_python_has_no_forbidden_dependency(failures: list[str]) -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted((REPO_ROOT / "kw_cli").glob("*.py"))
    ).lower()
    assert_true("active Python contains no intermediary command", FORBIDDEN_TOKEN not in source, failures)
    assert_true("active Python contains no intermediary import", FORBIDDEN_IMPORT not in source, failures)
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert_true("CLI and package versions agree", f'version = "{kw_main.PROJECT_VERSION}"' in pyproject, failures)
    payload = kw_main.version_payload()
    assert_true("version reports active runtime module", str(payload.get("runtime_module") or "").endswith("kw_cli\\main.py") or str(payload.get("runtime_module") or "").endswith("kw_cli/main.py"), failures)


def main() -> int:
    failures: list[str] = []
    test_native_probe_registry(failures)
    test_active_python_has_no_forbidden_dependency(failures)
    if failures:
        print("FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("test_native_provider_independence passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
