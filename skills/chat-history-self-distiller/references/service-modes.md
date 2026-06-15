# Service Modes

Use these modes to keep the analysis commercially usable instead of over-processing every request.

## Orientation

Goal: decide whether the data can support the user's real question.

Deliver:

- detected format and fields
- sender list and target alias check
- time span and message volume
- 3-5 likely analysis directions
- questions needed before deep analysis

Stop here if the data is too small, malformed, or the user's target is ambiguous.

## Standard Report

Goal: give useful conclusions without generating a reusable skill.

Deliver:

- person or group profile
- identity lock summary
- current dominant line plus historical roots or active secondary lines when relevant
- evidence table
- high/medium/low confidence labels
- uncertainty and missing data
- practical reading of the findings

If the user asks a direct interpretive question, include a concise answer in the response and record the candidate-answer logic in `_analysis/candidate_answers.json` when a run folder is being produced.

## Report Pack

Goal: produce a readable product-like folder without collapsing every topic into one main report.

Deliver:

- `00_overview.md`: stable multi-line persona/profile report
- `01_behavior_language.md`: speech style and interaction rhythm
- `02_relationship_network.md`: relationship roles and dynamics
- `03_emotional_trajectory.md`: emotional and growth trajectory
- `04_cognitive_style.md`: thinking, values, judgment priority, decision style
- optional `05_self_review.md`: first-person self-review when requested
- optional `08_user_questions_and_evidence.md`: explicit user questions and answers
- optional `09_mental_health_signals.md`: psychological/mental-health signal analysis when requested
- optional `10_targeted_questioner_handoff.md`: downstream handoff for targeted questioning, calibration, or final-report workflows
- optional `99_corrections_and_review.md`: user corrections and what changed

The main report may point to user-question and mental-health files, but should not absorb them wholesale.

If a downstream handoff is produced, it must not become a second report or a question interview. It should summarize upstream locks, seed claims, follow-up leverage points, report routing, question routing, and compatibility boundaries for a later workflow.

## Deep Self Skill

Goal: turn long-term chat evidence into a reusable personal skill.

Deliver:

- `self.md`
- `persona.md`
- `evidence.md`
- `meta.json`
- draft `SKILL.md`

This mode requires a preview and correction loop before installation.

## Relationship Map

Goal: understand multiple speakers and relationship dynamics.

Deliver:

- per-speaker profiles
- interaction patterns
- conflict/support themes
- privacy-aware summary

Never present third-party portraits as complete personality truth.

## Mental-Health Signals

Goal: answer a user's explicit psychological/mental-health concern without turning the whole profile into a diagnosis.

Deliver:

- signal categories with evidence and dates
- protective factors and counter-evidence
- confidence and limits
- professional-evaluation wording when appropriate

Do not recommend medication changes. Do not infer disorders from keyword counts alone. Keep this output separate from stable persona files unless the user confirms it as part of their self-model.
