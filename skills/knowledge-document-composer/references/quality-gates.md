# Knowledge Document Composer Quality Gates

Run these gates after `draft_report.md`, critique, and `revised_report.md`, and
before `final_report.md`. Write the human-readable result in `quality_check.md`
and the machine-readable result in `quality_gate.json`.

Use this status vocabulary:

- `pass`: the gate is satisfied.
- `revise`: the draft can be fixed without new source work.
- `block`: final delivery is not allowed until the issue is fixed or explicitly downgraded by the user.

If any blocking gate fails, do not produce `final_report.md`. Revise the draft
or revised candidate, rerun the gates, and only then finalize.

Use `scripts/final_report_auditor.py` as the hard final gate for audited
workflow outputs. `scripts/final_report_writer.py` calls the auditor before it
creates `final_report.md`.

## Gate 1: Evidence Gate

Pass criteria:

- Key Source claims have timestamps, transcript ids, segment ids, quotes, or artifact references when available.
- Claims derived from `source_logic.md`, `logic_graph.json`,
  `claims.json`, or `video_analysis_pack.md` name the artifact.
- Every Source claim in `draft_report.md` or `final_report.md` is either
  present in `20_document/claim_map.json` or has been added there with
  Source / Inference / Extension category, evidence anchors, confidence, and
  status before final delivery.
- For audited video workflows, Source claims in `claim_map.json` trace back to
  `10_video/05_gap_check/claim_source_audit.json` with non-blocking evidence
  status.
- Inference claims have evidence anchors where possible and include a reasoning bridge.
- Extension claims name their origin, such as user request, outside framework, critique, or application.

Fail patterns:

- A Source claim appears with no evidence even though transcript or artifact evidence exists.
- A claim from the composer is written as if it came from the source.
- The report cites only the final pack when more precise evidence is available.
- The final report introduces a new Source claim that is not registered in `claim_map.json`.
- A claim with `needs_verification`, `uncertain`, or `excluded` status appears as a settled Source claim.

Blocking rule:

- Block final delivery when a central Source claim lacks available evidence.
- Block final delivery when any unregistered or weak claim is written as Source.

## Gate 2: Example Completeness Gate

Pass criteria:

- Every important example is described concretely before abstraction.
- For each important example, the report explains what it is, why it is
  introduced, how it works, and what conclusion it supports.
- The report distinguishes foundational examples from illustrative examples.
- Limits of examples are stated when relevant.

Fail patterns:

- The draft says only "mental math", "tool use", "the classroom example", or another label without explanation.
- The draft jumps from an example name to a broad theme.
- The draft drops examples listed as must-preserve evidence in `commitments.md`.

Blocking rule:

- Block final delivery when an important source example is only named or summarized abstractly.

## Gate 3: Language Logic Gate

Pass criteria:

- The report shows how the speaker's wording, sequence, contrasts, questions,
  and transitions help produce the conclusion.
- Concept transitions are explained, not merely named.
- The draft preserves the source's rhetorical progression before adding critique or extensions.
- Unusual source terms are explained in the source's own logic before outside terms are introduced.

Fail patterns:

- The report says the speaker "shifts", "reframes", or "moves beyond"
  something without showing the wording or sequence that creates the shift.
- The report replaces source language with the composer's framework too early.
- The final synthesis ignores how the speaker built the conclusion.

Blocking rule:

- Block final delivery when the source's conclusion appears without its language or sequence logic.

## Gate 4: Argument Continuity Gate

Pass criteria:

- The report makes the path visible: setup -> tension/problem -> example ->
  concept shift -> claim -> implication -> conclusion.
- Each major claim follows from a prior example, concept, or source move.
- Reasoning bridges are explicit where the source compresses an argument.
- The final synthesis follows from the reconstructed chain.

Fail patterns:

- A paragraph jumps from a concrete example to an abstract conclusion without an intermediate explanation.
- The report rearranges the source so much that the conclusion path becomes unclear.
- The report asserts implications that are not supported by Source or labeled Inference / Extension.

Blocking rule:

- Block final delivery when the reader cannot follow how the report moves from evidence to conclusion.

## Gate 5: Source / Inference / Extension Gate

Pass criteria:

- Source, Inference, and Extension are separated through headings, labels, footnotes, tables, or precise wording.
- Source reconstruction is free of added critique, outside theory, and user ideas.
- Inferences are phrased as derived interpretations, not direct source statements.
- Extensions are useful where requested but clearly attributed outside the source.

Fail patterns:

- User ideas are blended into the source thesis.
- Critique is inserted into Source reconstruction.
- External frameworks appear without an Extension label.
- Recommendations appear as if the speaker gave them.

Blocking rule:

- Block final delivery when Extension is written as Source.

## Gate 6: User Fit Gate

Pass criteria:

- The report answers the user's actual request, document type, and depth requirement.
- The output preserves the user's requested focus while maintaining source faithfulness.
- If the user asked for expansion, critique, script, briefing, or essay form, the structure reflects that request.

Fail patterns:

- The report gives a generic summary of the video topic.
- The report is too abstract for a user who asked for reasoning details.
- The report ignores requested language, default conversation language, format, or audience.
- The report explains the workflow instead of delivering the document.

Blocking rule:

- Block final delivery when the report does not answer the user's requested output.

## Gate 6A: Language Match Gate

Pass criteria:

- The final language follows the user's requested language.
- If no language was requested, it follows the current conversation language
  recorded in `commitments.md`.
- For `zh-CN`, the report body is substantially Chinese while still preserving
  machine-readable headings, claim ids, and source quotes when needed.
- Source quotes, transcript previews, claim ids, file paths, and section labels
  may remain in their original language when they are evidence or workflow
  anchors.

Fail patterns:

- `final_language` is `zh-CN`, but the report body is effectively English.
- The report only mentions `zh-CN` in metadata while the actual explanation is
  not Chinese.
- The report switches language by section without a source or evidence reason.

Blocking rule:

- Block final delivery when final language conflicts with the requested/default
  language.

## Gate 7: Gap Gate

Pass criteria:

- Missing transcripts, low-confidence spans, unavailable timestamps, and upstream gaps are acknowledged.
- `gap_check.md` is consulted when available.
- If `gap_check.md` is missing, the report says gap status is unavailable.
- Uncertain claims are marked rather than smoothed over.

Fail patterns:

- The report treats incomplete transcript material as complete.
- The report hides missing evidence.
- The report gives confident claims for segments marked uncertain upstream.

Blocking rule:

- Block final delivery when known gaps affect the central thesis and are not disclosed.

## Gate 8: No-Empty-Abstraction Gate

Pass criteria:

- Abstract labels are paired with concrete explanation.
- Terms such as "agency", "tool use", "rationality", "modernity",
  "cognitive shift", "language logic", or "paradigm" are defined through
  source material before being used.
- The draft replaces vague summaries with source-grounded reasoning.

Fail patterns:

- The report says "this reflects a deeper shift" without naming the shift and evidence.
- The report relies on elegant but empty phrases.
- The report compresses the speaker's reasoning into broad labels.

Blocking rule:

- Block final delivery when the core explanation depends on vague abstraction.

## Gate 9: Template Coverage Gate

Pass criteria:

- The draft includes the required functions from `report-template.md`, adapted to the requested output type.
- Concrete examples, argument chain, concept map, and Source / Inference /
  Extension separation are present unless explicitly unnecessary for the
  user's format.
- Any omitted template section has a reason recorded in `quality_check.md`.

Fail patterns:

- The draft skips source reconstruction.
- The draft lacks an argument chain.
- The draft has no place for user extensions even though the user asked for expansion.

Blocking rule:

- Block final delivery when a required function is omitted without reason.

## Gate 10: Final Approval Rule

Before creating `final_report.md`, `quality_gate.json` must exist and include:

```json
{
  "approved_for_final_report": true,
  "source_status": "source_confirmed",
  "report_scope": "full",
  "gates": [],
  "blocking_gates": []
}
```

The exact `source_status` may be `source_partial` only when `report_scope` is
`partial` and the report visibly says Partial Scope.

`quality_check.md` must also include:

```markdown
## Gate Results

| Gate | Status | Evidence | Required revision |
| --- | --- | --- | --- |
| Evidence |  |  |  |
| Example completeness |  |  |  |
| Language logic |  |  |  |
| Argument continuity |  |  |  |
| Source / Inference / Extension |  |  |  |
| User fit |  |  |  |
| Language match |  |  |  |
| Gap |  |  |  |
| No-empty-abstraction |  |  |  |
| Template coverage |  |  |  |

## Final Approval

- Blocking gates remaining:
- Revisions completed:
- Approved to create final_report.md: yes/no
```

Approval rule:

- If any gate status is `block`, approval must be `no`.
- If any gate status is `revise`, revise first unless the revision is explicitly deferred by the user.
- Only create `final_report.md` when `quality_gate.json.approved_for_final_report`
  is `true` and the matching `quality_check.md` says approval is `yes`.
- Do not approve a normal final report when source status is `secondary_only`,
  `source_blocked`, `source_failed`, or `degraded_report_only`.
- Do not approve `source_partial` unless the report is clearly partial and does
  not reconstruct missing source sequence.
