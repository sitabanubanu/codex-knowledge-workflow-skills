"""Acquisition bundle helpers for the Knowledge Workflow CLI."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
STATUS_VALUES = {
    "material_acquired",
    "partial_material_acquired",
    "metadata_only",
    "secondary_only",
    "blocked",
    "failed",
    "unsupported",
}
ARTIFACT_TYPES = {
    "transcript",
    "subtitle",
    "page_markdown",
    "page_text",
    "audio",
    "video",
    "metadata",
    "search_result",
    "comments",
    "unknown",
}
SOURCE_CLASSES = {"primary", "partial_primary", "secondary", "metadata_only", "unknown"}
REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "created_at",
    "input",
    "source_url",
    "source_id",
    "platform",
    "acquisition_layer",
    "active_backend",
    "status",
    "artifacts",
    "metadata",
    "privacy",
    "limits",
    "failures",
    "next_action",
}
REQUIRED_PRIVACY_FIELDS = {
    "cookies_used",
    "browser_session_used",
    "secrets_redacted",
    "contains_user_private_data",
}
SECRET_KEY_MARKERS = {
    "authorization",
    "auth_header",
    "cookie",
    "cookies",
    "cookie_header",
    "cookie_value",
    "secret",
    "session",
    "token",
}
ALLOWED_SECRET_LIKE_PATHS = {
    ("privacy", "browser_session_used"),
    ("privacy", "cookies_used"),
    ("privacy", "secrets_redacted"),
}


class BundleError(Exception):
    """Raised when acquisition bundle handling fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(payload), encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise BundleError(f"cannot read manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BundleError(f"manifest is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise BundleError("manifest root must be an object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".srt", ".vtt", ".json3"}:
        return "subtitle"
    if suffix in {".txt", ".md", ".jsonl", ".json"}:
        return "transcript"
    if suffix in {".mp3", ".m4a", ".wav", ".opus"}:
        return "audio"
    if suffix in {".mp4", ".webm", ".mov", ".mkv"}:
        return "video"
    return "unknown"


def default_source_class(artifact_type: str) -> str:
    if artifact_type in {"transcript", "subtitle"}:
        return "primary"
    if artifact_type in {"audio", "video"}:
        return "primary"
    if artifact_type == "metadata":
        return "metadata_only"
    return "unknown"


def normalize_artifact_path(bundle_root: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return bundle_root / path


def artifact_entry(
    *,
    bundle_root: Path,
    path: Path,
    artifact_type: str,
    source_class: str,
    description: str = "",
    language: str = "unknown",
    created_by: str = "",
) -> dict[str, Any]:
    rel_path = path.relative_to(bundle_root).as_posix()
    entry: dict[str, Any] = {
        "path": rel_path,
        "type": artifact_type,
        "source_class": source_class,
        "description": description,
        "language": language,
        "created_by": created_by,
    }
    if path.is_file():
        entry["bytes"] = path.stat().st_size
        entry["sha256"] = sha256_file(path)
    return entry


def make_manifest(
    *,
    project_root: Path,
    input_value: str,
    source_url: str = "",
    source_id: str = "",
    platform: str = "unknown",
    acquisition_layer: str = "agent-reach",
    active_backend: str | None = None,
    status: str,
    artifacts: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    privacy: dict[str, Any] | None = None,
    limits: list[str] | None = None,
    failures: list[dict[str, Any]] | None = None,
    next_action: str = "",
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "input": input_value,
        "source_url": source_url,
        "source_id": source_id,
        "platform": platform,
        "acquisition_layer": acquisition_layer,
        "active_backend": active_backend or "",
        "status": status,
        "artifacts": artifacts or [],
        "metadata": metadata or {},
        "privacy": {
            "cookies_used": False,
            "browser_session_used": False,
            "secrets_redacted": True,
            "contains_user_private_data": False,
            **(privacy or {}),
        },
        "limits": limits or [],
        "failures": failures or [],
        "next_action": next_action,
    }


def manifest_path(project_root: Path) -> Path:
    return project_root / "00_acquisition" / "manifest.json"


def write_manifest(project_root: Path, manifest: dict[str, Any]) -> Path:
    path = manifest_path(project_root)
    write_json(path, manifest)
    return path


def _contains_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker == lowered or marker in lowered for marker in SECRET_KEY_MARKERS)


def _scan_secret_fields(value: Any, path: tuple[str, ...] = ()) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, str(key))
            if child_path not in ALLOWED_SECRET_LIKE_PATHS and _contains_secret_key(str(key)):
                errors.append("secret-like field is not allowed: " + ".".join(child_path))
            errors.extend(_scan_secret_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_scan_secret_fields(child, (*path, str(index))))
    elif isinstance(value, str):
        lowered = value.lower()
        if "authorization:" in lowered or "cookie:" in lowered or "set-cookie:" in lowered:
            errors.append("secret-like literal is not allowed at: " + ".".join(path))
    return errors


def validate_manifest(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    bundle_root = path.parent
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    errors.extend(f"missing required field: {field}" for field in missing)

    status = manifest.get("status")
    if status not in STATUS_VALUES:
        errors.append(f"invalid status: {status!r}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be a list")
        artifacts = []

    privacy = manifest.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object")
        privacy = {}
    else:
        for field in sorted(REQUIRED_PRIVACY_FIELDS - set(privacy)):
            errors.append(f"missing privacy field: {field}")
        if privacy.get("secrets_redacted") is not True:
            errors.append("privacy.secrets_redacted must be true")

    errors.extend(_scan_secret_fields(manifest))

    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} must be an object")
            continue
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"artifact {index} missing path")
            continue
        artifact_type = artifact.get("type")
        source_class = artifact.get("source_class")
        if artifact_type not in ARTIFACT_TYPES:
            errors.append(f"artifact {index} invalid type: {artifact_type!r}")
        if source_class not in SOURCE_CLASSES:
            errors.append(f"artifact {index} invalid source_class: {source_class!r}")
        artifact_path = normalize_artifact_path(bundle_root, path_value)
        if not artifact_path.is_file():
            errors.append(f"artifact {index} path does not exist: {path_value}")
        if status == "metadata_only" and source_class in {"primary", "partial_primary"}:
            errors.append("metadata_only bundle cannot contain primary or partial_primary artifacts")
        if artifact_type == "metadata" and source_class in {"primary", "partial_primary"}:
            errors.append("metadata artifact cannot be primary material")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest,
        "manifest_path": str(path),
    }


def build_local_bundle(
    *,
    input_path: Path,
    project_root: Path,
    language: str = "unknown",
    source_class: str | None = None,
) -> Path:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise BundleError(f"local input does not exist: {input_path}")

    project_root = project_root.resolve()
    bundle_root = project_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    logs_root = bundle_root / "logs"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)

    target = artifacts_root / input_path.name
    if input_path != target:
        shutil.copy2(input_path, target)

    artifact_type = artifact_type_for(target)
    chosen_source_class = source_class or default_source_class(artifact_type)
    entry = artifact_entry(
        bundle_root=bundle_root,
        path=target,
        artifact_type=artifact_type,
        source_class=chosen_source_class,
        language=language,
        description="User-provided local material.",
        created_by="build_local_bundle",
    )
    status = "material_acquired" if chosen_source_class == "primary" else "partial_material_acquired"
    manifest = make_manifest(
        project_root=project_root,
        input_value=str(input_path),
        source_id=input_path.stem,
        platform="local_file",
        acquisition_layer="local_file",
        active_backend="local_copy",
        status=status,
        artifacts=[entry],
        metadata={"original_path": str(input_path), "artifact_type": artifact_type},
        privacy={
            "cookies_used": False,
            "browser_session_used": False,
            "secrets_redacted": True,
            "contains_user_private_data": True,
        },
        limits=[],
        failures=[],
        next_action="ingest_bundle",
    )
    write_text(logs_root / "acquisition_notes.md", "# Local Bundle\n\nUser-provided local material was copied into the acquisition bundle.\n")
    return write_manifest(project_root, manifest)


def cli_validate(manifest: Path) -> int:
    result = validate_manifest(manifest)
    print(stable_json({key: value for key, value in result.items() if key != "manifest"}), end="")
    return 0 if result["valid"] else 1
