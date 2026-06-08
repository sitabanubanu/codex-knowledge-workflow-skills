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

## Product Modes

Choose the smallest mode that can satisfy the user's current decision:

| Mode | When To Use | Deliverable | Confirmation |
|---|---|---|---|
| `orientation` | User is exploring, file quality is unknown, or the request is broad | brief data map, top senders, feasibility, likely next questions | ask before deep interpretation |
| `standard-report` | User wants to understand one person or one group | evidence-backed portrait/report with confidence labels | confirm uncertain or sensitive claims |
| `deep-self-skill` | User wants a reusable personal skill or long-term self memory | `self.md`, `persona.md`, `evidence.md`, `meta.json`, draft `SKILL.md` | mandatory preview and correction |
| `team/relationship-map` | User cares about several people and dynamics | per-person profiles plus relationship dynamics | confirm names, aliases, and privacy boundary |

Default ladder:

1. Run `orientation` first when the task direction or input quality is unclear.
2. Move to `standard-report` when the user has a clear target and wants conclusions.
3. Move to `deep-self-skill` only when the user explicitly wants a reusable skill/memory.

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
- `_analysis/stats.json`: yearly/monthly sender stats, text length, active hours, high-frequency words.
- `_split/part_*.json`: chunks for very large files.
- `_profiles/{sender}.json`: complete per-sender profile.
- `_samples/{sender}_samples.json`: first/last messages, monthly samples, long messages, keyword hits.
- `_analysis/cross_validation.json`: themes with evidence across different months.
- `_analysis/behavior_patterns.json`: non-keyword behavioral patterns such as emotion-to-analysis sequences, self-mockery followed by silence, repeated pings, and ignored questions.
- `_analysis/principle_statements.json`: sentence-structure matches where the speaker states rules, redefines concepts, explains causality, or overturns prior beliefs.
- `_analysis/cognitive_break_windows.json`: suspicious time windows where long messages, multiple topic domains, and principle statements cluster.
- `_analysis/core_thread_burn.md`: mandatory synthesis scratchpad before deep reports or personal skills.
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
- Every final report or generated personal skill must include a short participant summary: human count, canonical sender buckets, confirmed aliases, and excluded non-human buckets.

### Phase 7: Read Evidence, Not Raw Data

Read these outputs in order:

1. `_analysis/structure.json`
2. `_analysis/participant_map.json`
3. `_analysis/stats.json`
4. `_profiles/_sender_list.json`
5. `_samples/{target}_samples.json` for the target person
6. `_analysis/behavior_patterns.json`
7. `_analysis/principle_statements.json`
8. `_analysis/cognitive_break_windows.json`
9. `_analysis/cross_validation.json`

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
- From `cognitive_break_windows.json`: inspect weeks where multiple domains become intense at once. Treat them as candidate turning points, not confirmed transformations.
- From `cross_validation.json`: decide confidence. High-confidence claims need cross-time evidence; a vivid one-off quote is not enough.
- Only then synthesize the report. If a major claim lacks evidence, mark it `Low` or `Insufficient`.

### Phase 7.5: Core Thread Burn

This phase is mandatory before any `standard-report`, `deep-self-skill`, or sensitive profile interpretation. Do not skip from evidence reading directly to the report.

Create `_analysis/core_thread_burn.md` with this structure:

```markdown
# Core Thread Burn

## Raw Quote Pile
15-20 strong direct quotes. Do not classify, rank, or sort them by topic. Mix politics, friendship, self-talk, future imagination, conflict, care, and principles.

## One Problem Hypothesis
If these quotes are all from the same person, what recurring problem are they trying to solve? Do not answer with personality traits or types. Name the long-running problem, pressure, or fight.

## Contradiction Test
Choose the two most contradictory pieces of evidence. Can the hypothesis explain both without flattening either one? If not, discard or revise the hypothesis.

## Core Thread
Compress the revised line into 1-2 sentences only if the hypothesis survives verification. This is a working thread, not final truth.

## Evidence That Does Not Fit
List any strong quote that resists the thread. If important evidence does not fit, either revise the thread or downgrade the final report to an evidence report.

## Mandatory Verification
For each claim in the proposed Core Thread:

1. List 3 specific dated quotes that directly support it. Use date + quote, not paraphrase.
2. Name one concrete type of evidence that would falsify it.
3. List any quote in the Raw Quote Pile or samples that contradicts or complicates it.
4. Name at least one alternative explanation that could also fit the same evidence.

If any answer is weak, vague, or missing, the claim is not ready for the final report.

## Burn Result
Choose one:

- `Core Thread Found`: verified enough to organize a deep report.
- `Weak Thread`: useful hypothesis, but not strong enough to organize the report. Keep it as `Hypothesis`.
- `No Stable Thread`: evidence does not support a single organizing line. Downgrade to evidence report or ask the user for direction.
```

Use these fuel sources first:

- direct quotes from samples and evidence ledger
- `principleStatements` from `{target}_samples.json`
- `_analysis/principle_statements.json`
- `_analysis/behavior_patterns.json`
- `_analysis/cognitive_break_windows.json`

The core question is: what long-running problem does this person repeatedly process across unrelated surfaces? Keep the question sharp, but avoid dramatic destiny claims.

Important: the burn is allowed to fail. A failed burn is a valid result and should lower hallucination risk. Do not invent a core thread to satisfy the workflow. If the best answer is `Weak Thread` or `No Stable Thread`, say so and write a narrower report.

### Phase 7.6: Candidate Answer Loop

This phase is mandatory for user questions that ask for an answer, judgment, interpretation, or "what changed". Do not expose raw detector labels as the answer.

Process:

1. Generate 2-4 candidate answers from the run folder:
   - `_analysis/core_thread_burn.md`
   - `_findings/findings.json`
   - `_evidence/evidence_ledger.json`
   - `_analysis/cognitive_break_windows.json`
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
- `Weak Thread`: do not organize the whole report around it. Present it as a possible line and foreground micro-scenes.
- `No Stable Thread`: produce an evidence report only: observations, quotes, limits, and next questions.

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

If `_manifest.json`, `_analysis/run_summary.json`, and produced files disagree, fix the metadata before final delivery. If metadata cannot be updated, state the mismatch explicitly.

## Commercial Quality Checklist

Before saying the work is done:

- Raw file was not directly loaded wholesale.
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
- If the burn result is weak, the final deliverable is narrowed rather than forced into a grand explanation.
- Runtime status of the analyzer is clear: `SmokeTested`, `PartiallySmokeTested`, `RuntimeBlocked`, `RuntimeUnverified`, or `RuntimeFailed`.
- Task route was explicit: profile, relationship, theme, conflict, timeline, evidence extraction, paper/report review, or self-skill.
- Non-native files were normalized through an adapter before interpretation.
- Evidence ledger exists or the final answer explains why it was unnecessary for the selected mode.

## Common Failure Modes

| Failure | Result | Correct Move |
|---|---|---|
| Read the whole JSON | Context overflow and shallow conclusions | Run analyzer first |
| Analyze group chat as one voice | Wrong attribution | Use per-sender profiles |
| Count aliases or system buckets as people | Wrong participant count and polluted reports | Use `participant_map.json`; confirm aliases before analysis |
| Treat names in top words as catchphrases | Metadata becomes personality evidence | Filter aliases, group names, reply/file/link/media/system terms |
| Trust one emotional quote | Overfitting | Require cross-time evidence |
| Output personality labels only | Vague, not useful | Model operating pattern |
| Hide uncertainty | False confidence | Use confidence labels |
| Generate a skill immediately | User feels misrepresented | Preview and correct first |
| Force a core thread | Grand but false story | Mark `Weak Thread` or `No Stable Thread` and narrow the report |
| Treat fuel as conclusion | Principle/window signals become hallucinated traits | Verify with dated quotes and alternative explanations |

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
