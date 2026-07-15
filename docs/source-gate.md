# Source Gate Summary

The source gate prevents complete analysis when material is secondary, stale,
or primary for the wrong task scope.

## Admission Rule

Full or explicitly partial analysis requires all of:

- valid Acquisition Bundle v2;
- current manifest/artifact hashes;
- `primary` or `partial_primary` source class;
- artifact scope matching `analysis_target`;
- current `gate_receipt.json`.

| Target | Matching scope |
| --- | --- |
| `video_content` | `video_transcript` |
| `social_post` | `social_post_text` |
| `web_article` | `article_body` |
| `repository` | `repository_document` |

`search_triage` does not unlock a normal full report.

## Allowed Source Status

- `source_confirmed` permits full decomposition.
- `source_partial` permits only visibly partial, gap-aware decomposition.

`secondary_only`, `source_blocked`, `source_failed`, and
`degraded_report_only` permit degraded output only.

Canonical v1 statuses also record `scope_status` and `pipeline_decision` so a
pipeline stop is not confused with whether a degraded user explanation is
allowed. Target mismatch stops before audit while retaining the existing
`degraded_report_only` compatibility status. Local media awaiting ASR is
`pending_derivation` until a transcript is validated.

The final status is published by the Source Gate through the shared contract.
ASR and normalization results are provisional until the stored status and
gate receipt have both passed validation.

## Non-Promotable Context

Metadata, screenshots, search snippets, comments, page shell state, third-party
summaries, and social captions for an embedded-video task cannot be promoted
into the missing primary scope.

## Delivery Gate

Source admission alone is not final delivery. Analysis, composer, quality gate,
and final report must also have current chained receipts and hashes.
