# Question Generation

Use this before producing follow-up questions.

## Core Rule

Questions follow leverage, not template.

A good question changes the model if answered.

## Valid Question Test

Every question must answer:

```text
Pending claim:
Current evidence:
Why this is uncertain:
If user confirms:
If user denies:
Report impact:
```

If the answer would not change any claim, weight, report route, or action recommendation, do not ask it.

## Prioritize These Questions

Ask about:

- current dominant line vs historical root;
- high-confidence evidence with uncertain interpretation;
- medium-confidence claims that entered the main report;
- user-corrected claims that need stable wording;
- contradictions that affect future action;
- areas where report routing depends on user confirmation;
- claims likely to become generic if not sharpened.

Avoid asking about:

- already locked identity facts;
- low-stakes details;
- generic strengths/weaknesses;
- sensitive psychological diagnosis unless user explicitly requests signal analysis;
- third-party private claims unless needed and allowed.

## Question Count

Default: 5-8 questions.

Maximum: 12 questions.

If there are more than 12 candidate questions, rank by:

1. ability to change the core line;
2. ability to prevent a false main report;
3. direct user concern;
4. action relevance;
5. evidence uncertainty.

## Output Shape

```markdown
# Question Plan

## Q1

Question:

Pending claim:

Current evidence:

Why this matters:

If confirmed:

If denied:

Report impact:
```

## Bad Questions

Do not ask:

- "What are your strengths?"
- "What are your weaknesses?"
- "What is your personality?"
- "What do you want in the future?"

unless the question is tied to a specific claim and report decision.

## Good Question Pattern

Instead of:

```text
What are your goals?
```

Ask:

```text
The report treats your recent AI/agent work as a current dominant line rather than a temporary tool interest. Is that accurate, or is AI mainly a method you use while pursuing a different goal? If you answer "method", the final report should demote AI from main line to execution tool.
```
