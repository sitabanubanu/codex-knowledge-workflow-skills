# Downstream Handoff

Use this reference when the current run may feed a separate targeted-questioning, calibration, or final-report workflow.

The goal is to help a downstream skill ask better questions without redoing the upstream evidence analysis or breaking identity, privacy, and source boundaries.

## Core Rule

The handoff is not a new report and not an interview. It is a compact contract:

```text
what is locked
what is supported
what is uncertain
what should be asked next
what must not be reinterpreted by default
```

## When To Produce It

Produce `_exports/10_targeted_questioner_handoff.md` when:

- the output mode is `report-pack`;
- the user wants a formal persona/self report that may need follow-up questions;
- the report contains Medium/Low claims that would materially change with user confirmation;
- the user has corrected prior reports and a downstream workflow needs those corrections;
- the user explicitly mentions a later targeted-questioning, final-report, or calibration skill.

For `orientation`, produce only a short "next questions" section unless the user explicitly asks for a handoff.

## Required Shape

```markdown
# Targeted Questioner Handoff

## 1. Upstream Locks
- Target canonical sender:
- User-provided aliases:
- Confirmed aliases:
- Human participants counted:
- Excluded non-human/system buckets:
- Gender/pronoun source:
- Mental-health boundary:
- Third-party privacy boundary:

## 2. Source Materials
| File | Purpose | Notes |
|---|---|---|
| _analysis/identity_lock.md | identity boundary | ... |
| _analysis/core_thread_burn.md | core-line reasoning | ... |
| _evidence/evidence_ledger.json | claim evidence | ... |
| _analysis/candidate_answers.json | direct-question candidates | optional |
| _review/preview.md | risky claims and blind spots | ... |
| _exports/99_corrections_and_review.md | user corrections | optional |

## 3. Current Model
- Current dominant line:
- Historical root:
- Active secondary lines:
- Contextual or weak lines:
- Downgraded or excluded lines:
- Evidence that does not fit:

## 4. Claim Table Seed
| Claim | Tier | Confidence | Evidence Pointer | Risk | Needs Follow-up |
|---|---|---|---|---|---|

## 5. Follow-Up Leverage Points
| Point | Why It Matters | If Confirmed | If Denied | Suggested Question |
|---|---|---|---|---|

## 6. Suggested Report Routing
- Evidence center of gravity:
- Sections to emphasize:
- Sections to keep short:
- Candidate appendices:

## 7. Suggested Question Routing
- Highest-leverage question areas:
- Do not ask / avoid over-weighting:
- User corrections already applied:

## 8. Compatibility Contract
- Do not override `identity_lock.md` unless the user explicitly asks for identity re-audit.
- Do not reinterpret `participant_map.json` by default.
- Do not promote system buckets, empty senders, group names, forwarded-chat names, @mentions, or alias candidates into people.
- Preserve evidence / inference / user correction separation.
- Preserve mental-health boundaries and keep sensitive-topic analysis separate.
- Do not turn downstream user correction into automatic flattery or automatic truth; classify it first.
```

## Follow-Up Leverage Point Rule

A follow-up point is valid only if the user's answer could change at least one important report decision:

- confirm or weaken a current dominant line;
- demote a historical root to an episode;
- promote an active secondary line to the main report;
- split one over-broad claim into narrower claims;
- move a user-question answer into or out of the main report;
- change report routing, such as relationship-centered, work-centered, creation-centered, family-centered, or comprehensive.

Do not include generic questions such as "what are your strengths?" or "what are your goals?" unless tied to a concrete claim and evidence risk.

Use this shape for each point:

```text
Pending claim:
Why it matters:
Current evidence:
Risk:
If user confirms:
If user denies:
Suggested question:
```

## Report Routing Hints

Report shape follows evidence center of gravity. Do not force every person into the same final structure.

Common centers:

- relationship/romance heavy: emphasize approach/withdrawal, attachment signals, conflict loops, standards, and relationship timeline;
- work/study heavy: emphasize ability structure, execution model, constraints, growth path, and practical strategy;
- AI/creation/project heavy: emphasize creation thread, tool use, engineering/product thinking, and output path;
- family/origin heavy: emphasize family role, responsibility boundary, long-term influence, and current correction;
- friendship/group-chat heavy: emphasize social role, group function, interaction style, and relationship network;
- emotion/mental-health heavy: emphasize triggers, regulation, protective factors, and limits; keep diagnosis separate;
- mixed evidence: use a multi-line model and keep low-weight material in appendices.

## Weight And Placement

Weight must affect placement, length, and tone, not only labels.

- Core/current dominant lines may be in the main handoff model.
- Historical roots may be included, but must not override recent evidence.
- Active secondary lines may receive follow-up questions.
- Episodes and low-weight material belong in "Do not over-weight" or appendices.
- Noise should be omitted unless it protects against a known false interpretation.

## Metadata

When the handoff is produced, add it to:

- `_manifest.json.finalDeliverables`
- `_analysis/run_summary.json.finalDeliverables`, when run summary is updated

Optional manifest field:

```json
{
  "downstreamHandoffPath": "_exports/10_targeted_questioner_handoff.md"
}
```
