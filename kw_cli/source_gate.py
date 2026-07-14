"""Analysis-target and artifact-scope rules for the source gate."""

from __future__ import annotations

from typing import Any


ANALYSIS_TARGETS = {
    "auto",
    "video_content",
    "social_post",
    "web_article",
    "repository",
    "search_triage",
}
OPERATIONS = {"auto", "read", "search", "extract_transcript"}
CONTENT_SCOPES = {
    "article_body",
    "comments",
    "media",
    "metadata",
    "repository_document",
    "search_result",
    "social_post_text",
    "unknown",
    "video_transcript",
}

VIDEO_PLATFORMS = {"youtube", "bilibili", "xiaoyuzhou", "local_file"}
SOCIAL_PLATFORMS = {"x", "twitter", "xiaohongshu", "reddit", "facebook", "instagram", "v2ex", "xueqiu"}
REPOSITORY_PLATFORMS = {"github"}
SEARCH_PLATFORMS = {"search", "exa_search"}
UPSTREAM_AGENT_REACH_PLATFORMS = {
    "web",
    "youtube",
    "rss",
    "exa_search",
    "github",
    "twitter",
    "x",
    "bilibili",
    "reddit",
    "facebook",
    "instagram",
    "xiaohongshu",
    "linkedin",
    "xiaoyuzhou",
    "v2ex",
    "xueqiu",
}

TARGET_PRIMARY_SCOPES = {
    "video_content": {"video_transcript"},
    "social_post": {"social_post_text"},
    "web_article": {"article_body"},
    "repository": {"repository_document"},
    "search_triage": set(),
}


def infer_analysis_target(platform: str, requested: str = "auto") -> str:
    if requested and requested != "auto":
        if requested not in ANALYSIS_TARGETS:
            raise ValueError(f"unsupported analysis target: {requested}")
        return requested
    if platform in VIDEO_PLATFORMS:
        return "video_content"
    if platform in SOCIAL_PLATFORMS:
        return "social_post"
    if platform in REPOSITORY_PLATFORMS:
        return "repository"
    if platform in SEARCH_PLATFORMS:
        return "search_triage"
    return "web_article"


def infer_operation(analysis_target: str, requested: str = "auto") -> str:
    if requested and requested != "auto":
        if requested not in OPERATIONS:
            raise ValueError(f"unsupported operation: {requested}")
        return requested
    if analysis_target == "video_content":
        return "extract_transcript"
    if analysis_target == "search_triage":
        return "search"
    return "read"


def infer_content_scope(artifact_type: str, platform: str) -> str:
    if artifact_type in {"transcript", "subtitle"}:
        return "video_transcript"
    if artifact_type in {"audio", "video"}:
        return "media"
    if artifact_type == "metadata":
        return "metadata"
    if artifact_type == "search_result":
        return "search_result"
    if artifact_type == "comments":
        return "comments"
    if artifact_type in {"page_text", "page_markdown"}:
        if platform in SOCIAL_PLATFORMS:
            return "social_post_text"
        if platform in REPOSITORY_PLATFORMS:
            return "repository_document"
        return "article_body"
    return "unknown"


def matching_primary_artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    target = str(manifest.get("analysis_target") or "auto")
    allowed_scopes = TARGET_PRIMARY_SCOPES.get(target, set())
    return [
        artifact
        for artifact in manifest.get("artifacts") or []
        if isinstance(artifact, dict)
        and artifact.get("source_class") == "primary"
        and artifact.get("content_scope") in allowed_scopes
    ]


def matching_partial_artifacts(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    target = str(manifest.get("analysis_target") or "auto")
    allowed_scopes = TARGET_PRIMARY_SCOPES.get(target, set())
    return [
        artifact
        for artifact in manifest.get("artifacts") or []
        if isinstance(artifact, dict)
        and artifact.get("source_class") in {"partial_primary", "primary"}
        and artifact.get("content_scope") in allowed_scopes
    ]


def allowed_report_type(source_status: str, analysis_target: str) -> str:
    if source_status == "source_confirmed":
        return "full_video_analysis_pack" if analysis_target == "video_content" else "full_source_analysis_pack"
    if source_status == "source_partial":
        return "partial_video_analysis_pack" if analysis_target == "video_content" else "partial_source_analysis_pack"
    if source_status == "source_blocked":
        return "blocked_source_report"
    if source_status == "source_failed":
        return "failed_source_report"
    return "degraded_source_report"


def scope_summary(manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    target = str(manifest.get("analysis_target") or "auto")
    required = TARGET_PRIMARY_SCOPES.get(target, set())
    available = {
        str(item.get("content_scope"))
        for item in manifest.get("artifacts") or []
        if isinstance(item, dict) and item.get("content_scope")
    }
    return sorted(required & available), sorted(required - available)
