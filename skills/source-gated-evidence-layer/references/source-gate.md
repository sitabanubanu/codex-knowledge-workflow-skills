# Target and Scope Source Gate

Validate the bundle before reading artifacts.

## Target Matrix

| Analysis target | Required primary scope |
| --- | --- |
| `video_content` | `video_transcript` |
| `social_post` | `social_post_text` |
| `web_article` | `article_body` |
| `repository` | `repository_document` |
| `search_triage` | no full-report scope |

An artifact must be `primary` or `partial_primary`, and its `content_scope`
must satisfy the target. Acquisition success alone is insufficient.

## Status Mapping

| Bundle result | Source result |
| --- | --- |
| `material_acquired` plus matching primary scope | `source_confirmed` |
| `partial_material_acquired` plus matching partial scope | `source_partial` |
| primary material with the wrong scope | `degraded_report_only` |
| `metadata_only` | `secondary_only` |
| `secondary_only` | `secondary_only` |
| `blocked` | `source_blocked` |
| `failed` | `source_failed` |
| `unsupported` | `degraded_report_only` |

Always write `source_status.json` and `gate_receipt.json`, including for
blocked and failed outcomes. Preserve run, attempt, bundle, source,
fingerprint, target, operation, approved/uncovered scopes, manifest hash,
permission flags, reason, and next step.

The gate receipt binds the source-status hash to the manifest hash. An
ASR-derived transcript also records its path, byte count, and SHA-256 in the
receipt. Only a current receipt and `source_confirmed` or `source_partial` can
enter audit.
