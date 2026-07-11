# Acquisition Bundle Protocol v2

`00_acquisition/manifest.json` is the only stable handoff between acquisition
and evidence judgment.

Agent-Reach gets material. Knowledge Workflow decides whether that material is
task-primary, auditable, and sufficient for a report.

## Layout

```text
<project>/
  logs/
    run_identity.json
  .kw_staging/                 # temporary; never a result
  acquisition_history/        # prior validated attempts
  run_history/                # prior downstream results
  00_acquisition/
    manifest.json
    artifacts/
    logs/
      agent_reach_doctor.json
      route_plan.json
      commands.jsonl
      acquisition_notes.md
```

An attempt writes to `.kw_staging/<attempt_id>/00_acquisition`. It is promoted
only after schema, path, byte-count, hash, privacy, and status validation pass.

## Manifest

Schema v2 requires these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `2`. |
| `created_at` | UTC creation timestamp. |
| `input` | Redacted URL, query, or local path. |
| `source_url` | Redacted canonical URL when applicable. |
| `source_id` | Platform-stable source identifier. |
| `platform` | `youtube`, `bilibili`, `x`, `xiaohongshu`, `web`, `github`, `search`, or `local_file`. |
| `acquisition_layer` | Upstream layer: `agent-reach`, `agent_reach_export`, `browser_export`, or `local_file`. |
| `active_backend` | Doctor-selected backend actually considered. |
| `status` | Acquisition result only; never a source-gate decision. |
| `run_id` | Immutable project-run identifier. |
| `attempt_id` | Identifier for this acquisition attempt. |
| `bundle_id` | Identifier for the promoted bundle. |
| `analysis_target` | Material scope the evidence layer must satisfy. |
| `operation` | Capability required from the backend. |
| `source_fingerprint` | Stable source identity hash. |
| `artifacts` | Artifact records defined below. |
| `metadata` | Redacted, non-authoritative route and source metadata. |
| `privacy` | Boolean privacy declarations. |
| `limits` | Known acquisition limits. |
| `failures` | Redacted stage failures. |
| `next_action` | Safe next step. |

Schema v1 is accepted only as a legacy compatibility input and receives a
validation warning. New producers must write v2.

## Run Identity

`logs/run_identity.json` binds one project root to:

- `run_id`;
- platform and source id;
- source fingerprint;
- analysis target;
- operation.

Rules:

1. A non-empty project root cannot be reused implicitly.
2. `--resume` is required for another attempt.
3. Resume fails when source fingerprint, target, or operation differs.
4. A local-file fingerprint includes the file SHA-256, not only its path.
5. Refreshed URL access tokens may be redacted from identity when the stable
   source id and URL path are unchanged.

## Analysis Targets

| Target | Required primary scope | Default operation |
| --- | --- | --- |
| `video_content` | `video_transcript` | `extract_transcript` |
| `social_post` | `social_post_text` | `read` |
| `web_article` | `article_body` | `read` |
| `repository` | `repository_document` | `read` |
| `search_triage` | none; search remains secondary | `search` |

`auto` is accepted at the CLI but must be resolved before a v2 manifest is
written.

## Artifact Records

Every artifact requires:

| Field | Meaning |
| --- | --- |
| `artifact_id` | Unique artifact identifier. |
| `path` | Relative path contained by `00_acquisition/`. Absolute paths and `..` are invalid. |
| `type` | `transcript`, `subtitle`, `page_markdown`, `page_text`, `audio`, `video`, `metadata`, `search_result`, `comments`, or `unknown`. |
| `source_class` | `primary`, `partial_primary`, `secondary`, `metadata_only`, or `unknown`. |
| `content_scope` | `video_transcript`, `social_post_text`, `article_body`, `repository_document`, `search_result`, `comments`, `media`, `metadata`, or `unknown`. |
| `coverage` | `full`, `partial`, or `unknown`. |
| `run_id` | Must equal manifest `run_id`. |
| `source_id` | Must equal manifest `source_id`. |
| `bytes` | Exact file size. |
| `sha256` | Exact file SHA-256. |

Optional descriptive fields include `language`, `description`, and
`created_by`.

`source_class` is acquisition-side provenance. It does not by itself unlock a
report. The source gate also requires a target-compatible `content_scope`.

## Acquisition Status

Allowed values:

- `material_acquired`: at least one primary artifact exists;
- `partial_material_acquired`: primary coverage is partial;
- `metadata_only`: only metadata exists;
- `secondary_only`: only search results or secondary material exists;
- `blocked`: access or capability is blocked;
- `failed`: acquisition execution failed;
- `unsupported`: no adapter route exists.

Status invariants:

- `material_acquired` requires a `primary` artifact;
- `partial_material_acquired` requires `primary` or `partial_primary`;
- blocked, failed, unsupported, metadata-only, and secondary-only bundles
  cannot contain primary artifacts;
- metadata artifacts can never be primary.

## Capability Gate

Before executing a platform command, the adapter writes
`logs/route_plan.json` and verifies:

1. Agent-Reach doctor reports the selected backend with `status: ok`.
2. The adapter implements the requested operation for that backend and input.
3. When the selected backend is OpenCLI, the actual `edge` or `chrome` host is
   declared before execution. A generic extension/profile label is not host
   evidence.

If either check fails, write a blocked bundle. Do not fall through to an
unrelated generic route. Examples:

- Bilibili search API cannot satisfy `extract_transcript`;
- X OpenCLI search capability is not a documented single-status reader;
- social-post text does not satisfy embedded-video analysis.

## Source Gate Mapping

The evidence layer maps acquisition results to:

- `source_confirmed`;
- `source_partial`;
- `secondary_only`;
- `source_blocked`;
- `source_failed`;
- `degraded_report_only`.

It admits full decomposition only when primary artifacts match the analysis
target. `social_post_text`, metadata, comments, and screenshots cannot satisfy
`video_content`; only `video_transcript` can.

## Provenance Receipts

After ingest, each stage binds downstream output to the current run:

| Receipt | Binds |
| --- | --- |
| `10_video/00_source/gate_receipt.json` | Manifest hash, source-status hash, target decision, optional ASR-derived transcript hash. |
| `10_video/analysis_receipt.json` | Gate receipt, evidence audit, and analysis-pack hash. |
| `20_document/composer_receipt.json` | Analysis receipt, claim map, and composer intake. |
| `20_document/final_report_receipt.json` | Composer receipt, quality gate, and final-report hash. |

Every receipt repeats run, bundle, source, fingerprint, target, and gate-input
hash. A missing or mismatched receipt makes the corresponding output stale.
Status and export commands must not infer success from file existence.

## Retry and History

- Failed staging attempts are removed and never promoted.
- On successful `--resume`, the previous `00_acquisition` moves to
  `acquisition_history/<attempt-or-bundle-id>/`.
- When the new bundle is ingested, previous `10_video`, `20_document`, and
  `30_final` move to `run_history/<attempt-or-bundle-id>/`.
- History is auditable but never considered current output.

## Privacy

`privacy` requires boolean fields:

- `cookies_used`;
- `browser_session_used`;
- `secrets_redacted` (must be `true`);
- `contains_user_private_data`.

Hard rules:

- never persist cookie contents, authorization headers, session ids, tokens,
  visitor data, PO tokens, passwords, or proxy credentials;
- redact sensitive URL query values in manifest, preflight, run state,
  acquisition notes, commands, errors, and backend JSON;
- cookie files remain user-managed and are passed by path only;
- browser-visible material must be exported into an artifact before ingest;
- browser-backed routes record the declared host when known and record
  `unknown` rather than inferring one when it is not known;
- authorized browser exports enter through `kw browser-import` or
  `kw run --browser-source-url ... --browser-platform ...`;
- browser exports preserve the redacted source URL, explicit platform,
  target, operation, content scope, byte count, and SHA-256;
- never bypass CAPTCHA, paywalls, private access, region restrictions, or
  account permissions.

## Validation

```powershell
python .\kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
```

Validation fails on missing fields, invalid enum values, escaping paths,
missing files, byte/hash mismatch, run/source mismatch, status invariants, or
unredacted secret-like manifest data.
