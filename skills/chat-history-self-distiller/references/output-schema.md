# Output Schema

Analyzer output directory:

```text
_manifest.json
_normalized/
  messages.json
_analysis/
  structure.json
  participant_map.json
  stats.json
  behavior_patterns.json
  principle_statements.json
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
- `_analysis/principle_statements.json`: extracted rule-like, redefining, causal, attribution-reframing, or belief-reversal statements.
- `_analysis/cognitive_break_windows.json`: candidate windows where long messages, topic-domain spread, and principle statements cluster.
- `_analysis/core_thread_burn.md`: mandatory pre-report synthesis scratchpad for deep reports and personal skills.
- `_analysis/candidate_answers.json`: optional internal candidate-answer ledger for interpretive questions; do not expose raw mechanics as the final answer.
- `_evidence/evidence_ledger.json`: claim-to-evidence index. It may start empty after the analyzer run and be populated during interpretation.
- `_findings/findings.json`: structured findings grouped by route, confidence, and status.
- `_review/preview.md`: user-facing confirmation preview before finalizing sensitive conclusions or generated skills.
- `_exports/`: final report artifacts when requested.

Final `_manifest.json` fields after interpretation:

```json
{
  "mode": "deep-self-skill",
  "taskRoute": "profile + deep-self-skill",
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
- `One Problem Hypothesis`
- `Contradiction Test`
- `Mandatory Verification`
- `Core Thread`
- `Evidence That Does Not Fit`
- `Burn Result`: `Core Thread Found`, `Weak Thread`, or `No Stable Thread`

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
