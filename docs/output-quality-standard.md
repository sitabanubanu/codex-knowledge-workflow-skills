# Output Quality Standard

The workflow is acceptable only when a reader can tell what came from source
material, what was inferred, and what is an extension beyond the source.

## Required Layers

Every reusable final report must preserve these layers:

- `Source`: claims directly supported by transcript, subtitles, ASR, or another
  confirmed primary material artifact.
- `Inference`: cautious reasoning based on one or more Source claims.
- `Extension`: application, recommendation, or reuse suggestion that goes
  beyond the source.

Do not move uncertain interpretation into `Source`.

## Required Traceability

- `claim_map.json` must contain accepted claim IDs for reusable claims.
- Final reports must keep visible claim IDs, such as `doc_claim_001`.
- Batch synthesis must cite both item ID and claim ID.
- Conflict or uncertainty must stay visible instead of being silently merged.
- Failed, partial, or unapproved batch items must not contribute content claims
  to cross-source synthesis.

## Gate Requirements

A report is ready for reuse only when:

- `source_status.json` identifies source status.
- `primary_material_available` is present.
- `quality_gate.json` sets `approved_for_final_report` to `true`.
- The final report includes `## Source`, `## Inference`, and `## Extension`.
- Evidence gaps, limits, or blocked routes are named.

If any of these are missing, the correct outcome is `needs_review`, degraded
output, or a clear failure message, not a complete-looking report.

## Failure Standards

Failure output must answer three questions:

- What failed?
- Is it a material, permission, platform, dependency, or workflow issue?
- What can the user provide or run next?

Examples of unsupported conclusions:

- Treating a URL, title, screenshot, thumbnail, or metadata as a transcript.
- Treating a browser-discovered media URL as confirmed source material before
  the file is fetched and parsed.
- Treating missing cookies, private videos, CAPTCHA, paywalls, or region locks
  as problems the workflow should bypass.

## Human Review Checklist

- Can each important statement be traced back to a claim ID or source segment?
- Are Source, Inference, and Extension clearly separated?
- Does the report state limits instead of hiding them?
- Does batch synthesis use only completed and quality-approved items?
- Would a reader understand what material is needed if the workflow stopped?

