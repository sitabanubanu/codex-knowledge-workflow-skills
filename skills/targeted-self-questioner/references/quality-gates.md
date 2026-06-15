# Quality Gates

Run these gates before final delivery.

## Gate 1: Input And Locks

- input source is identified;
- upstream handoff or report folder is read when available;
- identity lock is inherited;
- participant and alias boundaries are not reopened by default;
- raw large chat files are not read.

Fail if the skill re-analyzes raw chat or changes identity without user request.

## Gate 2: Claim Table

- important claims are extracted;
- each claim has evidence pointer or source label;
- confidence and user-confirmation status are visible;
- claims that need follow-up are marked.

Fail if questions are generated before claim risks are known.

## Gate 3: Report Routing

- report shape follows evidence center of gravity;
- user goal is considered;
- low-weight topics are not promoted to main structure.

Fail if the report is a fixed generic personality template.

## Gate 4: Question Leverage

Every question must state:

- pending claim;
- current evidence;
- why it matters;
- if confirmed;
- if denied;
- report impact.

Fail if generic questionnaire items appear without tied claims.

## Gate 5: Correction Handling

- each user answer is classified as `Accept`, `Narrow`, `Downgrade`, `Override`, `Hold`, or `Resist`;
- corrections are logged;
- the model does not blindly flatter or ignore the user.

Fail if user corrections disappear into prose without a trace.

## Gate 6: Weight And Placement

- core/current lines are main sections;
- historical roots are time-labeled;
- active threads are secondary;
- episodes and noise are appendix or omitted.

Fail if low-weight episodes receive main-report space.

## Gate 7: Final Report Chain

High-weight final sections preserve:

```text
Question -> initial judgment -> evidence -> user correction -> weight change -> final judgment -> action impact
```

Fail if the final report compresses calibrated analysis into static columns.

## Gate 8: Sensitive Boundaries

- mental-health material is signal-based and separate when requested;
- no diagnosis unless explicitly requested as non-clinical signal discussion;
- third-party privacy is protected;
- upstream privacy boundaries are preserved.

Fail if psychological signals become stable identity labels.
