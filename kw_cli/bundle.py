"""Acquisition bundle helpers for the Knowledge Workflow CLI."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import run_context, source_gate
from .redaction import contains_unredacted_secret, redact_url, sanitize_data


SCHEMA_VERSION = 2
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
    "run_id",
    "attempt_id",
    "bundle_id",
    "analysis_target",
    "operation",
    "source_fingerprint",
}
V1_REQUIRED_MANIFEST_FIELDS = REQUIRED_MANIFEST_FIELDS - {
    "run_id",
    "attempt_id",
    "bundle_id",
    "analysis_target",
    "operation",
    "source_fingerprint",
}
REQUIRED_ARTIFACT_FIELDS = {
    "artifact_id",
    "path",
    "type",
    "source_class",
    "content_scope",
    "coverage",
    "run_id",
    "source_id",
    "bytes",
    "sha256",
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


def contained_artifact_path(bundle_root: Path, path_value: str) -> Path:
    if Path(path_value).is_absolute():
        raise BundleError(f"artifact path must be relative to bundle root: {path_value}")
    root = bundle_root.resolve()
    resolved = (root / path_value).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise BundleError(f"artifact path escapes bundle root: {path_value}") from exc
    return resolved


def artifact_entry(
    *,
    bundle_root: Path,
    path: Path,
    artifact_type: str,
    source_class: str,
    description: str = "",
    language: str = "unknown",
    created_by: str = "",
    content_scope: str = "",
    coverage: str = "",
    run_id: str = "",
    source_id: str = "",
) -> dict[str, Any]:
    bundle_root = bundle_root.resolve()
    path = path.resolve()
    try:
        rel_path = path.relative_to(bundle_root).as_posix()
    except ValueError as exc:
        raise BundleError(f"artifact is outside bundle root: {path}") from exc
    entry: dict[str, Any] = {
        "artifact_id": run_context.new_id("artifact"),
        "path": rel_path,
        "type": artifact_type,
        "source_class": source_class,
        "content_scope": content_scope or "unknown",
        "coverage": coverage or ("full" if source_class == "primary" else "partial" if source_class == "partial_primary" else "unknown"),
        "run_id": run_id,
        "source_id": source_id,
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
    run_id: str = "",
    attempt_id: str = "",
    bundle_id: str = "",
    analysis_target: str = "auto",
    operation: str = "auto",
    source_fingerprint: str = "",
) -> dict[str, Any]:
    if analysis_target == "auto" and any(
        isinstance(item, dict) and item.get("type") in {"transcript", "subtitle", "audio", "video"}
        for item in artifacts or []
    ):
        chosen_target = "video_content"
    else:
        chosen_target = source_gate.infer_analysis_target(platform, analysis_target)
    chosen_operation = source_gate.infer_operation(chosen_target, operation)
    chosen_run_id = run_id or run_context.new_id("run")
    chosen_attempt_id = attempt_id or run_context.new_id("attempt")
    chosen_bundle_id = bundle_id or run_context.new_id("bundle")
    chosen_source_id = source_id or "source"
    chosen_fingerprint = source_fingerprint or run_context.fingerprint(
        platform=platform,
        source_id=chosen_source_id,
        source_value=source_url or input_value,
    )
    normalized_artifacts: list[dict[str, Any]] = []
    for raw in artifacts or []:
        artifact = dict(raw)
        artifact.setdefault("artifact_id", run_context.new_id("artifact"))
        artifact["run_id"] = chosen_run_id
        artifact["source_id"] = chosen_source_id
        if not artifact.get("content_scope") or artifact.get("content_scope") == "unknown":
            artifact["content_scope"] = source_gate.infer_content_scope(str(artifact.get("type") or "unknown"), platform)
        artifact.setdefault(
            "coverage",
            "full" if artifact.get("source_class") == "primary" else "partial" if artifact.get("source_class") == "partial_primary" else "unknown",
        )
        normalized_artifacts.append(artifact)

    return sanitize_data({
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "input": input_value,
        "source_url": source_url,
        "source_id": chosen_source_id,
        "platform": platform,
        "acquisition_layer": acquisition_layer,
        "active_backend": active_backend or "",
        "status": status,
        "run_id": chosen_run_id,
        "attempt_id": chosen_attempt_id,
        "bundle_id": chosen_bundle_id,
        "analysis_target": chosen_target,
        "operation": chosen_operation,
        "source_fingerprint": chosen_fingerprint,
        "artifacts": normalized_artifacts,
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
    })


def manifest_path(project_root: Path) -> Path:
    return project_root / "00_acquisition" / "manifest.json"


def write_manifest(project_root: Path, manifest: dict[str, Any]) -> Path:
    path = manifest_path(project_root)
    write_json(path, sanitize_data(manifest))
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
        elif contains_unredacted_secret(value):
            errors.append("unredacted secret-like value is not allowed at: " + ".".join(path))
    return errors


def validate_manifest(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    bundle_root = path.parent
    errors: list[str] = []
    warnings: list[str] = []

    schema_version = manifest.get("schema_version")
    if schema_version == 1:
        required_fields = V1_REQUIRED_MANIFEST_FIELDS
        warnings.append("schema_version 1 is legacy and lacks run/scope integrity fields")
    elif schema_version == SCHEMA_VERSION:
        required_fields = REQUIRED_MANIFEST_FIELDS
    else:
        required_fields = REQUIRED_MANIFEST_FIELDS
        errors.append(f"unsupported schema_version: {schema_version!r}")

    missing = sorted(required_fields - set(manifest))
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

    if schema_version == SCHEMA_VERSION:
        if manifest.get("analysis_target") not in source_gate.ANALYSIS_TARGETS - {"auto"}:
            errors.append(f"invalid analysis_target: {manifest.get('analysis_target')!r}")
        if manifest.get("operation") not in source_gate.OPERATIONS - {"auto"}:
            errors.append(f"invalid operation: {manifest.get('operation')!r}")
        for field in ("run_id", "attempt_id", "bundle_id", "source_fingerprint"):
            if not isinstance(manifest.get(field), str) or not manifest.get(field):
                errors.append(f"{field} must be a non-empty string")

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
        try:
            artifact_path = contained_artifact_path(bundle_root, path_value)
        except BundleError as exc:
            errors.append(f"artifact {index} {exc}")
            continue
        if not artifact_path.is_file():
            errors.append(f"artifact {index} path does not exist: {path_value}")
            continue
        if schema_version == SCHEMA_VERSION:
            for field in sorted(REQUIRED_ARTIFACT_FIELDS - set(artifact)):
                errors.append(f"artifact {index} missing required field: {field}")
            if artifact.get("run_id") != manifest.get("run_id"):
                errors.append(f"artifact {index} run_id does not match manifest")
            if artifact.get("source_id") != manifest.get("source_id"):
                errors.append(f"artifact {index} source_id does not match manifest")
            if artifact.get("content_scope") not in source_gate.CONTENT_SCOPES:
                errors.append(f"artifact {index} invalid content_scope: {artifact.get('content_scope')!r}")
            if artifact.get("coverage") not in {"full", "partial", "unknown"}:
                errors.append(f"artifact {index} invalid coverage: {artifact.get('coverage')!r}")
            expected_bytes = artifact.get("bytes")
            if not isinstance(expected_bytes, int) or expected_bytes < 0:
                errors.append(f"artifact {index} bytes must be a non-negative integer")
            elif artifact_path.stat().st_size != expected_bytes:
                errors.append(f"artifact {index} byte size mismatch: {path_value}")
            expected_sha = artifact.get("sha256")
            if not isinstance(expected_sha, str) or len(expected_sha) != 64:
                errors.append(f"artifact {index} sha256 must be a 64-character digest")
            elif sha256_file(artifact_path) != expected_sha:
                errors.append(f"artifact {index} sha256 mismatch: {path_value}")
        if status == "metadata_only" and source_class in {"primary", "partial_primary"}:
            errors.append("metadata_only bundle cannot contain primary or partial_primary artifacts")
        if artifact_type == "metadata" and source_class in {"primary", "partial_primary"}:
            errors.append("metadata artifact cannot be primary material")

    primary_classes = {
        str(item.get("source_class"))
        for item in artifacts
        if isinstance(item, dict) and item.get("source_class") in {"primary", "partial_primary"}
    }
    if status == "material_acquired" and "primary" not in primary_classes:
        errors.append("material_acquired bundle must contain a primary artifact")
    if status == "partial_material_acquired" and not primary_classes:
        errors.append("partial_material_acquired bundle must contain primary or partial_primary material")
    if status in {"metadata_only", "secondary_only", "blocked", "failed", "unsupported"} and primary_classes:
        errors.append(f"{status} bundle cannot contain primary or partial_primary artifacts")

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
    analysis_target: str = "auto",
    operation: str = "auto",
    resume: bool = False,
) -> Path:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise BundleError(f"local input does not exist: {input_path}")

    project_root = project_root.resolve()
    source_id = input_path.stem
    source_identity_value = f"{input_path}\nsha256={sha256_file(input_path)}"
    chosen_target = source_gate.infer_analysis_target("local_file", analysis_target)
    chosen_operation = source_gate.infer_operation(chosen_target, operation)
    try:
        identity = run_context.ensure_run_identity(
            project_root=project_root,
            platform="local_file",
            source_id=source_id,
            source_value=source_identity_value,
            analysis_target=chosen_target,
            operation=chosen_operation,
            resume=resume,
        )
        attempt = run_context.prepare_attempt(project_root=project_root, identity=identity)
    except run_context.RunContextError as exc:
        raise BundleError(str(exc)) from exc

    work_root = attempt.work_project_root
    bundle_root = work_root / "00_acquisition"
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
        content_scope=source_gate.infer_content_scope(artifact_type, "local_file"),
        run_id=attempt.run_id,
        source_id=source_id,
    )
    status = "material_acquired" if chosen_source_class == "primary" else "partial_material_acquired"
    manifest = make_manifest(
        project_root=work_root,
        input_value=str(input_path),
        source_id=source_id,
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
        run_id=attempt.run_id,
        attempt_id=attempt.attempt_id,
        analysis_target=chosen_target,
        operation=chosen_operation,
        source_fingerprint=str(identity["source_fingerprint"]),
    )
    write_text(logs_root / "acquisition_notes.md", "# Local Bundle\n\nUser-provided local material was copied into the acquisition bundle.\n")
    staged_manifest = write_manifest(work_root, manifest)
    validation = validate_manifest(staged_manifest)
    if not validation["valid"]:
        run_context.abandon_attempt(attempt)
        raise BundleError("local acquisition bundle failed validation: " + "; ".join(validation["errors"]))
    try:
        return run_context.promote_attempt(attempt)
    except run_context.RunContextError as exc:
        run_context.abandon_attempt(attempt)
        raise BundleError(str(exc)) from exc


def _build_export_bundle(
    *,
    input_path: Path,
    source_url: str,
    platform: str,
    project_root: Path,
    language: str = "unknown",
    source_class: str = "primary",
    analysis_target: str = "auto",
    operation: str = "auto",
    content_scope: str = "",
    browser_host: str = "",
    credentialed_session: bool = False,
    export_name: str,
    acquisition_layer: str,
    active_backend: str,
    handoff: str,
    artifact_description: str,
    created_by: str,
    browser_session_used: bool,
    contains_user_private_data: bool,
    limit: str,
    resume: bool = False,
) -> Path:
    """Turn a local upstream export into a Bundle v2 artifact."""
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise BundleError(f"{export_name} export does not exist: {input_path}")
    if not source_url.startswith(("http://", "https://")):
        raise BundleError(f"{export_name} export source URL must be http:// or https://")
    if source_class not in {"primary", "partial_primary"}:
        raise BundleError(f"{export_name} export source class must be primary or partial_primary")
    chosen_browser_host = str(browser_host or "").strip().lower()
    if chosen_browser_host not in {"", "edge", "chrome"}:
        raise BundleError(f"{export_name} export host must be edge or chrome when supplied")

    chosen_target = source_gate.infer_analysis_target(platform, analysis_target)
    chosen_operation = source_gate.infer_operation(chosen_target, operation)
    if chosen_target == "video_content":
        artifact_type = artifact_type_for(input_path)
        if artifact_type not in {"transcript", "subtitle", "audio", "video"}:
            raise BundleError("video export must be transcript, subtitle, audio, or video material")
    else:
        if input_path.suffix.lower() not in {".txt", ".md"}:
            raise BundleError("page export must be a text or Markdown file")
        artifact_type = "page_markdown" if input_path.suffix.lower() == ".md" else "page_text"

    inferred_scope = source_gate.infer_content_scope(artifact_type, platform)
    chosen_scope = content_scope or inferred_scope
    if chosen_scope not in source_gate.CONTENT_SCOPES:
        raise BundleError(f"unsupported export content scope: {chosen_scope}")
    if content_scope and chosen_scope != inferred_scope:
        raise BundleError(
            f"export type {artifact_type!r} requires content scope {inferred_scope!r}, "
            f"not {chosen_scope!r}"
        )
    required_scopes = source_gate.TARGET_PRIMARY_SCOPES.get(chosen_target, set())
    raw_video_media = chosen_target == "video_content" and chosen_scope == "media"
    if required_scopes and chosen_scope not in required_scopes and not raw_video_media:
        raise BundleError(
            f"export scope {chosen_scope!r} cannot satisfy target {chosen_target!r}; "
            f"expected one of {sorted(required_scopes)}"
        )

    project_root = project_root.resolve()
    stable_source_url = redact_url(source_url)
    source_id = f"{platform}-{hashlib.sha256(stable_source_url.encode('utf-8')).hexdigest()[:16]}"
    source_identity_value = f"{stable_source_url}\nartifact_sha256={sha256_file(input_path)}"
    try:
        identity = run_context.ensure_run_identity(
            project_root=project_root,
            platform=platform,
            source_id=source_id,
            source_value=source_identity_value,
            analysis_target=chosen_target,
            operation=chosen_operation,
            resume=resume,
        )
        attempt = run_context.prepare_attempt(project_root=project_root, identity=identity)
    except run_context.RunContextError as exc:
        raise BundleError(str(exc)) from exc

    work_root = attempt.work_project_root
    bundle_root = work_root / "00_acquisition"
    artifacts_root = bundle_root / "artifacts"
    logs_root = bundle_root / "logs"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)
    target = artifacts_root / input_path.name
    shutil.copy2(input_path, target)

    entry = artifact_entry(
        bundle_root=bundle_root,
        path=target,
        artifact_type=artifact_type,
        source_class=source_class,
        language=language,
        description=artifact_description,
        created_by=created_by,
        content_scope=chosen_scope,
        coverage="full" if source_class == "primary" else "partial",
        run_id=attempt.run_id,
        source_id=source_id,
    )
    status = "material_acquired" if source_class == "primary" else "partial_material_acquired"
    manifest = make_manifest(
        project_root=work_root,
        input_value=source_url,
        source_url=source_url,
        source_id=source_id,
        platform=platform,
        acquisition_layer=acquisition_layer,
        active_backend=active_backend,
        status=status,
        artifacts=[entry],
        metadata={
            "artifact_type": artifact_type,
            "handoff": handoff,
            "browser_host": chosen_browser_host or "unknown",
            "browser_host_identity": "declared" if chosen_browser_host else "not_provided",
        },
        privacy={
            "cookies_used": credentialed_session,
            "browser_session_used": browser_session_used,
            "secrets_redacted": True,
            "contains_user_private_data": contains_user_private_data,
        },
        limits=[limit],
        failures=[],
        next_action="ingest_bundle",
        run_id=attempt.run_id,
        attempt_id=attempt.attempt_id,
        analysis_target=chosen_target,
        operation=chosen_operation,
        source_fingerprint=str(identity["source_fingerprint"]),
    )
    write_text(
        logs_root / "acquisition_notes.md",
        f"# {export_name} Export Bundle\n\n"
        "The local artifact was exported from user-authorized upstream material. "
        "No cookie values, session tokens, or restricted asset URLs were persisted.\n",
    )
    staged_manifest = write_manifest(work_root, manifest)
    validation = validate_manifest(staged_manifest)
    if not validation["valid"]:
        run_context.abandon_attempt(attempt)
        raise BundleError(f"{export_name} export bundle failed validation: " + "; ".join(validation["errors"]))
    try:
        return run_context.promote_attempt(attempt)
    except run_context.RunContextError as exc:
        run_context.abandon_attempt(attempt)
        raise BundleError(str(exc)) from exc


def build_browser_export_bundle(
    *,
    input_path: Path,
    source_url: str,
    platform: str,
    project_root: Path,
    language: str = "unknown",
    source_class: str = "primary",
    analysis_target: str = "auto",
    operation: str = "auto",
    content_scope: str = "",
    browser_host: str = "",
    resume: bool = False,
) -> Path:
    """Turn an authorized browser-visible export into a Bundle v2 artifact."""
    return _build_export_bundle(
        input_path=input_path,
        source_url=source_url,
        platform=platform,
        project_root=project_root,
        language=language,
        source_class=source_class,
        analysis_target=analysis_target,
        operation=operation,
        content_scope=content_scope,
        browser_host=browser_host,
        credentialed_session=False,
        export_name="Browser",
        acquisition_layer="browser_export",
        active_backend="authorized_browser_session",
        handoff="browser_visible_export",
        artifact_description="Material visibly available through the user's authorized browser session and exported locally.",
        created_by="build_browser_export_bundle",
        browser_session_used=True,
        contains_user_private_data=True,
        limit="The workflow validates the exported artifact; it does not infer completeness from page playability alone.",
        resume=resume,
    )


def build_agent_reach_export_bundle(
    *,
    input_path: Path,
    source_url: str,
    platform: str,
    project_root: Path,
    language: str = "unknown",
    source_class: str = "primary",
    analysis_target: str = "auto",
    operation: str = "auto",
    content_scope: str = "",
    browser_host: str = "",
    credentialed_session: bool = False,
    resume: bool = False,
) -> Path:
    """Import task-primary material acquired by an Agent-Reach native route."""
    return _build_export_bundle(
        input_path=input_path,
        source_url=source_url,
        platform=platform,
        project_root=project_root,
        language=language,
        source_class=source_class,
        analysis_target=analysis_target,
        operation=operation,
        content_scope=content_scope,
        browser_host=browser_host,
        credentialed_session=credentialed_session,
        export_name="Agent-Reach",
        acquisition_layer="agent_reach_export",
        active_backend="agent-reach_native_export",
        handoff="agent_reach_native_export",
        artifact_description="Task-primary material acquired through an Agent-Reach native route and exported locally.",
        created_by="build_agent_reach_export_bundle",
        browser_session_used=bool(browser_host),
        contains_user_private_data=credentialed_session,
        limit="The workflow validates the exported primary material; it does not treat raw search results or metadata as source evidence.",
        resume=resume,
    )


def cli_validate(manifest: Path) -> int:
    result = validate_manifest(manifest)
    print(stable_json({key: value for key, value in result.items() if key != "manifest"}), end="")
    return 0 if result["valid"] else 1
