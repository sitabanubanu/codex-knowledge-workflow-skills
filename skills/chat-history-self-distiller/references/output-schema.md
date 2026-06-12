# Output Schema

Analyzer output directory:

```text
_manifest.json
_normalized/
  messages.json
_analysis/
  structure.json
  participant_map.json
  identity_lock.md
  stats.json
  behavior_patterns.json
  principle_statements.json
  contradictions.json
  cognitive_break_windows.json
  core_thread_burn.md
  candidate_answers.json
  split_info.json
  cross_validation.json
  run_summary.json
_split/
  part_001.json
_profiles/
  _sender_list.json
  {sender}.json
_samples/
  {sender}_samples.json
_evidence/
  evidence_ledger.json
_findings/
  findings.json
_review/
  preview.md
_exports/
  00_overview.md
  01_behavior_language.md
  02_relationship_network.md
  03_emotional_trajectory.md
  04_cognitive_style.md
  05_self_review.md
  08_user_questions_and_evidence.md
  09_mental_health_signals.md
  99_corrections_and_review.md
  report.md
draft_skill/
  self.md
  persona.md
  evidence.md
  meta.json
  SKILL.md
```

Core file meanings:

- `_manifest.json`: run scope, input type, selected mode, task route, privacy boundary, and created time.
- `_normalized/messages.json`: normalized records from native JSON chat data or adapted exports.
- `_analysis/participant_map.json`: raw sender buckets, human participant buckets, non-human/system buckets, confirmed aliases, alias candidates, mention signals, unresolved names, and tokens excluded from speech-style/top-word analysis.
- `_analysis/identity_lock.md`: human count, canonical target, confirmed aliases, excluded non-human/system buckets, and gender/pronoun source. This lock must be copied into or summarized by final profile reports.
- `_analysis/principle_statements.json`: extracted rule-like, redefining, causal, attribution-reframing, or belief-reversal statements.
- `_analysis/contradictions.json`: ranked structural tension candidates. These are inputs for Core Thread Burn, not final conclusions.
- `_analysis/cognitive_break_windows.json`: candidate windows where long messages, topic-domain spread, and principle statements cluster.
- `_analysis/core_thread_burn.md`: mandatory pre-report synthesis scratchpad for deep reports and personal skills.
- `_analysis/candidate_answers.json`: optional internal candidate-answer ledger for interpretive questions; do not expose raw mechanics as the final answer.
- `_evidence/evidence_ledger.json`: claim-to-evidence index. It may start empty after the analyzer run and be populated during interpretation.
- `_findings/findings.json`: structured findings grouped by route, confidence, and status.
- `_review/preview.md`: user-facing confirmation preview before finalizing sensitive conclusions or generated skills.
- `_exports/`: final report artifacts when requested, including `report.md` for a single report or numbered report-pack files for `report-pack`.
- `_exports/08_user_questions_and_evidence.md`: explicit user questions, selected answers, evidence, complications, confidence, and whether each answer should update the main profile.
- `_exports/09_mental_health_signals.md`: optional sensitive-topic report for psychological/mental-health signal analysis. It is separate from the main persona report and must not be treated as a diagnosis.
- `_exports/99_corrections_and_review.md`: user corrections, accepted/narrowed/held hypotheses, and what changed in the report.

Final `_manifest.json` fields after interpretation:

```json
{
  "mode": "deep-self-skill",
  "taskRoute": "profile + deep-self-skill",
  "deliveryPath": "deep-self-skill",
  "pathReason": "user explicitly requested reusable self/persona memory",
  "requiredDeliverables": [
    "_analysis/participant_map.json",
    "_analysis/core_thread_burn.md",
    "draft_skill/self.md",
    "draft_skill/persona.md",
    "draft_skill/evidence.md",
    "draft_skill/meta.json",
    "draft_skill/SKILL.md",
    "_review/preview.md"
  ],
  "explicitNonGoals": [
    "do not install generated skill before user confirmation"
  ],
  "interpretationStatus": "draft-skill-generated",
  "finalDeliverables": [
    "draft_skill/self.md",
    "draft_skill/persona.md",
    "draft_skill/evidence.md",
    "draft_skill/meta.json",
    "draft_skill/SKILL.md"
  ],
  "requiresUserConfirmation": true,
  "previewPath": "_review/preview.md",
  "behaviorPatternsAvailable": true,
  "principleStatementsAvailable": true,
  "structuralTensionsAvailable": true,
  "cognitiveBreakWindowsAvailable": true,
  "coreThreadBurnPath": "_analysis/core_thread_burn.md"
}
```

`_analysis/principle_statements.json` shape:

```json
{
  "note": "Heuristic sentence-structure matches, not final conclusions.",
  "statementsBySender": {
    "me": [
      {
        "date": "2026-01-01",
        "datetime": "2026-01-01 20:00:00",
        "pattern": "redefinition",
        "matched": "X不是Y，X是Z",
        "content": "..."
      }
    ]
  },
  "summary": {
    "me": {
      "total": 12,
      "patterns": { "redefinition": 3 }
    }
  }
}
```

`_analysis/contradictions.json` shape:

```json
{
  "note": "Structural tension candidates, not proof of inconsistency.",
  "priorityOrder": [
    "long_denial_to_admission",
    "principle_vs_behavior",
    "stance_reversal"
  ],
  "contradictionsBySender": {
    "me": [
      {
        "tensionId": "T001",
        "type": "long_denial_to_admission",
        "detectorType": "Type 6",
        "status": "tensionCandidate",
        "confidence": "High",
        "burnPriority": 1,
        "poleA": {
          "source": "principle_statements",
          "dateRange": "2025-01-01 to 2025-06-01",
          "occurrences": 3,
          "topicDomains": ["self"],
          "evidence": []
        },
        "poleB": {
          "source": "normalized_messages",
          "date": "2026-01-01",
          "stance": "admission",
          "topicDomains": ["self"],
          "content": "..."
        },
        "tensionDescription": "..."
      }
    ]
  },
  "summary": {
    "totalContradictions": 1,
    "byType": { "long_denial_to_admission": 1 },
    "byConfidence": { "High": 1 }
  }
}
```

`_analysis/cognitive_break_windows.json` shape:

```json
{
  "note": "Candidate cognitive restructuring windows. Verify manually.",
  "windows": [
    {
      "weekStart": "2026-01-05",
      "weekEnd": "2026-01-11",
      "sender": "me",
      "longMessageCount": 5,
      "principleStatementCount": 2,
      "topicDomains": ["self", "relationship", "future"],
      "status": "suspected_cognitive_break",
      "coreQuotes": []
    }
  ]
}
```

`_analysis/core_thread_burn.md` required sections:

- `Raw Quote Pile`
- `Candidate Lines`
- `One Problem Hypothesis`
- `Contradiction Test`: must start from `_analysis/contradictions.json` when tension candidates exist.
- `Mandatory Verification`
- `Time-Weight Check`
- `Core Thread`
- `Current Dominant Line`
- `Evidence That Does Not Fit`
- `Burn Result`: `Core Thread Found`, `Multi-Line Model`, `Weak Thread`, or `No Stable Thread`

`_analysis/identity_lock.md` required shape:

```markdown
# Identity Lock

| Field | Value | Source |
|---|---|---|
| Target canonical sender | ... | participant_map |
| Confirmed aliases | ... | participant_map / user |
| Human participants counted | ... | participant_map |
| Excluded non-human/system buckets | ... | participant_map |
| Gender/pronoun source | unknown / user-provided / direct self-statement | ... |

## Prohibited Inferences

- Do not count group names, empty sender buckets, system buckets, forwarded-chat speakers, @mentions, or old display names as people.
- Do not infer gender from pronoun counts, language style, nicknames, emoji, or topics.
```

`_analysis/candidate_answers.json` optional shape:

```json
{
  "question": "用户的问题",
  "selectedCandidateId": "A",
  "candidates": [
    {
      "id": "A",
      "answer": "one sentence",
      "support": [
        { "date": "2026-01-01", "quote": "...", "source": "_samples/me_samples.json" }
      ],
      "complication": "...",
      "confidence": "Medium",
      "decision": "selected"
    }
  ],
  "userFacingAnswer": "plain answer without detector mechanics"
}
```

`_exports/08_user_questions_and_evidence.md` required shape:

```markdown
# User Questions And Evidence

## Q1: 用户原问题

Short answer:

Evidence:
- date/source + quote or pointer
- date/source + quote or pointer

Complication:

Relationship to main report:
- promote to main report / summarize only / keep as topical answer / do not promote

Confidence:
```

`_review/preview.md` required structure:

```markdown
# Confirmation Preview

## Core Claims
| Claim | Tier | Confidence | Evidence |
|---|---|---|---|

## Persona Rules
| Rule | Tier | Confidence | Evidence |
|---|---|---|---|

## Risky Inferences
| Inference | Why Risky | What To Confirm |
|---|---|---|

## Blind Spots
| Missing Area | Effect |
|---|---|

## Questions For User
1. ...
```

Evidence claim types:

- `Direct Quote`: dated quote or source section.
- `Keyword Cross Validation`: repeated keyword/theme evidence across months or sections.
- `Sequence Pattern`: behavior pattern from `_analysis/behavior_patterns.json`.
- `Statistical Pattern`: count, timing, length, sender share, or recurrence.
- `Human Inference`: interpretation built from evidence; must be Medium/Low unless user confirmed.

Delivery tiers:

- `Confirmed Pattern`: can enter `self.md` or `persona.md`.
- `Probable Pattern`: can enter final files only with a confirmation note.
- `Hypothesis`: stays in `preview.md` or `evidence.md` until confirmed.

Runtime status:

- `SmokeTested`: analyzer ran on sample or real data.
- `PartiallySmokeTested`: only part of the workflow ran.
- `RuntimeBlocked`: runtime could not be exercised because of environment, credentials, cost, or missing dependency.
- `RuntimeUnverified`: no runtime check attempted.
- `RuntimeFailed`: minimal run failed.
