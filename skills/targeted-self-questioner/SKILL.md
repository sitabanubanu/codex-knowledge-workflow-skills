---
name: targeted-self-questioner
description: Generate targeted follow-up questions, absorb user corrections, update claim weights, and produce calibrated personalized self-analysis reports from existing chat-history/persona analysis outputs. Use after chat-history-self-distiller or similar reports when the user wants targeted questions, report calibration, final self/persona reports, correction handling, growth direction, relationship-focused reports, execution-focused reports, or evidence-backed self-understanding.
---

# Targeted Self Questioner

## Purpose

Use this skill as a second-stage calibration workflow after an existing persona, chat-history, or self-analysis report already exists.

This skill does not replace upstream evidence analysis. It turns an initial model into targeted questions, absorbs user answers, updates claim weights, and writes a final question-driven report.

Core distinction:

- upstream analysis sees what the records support;
- this skill asks what would change the model;
- the final report preserves the chain from question to evidence to user correction to final judgment.

## Required Principle

Do not produce a generic questionnaire or a fixed one-size-fits-all personality report.

Questions follow leverage, not template.

Report shape follows evidence center of gravity.

Upstream locks are inherited by default.

## Navigation

Read references only when needed:

- `references/input-contract.md`: always read when starting from a folder, handoff file, or prior report.
- `references/report-routing.md`: read before choosing final report structure.
- `references/question-generation.md`: read before producing follow-up questions.
- `references/correction-policy.md`: read when processing user answers or objections.
- `references/weighting-rules.md`: read when ranking main lines, roots, turns, episodes, and noise.
- `references/final-report-template.md`: read before writing a calibrated final report.
- `references/quality-gates.md`: read before final delivery.

## Workflow

### Step 1: Identify Input

Prefer an upstream handoff file:

```text
_exports/10_targeted_questioner_handoff.md
```

If no handoff exists, use available prior-report files such as:

```text
_analysis/identity_lock.md
_analysis/core_thread_burn.md
_evidence/evidence_ledger.json
_analysis/candidate_answers.json
_review/preview.md
_exports/00_overview.md
_exports/08_user_questions_and_evidence.md
_exports/99_corrections_and_review.md
```

If the user only pasted a report or long self-description, proceed but mark source confidence lower because upstream evidence locks may be missing.

### Step 2: Inherit Locks

Before asking questions or writing a report, preserve upstream constraints:

- target person and canonical sender;
- participant count and alias boundaries;
- excluded system/non-human buckets;
- evidence / inference / user correction separation;
- mental-health and diagnosis boundaries;
- third-party privacy boundaries.

Do not reopen identity mapping unless the user explicitly asks for identity re-audit.

### Step 3: Build Claim Table

Extract a claim table from the prior analysis:

```text
Claim
Evidence pointer
Confidence
User-confirmation status
Risk
Potential report impact
Needs follow-up: yes/no
```

Do not ask about every claim. Only high-leverage claims should become questions.

### Step 4: Route The Report

Choose report shape by evidence center of gravity and user goal. Do not force every person into the same report.

Examples:

- relationship-heavy evidence -> relationship pattern, approach/withdrawal, conflict loops, choice standards;
- work/study-heavy evidence -> ability structure, execution model, constraints, growth path;
- creation/project/AI-heavy evidence -> creation thread, tool use, engineering/product thinking, output path;
- family-heavy evidence -> family role, responsibility boundary, long-term influence;
- mixed evidence -> multi-line model with appendices for low-weight material.

### Step 5: Generate Leverage Questions

Default: ask 5-8 questions. Maximum: 12.

Each question must be tied to:

- pending claim;
- evidence risk;
- what would change if the user confirms it;
- what would change if the user denies it.

Do not ask generic questions such as "What are your strengths?" unless tied to a concrete claim.

### Step 6: Process User Answers

Classify each answer:

- `Accept`: confirms and sharpens the claim.
- `Narrow`: makes the claim more specific.
- `Downgrade`: lowers the claim's weight.
- `Override`: provides a clear fact that replaces model inference.
- `Hold`: plausible but not sufficiently evidenced.
- `Resist`: conflicts with strong evidence; keep the tension visible.

User correction is modeling data, not an automatic command to flatter or conform.

### Step 7: Update Claims

Write or present:

```text
_claim_updates.md
_correction_log.md
```

If no files are requested, provide the same information in the answer.

### Step 8: Write Final Report

The final report must be question-driven, not column-driven.

For each high-weight section, preserve the chain:

```text
Question
Short answer
Why this question matters
Initial judgment
Key evidence
User correction
Weight change
Final judgment
Action impact
```

Do not mechanically fill every field for low-weight sections. Compress low-weight material into appendices or short notes.

## Output Modes

Choose the smallest mode that satisfies the user:

| Mode | Use When | Output |
|---|---|---|
| `brief` | user wants a fast calibration pass | 5-8 questions plus key claim risks |
| `deep` | user wants a full calibration workflow | claim table, question plan, answer processing, claim updates |
| `revision` | user says a report is wrong | correction classification and targeted rewrites |
| `final-report` | user already answered questions | question-driven final report |

## Default Output Files

When producing files, use:

```text
_question_plan.md
_user_answers.md
_claim_table.md
_claim_updates.md
_correction_log.md
_final_persona_report.md
```

Do not create extra README or process-history files unless the user asks.

## Final Check

Before final delivery, verify:

- upstream locks were inherited;
- every question can change a report decision;
- report routing matches evidence center of gravity;
- user corrections were classified, not blindly accepted;
- low-weight episodes did not occupy main-report space;
- final report preserved question -> evidence -> correction -> judgment chain;
- sensitive mental-health content is separate and not diagnostic unless explicitly requested as signal analysis.
