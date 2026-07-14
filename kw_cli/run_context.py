"""Immutable run identity and acquisition-attempt staging helpers."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .redaction import redact_text, sanitize_data


class RunContextError(Exception):
    """Raised when a project root is reused for a different source or target."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def fingerprint(*, platform: str, source_id: str, source_value: str) -> str:
    stable = "\n".join([platform, source_id, redact_text(source_value)]).encode("utf-8")
    return hashlib.sha256(stable).hexdigest()


def run_identity_path(project_root: Path) -> Path:
    return project_root / "logs" / "run_identity.json"


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(sanitize_data(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def ensure_run_identity(
    *,
    project_root: Path,
    platform: str,
    source_id: str,
    source_value: str,
    analysis_target: str,
    operation: str,
    resume: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    path = run_identity_path(project_root)
    current_fingerprint = fingerprint(platform=platform, source_id=source_id, source_value=source_value)
    existing = read_json(path)
    if existing:
        if not resume:
            raise RunContextError(
                f"project root already belongs to run {existing.get('run_id')}; use --resume only for the same source and target"
            )
        if existing.get("source_fingerprint") != current_fingerprint:
            raise RunContextError("--resume source does not match the existing project run")
        if existing.get("analysis_target") != analysis_target:
            raise RunContextError("--resume analysis target does not match the existing project run")
        if existing.get("operation") != operation:
            raise RunContextError("--resume acquisition operation does not match the existing project run")
        return existing

    identity = {
        "schema_version": 1,
        "run_id": new_id("run"),
        "created_at": utc_now(),
        "platform": platform,
        "source_id": source_id,
        "source_fingerprint": current_fingerprint,
        "analysis_target": analysis_target,
        "operation": operation,
        "input": redact_text(source_value),
    }
    write_json(path, identity)
    return identity


@dataclass(frozen=True)
class AcquisitionAttempt:
    project_root: Path
    work_project_root: Path
    run_id: str
    attempt_id: str
    analysis_target: str
    operation: str


def prepare_attempt(*, project_root: Path, identity: dict[str, Any]) -> AcquisitionAttempt:
    attempt_id = new_id("attempt")
    work_project_root = project_root.resolve() / ".kw_staging" / attempt_id
    work_project_root.mkdir(parents=True, exist_ok=False)
    return AcquisitionAttempt(
        project_root=project_root.resolve(),
        work_project_root=work_project_root,
        run_id=str(identity["run_id"]),
        attempt_id=attempt_id,
        analysis_target=str(identity["analysis_target"]),
        operation=str(identity["operation"]),
    )


def promote_attempt(attempt: AcquisitionAttempt) -> Path:
    staged = attempt.work_project_root / "00_acquisition"
    manifest = staged / "manifest.json"
    if not manifest.is_file():
        raise RunContextError("acquisition attempt did not produce manifest.json")

    target = attempt.project_root / "00_acquisition"
    if target.exists():
        existing = read_json(target / "manifest.json")
        archive_id = str(existing.get("attempt_id") or existing.get("bundle_id") or new_id("legacy"))
        archive = attempt.project_root / "acquisition_history" / archive_id
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            archive = archive.with_name(archive.name + "-" + uuid.uuid4().hex[:8])
        target.replace(archive)
    staged.replace(target)
    shutil.rmtree(attempt.work_project_root, ignore_errors=True)
    staging_root = attempt.project_root / ".kw_staging"
    try:
        staging_root.rmdir()
    except OSError:
        pass
    return target / "manifest.json"


def abandon_attempt(attempt: AcquisitionAttempt) -> None:
    shutil.rmtree(attempt.work_project_root, ignore_errors=True)
