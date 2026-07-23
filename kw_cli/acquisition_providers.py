"""Project-owned capability probes for native acquisition providers."""

from __future__ import annotations

import glob
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


OPENCLI_EXTENSION_ID = "ildkmabpimmkaediidaifkhjpohdnifk"
PathLookup = Callable[[str], str | None]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

CHANNEL_CATALOG: dict[str, tuple[str, str]] = {
    "web": ("Public web pages", "native_adapter"),
    "youtube": ("YouTube metadata, subtitles, audio, and transcripts", "native_adapter"),
    "rss": ("RSS and Atom feeds", "external_export"),
    "exa_search": ("Web search", "native_adapter"),
    "github": ("Repositories and code", "native_adapter"),
    "twitter": ("Twitter/X posts", "native_adapter_or_external_export"),
    "bilibili": ("Bilibili detail, audio, and subtitles", "native_adapter_or_external_export"),
    "xiaohongshu": ("Xiaohongshu notes and comments", "native_adapter_or_external_export"),
    "reddit": ("Reddit posts and comments", "external_export"),
    "facebook": ("Facebook posts and pages", "external_export"),
    "instagram": ("Instagram profiles and posts", "external_export"),
    "linkedin": ("LinkedIn profiles, companies, and jobs", "external_export"),
    "xiaoyuzhou": ("Xiaoyuzhou podcast material", "external_export"),
    "v2ex": ("V2EX topics and replies", "external_export"),
    "xueqiu": ("Xueqiu market and community material", "external_export"),
}


def external_tool_environment() -> dict[str, str]:
    """Keep optional provider caches outside agent-private environments."""

    root = Path(os.environ.get("KW_TOOLS_ROOT", Path.home() / "github-tools")).expanduser().resolve()
    environment = os.environ.copy()
    environment["UV_TOOL_DIR"] = str(root / "runtimes" / "uv-tools")
    environment["UV_CACHE_DIR"] = str(root / "cache" / "uv")
    environment["PIP_CACHE_DIR"] = str(root / "cache" / "pip")
    environment["PIPX_HOME"] = str(root / "runtimes" / "pipx")
    environment["PIPX_BIN_DIR"] = str(root / "bin")
    return environment


def _run_probe(
    command: list[str],
    *,
    timeout: int = 15,
    runner: CommandRunner = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    return runner(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        env=external_tool_environment(),
    )


def _command_output(
    command: list[str],
    *,
    runner: CommandRunner = subprocess.run,
    timeout: int = 15,
) -> tuple[int, str]:
    try:
        completed = _run_probe(command, timeout=timeout, runner=runner)
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)
    return completed.returncode, "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()


def _extension_roots(host: str) -> list[Path]:
    roots: list[Path] = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        if host == "chrome":
            roots.append(Path(local) / "Google" / "Chrome" / "User Data")
        if host == "edge":
            roots.append(Path(local) / "Microsoft" / "Edge" / "User Data")
    home = Path.home()
    if host == "chrome":
        roots.extend(
            [
                home / ".config" / "google-chrome",
                home / ".config" / "chromium",
                home / "Library" / "Application Support" / "Google" / "Chrome",
            ]
        )
    if host == "edge":
        roots.extend(
            [
                home / ".config" / "microsoft-edge",
                home / "Library" / "Application Support" / "Microsoft Edge",
            ]
        )
    return roots


def installed_opencli_hosts() -> list[str]:
    hosts: list[str] = []
    for host in ("edge", "chrome"):
        found = False
        for root in _extension_roots(host):
            pattern = str(root / "*" / "Extensions" / OPENCLI_EXTENSION_ID)
            if glob.glob(pattern):
                found = True
                break
        if found:
            hosts.append(host)
    return hosts


def _item(
    *,
    status: str,
    active_backend: str = "",
    backends: list[str] | None = None,
    message: str = "",
    provider_id: str = "",
    browser_hosts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "active_backend": active_backend,
        "backends": backends or [],
        "message": message,
        "provider_id": provider_id or active_backend.lower().replace(" ", "_").replace("-", "_"),
        "browser_hosts": browser_hosts or [],
    }


def _opencli_probe(path_lookup: PathLookup, runner: CommandRunner) -> dict[str, Any]:
    executable = path_lookup("opencli")
    if not executable:
        return _item(status="off", backends=["OpenCLI"], message="OpenCLI is not installed.")
    code, output = _command_output([executable, "daemon", "status"], runner=runner, timeout=5)
    lowered = output.lower()
    connected = "extension:" in lowered and "connected" in lowered and "disconnected" not in lowered
    hosts = installed_opencli_hosts()
    ready = code == 0 and (connected or bool(hosts))
    return _item(
        status="ok" if ready else "warn",
        active_backend="OpenCLI" if ready else "",
        backends=["OpenCLI"],
        message=(
            "OpenCLI and an authorized browser extension are ready."
            if ready
            else "OpenCLI is installed, but no connected or installed Edge/Chrome extension was detected."
        ),
        provider_id="opencli",
        browser_hosts=hosts,
    )


def _simple_command_probe(
    command_name: str,
    backend: str,
    args: list[str],
    *,
    path_lookup: PathLookup,
    runner: CommandRunner,
    timeout: int = 5,
) -> dict[str, Any]:
    executable = path_lookup(command_name)
    if not executable:
        return _item(status="off", backends=[backend], message=f"{command_name} is not installed.")
    code, output = _command_output([executable, *args], runner=runner, timeout=timeout)
    return _item(
        status="ok" if code == 0 else "warn",
        active_backend=backend if code == 0 else "",
        backends=[backend],
        message=(output[-500:] if output else f"{backend} is ready.") if code == 0 else (output[-500:] or f"{backend} probe returned {code}."),
        provider_id=command_name,
    )


def _first_ready(*items: dict[str, Any], backends: list[str]) -> dict[str, Any]:
    for item in items:
        if item.get("status") == "ok" and item.get("active_backend"):
            result = dict(item)
            result["backends"] = backends
            return result
    installed = next((item for item in items if item.get("status") in {"warn", "error"}), None)
    return _item(
        status=str((installed or {}).get("status") or "off"),
        backends=backends,
        message=str((installed or {}).get("message") or "No native provider is ready."),
        browser_hosts=list((installed or {}).get("browser_hosts") or []),
    )


def build_capability_report(
    *,
    path_lookup: PathLookup = shutil.which,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    """Return the provider health object consumed by route planning."""

    opencli = _opencli_probe(path_lookup, runner)
    curl = _simple_command_probe("curl", "Jina Reader", ["--version"], path_lookup=path_lookup, runner=runner)
    ytdlp = _simple_command_probe("yt-dlp", "yt-dlp", ["--version"], path_lookup=path_lookup, runner=runner)
    gh = _simple_command_probe("gh", "gh CLI", ["--version"], path_lookup=path_lookup, runner=runner)
    bili = _simple_command_probe("bili", "bili-cli", ["--version"], path_lookup=path_lookup, runner=runner)
    twitter = _simple_command_probe("twitter", "twitter-cli", ["status"], path_lookup=path_lookup, runner=runner)
    xhs = _simple_command_probe("xhs", "xhs-cli", ["--version"], path_lookup=path_lookup, runner=runner)
    mcporter = _simple_command_probe("mcporter", "mcporter", ["config", "list"], path_lookup=path_lookup, runner=runner)

    exa_ready = mcporter.get("status") == "ok" and "exa" in str(mcporter.get("message") or "").lower()
    exa = _item(
        status="ok" if exa_ready else ("warn" if path_lookup("mcporter") else "off"),
        active_backend="Exa via mcporter" if exa_ready else "",
        backends=["Exa via mcporter"],
        message="Exa MCP is configured." if exa_ready else "mcporter or its Exa configuration is unavailable.",
        provider_id="mcporter_exa",
    )
    xhs_mcp_ready = mcporter.get("status") == "ok" and "xiaohongshu" in str(mcporter.get("message") or "").lower()
    xhs_mcp = _item(
        status="ok" if xhs_mcp_ready else "off",
        active_backend="xiaohongshu-mcp" if xhs_mcp_ready else "",
        backends=["xiaohongshu-mcp"],
        message="Xiaohongshu MCP is configured." if xhs_mcp_ready else "Xiaohongshu MCP is not configured.",
        provider_id="xiaohongshu_mcp",
    )

    report: dict[str, Any] = {
        "schema_version": 1,
        "owner": "knowledge-workflow",
        "web": curl,
        "youtube": _first_ready(ytdlp, opencli, backends=["yt-dlp", "OpenCLI"]),
        "x_video": _first_ready(ytdlp, backends=["yt-dlp"]),
        "github": gh,
        "bilibili": _first_ready(bili, opencli, backends=["bili-cli", "OpenCLI"]),
        "twitter": _first_ready(twitter, opencli, backends=["twitter-cli", "OpenCLI"]),
        "xiaohongshu": _first_ready(opencli, xhs_mcp, xhs, backends=["OpenCLI", "xiaohongshu-mcp", "xhs-cli"]),
        "exa_search": exa,
    }
    for channel in CHANNEL_CATALOG:
        if channel not in report:
            capability, integration = CHANNEL_CATALOG[channel]
            report[channel] = _item(
                status="external_export",
                backends=[],
                message=f"{capability} can enter through the provider-neutral source import contract ({integration}).",
                provider_id="external_export",
            )
    return report


def runtime_metadata(*, path_lookup: PathLookup = shutil.which) -> dict[str, Any]:
    tools = ["curl", "yt-dlp", "opencli", "bili", "gh", "twitter", "xhs", "mcporter"]
    return {
        "schema_version": 1,
        "owner": "knowledge-workflow",
        "runtime_dependency": "none",
        "tools": {name: str(path_lookup(name) or "") for name in tools},
    }
