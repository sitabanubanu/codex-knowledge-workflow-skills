# Quality Gates

Run these gates before final delivery. They turn fluent analysis into an auditable deliverable.

## Gate 1: Scope

- target person, people, documents, or folder is clear
- time span or document span is known
- selected route is named
- output mode is named

If not, deliver orientation only.

## Gate 2: Parse Integrity

- input format was detected
- required fields were mapped
- failed files or missing fields were listed
- non-native files were converted or explicitly blocked
- expected analyzer outputs are either present or explicitly marked missing

Fail this gate if the agent invents the contents of a missing analyzer file.

## Gate 3: Evidence Coverage

High-confidence behavioral claims need at least 3 independent evidence points across different months, years, or sections.

Medium-confidence claims need at least 2 evidence points, or one strong quote plus supporting statistics.

Low-confidence claims must be labeled and should not appear as final truth.

Delivery tiers:

- `Confirmed Pattern`: High confidence and safe for `self.md` or `persona.md`.
- `Probable Pattern`: Medium confidence or context-limited; may appear in final files only with a confirmation note.
- `Hypothesis`: Low confidence or mostly inference; keep in `_review/preview.md` or `evidence.md`, not as stable memory.

Fail this gate if a Medium/Low/Hypothesis claim is phrased as a fixed identity label.

## Gate 4: Attribution

- every quote has date/time or section/page when available
- every relationship claim names the side(s) providing evidence
- every document claim names the source file

## Gate 4.5: Participant Identity

Mandatory before profile reports, relationship maps, generated personal skills, or sensitive identity/persona interpretation.

Check `_analysis/participant_map.json`:

- `humanParticipants` are the only people counted in the report
- `nonHumanBuckets` are excluded from participant count and personality analysis
- target speaker is resolved to one canonical sender bucket
- aliases are separated into confirmed aliases and candidates
- @mentions, forwarded-chat speakers, old display names, group names, and empty sender buckets are not counted as separate people
- participant names, aliases, group names, reply/file/link/media/system terms are not used as catchphrase or speech-style evidence
- final report includes a short participant summary with human count, canonical sender buckets, confirmed aliases, and excluded non-human buckets

Fail this gate if:

- the report counts a system/group/empty sender bucket as a person
- the report turns an alias or @mention into an extra person without evidence
- the report treats a participant name, old nickname, group name, or metadata token as a catchphrase
- the agent proceeds to deep interpretation while target identity or participant count is uncertain

## Gate 5: Core Thread Burn

Mandatory before deep profile reports, generated personal skills, or sensitive identity/persona interpretation.

Check `_analysis/core_thread_burn.md`:

- contains 15-20 mixed direct quotes
- states one recurring-problem hypothesis, or explicitly says no stable hypothesis is supported
- tests the hypothesis against contradictory evidence
- verifies each core claim with 3 dated quotes
- names concrete falsifying evidence for each core claim
- names at least one alternative explanation
- chooses a burn result: `Core Thread Found`, `Weak Thread`, or `No Stable Thread`
- compresses the working core thread into 1-2 sentences only when verified
- names strong evidence that does not fit

Fail this gate if:

- the report jumps from samples directly to conclusions
- the core thread is only a personality label
- contradictory evidence is ignored
- falsification conditions are vague or missing
- alternative explanations are not considered
- `Weak Thread` or `No Stable Thread` is treated as if it were `Core Thread Found`
- the burn file does not exist for a deep report or draft personal skill

If the core thread fails contradiction or falsification tests, downgrade the deliverable to an evidence report or rerun the burn. A failed burn is acceptable; a forced thread is not.

## Gate 5.5: Small-To-Large Report Shape

For deep profile/self analysis, the report should grow from evidence instead of filling personality boxes.

Check:

- report opens with a concrete quote, scene, or observation
- includes 3 micro-scenes with dates and quotes
- explains what larger pattern these scenes suggest
- states what the pattern cannot explain
- states what evidence would change the conclusion
- keeps structured personality fields as an appendix unless the user requested them

Fail this gate if the report is mostly a checklist of traits, motivations, defenses, and growth claims without scene-level grounding.

## Gate 5.6: Candidate Answer Confirmation

For direct user questions, the agent must answer through a candidate loop before final output.

Check:

- 2-4 candidate answers were considered when the question is interpretive
- each candidate has source confirmation from samples or profiles
- each candidate has 2-3 supporting dated quotes or source pointers
- each candidate has at least one complicating or contradictory point
- final answer selects the best candidate and optionally names one meaningful alternate

Fail this gate if:

- the answer is just "evidence insufficient" without a best-effort candidate answer
- the answer treats "detector did not find X" as "X did not happen"
- the answer jumps from detector output directly to conclusion without quote/source confirmation

## Gate 5.7: User-Facing Answer Hygiene

Intermediate detector mechanics are not the answer.

Do not show these unless the user asks for methodology:

- regex families or sentence templates
- raw detector counts
- internal file names as the main explanation
- long process narration

Fail this gate if the final answer talks more about detector labels than about the user's question.

## Gate 5.8: Non-Horoscope Specificity

Core identity claims must be hard to paste onto a generic person.

For each core claim, check:

- Would this claim still sound true for 100 random college students? If yes, it is too generic.
- Does it have dated scenes, direct quotes, or concrete artifacts?
- Does it state when the pattern fails or does not apply?
- Does it predict a recognizable response pattern in similar future situations?
- Is it written as `Trigger -> Processing move -> Output -> Boundary`, not just a label?

Fail this gate if:

- the core claim is only "thinker", "creator", "analyst", "sensitive", "independent", or similar broad wording
- the claim has no failure boundary
- the claim lacks concrete artifacts, dates, or quotes
- user correction is accepted wholesale without checking evidence and scope

## Gate 5.9: Anti-Appeasement Correction Handling

User corrections are evidence, not commands.

For each correction, classify the response:

- `Accept`
- `Narrow`
- `Hold As Hypothesis`
- `Ask`
- `Resist`

Fail this gate if a user-preferred label is immediately promoted to the core thread without evidence, scope limits, and an alternative explanation.

## Gate 6: Privacy

- third-party private content is minimized
- third-party portraits are partial and context-bound
- sensitive quotes are shortened unless necessary

## Gate 7: Confirmation

Mandatory before:

- installing a generated personal skill
- writing long-term self memory
- presenting sensitive identity claims as high confidence
- exporting a formal report meant to be shared

Preview:

- top 5 self-memory claims
- top 5 persona rules
- 3 highest-risk inferences
- 3 known blind spots or missing data areas
- concrete user questions

Fail this gate if `_review/preview.md` still contains only scaffold/template text.

## Gate 8: Reproducibility

The run folder should contain:

- `_manifest.json`
- `_analysis/run_summary.json`
- `_analysis/structure.json`
- `_analysis/stats.json`
- `_analysis/behavior_patterns.json` when generated by this skill version
- `_analysis/principle_statements.json` when generated by this skill version
- `_analysis/cognitive_break_windows.json` when generated by this skill version
- `_analysis/core_thread_burn.md` for deep reports or generated personal skills
- `_evidence/evidence_ledger.json` or explanation for omission
- final report or draft skill outputs if requested

## Gate 9: Metadata Consistency

The final metadata must match the actual work performed.

Check:

- `_manifest.json.mode` matches the final deliverable mode.
- `_manifest.json.taskRoute` matches the final route.
- `_manifest.json.interpretationStatus` is present after interpretation.
- `_manifest.json.finalDeliverables` lists generated report or draft skill files.
- `_manifest.json.requiresUserConfirmation` is true for personal skills or sensitive identity/persona conclusions.
- `_manifest.json.previewPath` points to a populated preview when confirmation is required.
- `_manifest.json.coreThreadBurnPath` points to `_analysis/core_thread_burn.md` for deep reports or generated personal skills.
- `_analysis/run_summary.json` does not contradict `_manifest.json`.

Fail this gate if the manifest says `orientation` but the folder contains interpreted reports or `draft_skill/`.

## Gate 10: Generated Personal Skill Usability

A generated personal `SKILL.md` must be usable by another agent without reading the whole source analysis.

It must:

- say it is `DRAFT` until user confirmed
- instruct the agent to read `self.md`, `persona.md`, and `evidence.md` before making sensitive claims
- state data boundaries and privacy rules
- say user corrections override evidence-derived claims
- include "when to use" and "how to interact" rules

Fail this gate if the generated `SKILL.md` is only a summary and does not route the agent to the supporting files.
