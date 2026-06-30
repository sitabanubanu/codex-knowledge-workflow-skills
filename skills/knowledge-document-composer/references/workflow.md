# Knowledge Document Composer Workflow

Use this workflow to turn upstream `10_video` artifacts into a source-faithful document under `20_document`.
Do not start with a polished summary. Build the reconstruction and decision artifacts first, then draft.

The final report must be written in the user's requested language. If the user does not specify a language, use the current conversation language by default and record that decision in `commitments.md`. Keep evidence labels and Source / Inference / Extension distinctions clear even when the final prose is not English.

## Output Order

Create these files in this order unless the user explicitly asks only for an intermediate artifact:

```text
20_document/composer_intake.json
20_document/commitments.md
20_document/source_reconstruction.md
20_document/claim_map.json
20_document/expansion_plan.md
20_document/report_outline.md
20_document/draft_report.md
20_document/critique.md
20_document/revised_report.md
20_document/quality_gate.json
20_document/quality_check.md
20_document/final_report.md
```

Optional formatted outputs such as docx, pdf, slides, briefing notes, or scripts are later-stage outputs. Create them only when requested after `final_report.md` is stable.

For audited video workflows, run `scripts/document_composer_runner.py` before
drafting. It verifies `10_video/video_analysis_pack.md`,
`10_video/00_source/source_status.json`, and
`10_video/05_gap_check/evidence_audit.json`,
`10_video/05_gap_check/evidence_map.json`, and
`10_video/05_gap_check/claim_source_audit.json`, then writes
`composer_intake.json` and pre-draft planning artifacts. This runner is a gate
and planning scaffold; it must not create `draft_report.md` or
`final_report.md`.

After the planning artifacts exist, use `scripts/final_report_writer.py` to run
the draft -> critique -> revise -> source audit -> final report loop. Use
`scripts/final_report_auditor.py` independently when a human or another agent
edits `draft_report.md` or `revised_report.md`.

## Artifact Writing Reliability

For long reports, transcripts, JSON maps, or multi-section artifacts, write files through file-based generation, a reusable script, or small scoped patches. Do not put a whole report or transcript inside one giant shell command. On Windows, long inline commands can fail before the file is written and make the workflow look like a content failure.

After writing a large artifact, reopen it from disk and verify at least the title, final language, expected sections, and rough size before treating the stage as complete.

## Phase 1: Intake and Artifact Check

Load the upstream package before writing:

- `video_analysis_pack.md`
- `evidence_audit.json`
- `clean_transcript.md` or `clean_transcript.jsonl`
- `source_logic.md`
- `logic_graph.json`
- `claims.json`
- `examples.json`
- `concepts.json`
- `analogies.json`
- `gap_check.md`
- `evidence_map.json`
- `claim_source_audit.json`

Also load `metadata.json`, `acquisition_notes.md`, `syntax_segments.json`, and `argument_segments.json` when they are available and relevant to evidence or structure.

Minimum required source material:

- `video_analysis_pack.md`, or
- a transcript plus at least one logic or inventory artifact.

Stop if there is no reliable source material to reconstruct. Do not invent a report from conversation memory.

Stop the normal document workflow if `evidence_audit.json` contains error
findings, if its output root does not match the current upstream video root, or
if its pack gate does not allow a full or explicitly partial pack.
Also stop if `evidence_map.json` or `claim_source_audit.json` is missing,
mismatched, malformed, or if claim source audit reports blocking claims.

Degrade explicitly when artifacts are partial:

- If `clean_transcript` is missing, use `video_analysis_pack.md` and mark transcript evidence as unavailable.
- If `source_logic.md` or `logic_graph.json` is missing, reconstruct argument flow from transcript and claims, and mark lower confidence.
- If `claims.json`, `examples.json`, `concepts.json`, or `analogies.json` is missing, derive a provisional inventory from available source artifacts and mark it as provisional.
- If `gap_check.md` is missing, add a gap note in `commitments.md` and `quality_check.md`.

Record the intake result in `commitments.md` under "Source Status". Name missing artifacts and explain whether the workflow stopped, degraded, or continued.

## Phase 2: Commitments

Create `commitments.md` before any final-style drafting.

Required fields:

- Source status: known artifacts, missing artifacts, evidence quality, and degradation decisions.
- Source question: the problem or question the original source is organized around.
- Source thesis: the answer or position the source itself advances.
- Narrative spine: the source's progression from setup to conclusion.
- Target document goal: what the user wants the document to do.
- Final language: the user's requested language, or the current conversation language when no explicit language was requested.
- Audience: reader knowledge level, use case, and expected level of detail.
- Must-preserve evidence: examples, timestamps, transcript ids, claims, transitions, and unusual wording that must not be dropped.
- Expansion boundaries: what may be added, what needs outside verification, and what must not be attributed to the source.

Decision rules:

- If the user asks for "analysis", "report", "essay", "briefing", or similar but does not specify audience, infer a practical audience from the conversation and state the assumption.
- If the user does not specify final language, use the current conversation language and state the assumption.
- If the user asks for expansion, place the expansion inside boundaries before drafting.
- If the source thesis is unclear, write the best candidate thesis and mark confidence.
- If examples drive the argument, list them as must-preserve evidence.

## Phase 3: Source Reconstruction

Create `source_reconstruction.md` before any final-style draft.

This artifact is Source-only. It must reconstruct what the original source says or clearly implies through its own sequence, wording, examples, and argument moves.

Required sections:

- Core question.
- Source thesis.
- Speaker's language logic and rhetorical progression.
- Argument sequence from setup to conclusion.
- Key examples and how each example functions in the source.
- Concept transitions: where the speaker shifts from one concept, frame, or level of abstraction to another.
- Key claims with evidence anchors where available.
- Source gaps and ambiguities inherited from `gap_check.md` or intake.

Rules:

- Preserve concrete examples before abstracting them.
- Explain why each example appears at that point in the source.
- Show how the source moves from example to concept to claim to implication.
- Keep the speaker's original progression visible even if the final report later reorganizes it.
- Do not add critique, external frameworks, user ideas, or recommendations here.
- Use timestamps, transcript ids, segment ids, artifact filenames, or quotes when available.

Reject this pattern:

```text
The speaker moves from mental math to tool use.
```

Replace it with a concrete reconstruction:

```text
The speaker first uses the mental-math example to show how a familiar manual skill feels like intelligence when performed internally. The source then shifts to tool use by asking what changes when the same operation is offloaded to an external aid. This transition supports the later claim that the boundary between internal ability and external augmentation is unstable.
```

## Phase 4: Claim Map

Create `claim_map.json` after `source_reconstruction.md`.

Every claim used in the draft must be categorized:

- `Source`: explicitly stated by the source or reconstructed from the source's own language logic.
- `Inference`: reasonably derived from the source but not directly stated.
- `Extension`: added from user goals, external frameworks, outside knowledge, critique, or downstream synthesis.

Required claim fields:

- `id`
- `text`
- `category`
- `source_evidence`
- `confidence`
- `status`
- `document_use`

Rules:

- Source claims require evidence anchors when timestamps, transcript ids, segment ids, or artifact references are available.
- Inference claims should include anchors where possible and must explain the reasoning bridge.
- Extension claims must name their origin, such as user request, external knowledge, critique, or proposed application.
- Claims with `status` of `needs_verification`, `uncertain`, or `excluded` must not appear in the final report as settled claims.
- If an Extension helps the user but lacks verification, frame it as a possibility, recommendation, or separate extension rather than as source content.

## Phase 5: Expansion Plan

Create `expansion_plan.md` before the outline.

Required sections:

- User-requested additions.
- Source logic available for extension.
- Compatible extensions.
- Needs external verification.
- Must not be attributed to source.
- Integration strategy.

Decision rules:

- If the user requests only source-faithful reconstruction, keep expansion minimal and say so.
- If the user requests critique, recommendations, applications, or theory-building, place them in Extension or clearly labeled Inference.
- If an added idea changes the source's thesis, do not blend it into the source narrative; create a separate user-extension section.
- If external verification is needed and no browsing or sources are available, mark the idea as unverified rather than assert it.

## Phase 6: Outline

Create `report_outline.md` before drafting.

Each section must include:

- Section purpose.
- Key claim.
- Evidence or artifact references.
- Example placement.
- Concept transition or argument move.
- Source / Inference / Extension category, or a clear mixed-category note.
- Open questions or risks.

Outline rules:

- Put concrete examples before the abstract synthesis they support.
- Keep the source reconstruction early unless the user asks for a different format.
- Do not let a final synthesis appear before the reader has seen the evidence and reasoning path.
- If the final document is a short briefing, preserve the same logic in compressed form.

## Phase 7: Draft

Create `draft_report.md` only after `commitments.md`, `source_reconstruction.md`, `claim_map.json`, `expansion_plan.md`, and `report_outline.md` exist.

Drafting rules:

- Follow the user's requested document type and language. If no language was requested, follow the current conversation language recorded in `commitments.md`.
- Start from source-faithful reconstruction before adding interpretation.
- Explain each important example concretely: what it is, why it is introduced, how it works, and what conclusion it supports.
- Make transitions explicit: setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion.
- Keep Source, Inference, and Extension visible through section labels, parenthetical tags, footnotes, or careful wording.
- When expanding, say "an extension of the source logic is..." or equivalent instead of implying the source said it.
- Preserve source uncertainty and missing evidence notes.
- Avoid empty abstractions such as "this shows a shift in thinking" unless the next sentence names the exact shift and why it matters.

## Phase 8: Critique and Revision

Create `critique.md` after `draft_report.md`.

The critique must check:

- Whether the draft keeps Source / Inference / Extension visibly separated.
- Whether Source claims cite registered claim ids from `claim_map.json`.
- Whether `source_partial` remains visibly labeled as Partial Scope.
- Whether known evidence gaps are carried into the report.
- Whether any weak claim is presented as settled Source.

Create `revised_report.md` after applying critique findings. Do not audit
`final_report.md` directly unless it is a manually edited candidate; normally
audit `revised_report.md` and copy it to `final_report.md` only after approval.

## Phase 9: Quality Check and Source Audit

Create `quality_check.md` using `quality-gates.md` before `final_report.md`.
Also create machine-readable `quality_gate.json`.

For each gate:

- Mark `pass`, `revise`, or `block`.
- Cite the draft section affected.
- Name the required change.
- Make the revision before final delivery.

Blocking failures include:

- Source claims without available evidence anchors.
- Important examples mentioned only as labels.
- Unexplained jumps from example to abstraction to conclusion.
- Extensions written as if the source stated them.
- Missing source gaps or transcript limitations.
- A report that answers a generic topic instead of the user's actual request.

If any blocking gate fails, revise `draft_report.md` or `revised_report.md` and
rerun the auditor. Do not create `final_report.md` until
`quality_gate.json.approved_for_final_report` is `true`.

## Phase 10: Final Report and Optional Outputs

Create `final_report.md` only after quality gates pass.

Final report requirements:

- Answer the user's document goal.
- Preserve the source thesis and argument logic accurately.
- Include source reconstruction before interpretation unless the user requested a different order.
- Explain concrete examples before using them as abstractions.
- Distinguish Source, Inference, and Extension.
- Mark gaps, uncertainty, and low-confidence claims.
- Reflect all required revisions from `quality_check.md`.

Optional outputs:

- `briefing_note.md`: compressed operational summary from `final_report.md`.
- `presentation_outline.md`: slide-ready structure with claims, examples, and evidence notes.
- `final_report.docx` or `final_report.pdf`: formatted exports only after the Markdown report is stable.
- `slides.pptx`: only after a presentation outline exists.

## Stop and Return Conditions

Stop and report blocked when:

- Required source artifacts are missing and no reliable reconstruction can be made.
- The user asks for claims that require external verification but browsing or source access is unavailable.
- Existing artifacts conflict in a way that cannot be reconciled without rerunning an upstream stage.
- Producing the requested final output would require pretending that Extension is Source.

When degraded but not blocked, continue only after recording the degraded basis in `commitments.md`, `source_reconstruction.md`, and `quality_check.md`.
