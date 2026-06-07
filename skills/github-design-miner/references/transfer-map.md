# Design Transfer Map

Use the transfer map to turn mined patterns into a practical improvement plan.

## Current Project Gap Table

| Area | Current State | External Pattern | Fit | Recommendation |
|---|---|---|---|---|
| Already strong | What the project already does well | Do not overwrite | keep | preserve |
| Present but weak | Exists but incomplete | pattern to strengthen | medium/high | improve |
| Missing | Not present | pattern to add | medium/high | add |
| Unsuitable | External pattern does not fit | reject | low | do not add |
| Dangerous | Would damage the project's soul | reject | negative | avoid |

## Transfer Map Format

| External Logic | Transferable Pattern | Landing Point | Priority | Risk | Validation |
|---|---|---|---|---|---|
| Project/module idea | Named pattern | file/module/workflow to change | high/medium/low | what could go wrong | how to check success |

Priority:

- `high`: closes a major gap with limited risk.
- `medium`: useful but needs more design or has cost.
- `low`: optional polish or future path.
- `avoid`: would bloat or distort the project.

## Preserve The Soul

Always include:

```text
Keep:
- original core value
- current strong workflow
- domain language
- user trust boundary

Do not import:
- patterns that replace the core purpose
- unnecessary dependencies
- product assumptions from another domain
- complexity that does not solve the user's pain
```

## Implementation Brief

If the user asks to implement, produce:

```text
Files to modify:
- path: purpose

Files to add:
- path: purpose

Logic to preserve:
- ...

Implementation order:
1. ...
2. ...
3. ...

Validation:
- static/file checks
- sample run
- output structure check
- user review gate

Risks:
- ...
```

Do not skip validation just because changes are documentation-only. Skills need trigger, workflow, and output-shape checks.
