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

Canonical v1 status records preserve the compatibility `source_status` enum
and add two orthogonal decisions:

- `scope_status`: `matched`, `partial_match`, `target_mismatch`,
  `pending_derivation`, or `not_evaluated`;
- `pipeline_decision`: `continue_full`, `continue_partial`, or
  `stop_before_audit`.

Wrong-scope primary material is `degraded_report_only` plus
`target_mismatch` and `stop_before_audit`. It may receive a degraded mismatch
explanation, but never a normal report. Local audio/video awaiting ASR is
`pending_derivation`, not a target mismatch.

Always write `source_status.json` and `gate_receipt.json`, including for
blocked and failed outcomes. Preserve run, attempt, bundle, source,
fingerprint, target, operation, approved/uncovered scopes, manifest hash,
permission flags, reason, and next step.

The public `kw.py ingest/run/resume` path is the final status authority.
Internal normalizer and ASR scripts may produce provisional stage state, but
the Source Gate must rebuild, atomically publish, and validate the canonical
status before writing the gate receipt.

The gate receipt binds the source-status hash to the manifest hash. An
ASR-derived transcript also records its path, byte count, and SHA-256 in the
receipt. Only a current receipt and `source_confirmed` or `source_partial` can
enter audit.
