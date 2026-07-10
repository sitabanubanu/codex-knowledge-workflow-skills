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

## Non-Promotable Context

Metadata, screenshots, search snippets, comments, page shell state, third-party
summaries, and social captions for an embedded-video task cannot be promoted
into the missing primary scope.

## Delivery Gate

Source admission alone is not final delivery. Analysis, composer, quality gate,
and final report must also have current chained receipts and hashes.
