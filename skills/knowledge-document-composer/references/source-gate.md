# Source Gate

Use this gate before writing any document artifact from a `video_analysis_pack`,
transcript, claim map, logic graph, source notes, or any derived upstream artifact.
The gate decides what kind of document the composer is allowed to produce.

## Intake Requirement

Read source status before writing:

- Check upstream `00_source/metadata.json`, `00_source/acquisition_notes.md`,
  `video_analysis_pack.md`, `05_gap_check/gap_check.md`, artifact headers, and any
  user-provided status notes.
- Look for `source_status`, `allowed_report_type`, `source_classes`,
  `primary_material_available`, `status_reason`, `failed_probes`, and gaps.
- If no machine-readable status exists, infer the most conservative status from
  the evidence. Do not assume `source_confirmed`.
- Treat Firecrawl pages, search snippets, platform metadata, show notes, Podwise
  notes, third-party summaries, and visible page descriptions as secondary unless
  they include a first-party transcript or user-provided primary material.

## Status Values

Only use these statuses:

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

Do not invent temporary status names to bypass this gate.

## Hard Gate

### `source_confirmed`

Allowed:

- Write a full source-faithful speaker logic reconstruction.
- Write full argument flow, full source reconstruction, full claim inventory,
  source logic summary, and final report.
- Use Source claims when backed by transcript, audio-derived transcript,
  browser-visible transcript, or other first-party primary material.

Required:

- Preserve evidence anchors when available.
- Still separate Source, Inference, and Extension.

### `source_partial`

Allowed:

- Write only a partial report over the acquired primary-material range.
- Write partial source reconstruction, partial argument flow, and partial claim
  inventory for covered spans only.
- Use Source claims only inside the documented coverage range.

Required:

- Label the document, commitments, reconstruction, claim map, draft, and final
  output as partial.
- State the covered range, missing range, source classes, confidence, and gaps.
- Preserve unknowns instead of filling missing speaker logic from secondary
  material.

Forbidden:

- Do not present the output as a full report.
- Do not reconstruct missing segments.
- Do not use secondary material to complete a speaker logic chain while calling
  it source-faithful.

### `secondary_only`, `source_blocked`, `source_failed`, `degraded_report_only`

Allowed:

- Write a degraded source report, acquisition failure report, blocked-source
  explanation, background note, source ledger, or next-step acquisition plan.
- Summarize visible page context or secondary material only as background, with
  source labels and confidence limits.
- Explain what cannot be known without primary transcript or audio.

Forbidden:

- Do not write a full speaker logic reconstruction.
- Do not write a full argument chain, full source reconstruction, full claim
  inventory, or complete source logic.
- Do not make a degraded output look like a normal full report.
- Do not label secondary summaries, search snippets, platform metadata, or page
  observations as transcript, primary source, or source-confirmed evidence.
- Do not infer the speaker's complete sequence, examples, concept transitions,
  or conclusions from secondary summaries.

When these statuses apply, stop the normal document workflow and produce only the
allowed degraded output. The output must say that primary transcript/audio was
not available.

## Full Transcript Requests

If the user asks for a complete transcript, verbatim transcript, full text, or
complete wording, require primary transcript/audio/browser-visible transcript.

- With `source_confirmed`, provide only the transcript material actually present.
- With `source_partial`, provide only the available span and label it partial.
- With `secondary_only`, `source_blocked`, `source_failed`, or
  `degraded_report_only`, state that the complete transcript cannot be produced
  from the available material.

Never use a summary, web page, search result, model reconstruction, or secondary
notes as a substitute for verbatim transcript.

## Source / Inference / Extension Requirement

Every final or degraded document must distinguish:

- `Source`: backed by primary material or explicitly limited source artifacts.
- `Inference`: derived from available source material with a reasoning bridge.
- `Extension`: added by the user, outside knowledge, critique, application, or
  downstream synthesis.

Rules:

- Degraded and secondary-only reports usually have no full Source reconstruction.
  Label their factual basis as background or secondary context.
- Do not upgrade Inference or Extension into Source.
- Do not hide evidence limitations in polished prose.
- Mark uncertainty whenever evidence is incomplete, indirect, or low confidence.

## Commitment Record

Before drafting, record the gate decision in `commitments.md` or in the degraded
output itself:

```json
{
  "source_status": "",
  "allowed_report_type": "",
  "primary_material_available": false,
  "source_classes": [],
  "covered_range": "",
  "missing_range": "",
  "status_reason": "",
  "composer_decision": "full|partial|degraded|blocked"
}
```

If the gate decision is `partial`, `degraded`, or `blocked`, repeat that status in
the title or opening source-status section of the output.
