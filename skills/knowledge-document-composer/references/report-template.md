# Knowledge Video Report Template

Use this template for reports, essays, research notes, briefings, and scripts derived from knowledge-heavy videos or transcripts.
Adapt headings to the user's requested document type and language, but keep the required reasoning functions.

Do not produce a vague report that only names a theme, such as "from mental math to tool use", without explaining the actual example, why the speaker uses it, and how it supports the argument.

## Title

`[Working title that names the source question or thesis]`

## Document Goal

- User request:
- Intended reader:
- Output type:
- Desired depth:
- Final language: requested language, or current conversation language if the user did not specify one.

## Source Status

- Source artifacts used:
- Missing artifacts:
- Evidence quality:
- Transcript or timestamp availability:
- Known source gaps:
- Degradation decisions:

## Core Question and Source Thesis

### Core Question

State the question the source is trying to answer.

### Source Thesis

State the source-faithful thesis. Do not include critique or user extensions here.

### Narrative Spine

Summarize the source's main route:

```text
setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion
```

## Full Source Reconstruction

This section is Source-only.

Required content:

- Reconstruct the source in its own order unless there is a strong user reason to reorganize.
- Preserve the speaker's main transitions.
- Keep concrete examples attached to the claims they support.
- Include evidence anchors such as timestamps, transcript ids, segment ids, or artifact names when available.
- Mark gaps or uncertain spans.

Suggested structure:

### Opening Setup

What situation, question, or tension starts the source?

### Development

How does the speaker build the argument step by step?

### Turning Points

Where does the speaker change frame, concept, scale, or conclusion path?

### Conclusion Path

How does the speaker arrive at the final point?

## Speaker's Language Logic and Rhetorical Progression

Explain how the speaker's wording, sequence, and transitions produce the conclusion.

Include:

- Repeated terms or contrasts.
- Changes in pronouns, scale, framing, or category.
- Questions the speaker asks and answers.
- Moves from familiar examples to abstract claims.
- Moves from description to evaluation or prescription.
- Any rhetorical device that changes the reader's interpretation.

Use evidence where possible. Do not merely label the rhetoric; explain how it works.

## Concrete Examples

For each important example, use this unit:

```markdown
### Example: [specific example name]

- What the example is: [concrete description]
- Where it appears: [timestamp, transcript id, segment id, or artifact reference]
- Why it is introduced: [local argumentative purpose]
- How it works: [step-by-step reasoning inside the example]
- What claim it supports: [Source claim id or text]
- What it does not prove: [limits or overreach guard]
- Later use in the report: [section or synthesis it supports]
```

Rules:

- Explain the example before abstracting it.
- Do not replace an example with a generic label.
- If an example is vivid but not central, mark it as illustrative rather than foundational.
- If an example is missing detail because the transcript is incomplete, say so.

## Argument Chain

Show the reasoning path in order:

```text
setup -> tension/problem -> example -> concept shift -> claim -> implication -> conclusion
```

For each link, include:

- Source move:
- Evidence:
- Reasoning bridge:
- Claim category: Source, Inference, or Extension.
- Continuity check: why the next link follows.

No link should jump directly from example to grand conclusion without the intermediate reasoning.

## Concept Map and Key Terms

For each key concept:

```markdown
### [Concept]

- Source meaning:
- Evidence:
- Related examples:
- Related claims:
- Contrast or neighboring term:
- Later use in report:
- Category: Source / Inference / Extension
```

Rules:

- Define concepts from the source before using outside definitions.
- If the report adds a framework, label it as Extension.
- Show concept transitions, not only definitions.

## Source / Inference / Extension Map

Use one of these forms depending on document length.

### Compact Form

Label sections or paragraphs:

- `[Source]`
- `[Inference]`
- `[Extension]`

### Detailed Form

```markdown
| Claim | Category | Evidence or origin | Confidence | Document use |
| --- | --- | --- | --- | --- |
|  | Source |  |  |  |
|  | Inference |  |  |  |
|  | Extension |  |  |  |
```

Operational rules:

- Source: what the source says or clearly implies through its own logic.
- Inference: what the composer derives from the source.
- Extension: user ideas, critique, applications, outside frameworks, or recommendations.
- Extension can be useful, but it must not be written as if the source said it.
- In audited final reports, the Source section must cite registered claim ids
  from `claim_map.json`, such as `doc_claim_001`.
- A `source_partial` report must include `Partial Scope` in the title or source
  status section and must not fill missing source sequence from secondary
  material.

## Final Report Closure

For the final report loop, keep these artifacts:

```text
draft_report.md -> critique.md -> revised_report.md -> quality_gate.json -> final_report.md
```

`quality_gate.json` is the machine-readable authority for whether
`final_report.md` may exist. If the gate blocks, revise the report candidate
instead of weakening the gate.

## User-Extension Section

Use this when the user asks to add their own ideas, applications, critique, or expanded theory.

Suggested headings:

### Extension Goal

What the user wants to add.

### Fit With Source Logic

Which source claims or examples make the extension plausible.

### Added Material

What is added beyond the source.

### Verification Needed

What would need external evidence before being asserted as fact.

### Attribution Boundary

State what must not be attributed to the source.

Template language:

```text
The source establishes [source claim]. A compatible extension is [extension], but this added point is not directly stated in the source and would require [verification] before being treated as factual.
```

## Critique, Limits, and Uncertainty

Cover:

- Source gaps.
- Transcript gaps.
- Claims with weak or indirect evidence.
- Examples that may not support as much as the source suggests.
- Alternative interpretations.
- User-requested critique, clearly labeled as Inference or Extension.

Rules:

- Do not let critique rewrite the source reconstruction.
- Do not hide missing evidence.
- Do not overstate extensions as conclusions.

## Final Synthesis and Practical Implications

Synthesize only after reconstruction, examples, concepts, and argument chain are clear.

Include:

- Source-faithful synthesis.
- Inference-based synthesis, if useful.
- Extension or practical implications, if requested.
- What the reader should now understand or do.

Practical implications must say whether they come from the source, from inference, or from extension.

## Anti-Patterns to Reject

Reject and revise drafts that:

- Say "the speaker moves from X to Y" without explaining X, Y, and the transition.
- Mention an example by name but do not explain how it supports a claim.
- State a conclusion before reconstructing the source path.
- Use broad labels such as "cognitive shift", "tool use", "agency", or "modernity" without source-grounded explanation.
- Blend user ideas into the source thesis.
- Hide transcript gaps or low-confidence evidence.
- Present a smooth essay that is elegant but not auditable.

## Short Report Variant

For a brief or executive summary, keep the same functions in compressed form:

1. Source status.
2. Core question and thesis.
3. Two to five source reconstruction bullets with examples.
4. Argument chain.
5. Source / Inference / Extension split.
6. Limits and practical implications.

Short does not mean abstract. Important examples still need concrete explanation.
