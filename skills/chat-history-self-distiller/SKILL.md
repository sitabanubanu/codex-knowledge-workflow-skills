---
name: chat-history-self-distiller
description: Analyze large Chinese chat exports and adjacent long personal/document datasets without loading the whole file, separate speakers or document sections, route the task, build evidence-backed reports, and optionally generate a reusable self/persona skill draft. Use for requests like "分析我的聊天记录", "从群聊记录分析我", "把多年聊天蒸馏成 skill", "群聊人物画像", "分析多份聊天/文档里的主题和关系", or "用聊天记录生成 self/persona".
metadata:
  short-description: Evidence-backed chat-to-self/persona distillation
---

# Chat History Self Distiller

## Critical First Rule

**Do not `Read` a large raw chat file first.** Run the bundled analyzer before inspecting content. The raw file is evidence storage, not the first analysis surface.

If the analyzer fails, read the error and inspect only the minimum structure needed to fix parsing. Do not manually recreate the whole pipeline unless the tool is unavailable.

Use this skill when the user wants to analyze large chat histories, especially Chinese group chats or long personal chat exports, to understand people, relationships, speech patterns, growth trajectory, recurring themes, contradictions, or to generate a reusable self/persona skill. It may also guide adjacent long-document analysis when the document is being used as behavioral, relationship, or long-term evidence.

Core rule: do not `Read` an entire large chat file. First run the bundled analyzer, then inspect its structured outputs and sampled evidence.

## What This Skill Does

This skill combines two workflows:

- Large chat evidence analysis: structure detection, stats, chunking, per-sender profiles, strategic sampling, and cross-time evidence validation.
- Self/persona distillation: turn verified evidence into `self.md`, `persona.md`, `evidence.md`, `meta.json`, and a generated `SKILL.md` draft.

It is designed for commercial-grade reliability: explicit data boundaries, reproducible intermediate files, evidence confidence, user confirmation, correction handling, and exportable deliverables.

## Navigation

Read references only when needed:

- `references/input-adapters.md`: when input is not already a JSON chat export.
- `references/task-router.md`: when the request could mean profile, relationship, theme, conflict, timeline, paper/report review, or self-skill generation.
- `references/analyzer-modules.md`: when adding or selecting a specialized analyzer such as conflict, duplication, inconsistency, timeline, or claim extraction.
- `references/quality-gates.md`: before final delivery, especially for high-impact conclusions or generated personal skills.
- `references/service-modes.md`: when choosing `orientation`, `standard-report`, `deep-self-skill`, or `relationship-map`.
- `references/output-schema.md`: when writing or inspecting deliverable files.
- `references/downstream-handoff.md`: when a report may feed a follow-up questioning, calibration, or final-report skill.

## Product Modes

Choose the smallest mode that can satisfy the user's current decision:

| Mode | When To Use | Deliverable | Confirmation |
|---|---|---|---|
| `orientation` | User is exploring, file quality is unknown, or the request is broad | brief data map, top senders, feasibility, likely next questions | ask before deep interpretation |
| `standard-report` | User wants to understand one person or one group | evidence-backed portrait/report with confidence labels | confirm uncertain or sensitive claims |
| `deep-self-skill` | User wants a reusable personal skill or long-term self memory | `self.md`, `persona.md`, `evidence.md`, `meta.json`, draft `SKILL.md` | mandatory preview and correction |
| `report-pack` | User wants a folder of readable reports, comparisons, or multi-angle analysis artifacts | overview report, focused sub-reports, participant map, evidence ledger | confirm identity and sensitive claims |
| `team/relationship-map` | User cares about several people and dynamics | per-person profiles plus relationship dynamics | confirm names, aliases, and privacy boundary |

Default ladder:

1. Run `orientation` first when the task direction or input quality is unclear.
2. Move to `standard-report` when the user has a clear target and wants conclusions.
3. Move to `report-pack` when the user asks for multiple readable files, comparison packs, or a more product-like report folder.
4. Move to `deep-self-skill` only when the user explicitly wants a reusable skill/memory.

## Commercial Acceptance Criteria

A deliverable is product-quality only if it has:

- Clear scope: whose records, what time span, what output mode.
- Reproducible run folder with analyzer outputs.
- Evidence ledger linking major claims to quotes and dates.
- Confidence labels and uncertainty, not only fluent interpretation.
- Privacy treatment for third parties.
- User correction loop before installing or finalizing any personal skill.
- A next-step decision: stop, collect more data, deepen one theme, or install the generated skill.

## Data Boundary

- Default to local processing.
- Do not upload raw chat logs to external services.
- Do not expose third-party private content in final outputs unless the user explicitly asks and it is necessary.
- Analyze behavioral evidence, not medical or psychological diagnosis.
- For people other than the user, mark portraits as partial and context-bound.
- Every important conclusion should be supported by direct quotes and dates.

## Supported Inputs

Primary native input:

- JSON chat export with a message array.

Common supported shapes:

- WeChat-like: `messages[]` with `sender/content/timestamp/type`.
- Telegram-like: `messages[]` with `from/text/date/type`.
- Discord-like: `messages[]` with `author/content/timestamp`.
- Generic JSON: one large array field where each item has sender, content, and time fields.

Adjacent inputs are allowed only through an adapter step:

- TXT/CSV/HTML chat exports.
- Markdown, Word, PDF, Excel, or report files that should be treated as long evidence documents.
- Multi-document folders, after conversion into a normalized document map.

If the file is not native JSON, first use `references/input-adapters.md`. Do not pretend format support if no adapter or conversion path exists.

## Workflow

### Phase 0: Intake

Ask only what is needed:

1. Chat file path.
2. Target person or self aliases, if any.
3. Output goal: `report`, `self-skill`, or `both`.

If the user gives a broad request, assume `both` only when they explicitly want a reusable self/persona skill. Otherwise produce a report first.

Then classify the task using `references/task-router.md`. If direction is unclear, run `orientation` first and show the user the data map before deep interpretation.

### Phase 0.8: Delivery Path Lock

Before analysis, lock exactly one delivery path. This locks the product shape, not the interpretation quality.

Write this note in the run manifest if possible, and keep it visible in your working plan:

```text
Delivery path: orientation / standard-report / deep-self-skill / report-pack / team/relationship-map
Why this path: ...
Required deliverables: ...
Explicit non-goals: ...
Escalation rule: what user request or evidence would justify changing paths
```

Path contracts:

- `orientation`: produce a participant/data map, structure summary, feasibility notes, and next questions. Do not make deep personality claims.
- `standard-report`: produce a participant map, core-thread burn, one main evidence-backed report, evidence ledger, and preview when sensitive. Do not generate a reusable skill unless the user asks.
- `deep-self-skill`: produce a participant map, core-thread burn, `draft_skill/self.md`, `persona.md`, `evidence.md`, `meta.json`, draft `SKILL.md`, and confirmation preview. Do not install or present it as stable memory before user confirmation.
- `report-pack`: produce a participant map, identity lock, multi-line burn, `00_overview.md`, focused sub-reports such as `01_behavior_language.md`, `02_relationship_network.md`, `03_emotional_trajectory.md`, `04_cognitive_style.md`, optional `05_self_review.md`, optional `08_user_questions_and_evidence.md`, optional `09_mental_health_signals.md`, optional `_exports/10_targeted_questioner_handoff.md`, and an evidence ledger. Do not pretend this is a generated self skill or a completed interview-calibrated final report.
- `team/relationship-map`: produce participant identities, per-person summaries, relationship dynamics, boundaries, and privacy notes. Do not collapse several people into one voice.

Interpretive Conversation Mode may be used inside `standard-report`, `report-pack`, or `deep-self-skill` after the identity gate passes. If the user changes the goal mid-run, write a new path lock and explain which earlier deliverables are now out of scope. Do not mix delivery paths silently.

### Phase 0.5: Input Adapter

If the input is not native JSON chat data:

1. Convert or normalize it before analysis.
2. Preserve source references: file path, page/section/time, sender if available.
3. Write normalized material under `_normalized/`.
4. Continue only after the normalized data has stable `source`, `date/time or section`, `speaker/author if any`, and `content`.

### Phase 1-6: Run Local Analyzer

Run the bundled Node script. Do not rewrite this pipeline by hand:

```powershell
node "%USERPROFILE%\.codex\skills\chat-history-self-distiller\tools\analyze_chat.js" `
  --input "C:\path\to\chat.json" `
  --target "我的昵称,我,Me" `
  --out "C:\path\to\output_dir"
```

If no target is known, omit `--target`. The script will still create per-sender profiles.

If the user already knows real names, remarks, or old display names, pass them as an identity map to reduce ambiguity:

```powershell
node "%USERPROFILE%\.codex\skills\chat-history-self-distiller\tools\analyze_chat.js" `
  --input "C:\path\to\chat.json" `
  --identityMap "me=my_old_name|my_real_name;senderA=remark_name|old_display_name|real_name;senderB=nickname1|nickname2" `
  --out "C:\path\to\output_dir"
```

Tool contract:

- Input: native JSON chat export with detectable sender/content/time fields.
- Output: structured run folder with normalized messages, participant map, stats, profiles, samples, behavior patterns, cross-validation, and scaffolds for evidence and findings.
- If it fails: inspect the error, then inspect only field names or a tiny sample of the raw file. Prefer passing `--senderKey`, `--contentKey`, `--timeKey`, or `--typeKey` over manual analysis.
- If it succeeds: read generated outputs, not the raw file.

Outputs:

- `_manifest.json`: run scope, input type, selected mode, task route, and data boundary.
- `_normalized/messages.json`: normalized message records for native chat exports.
- `_analysis/structure.json`: field mapping, message count, senders, time span.
- `_analysis/participant_map.json`: raw sender buckets, human participant buckets, non-human/system buckets, alias candidates, outgoing mentions, unresolved names, and top-word exclusions.
- `_analysis/identity_lock.md`: created after the identity gate; the final report must not contradict it.
- `_analysis/stats.json`: yearly/monthly sender stats, text length, active hours, high-frequency words.
- `_split/part_*.json`: chunks for very large files.
- `_profiles/{sender}.json`: complete per-sender profile.
- `_samples/{sender}_samples.json`: first/last messages, monthly samples, long messages, keyword hits.
- `_analysis/cross_validation.json`: themes with evidence across different months.
- `_analysis/behavior_patterns.json`: non-keyword behavioral patterns such as emotion-to-analysis sequences, self-mockery followed by silence, repeated pings, and ignored questions.
- `_analysis/principle_statements.json`: sentence-structure matches where the speaker states rules, redefines concepts, explains causality, or overturns prior beliefs.
- `_analysis/contradictions.json`: ranked structural tension candidates, especially long denial to admission, principle vs behavior, and stance reversal. These are burn inputs, not verdicts.
- `_analysis/cognitive_break_windows.json`: suspicious time windows where long messages, multiple topic domains, and principle statements cluster.
- `_analysis/core_thread_burn.md`: mandatory synthesis scratchpad before deep reports or personal skills.
- `_analysis/candidate_answers.json`: optional candidate-answer ledger for direct user questions.
- `_evidence/evidence_ledger.json`: claim/evidence ledger scaffold.
- `_findings/findings.json`: structured findings scaffold.

### Phase 6.5: Participant Identity Gate

This gate is mandatory before any `standard-report`, `deep-self-skill`, relationship map, or sensitive identity/persona claim.

Read `_analysis/participant_map.json` before `_analysis/stats.json` or any samples. Do not infer people from top words, @mentions, forwarded-chat names, or group/system messages.

Confirm four things:

1. Raw sender buckets: every bucket in `rawSenderBuckets`.
2. Human participants: only buckets in `humanParticipants` count as people.
3. Non-human buckets: `nonHumanBuckets` are system, group, missing-sender, media, recall, call, location, red-packet, or other event records; they cannot become people.
4. Alias map: `confirmedAliases` are usable; `aliasCandidates`, `mentions`, `systemActors`, and `unresolvedNames` are leads that need evidence or user confirmation.

If the target person, participant count, or alias map is uncertain, stop at `orientation`, show the participant map briefly, and ask for confirmation. Do not continue to deep interpretation.

Rules:

- A display name, old nickname, real name, @mention, or forwarded-chat speaker is not a new person unless tied to one canonical sender bucket.
- A group name or system bucket is never a speaking person.
- `(空)` / empty sender buckets are missing-sender event records, not a participant.
- Do not use participant names, aliases, group names, `回复`, `引用消息`, `聊天记录`, `文件`, `链接`, `图片`, `视频`, or system-event terms as speech-style or catchphrase evidence.
- Do not infer gender from pronoun counts, language style, nicknames, emoji, topic interest, or "masculine/feminine" writing style. Gender/pronouns may be stated only when the user provided them, a direct self-statement exists, or the report marks them as `unknown`.
- Every final report or generated personal skill must include a short participant summary: human count, canonical sender buckets, confirmed aliases, and excluded non-human buckets.

Before writing any profile report, create a visible identity lock in `_analysis/identity_lock.md` or at the top of the report:

```text
Identity lock:
- Target canonical sender:
- Confirmed aliases:
- Human participants counted:
- Excluded non-human/system buckets:
- Gender/pronoun source: user-provided / direct self-statement / unknown
- Prohibited inferences: no gender/person count from pronoun frequency, top words, @mentions, forwarded-chat names, group names, or empty sender buckets
```

If the draft later says a different participant count, treats a system bucket as a person, or assigns gender from style/pronoun counts, the report fails and must be rewritten from the identity lock.

### Phase 7: Read Evidence, Not Raw Data

Read these outputs in order:

1. `_analysis/structure.json`
2. `_analysis/participant_map.json`
3. `_analysis/stats.json`
4. `_profiles/_sender_list.json`
5. `_samples/{target}_samples.json` for the target person
6. `_analysis/behavior_patterns.json`
7. `_analysis/principle_statements.json`
8. `_analysis/contradictions.json`
9. `_analysis/cognitive_break_windows.json`
10. `_analysis/cross_validation.json`

If an expected analyzer output is missing, do not reconstruct it from memory or invent its contents. Mark it as missing, continue only with available evidence, and downgrade any claim that depended on the missing file.

Only inspect original raw messages if a conclusion needs quote-level verification and the sampled evidence is insufficient.

Interpretation checklist:

- From `structure.json`: confirm field mapping, time span, target aliases, total message count, and whether the data can support the requested route.
- From `participant_map.json`: confirm participant count, canonical sender buckets, target resolution, non-human buckets, and aliases. If unresolved, stop and ask.
- From `stats.json`: inspect message share, active months/years, average length, active hours, and top words. Use this for footprint and speech style, not for deep personality claims by itself.
- From `_sender_list.json`: cross-check target speaker(s) against `participant_map.json`. If they disagree, trust the identity gate and stop for confirmation.
- From `{target}_samples.json`: inspect first/last messages, quarterly samples, long messages, keyword hits, and per-sender behavior patterns.
- From `behavior_patterns.json`: look for sequence-based evidence that keywords miss, especially emotion-to-analysis, self-mockery followed by silence, repeated pinging, ignored questions, and long rationalization after conflict.
- From `principle_statements.json`: look for how the target defines rules, causality, self/world models, and belief reversals. These are often stronger evidence than emotion words.
- From `contradictions.json`: inspect ranked structural tension candidates. Start with `long_denial_to_admission`, then `principle_vs_behavior`, then `stance_reversal`. Treat them as hypotheses to explain and verify, not proof of hypocrisy or inconsistency.
- From `cognitive_break_windows.json`: inspect weeks where multiple domains become intense at once. Treat them as candidate turning points, not confirmed transformations.
- From `cross_validation.json`: decide confidence. High-confidence claims need cross-time evidence; a vivid one-off quote is not enough.
- Only then synthesize the report. If a major claim lacks evidence, mark it `Low` or `Insufficient`.

### Phase 7.5: Multi-Line Core Thread Burn

This phase is mandatory before any `standard-report`, `deep-self-skill`, or sensitive profile interpretation. Do not skip from evidence reading directly to the report.

Create `_analysis/core_thread_burn.md` with this structure:

```markdown
# Core Thread Burn

## Raw Quote Pile
15-20 strong direct quotes. Do not classify, rank, or sort them by topic. Mix politics, friendship, self-talk, future imagination, conflict, care, and principles.

## Candidate Lines
Do not force one totalizing line. Generate 3-5 candidate lines when evidence supports them, for example:

- historical root line: an older wound, label, or formative self-story
- current dominant line: the pressure most active in the latest 6-12 months
- relationship/self-worth line
- study/work/future line
- body/health/emotion-regulation line
- expression/cognitive-style line

For each line, write:

- one-sentence claim
- strongest dated evidence
- recency: early / middle / recent / continuous
- scope: where this line applies and where it does not
- status: `current dominant`, `historical root`, `active secondary`, `contextual`, or `weak`

## One Problem Hypothesis
If a single thread exists, state it only after comparing candidate lines. If not, keep multiple lines. Do not answer with personality traits or types. Name the recurring problem, pressure, or fight, and say whether it is current or historical.

## Contradiction Test
Open `_analysis/contradictions.json` for the target person. Start with the highest-ranked structural tension candidate.

Priority: Type 6 `long_denial_to_admission` > Type 1 `principle_vs_behavior` > Type 5 `stance_reversal`. Within the same type, use High > Medium > Low.

The core thread must explain both poles without flattening either pole. Flattening means dismissing one side as unimportant, temporary, fake, or not real.

If the thread cannot explain a High-confidence tension after three attempts, the thread is wrong for this run or only partial. Burn again, or downgrade to `Weak Thread` / `No Stable Thread`.

## Core Thread
Compress the revised line into 1-2 sentences only if the hypothesis survives verification and recent evidence still supports it. This is a working thread, not final truth.

Also write a `Current Dominant Line` section. A vivid old quote may explain origins, but it cannot become the report's main line if the latest 6-12 months show that another pressure has become more active.

## Evidence That Does Not Fit
List any strong quote that resists the thread. If important evidence does not fit, either revise the thread or downgrade the final report to an evidence report.

## Mandatory Verification
For each claim in the proposed Core Thread:

1. List 3 specific dated quotes that directly support it. Use date + quote, not paraphrase.
2. Name one concrete type of evidence that would falsify it.
3. List any quote in the Raw Quote Pile or samples that contradicts or complicates it.
4. Name at least one alternative explanation that could also fit the same evidence.

If any answer is weak, vague, or missing, the claim is not ready for the final report.

## Time-Weight Check

For every candidate line, answer:

1. Is this line supported in the latest 6-12 months?
2. If it is mostly older than one year, should it be called `historical root` instead of `current dominant`?
3. Which line best explains recent behavior, current user questions, and the target person's own feedback?
4. Which line is attractive because it has a sharp quote, but may be outdated or too narrow?

## Burn Result
Choose one:

- `Core Thread Found`: verified enough to organize a deep report.
- `Multi-Line Model`: no single line should dominate; use several verified lines with a named current dominant line.
- `Weak Thread`: useful hypothesis, but not strong enough to organize the report. Keep it as `Hypothesis`.
- `No Stable Thread`: evidence does not support a single organizing line. Downgrade to evidence report or ask the user for direction.
```

Use these fuel sources first:

- direct quotes from samples and evidence ledger
- `principleStatements` from `{target}_samples.json`
- `_analysis/principle_statements.json`
- `_analysis/behavior_patterns.json`
- `_analysis/contradictions.json`
- `_analysis/cognitive_break_windows.json`

The core question is: what long-running problems does this person repeatedly process across unrelated surfaces, and which one is most alive now? Keep the question sharp, but avoid dramatic destiny claims.

Important: the burn is allowed to fail. A failed burn is a valid result and should lower hallucination risk. Do not invent a core thread to satisfy the workflow. If the best answer is `Weak Thread` or `No Stable Thread`, say so and write a narrower report.

### Phase 7.6: Candidate Answer Loop

This phase is mandatory for user questions that ask for an answer, judgment, interpretation, or "what changed". Do not expose raw detector labels as the answer.

Process:

1. Generate 2-4 candidate answers from the run folder:
   - `_analysis/core_thread_burn.md`
   - `_findings/findings.json`
   - `_evidence/evidence_ledger.json`
   - `_analysis/cognitive_break_windows.json`
   - `_analysis/contradictions.json`
   - `_analysis/principle_statements.json`
   - `_analysis/behavior_patterns.json`
   - `draft_skill/self.md` or `draft_skill/persona.md` when available
2. For each candidate, confirm against source evidence:
   - first use `_samples/{target}_samples.json`
   - then use `_profiles/{target}.json` only when quote-level confirmation is needed
3. Each candidate needs:
   - one-sentence answer
   - 2-3 supporting dated quotes or source pointers
   - 1 complicating or contradictory evidence point
   - confidence: High / Medium / Low / Insufficient
4. Select the best answer:
   - prefer the candidate that explains the user's question with the fewest unsupported assumptions
   - mention one alternate answer only if it materially changes interpretation
5. User-facing output must give the selected answer. Do not present detector mechanics unless the user asks how the answer was derived.

Important distinctions:

- "Detector did not find X" means only that the detector did not find X in its supported form. It does not prove the user never had X.
- A principle statement is fuel for candidate generation, not the answer.
- A cognitive break window is fuel for candidate generation, not proof of a life transformation.
- A behavior pattern is fuel for candidate generation, not a diagnosis or stable trait.
- A structural tension candidate is fuel for burn and answer generation, not proof that the person is hypocritical or inconsistent.

### Phase 8: Evidence-Backed Report

Choose the report template from `references/task-router.md`, then choose the report depth from the burn result.

Default report shape for deep profile/self analysis is "small-to-large":

1. One core observation, grounded in a concrete quote or scene.
2. 3 micro-scenes: date, quote, immediate context, what the scene shows.
3. Larger pattern: what these scenes jointly suggest, with confidence.
4. What this pattern cannot explain.
5. What would change the conclusion.
6. Optional appendix: footprint, speech style, motivation, defense, growth, tension.

Do not lead with a full personality field checklist unless the user asks for a structured profile. A good report should grow from evidence, not fill boxes.

Core conclusions must be written as a mechanism chain, not a loose label:

```text
Trigger -> Processing move -> Output -> Boundary / failure mode
```

Example shape:

- Trigger: messy systems, unfairness, logical inconsistency, blocked paths, or unstable relationships.
- Processing move: abstract the structure, redefine the problem, test it against examples, or turn it into a tool/project.
- Output: long analysis, practical advice, creative artifact, plan, or reusable skill.
- Boundary: immediate emotion, fatigue, body state, or intimate/private material may not enter the same analysis mode.

Do not stop at labels such as "thinker", "creator", "analyst", "builder", or "sensitive person". A label is allowed only as a shorthand after the mechanism is shown.

Burn result routing:

- `Core Thread Found`: use the verified thread as the organizing hypothesis, but keep contradictions visible.
- `Multi-Line Model`: organize the main report around multiple lines. Lead with the current dominant line, then show historical roots and active secondary lines.
- `Weak Thread`: do not organize the whole report around it. Present it as a possible line and foreground micro-scenes.
- `No Stable Thread`: produce an evidence report only: observations, quotes, limits, and next questions.

### Phase 8.5: Report Pack, User Questions, And Sensitive Topic Separation

For `report-pack`, keep the product readable by separating stable identity modeling from user-specific questions and sensitive topics.

Recommended report pack:

- `00_overview.md`: main persona/profile report. It may summarize sensitive or user-question findings, but should not absorb every answer.
- `01_behavior_language.md`: speech style, rhythm, interaction style.
- `02_relationship_network.md`: relationship roles and dynamics.
- `03_emotional_trajectory.md`: emotional and growth trajectory.
- `04_cognitive_style.md`: thinking, values, judgment priority, decision style.
- `05_self_review.md`: optional first-person self-review when requested.
- `08_user_questions_and_evidence.md`: answers to explicit user questions, with evidence and whether each answer should update the main profile.
- `09_mental_health_signals.md`: only when explicitly requested or clearly necessary; keep it separate from the main persona report.
- `10_targeted_questioner_handoff.md`: optional but recommended when the user may continue into a targeted follow-up, calibration, or final-report workflow. This is a handoff artifact, not another report.
- `99_corrections_and_review.md`: user corrections, accepted/narrowed/held hypotheses, and report changes.

User question report shape:

```markdown
# User Questions And Evidence

## Q1: ...

Short answer:

Evidence:
- date/source + quote or pointer
- date/source + quote or pointer

Complication:

Relationship to main report:
- promote to main report / summarize only / keep as topical answer / do not promote

Confidence:
```

Promotion rule: a user-question answer enters the main report only when it changes stable understanding of the person and has enough evidence. Otherwise keep it in `08_user_questions_and_evidence.md` and add only a short pointer in `00_overview.md`.

Mental-health separation rule: if the user asks "what psychological problems do I have?" or similar, answer in `09_mental_health_signals.md`. The main profile may say "recent anxiety/stress signals are strong; see the mental-health signal report" but must not turn the person's identity into a diagnosis.

For mental-health signal reports:

- Use "signals", "patterns", and "worth professional evaluation", not fixed diagnosis.
- Do not recommend medication changes.
- Do not infer disorders from keyword counts alone.
- Include protective factors and counter-evidence.
- Keep the report separate from `self.md` and stable persona rules unless the user explicitly confirms the pattern as part of their self-model.

### Phase 8.6: Downstream Handoff For Targeted Questioning

Use this phase when a report could feed a separate targeted-questioning, user-calibration, or final-report skill. Do not turn this phase into a multi-round interview inside this skill.

Read `references/downstream-handoff.md` and produce `_exports/10_targeted_questioner_handoff.md` for `report-pack` and for any `standard-report` where the user is likely to continue with targeted follow-up questions.

The handoff must preserve upstream locks and summarize only what the downstream workflow needs:

- identity lock and non-negotiable boundaries
- source files produced by this run
- current dominant line, historical roots, active secondary lines, and downgraded/excluded lines
- seed claim table with confidence and risk
- follow-up leverage points that could change report conclusions
- suggested report routing based on evidence center of gravity
- suggested question routing based on unresolved high-value claims
- user corrections already applied

Do not ask the follow-up questions here unless the user requested that inside the current turn. The handoff tells the next skill what to ask and what not to break.

### Phase 7.7: Interpretive Conversation Mode

Use this mode when the user wants a self-understanding conversation, asks "what kind of person am I?", reacts to prior reports emotionally, or values a useful narrative more than a formal audit.

The rule is: hard identity, living interpretation.

- Identity layer stays strict: participant count, aliases, target speaker, and non-human buckets must already be resolved by Phase 6.5.
- Interpretation layer stays alive: after the identity layer is safe, offer a coherent narrative, not only an evidence checklist.
- A strong narrative is allowed when it is labeled as an interpretive model, supported by evidence types, and open to correction.
- Do not smother the answer with detector mechanics, gate names, or "insufficient evidence" language unless the user asks for audit detail.
- Lead with the pattern that best helps the user continue the conversation. Put caveats after the main insight, not before it.

Good shape:

```text
One useful line: ...
Why I think this: ...
Where it may be wrong: ...
What I would ask you next: ...
```

Avoid two opposite failures:

- Over-audit: the report is technically safe but refuses to model the person.
- Over-story: the report sounds powerful but floats away from participant identity, quotes, dates, and contradictions.

For each target person, the optional structured appendix may include:

- Conversation footprint: message count, active years/months, relative share.
- Speech style: length, punctuation, emoji/particles, long-message pattern.
- Judgment priority: logic, usefulness, relationship, feeling, control, freedom, meaning, or other.
- Core motivation: being seen, safety, autonomy, competence, connection, significance, trace, or other.
- Defense pattern: humor, analysis, avoidance, aggression, self-mockery, rationalization, withdrawal, action, or other.
- Growth trajectory: early/middle/recent changes.
- Tension: two conflicting needs or behavioral patterns.
- Evidence table: date, quote, theme, confidence.

Build these fields from specific outputs:

| Report Field | Primary Source | Secondary Source |
|---|---|---|
| Conversation footprint | `structure.json`, `stats.json`, `_sender_list.json` | `_profiles/{sender}.json` |
| Speech style | `stats.avgMessageLength`, long messages, samples | punctuation/emoji visible in samples |
| Judgment priority | long messages, quarterly samples | repeated themes in `cross_validation.json` |
| Core motivation | repeated high/medium themes | direct quotes from samples |
| Defense pattern | `behavior_patterns.json` | long messages after emotion/conflict |
| Growth trajectory | first/last samples, quarterly samples | `cognitive_break_windows.json` and cross-time themes |
| Tension | conflicts between themes, principles, or behavior patterns | quote-level verification |
| Evidence table | samples + behavior pattern evidence | original profile only if needed |

For deep reports and personal skills, consult `_analysis/core_thread_burn.md`. Only organize the interpretation around the core thread if the burn result is `Core Thread Found`. Do not force every claim into one line; explicitly name evidence that complicates it.

Behavior-pattern evidence should not be overclaimed. Treat it as a clue to investigate, then support the final conclusion with quotes, dates, and repetition count.

For non-profile tasks, keep the same evidence discipline but change the lens:

- Theme analysis: topic, time span, representative evidence, trajectory.
- Conflict analysis: claim A, claim B, source/date, severity, confidence, possible resolution.
- Relationship analysis: interaction pattern, directionality, evidence from both sides, privacy boundary.
- Timeline: dated event, source, certainty, unresolved gaps.

Use confidence labels:

- `High`: at least 3 independent evidence points across different months or years.
- `Medium`: 2 evidence points or strong stats plus quote support.
- `Low`: 1 quote, sparse evidence, or mostly inference.
- `Insufficient`: not enough data.

Use delivery tiers:

- `Confirmed Pattern`: High confidence, repeated evidence, and safe to place in `self.md` or `persona.md`.
- `Probable Pattern`: Medium confidence or context-limited. Include it, but mark it as needing user confirmation.
- `Hypothesis`: Low confidence, missing negative evidence, or mostly inference. Keep it in `preview.md` or `evidence.md`; do not turn it into a stable persona rule.

Medium/Low claims must not read like final identity labels. Use wording such as "may", "in this group-chat context", "needs confirmation", or "evidence suggests".

Fuel is not conclusion:

- `principleStatements` are candidate worldview evidence, not automatic values.
- `cognitiveBreakWindows` are candidate turning points, not automatic life transformations.
- `behaviorPatterns` are sequence clues, not diagnoses or stable traits.
- If a report uses any of them, it must include dated quotes and state what the signal cannot prove.
- Do not show detector names, regex families, or counts in user-facing answers unless the user asks for methodology. Translate them into plain evidence-backed reasoning.

### Phase 9: Self/Persona Distillation

If the user wants a reusable self skill, generate these files in a draft output directory:

- `self.md`: factual memory, values, habits, relationships, growth trajectory.
- `persona.md`: speech style, emotion pattern, decision pattern, social behavior, hard rules.
- `evidence.md`: claim-to-evidence index with quotes and confidence.
- `meta.json`: source file, target aliases, created time, version, data boundary, confidence summary.
- `SKILL.md`: a runnable personal skill draft.

Use the prompts in `prompts/`:

- `evidence_to_self.md`
- `evidence_to_persona.md`
- `personal_skill_template.md`
- `correction_policy.md`

Do not write the generated skill into `.codex/skills` until the user confirms the draft feels accurate.

### Phase 10: User Confirmation, Correction, And Re-Burn

Before finalizing, populate `_review/preview.md`; do not leave the analyzer's scaffold text in place.

The preview must contain:

- 5 core self-memory claims, with confidence and evidence pointer.
- 5 persona rules, with confidence and evidence pointer.
- 3 highest-risk inferences that might be too strong.
- 3 known blind spots or missing data areas.
- concrete user confirmation questions.

Use this shape:

```markdown
# Confirmation Preview

## Core Claims
| Claim | Tier | Confidence | Evidence |

## Persona Rules
| Rule | Tier | Confidence | Evidence |

## Risky Inferences
| Inference | Why Risky | What To Confirm |

## Blind Spots
| Missing Area | Effect |

## Questions For User
1. ...
```

Then show the user a compact preview:

- Mark each as High/Medium/Low confidence.
- Ask the user which ones are wrong, too strong, or missing.

When the user corrects it:

- Record the correction in `evidence.md`.
- Update `self.md` or `persona.md`.
- Keep the original evidence and explain whether the correction overrides, narrows, or adds nuance.

Do not treat user correction as a command to flatter or conform. Treat it as new evidence and classify the response:

- `Accept`: correction matches evidence and improves precision.
- `Narrow`: correction is partly right; adjust scope or wording.
- `Hold As Hypothesis`: correction may be right but evidence is not yet enough.
- `Ask`: correction reveals a missing dimension that needs a follow-up question.
- `Resist`: correction conflicts with strong evidence; explain gently and keep both views visible.

Treat user reaction as modeling feedback, not only pass/fail validation:

- `Correction`: a fact or attribution is wrong. Fix the evidence ledger and affected files.
- `Direction Drift`: the user says the report is not what they wanted, feels shallow, or points somewhere else. Return to `_analysis/core_thread_burn.md`, rebuild the quote pile if needed, and re-run Phase 7.5.
- `Depth Challenge`: the user asks "deeper", "why", "not enough", or similar. Do not defend the previous framework. Re-test the core thread against contradictions and principle statements.
- `Withdrawal / fatigue`: if the user says "算了", goes silent, or shifts away from the topic, do not treat it as confirmation. Offer a lighter checkpoint or pause.

When re-burning, discard the old core thread if it cannot explain the user's objection. Do not argue that the report was correct just because it had evidence.

### Phase 11: Finalize Run Metadata

After interpretation or self-skill generation, update the run metadata so it matches the actual deliverables. If the analyzer started as `orientation` but the agent later produced a report or draft skill, `_manifest.json` must be updated.

Required final fields:

- `mode`: final mode actually delivered: `orientation`, `standard-report`, `relationship-map`, or `deep-self-skill`.
- `taskRoute`: final route actually used.
- `interpretationStatus`: `orientation-only`, `interpreted`, `draft-skill-generated`, `user-confirmed`, or `blocked`.
- `finalDeliverables`: list of report or draft-skill files produced.
- `requiresUserConfirmation`: `true` for any generated personal skill or sensitive identity/persona conclusions.
- `previewPath`: path to `_review/preview.md` if confirmation is required.
- `behaviorPatternsAvailable`: whether `_analysis/behavior_patterns.json` exists and was used.
- `structuralTensionsAvailable`: whether `_analysis/contradictions.json` exists and was used.
- `downstreamHandoffPath`: `_exports/10_targeted_questioner_handoff.md` when a handoff was produced.

If `_manifest.json`, `_analysis/run_summary.json`, and produced files disagree, fix the metadata before final delivery. If metadata cannot be updated, state the mismatch explicitly.

## Commercial Quality Checklist

Before saying the work is done:

- Raw file was not directly loaded wholesale.
- Delivery path was locked before analysis, and final deliverables match that path.
- Explicit non-goals were respected.
- Structure and sender fields were detected.
- `_analysis/participant_map.json` was read before interpretation.
- Human participant count, canonical sender buckets, and excluded non-human buckets were stated.
- Each person was separated before analysis.
- The target person's aliases were considered.
- Claims are supported by dated quotes.
- Important claims have confidence labels.
- Report distinguishes evidence from inference.
- Third-party privacy is protected.
- If a personal skill is generated, user confirmation happened first.
- If user confirmation has not happened, the generated skill is clearly marked `DRAFT`.
- `_review/preview.md` is populated with concrete claims, risky inferences, blind spots, and questions.
- `_manifest.json` mode/route/status match the actual final deliverables.
- Medium/Low claims are not promoted into stable persona rules without a confirmation note.
- `Hypothesis` claims remain in preview/evidence rather than final identity memory.
- Core Thread Burn result is reported honestly: `Core Thread Found`, `Weak Thread`, or `No Stable Thread`.
- High-ranked structural tension candidates were tested in the burn, and neither pole was flattened.
- If the burn result is weak, the final deliverable is narrowed rather than forced into a grand explanation.
- Runtime status of the analyzer is clear: `SmokeTested`, `PartiallySmokeTested`, `RuntimeBlocked`, `RuntimeUnverified`, or `RuntimeFailed`.
- Task route was explicit: profile, relationship, theme, conflict, timeline, evidence extraction, paper/report review, or self-skill.
- Non-native files were normalized through an adapter before interpretation.
- Evidence ledger exists or the final answer explains why it was unnecessary for the selected mode.
- For self-understanding reports, the final result was assessed on two axes: engineering compliance and user conversation value.
- If a downstream handoff is appropriate, `_exports/10_targeted_questioner_handoff.md` exists and preserves identity, privacy, source-separation, and mental-health boundaries.

## Common Failure Modes

| Failure | Result | Correct Move |
|---|---|---|
| Read the whole JSON | Context overflow and shallow conclusions | Run analyzer first |
| Mix delivery paths | Same skill/prompt produces incompatible folders and missed expectations | Lock one path in Phase 0.8; switch only with user request and updated manifest |
| Analyze group chat as one voice | Wrong attribution | Use per-sender profiles |
| Count aliases or system buckets as people | Wrong participant count and polluted reports | Use `participant_map.json`; confirm aliases before analysis |
| Treat names in top words as catchphrases | Metadata becomes personality evidence | Filter aliases, group names, reply/file/link/media/system terms |
| Trust one emotional quote | Overfitting | Require cross-time evidence |
| Output personality labels only | Vague, not useful | Model operating pattern |
| Hide uncertainty | False confidence | Use confidence labels |
| Generate a skill immediately | User feels misrepresented | Preview and correct first |
| Force a core thread | Grand but false story | Mark `Weak Thread` or `No Stable Thread` and narrow the report |
| Treat tension candidates as verdicts | The report accuses the person of hypocrisy or inconsistency without verification | Use `contradictions.json` as burn input only; verify both poles with dated evidence |
| Ignore high-ranked tensions | The report feels smooth but avoids the strongest internal pressure | Re-burn from the highest-ranked Type 6 / Type 1 candidate |
| Treat fuel as conclusion | Principle/window signals become hallucinated traits | Verify with dated quotes and alternative explanations |
| Turn safety gates into the whole answer | The user gets an audit, not understanding | Keep gates internal; deliver a useful, discussable model |

## Final Answer Shape

For report-only tasks:

```text
我完成了聊天记录证据分析。
分析范围：...
运行验证：...
Burn 结果：Core Thread Found / Weak Thread / No Stable Thread
我的回答：...
为什么我这样判断：...
关键证据：2-3 条 dated quote 或来源指针
一个备选解释：...
不能解释的部分：...
证据强度：...
仍然不确定：...
```

For self-skill tasks:

```text
我生成了自我 skill 草稿，还没有安装。
草稿位置：...
Burn 结果：...
最核心答案：...
支撑这个答案的 3 个场景：...
高置信结论：...
需要你确认的低/中置信结论：...
下一步：确认后再写入正式 skills 目录。
```

Do not include these in user-facing output unless explicitly asked:

- detector regex families such as `X不是Y，X是Z`
- raw counts such as "33 redefinition / 0 belief_reversal"
- internal file choreography
- long methodology explanations

Use those internally to select and verify the answer, then give the user the answer in plain language.
