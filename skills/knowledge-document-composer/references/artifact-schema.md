# Knowledge Document Composer Artifact Schema

This schema defines the intermediate and final artifacts produced by `knowledge-document-composer`.
The goal is to transform a video analysis package into a coherent document while preserving evidence,
separating Source / Inference / Extension, and avoiding dependence on conversation context.

## Inputs

Input usually comes from:

```text
outputs\knowledge-workflow\<project-id>\10_video\video_analysis_pack.md
```

The composer should also consult detailed artifacts under `10_video`, especially transcript,
inventory, source logic, logic graph, and gap check files:

```text
10_video\01_transcript\
10_video\03_inventory\
10_video\04_logic\
10_video\05_gap_check\
```

For audited video workflows, `10_video\05_gap_check\evidence_map.json` and
`10_video\05_gap_check\claim_source_audit.json` are required sidecars. They
confirm that claims, examples, and source-logic nodes remain traceable to
transcript evidence.

## Output Root

Write document artifacts under:

```text
outputs\knowledge-workflow\<project-id>\20_document\
```

All relative paths below are relative to that root.

## Source / Inference / Extension

Use this three-way classification throughout the document workflow:

- `Source`: the original material explicitly says it, or the statement is a faithful reconstruction of the source's own language logic.
- `Inference`: the agent reasonably derives it from source material, but it is not directly stated.
- `Extension`: the agent adds it from user goals, external frameworks, outside knowledge, critique, or downstream synthesis.

Rules:

- Never write Extension as if it were Source.
- Keep Source reconstruction free of added frameworks, critique, or user interpretation.
- Mark uncertainty when evidence is incomplete, indirect, or low confidence.
- Preserve evidence references for important Source and Inference claims.

## Directory Structure

The required files may live directly under `20_document` unless the workflow console chooses a more detailed layout.

```text
composer_intake.json
commitments.md
claim_map.json
expansion_plan.md
report_outline.md
source_reconstruction.md
draft_report.md
critique.md
revised_report.md
quality_gate.json
quality_check.md
final_report.md
```

Optional outputs:

```text
presentation_outline.md
briefing_note.md
final_report.docx
final_report.pdf
slides.pptx
```

## composer_intake.json

Purpose: machine-readable document-composer entry gate.

Use `scripts/document_composer_runner.py` after the upstream
`10_video/video_analysis_pack.md` has been built from a passing
`05_gap_check/evidence_audit.json`. The runner writes `composer_intake.json` and
the initial planning artifacts, but it must not write `draft_report.md` or
`final_report.md`.

Suggested fields:

```json
{
  "runner": "knowledge-document-composer-runner",
  "generated_at": "",
  "video_root": "",
  "document_root": "",
  "source_status": "source_confirmed|source_partial",
  "allowed_report_type": "",
  "composer_decision": "full|partial",
  "document_goal": "",
  "final_language": "",
  "audience": "",
  "evidence_audit": {
    "severity_counts": {},
    "pack_gate": {},
    "evidence_map": {
      "path": "10_video/05_gap_check/evidence_map.json",
      "summary": {}
    },
    "claim_source_audit": {
      "path": "10_video/05_gap_check/claim_source_audit.json",
      "summary": {}
    }
  },
  "files_written": [],
  "next_step": "draft_report_with_quality_gates"
}
```

Minimum expectations:

- Refuse normal document planning when source status is blocked, failed,
  secondary-only, degraded, or missing primary material.
- Refuse normal document planning when evidence audit has error findings.
- Refuse normal document planning when `evidence_map.json` or
  `claim_source_audit.json` is missing, mismatched, malformed, or when
  `claim_source_audit.summary.blocking_claims` is greater than zero.
- Refuse normal document planning when `evidence_audit.json` records sidecar
  summaries that do not match the actual `evidence_map.json` or
  `claim_source_audit.json` summaries.
- For `source_partial`, every downstream planning artifact must visibly preserve
  the partial-scope label.
- Do not create `final_report.md` until draft, critique, revision, and quality
  gates pass.

## commitments.md

Purpose: absorb ArcDeck's commitment idea as the global contract for document creation.
This file states what the document must preserve, where it may expand, and what it is trying to accomplish.

Suggested structure:

```markdown
# Commitments

## Source Question

## Source Thesis

## Narrative Spine

## Target Document Goal

## Audience

## Must-Preserve Evidence

## Expansion Boundaries
```

Guidance:

- `Source Question`: the problem or question the source is organized around.
- `Source Thesis`: the source-faithful central answer or position.
- `Narrative Spine`: the source's main progression from setup to conclusion.
- `Target Document Goal`: what the final document should do for the user.
- `Audience`: expected reader and their prior knowledge.
- `Must-Preserve Evidence`: examples, claims, timestamps, transcript IDs, or logic moves that cannot be dropped.
- `Expansion Boundaries`: what can be added, what needs external validation, and what must not be attributed to the source.

## claim_map.json

Purpose: structured claim inventory for document use.

Suggested fields:

```json
{
  "claims": [
    {
      "id": "doc_claim_001",
      "text": "",
      "category": "Source",
      "source_evidence": [
        {
          "artifact": "10_video/video_analysis_pack.md",
          "transcript_ids": ["t0001"],
          "start": 0.0,
          "end": 12.5,
          "quote": "",
          "notes": ""
        }
      ],
      "confidence": "high|medium|low",
      "status": "accepted|needs_verification|uncertain|excluded",
      "document_use": "thesis|section_claim|example_support|context|caveat|not_used"
    }
  ]
}
```

Rules:

- `category` must be one of `Source`, `Inference`, or `Extension`.
- `source_evidence` should be populated for Source claims and for Inference claims whenever possible.
- Extension claims should state their origin in `source_evidence.notes` or a similar evidence note, even when the origin is user-provided.
- Use `status` to prevent weak claims from silently entering `final_report.md`.

## expansion_plan.md

Purpose: explain how user extensions or downstream ideas connect to the original video logic.

This file must distinguish:

- Content that can extend the source's logic without distorting it.
- Content that needs external verification before being asserted.
- Content that must not be presented as something the original video or source said.

Suggested structure:

```markdown
# Expansion Plan

## Source Logic Available for Extension

## Compatible Extensions

## Needs External Verification

## Must Not Be Attributed to Source

## Integration Strategy
```

Use this file before drafting so the final report does not blur evidence categories.

## report_outline.md

Purpose: structure the final report before drafting.

Suggested structure:

```markdown
# Report Outline

## Working Title

## Reader Promise

## Section Outline

## Evidence Placement

## Source / Inference / Extension Placement

## Open Questions Before Draft
```

Each major section should identify its function, key claim, evidence, and whether the section is Source, Inference, Extension, or a clearly labeled mixture.

## source_reconstruction.md

Purpose: reconstruct only the original video or source material and its language logic.

Rules:

- Include only Source content.
- Preserve the source's own progression, examples, concepts, claims, and transitions.
- Do not add user extensions, external frameworks, critique, or final-report interpretation.
- Keep timestamps, transcript IDs, artifact links, or other evidence anchors close to key moves.
- Mark gaps inherited from `10_video\05_gap_check\gap_check.md`.

Suggested structure:

```markdown
# Source Reconstruction

## Core Question

## Source Thesis

## Language and Argument Flow

## Key Examples

## Key Concepts

## Key Claims

## Source Gaps and Ambiguities
```

## draft_report.md

Purpose: first complete draft of the target document.

Guidance:

- Use `commitments.md`, `claim_map.json`, `expansion_plan.md`, and `report_outline.md` before drafting.
- Keep Source / Inference / Extension separation visible in language, footnotes, labels, or section framing.
- Preserve complete examples, not only abstract conclusions.
- Explain abstract concepts before relying on them.
- Keep the reasoning chain visible enough that a reader can follow how the document moves from source material to any added interpretation.

Use `scripts/final_report_writer.py` for audited workflow scaffolding after
`document_composer_runner.py` has written the planning artifacts. The writer may
create a deterministic draft from the current planning files, but the same
Source / Inference / Extension and source-status rules apply to any manual draft.

## critique.md

Purpose: record the critique pass between draft and revision.

Minimum expectations:

- Identify whether the draft preserves Source / Inference / Extension separation.
- Identify missing registered Source claim ids, weak claims, or unsupported claims.
- For `source_partial`, verify that partial scope is visible before revision.
- Name revisions required before the final audit.

## revised_report.md

Purpose: final candidate after critique and revision.

Rules:

- This is the artifact audited before `final_report.md`.
- It must preserve visible `## Source`, `## Inference`, and `## Extension`
  sections or equivalent explicit labels.
- It must include registered Source claim ids from `claim_map.json` in the
  Source section.
- For `source_partial`, it must visibly say `Partial Scope`.
- It must include an evidence and limits section before final approval.

## quality_gate.json

Purpose: machine-readable final quality gate.

Use `scripts/final_report_auditor.py` directly, or via
`scripts/final_report_writer.py`, before creating or accepting
`final_report.md`.

Required fields:

```json
{
  "runner": "knowledge-document-final-report-auditor",
  "generated_at": "",
  "document_root": "",
  "report_path": "",
  "source_status": "source_confirmed|source_partial",
  "report_scope": "full|partial",
  "approved_for_final_report": false,
  "gates": [
    {
      "gate": "Evidence",
      "status": "pass|block",
      "evidence": "",
      "required_revision": ""
    }
  ],
  "blocking_gates": [],
  "registered_source_claims": [],
  "source_claims_used": [],
  "files_checked": []
}
```

Rules:

- `final_report.md` may be created only when
  `approved_for_final_report` is `true`.
- `secondary_only`, `source_blocked`, `source_failed`, and
  `degraded_report_only` must not pass this gate for a normal final report.
- `source_partial` may pass only as `report_scope: partial` with a visible
  partial-scope label.
- Any Source claim used in the report must be registered in `claim_map.json` as
  category `Source`, status `accepted`.

## quality_check.md

Purpose: final pre-delivery check before producing `final_report.md` or optional formatted outputs.

Must check:

- Whether examples are complete enough to support the claims that use them.
- Whether abstract concepts are explained before use.
- Whether the argument chain has reasoning jumps.
- Whether Source, Inference, and Extension are separated.
- Whether important judgments have evidence.
- Whether the report answers the user's question.
- Whether `10_video\05_gap_check\gap_check.md` has been read and addressed.
- Whether uncertainty is marked where evidence is insufficient.
- Whether `quality_gate.json` exists and approves final delivery.

Suggested structure:

```markdown
# Quality Check

## Evidence Coverage

## Example Completeness

## Concept Clarity

## Reasoning Continuity

## Source / Inference / Extension Separation

## Gap Check Follow-Up

## User Question Coverage

## Required Revisions

## Approval for Final
```

## final_report.md

Purpose: final Markdown report.

Requirements:

- Answer the user's document goal.
- Preserve the source thesis and argument logic accurately.
- Clearly distinguish Source, Inference, and Extension.
- Do not introduce a new Source claim unless it is registered in
  `claim_map.json` with evidence and, for audited video workflows, compatible
  with `10_video/05_gap_check/claim_source_audit.json`.
- Include enough examples and evidence for key claims.
- Mark uncertainty instead of overstating weak evidence.
- Reflect all required revisions from `quality_check.md`.

## Optional Outputs

These files are optional and should be generated only when the user or workflow requires them.

### presentation_outline.md

Purpose: slide-ready or talk-ready outline derived from `final_report.md`.

Include section titles, slide intent, key claims, examples, and evidence notes.

### briefing_note.md

Purpose: short operational summary for a reader who needs the result quickly.

Keep evidence categories visible, especially when recommendations include Extension.

### final_report.docx

Purpose: formatted Word document version of `final_report.md`.

Use only after the Markdown final report is stable.

### final_report.pdf

Purpose: fixed-layout PDF delivery version.

Use only after layout has been checked.

### slides.pptx

Purpose: presentation deck version.

Use `presentation_outline.md` as the planning source.

## Quality Gates

The composer must not deliver a final report until these gates pass:

- Extension is not written as Source.
- The document does not rely only on abstract summary; it includes concrete examples where the source provides or requires them.
- The document does not present conclusions without reconstructing the source's language and reasoning progression.
- The document does not ignore `video_analysis_pack.md` gaps or `10_video\05_gap_check\gap_check.md`.
- Insufficient evidence is marked with uncertainty instead of being overstated.
- The final report answers the user's stated question or document goal.
