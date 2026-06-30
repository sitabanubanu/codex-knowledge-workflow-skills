# Knowledge Video Decomposer Artifact Schema

This schema defines the intermediate artifacts produced by `knowledge-video-decomposer`.
The goal is to pass complete, evidence-linked source analysis to `knowledge-document-composer`
through files, without relying on conversation context.

## Output Root

The output root is usually selected by the workflow console:

```text
outputs\knowledge-workflow\<project-id>\10_video\
```

All relative paths below are relative to that root.

## Directory Structure

```text
00_source\
01_transcript\
02_segments\
03_inventory\
04_logic\
05_gap_check\
video_analysis_pack.md
```

## General Rules

- Preserve `timestamp`, `start` / `end`, `transcript_ids`, or `evidence_spans` for every important judgment whenever possible.
- Keep source claims and inferred claims separate. Do not mix what the source explicitly says with what the agent concludes.
- Do not put user extensions, outside frameworks, or downstream interpretation into `04_logic/source_logic.md`.
- If information comes from Chrome, yt-dlp, Firecrawl, ASR, captions, files, or another tool, record the source and confidence.
- If an artifact cannot be generated, record the failure and reason in `00_source/acquisition_notes.md` or `05_gap_check/gap_check.md`; do not pretend the artifact is complete.
- Prefer stable IDs that downstream files can reference, such as `t001`, `seg_argument_003`, `claim_012`, `concept_004`, or `ex_002`.

## Evidence Span Shape

Use this shape wherever a field is named `evidence_spans`:

```json
{
  "transcript_ids": ["t001", "t002"],
  "start": 12.3,
  "end": 44.8,
  "quote": "Short source-faithful excerpt or paraphrase anchor.",
  "source": "clean_transcript"
}
```

Keep quotes short. Use transcript IDs and timestamps as the durable reference.

## 00_source/metadata.json

Purpose: machine-readable source identity and acquisition summary.

Suggested fields:

```json
{
  "source_url": "",
  "canonical_url": "",
  "title": "",
  "speaker_or_channel": "",
  "platform": "",
  "published_at": "",
  "duration": "",
  "language": "",
  "source_type": "youtube|web_video|local_video|local_audio|transcript|subtitle|unknown",
  "collected_at": "",
  "tools_used": ["Chrome", "yt-dlp", "Firecrawl", "Hearsay", "ASR"],
  "confidence": "high|medium|low",
  "notes": ""
}
```

Field notes:

- `source_url`: user-provided URL or original path.
- `canonical_url`: resolved canonical source when available.
- `source_type`: identify the material type used for analysis.
- `tools_used`: include only tools actually used.
- `confidence`: overall acquisition confidence, not claim-level confidence.

## 00_source/acquisition_notes.md

Purpose: human-readable acquisition log.

Include:

- Material sources checked, such as page metadata, captions, transcript files, audio extraction, ASR, Firecrawl, or Chrome page inspection.
- Tool names, commands or connectors at a high level, and which outputs were trusted.
- Failed branches and why they failed, such as missing captions, blocked page content, unsupported file, or unusable ASR.
- Confidence by material source.
- Any mismatch between page title, channel, transcript language, visible metadata, or downloaded material.

## 00_source/asr_pipeline_report.json

Purpose: machine-readable local ASR provenance and quality report.

Use `scripts/asr_pipeline.py` when a user-provided or legitimately acquired
local audio/video file is transcribed through faster-whisper. The pipeline also
normalizes the ASR JSONL into canonical transcript artifacts.

Suggested fields:

```json
{
  "runner": "knowledge-video-asr-pipeline",
  "input_media": "",
  "asr_jsonl": "",
  "asr_markdown": "",
  "model": "base",
  "language": "zh|en|auto|unknown",
  "vad_filter": true,
  "runtime": {
    "python": "",
    "ffmpeg": {"available": true, "path": ""},
    "faster_whisper": {"available": true}
  },
  "quality": {
    "segments": 0,
    "timed_segments": 0,
    "timestamp_coverage": 0.0,
    "exact_wording_confidence": "low|medium-low|medium|medium-high|high",
    "structural_summary_confidence": "low|medium-low|medium|medium-high|high",
    "known_limitations": []
  },
  "next_step": "enter_segmentation_inventory_logic_gap_check"
}
```

## 00_source/asr_pipeline_report.md

Purpose: human-readable ASR provenance, confidence, and limitation note.

Include:

- Input media path.
- ASR engine and model.
- Runtime checks for ffmpeg and faster-whisper.
- Language setting and VAD setting.
- Exact wording confidence and structural-summary confidence.
- Known limitations, especially whether the transcript may contain wording
  errors and should not be treated as verbatim.

## 00_source/chrome_page_snapshot.md

Purpose: record what was visible in Chrome when page-state inspection mattered.

Suggested structure:

```markdown
# Chrome Page Snapshot

- title:
- visible author/channel:
- visible description:
- visible transcript status:
- page observations:
- links:
- interaction notes:
```

Use this file for visible page facts only. Put agent decisions about what to do next in `chrome_notes.md`.

## 00_source/chrome_notes.md

Purpose: record page reconnaissance judgments and decisions made during Chrome inspection.

Include:

- Why Chrome was used.
- What was inspected or clicked.
- Whether visible page context changed the acquisition plan.
- Whether transcript, metadata, comments, description, or linked resources looked usable.
- Any uncertainty caused by dynamic page state, login state, localization, or unavailable content.

## 00_source/chrome_media_probe.json

Purpose: machine-readable Chrome deep-probe result.

Use `scripts/chrome_media_probe.py` after Chrome/pageAssets/Playwright or manual
browser inspection has produced layer observations. The script normalizes the
observations; it does not launch or control Chrome.

Suggested fields:

```json
{
  "runner": "knowledge-video-chrome-media-probe",
  "source_url": "",
  "title": "",
  "trigger_reason": "",
  "chrome_route_used": true,
  "yt_dlp_chrome_cookies_attempted": false,
  "yt_dlp_chrome_cookies_succeeded": false,
  "layers": [
    {
      "layer": "visible_transcript|pageAssets_list|pageAssets_bundle|playwright_evaluate|network_media_inspection",
      "executed": true,
      "result": "success|not_found|blocked|not_run",
      "media_found": false,
      "local_files": [],
      "existing_local_files": [],
      "missing_local_files": [],
      "public_urls": [],
      "confirmed_public_downloadable": false,
      "notes": ""
    }
  ],
  "decision": {
    "visible_transcript_status": "available|partial|not_visible|not_checked|blocked|unknown",
    "page_state_observed": "opened|failed_to_open|login_required|captcha_required|paywalled|permission_required|video_unavailable|metadata_only|unknown",
    "chrome_deep_probe_exhausted": false,
    "deep_probe_layers_executed": [],
    "deep_probe_media_found": false,
    "browser_derived_media_exported": false,
    "downloadable_media_url_found": false,
    "suggested_acquisition_signal": "chrome_visible_transcript|browser_derived_media_acquired|browser_derived_media_url_found|chrome_deep_probe_exhausted|captcha|login_required|request_blocked",
    "suggested_source_status": "source_confirmed|source_partial|source_blocked|source_failed",
    "next_step": ""
  }
}
```

Minimum expectations:

- Page playability alone must not set `deep_probe_media_found=true`.
- `browser_derived_media_exported=true` requires an actual local media/subtitle
  file.
- A confirmed public downloadable media/subtitle URL may set
  `downloadable_media_url_found=true`, but must not emit
  `browser_derived_media_acquired` until the URL has been fetched, saved, and
  processed.
- CAPTCHA, paywall, permission, login, and unavailable-video states must route to
  blocked or failed source handling, not full analysis.

## 00_source/chrome_media_probe.md

Purpose: human-readable summary of the Chrome deep-probe layers and decision.

Include the URL, trigger reason, page state, visible transcript status, each
layer's executed/result/media findings, and the boundary that Chrome playability
alone is not primary material.

## 01_transcript/raw_transcript.jsonl

Purpose: preserve raw transcript segments before cleanup.

Format: JSON Lines, one raw transcript segment per line.

Suggested fields per line:

```json
{
  "id": "raw_0001",
  "start": 0.0,
  "end": 4.2,
  "text": "",
  "source": "captions|subtitle|ASR|manual|provided_transcript",
  "language": "",
  "confidence": "high|medium|low",
  "raw_index": 0
}
```

Do not normalize text here. Preserve raw spelling, punctuation, and segmentation as much as practical.

## 01_transcript/asr_transcript.jsonl

Purpose: preserve direct ASR segments before canonical normalization when local
audio/video is transcribed by `scripts/asr_pipeline.py`.

This file may be generated by `transcribe_faster_whisper.py` or supplied as
`--asr-jsonl` when resuming a prior ASR run. It should then pass through
`transcript_normalizer.py`, which writes `raw_transcript.jsonl` and
`clean_transcript.jsonl`.

Suggested fields per line:

```json
{
  "id": "t0001",
  "start": 0.0,
  "end": 4.2,
  "text": "",
  "source": "ASR",
  "engine": "faster-whisper",
  "model": "base",
  "language": "zh|en|unknown",
  "confidence": "low|medium|high",
  "raw_index": 0
}
```

## 01_transcript/asr_transcript.md

Purpose: readable ASR transcript preview before or alongside canonical
normalization.

Do not treat this as a final verbatim transcript unless the ASR quality policy
and review process support that claim.

## 01_transcript/clean_transcript.jsonl

Purpose: cleaned, normalized transcript segments for downstream evidence references.

Format: JSON Lines, one cleaned transcript segment per line.

Suggested fields per line:

```json
{
  "id": "t0001",
  "start": 0.0,
  "end": 4.2,
  "text": "",
  "normalized_text": "",
  "source_ids": ["raw_0001"],
  "language": "",
  "speaker": "",
  "confidence": "high|medium|low"
}
```

Use stable IDs because inventory, logic, and document composer artifacts should point back to them.

## 01_transcript/clean_transcript.md

Purpose: human-readable full transcript with timestamps.

Recommended format:

```markdown
# Clean Transcript

[00:00:00-00:00:04] Speaker: Text...
[00:00:04-00:00:09] Speaker: Text...
```

Keep the transcript readable while preserving enough timestamp detail for source checking.

## 02_segments/syntax_segments.json

Purpose: mechanical or syntax-oriented grouping of transcript material.

Use `scripts/transcript_segmenter.py` after `01_transcript/clean_transcript.jsonl`
exists and source status is `source_confirmed` or explicitly partial. This stage
is allowed to write `02_segments/syntax_segments.json`,
`02_segments/argument_segments.json`, and a segmentation gap note. It must not
write `03_inventory`, `04_logic`, or `video_analysis_pack.md`.

Suggested fields:

```json
{
  "segments": [
    {
      "id": "seg_syntax_001",
      "start": 0.0,
      "end": 32.4,
      "text": "",
      "transcript_ids": ["t0001", "t0002"],
      "split_reason": "pause|topic_shift|sentence_boundary|slide_change|speaker_change|length_limit|manual"
    }
  ]
}
```

Use this when downstream processing needs readable chunks but not argument roles.

## 02_segments/argument_segments.json

Purpose: semantic and rhetorical segmentation of the source argument.

Argument segment roles produced by the segmenter are heuristic labels for the
next extraction stage. They are not final claims, concepts, or source-logic
reconstruction. Later inventory and logic stages must verify roles and evidence
against transcript IDs.

Suggested fields:

```json
{
  "segments": [
    {
      "id": "seg_argument_001",
      "start": 0.0,
      "end": 88.2,
      "role": "opening",
      "title": "",
      "summary": "",
      "transcript_ids": ["t0001", "t0002"],
      "evidence_spans": []
    }
  ]
}
```

Allowed `role` values include:

- `opening`
- `question`
- `example`
- `definition`
- `claim`
- `analogy`
- `transition`
- `conclusion`
- `aside`

Use the closest role when a segment has multiple functions, and note secondary roles in `summary` if needed.

## 03_inventory/concepts.json

Purpose: key concepts and source-local definitions.

Use `scripts/inventory_extractor.py` after `02_segments/argument_segments.json`
exists and source status is `source_confirmed` or explicitly partial. This stage
is allowed to write `03_inventory/concepts.json`, `03_inventory/examples.json`,
`03_inventory/claims.json`, `03_inventory/analogies.json`, and an inventory gap
note. It must not write `04_logic` or `video_analysis_pack.md`.

Inventory extractor output is a candidate inventory. Later source-logic and
gap-audit stages must verify the candidate roles, claim types, and missing
definitions against transcript evidence.

Suggested fields:

```json
{
  "concepts": [
    {
      "id": "concept_001",
      "term": "",
      "normalized_term": "",
      "definition_in_source": "",
      "evidence_spans": [],
      "importance": "high|medium|low",
      "notes": ""
    }
  ]
}
```

Use `definition_in_source` only for the definition actually present or clearly implied in the source.

## 03_inventory/examples.json

Purpose: examples, cases, anecdotes, demonstrations, or scenarios used by the speaker.

Suggested fields:

```json
{
  "examples": [
    {
      "id": "ex_001",
      "name": "",
      "description": "",
      "what_it_demonstrates": "",
      "evidence_spans": [],
      "linked_claim_ids": ["claim_001"]
    }
  ]
}
```

Do not reduce an example to its conclusion. Preserve the setup, relevant details, and the role it plays in the argument.

## 03_inventory/claims.json

Purpose: claims made by the source or inferred by the decomposer.

Suggested fields:

```json
{
  "claims": [
    {
      "id": "claim_001",
      "text": "",
      "claim_type": "source_claim",
      "evidence_spans": [],
      "confidence": "high|medium|low",
      "linked_example_ids": ["ex_001"]
    }
  ]
}
```

Allowed `claim_type` values:

- `source_claim`: explicitly stated by the source.
- `inferred_claim`: reasonably inferred from the source.
- `uncertain_claim`: possible but insufficiently supported.

## 03_inventory/analogies.json

Purpose: analogies and mappings used by the speaker.

Suggested fields:

```json
{
  "analogies": [
    {
      "id": "analogy_001",
      "source_domain": "",
      "target_domain": "",
      "mapping": [
        {
          "source_element": "",
          "target_element": "",
          "relation": ""
        }
      ],
      "evidence_spans": [],
      "purpose": ""
    }
  ]
}
```

Record the analogy's purpose, such as explanation, persuasion, contrast, simplification, or framing.

## 04_logic/source_logic.md

Purpose: source-faithful reconstruction of the speaker's language logic.

Use `scripts/source_logic_builder.py` after `03_inventory` exists and source
status is `source_confirmed` or explicitly partial. This stage is allowed to
write `04_logic/source_logic.md`, `04_logic/logic_graph.json`, and a source
logic gap note. It must not write `video_analysis_pack.md`.

Rules:

- Write only what belongs to the source's own argument, language, sequence, and framing.
- Preserve the speaker's progression: question, setup, definitions, examples, claims, transitions, conclusions.
- Include timestamps, transcript IDs, or evidence references beside important moves.
- Do not add user extensions, external theories, critique, or document-composer interpretation.
- Flag ambiguity rather than resolving it with unsupported interpretation.

Suggested structure:

```markdown
# Source Logic

## Core Question

## Speaker Thesis

## Argument Flow

## Key Reasoning Moves

## Example-to-Claim Links

## Ambiguities
```

## 04_logic/logic_graph.json

Purpose: machine-readable argument graph for downstream composition.

Suggested fields:

```json
{
  "nodes": [
    {
      "id": "claim_001",
      "type": "claim",
      "label": "",
      "summary": "",
      "evidence_spans": []
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "source": "ex_001",
      "target": "claim_001",
      "type": "supports",
      "rationale": ""
    }
  ]
}
```

Allowed node types:

- `claim`
- `example`
- `concept`
- `analogy`
- `conclusion`
- `question`

Allowed edge types:

- `supports`
- `explains`
- `contrasts`
- `leads_to`
- `defines`
- `analogizes`

## 05_gap_check/gap_check.md

Purpose: identify weaknesses, missing evidence, or downstream risks before document composition.

Use `scripts/evidence_auditor.py` after `04_logic/source_logic.md` and
`04_logic/logic_graph.json` exist. This stage writes
`05_gap_check/evidence_audit.json` and `05_gap_check/gap_check.md`. It must not
write `video_analysis_pack.md`; the next pack-building stage must read the audit
gate first.

Check for:

- Abstract terms that are not explained.
- Examples that are incomplete or too compressed.
- Reasoning jumps between claims.
- Judgments that lack evidence.
- Confusion between Source, Inference, and Extension.
- Missing or low-confidence transcript material.
- Claims that need external verification before use in a final document.
- Important source sections that could not be acquired, parsed, or trusted.

Suggested structure:

```markdown
# Gap Check

## Missing or Weak Evidence

## Unexplained Concepts

## Incomplete Examples

## Reasoning Jumps

## Source / Inference / Extension Risks

## Acquisition Issues

## Downstream Notes
```

## 05_gap_check/evidence_audit.json

Purpose: machine-readable pre-pack evidence audit.

Suggested fields:

```json
{
  "runner": "knowledge-video-evidence-auditor",
  "generated_at": "",
  "output_root": "",
  "source_status": "source_confirmed|source_partial",
  "counts": {
    "transcript_rows": 0,
    "argument_segments": 0,
    "concepts": 0,
    "examples": 0,
    "claims": 0,
    "analogies": 0,
    "logic_nodes": 0,
    "logic_edges": 0
  },
  "severity_counts": {
    "error": 0,
    "warning": 0,
    "info": 0
  },
  "findings": [
    {
      "severity": "error|warning|info",
      "code": "",
      "message": "",
      "file": "",
      "item_id": "",
      "details": {}
    }
  ],
  "pack_gate": {
    "can_build_video_analysis_pack": true,
    "can_build_partial_pack": false,
    "next_step": "enter_video_analysis_pack_builder|enter_partial_video_analysis_pack_builder|fix_evidence_audit_findings"
  }
}
```

Minimum audit expectations:

- `source_status` must be `source_confirmed` or `source_partial`, and
  `primary_material_available` must be true.
- Transcript, segment, inventory, and logic graph evidence references must point
  to existing transcript IDs.
- Inventory links between examples and claims must point to existing IDs.
- Logic graph edges must point to existing graph nodes.
- Warnings may pass to the pack builder; errors must block pack creation.
- `source_confirmed` with no errors may enter full pack building.
- `source_partial` with no errors may enter explicitly partial pack building.

## video_analysis_pack.md

Purpose: main deliverable for `knowledge-document-composer`.

This file should be readable on its own and should point to the detailed artifacts under `10_video`.
It is the handoff contract between video decomposition and document composition.

Use `scripts/video_analysis_pack_builder.py` only after
`05_gap_check/evidence_audit.json` exists and its `pack_gate` allows a full or
explicitly partial pack. The builder writes only `video_analysis_pack.md`; it
does not rerun acquisition, transcript extraction, segmentation, inventory
extraction, source logic reconstruction, or evidence auditing.

Recommended structure:

```markdown
# Video Analysis Pack

## Source Summary

## Acquisition Confidence

## Transcript Location

## Speaker Thesis

## Argument Flow

## Key Examples

## Concepts

## Claims

## Analogies

## Source Logic Summary

## Gaps

## Downstream Notes
```

Minimum expectations:

- Link or name the transcript files used.
- Summarize acquisition confidence and major caveats.
- Preserve source-faithful thesis and argument flow.
- Separate source claims, inferred claims, and uncertain claims.
- List key examples with evidence references.
- Point to `04_logic/source_logic.md`, `04_logic/logic_graph.json`, and `05_gap_check/gap_check.md`.
- Include downstream cautions that the document composer must not ignore.
- For `source_partial`, title or body must visibly label the pack as partial scope.
- If `evidence_audit.json` contains error findings, do not write this file.
