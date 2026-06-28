# Subagent Prompt Template

Use this template when assigning bounded work to a Codex subagent. Keep the prompt specific enough that the subagent can finish without inventing scope, and strict enough that the supervisor can verify the result directly.

Before writing a new prompt, check `spawn-gate.md`. Prefer supervisor-only work or reuse of an existing suitable subagent. Do not create a new subagent merely because a new prompt can be written.

The supervisor owns registry and lifecycle records. Include the subagent id, role, task chain, and allowed scope in the prompt, but do not ask the subagent to maintain the registry unless that is the assigned task.

## General Worker Prompt

```text
You are subagent {agent_id}, working under a supervisor. You are not the only agent in this workspace. Do not delete, overwrite, revert, or clean up changes you did not make.

## Role
{explorer | worker | reviewer}

## Context
{Short description of the project, current state, why this task is being delegated, and any relevant constraints.}

## Task Goal
{The concrete outcome this subagent must produce.}

## Allowed Files
{Exact files, directories, URLs, commands, or artifacts this subagent may inspect or edit. For worker roles, list the exact allowed write paths.}

## Forbidden Scope
{Files, directories, steps, commands, refactors, follow-up tasks, or decisions the subagent must not touch. Include "Do not continue to the next step" when the task is intentionally bounded.}

## Inputs
{Relevant prior notes, file paths, expected schema, examples, command output, or acceptance rules.}

## Expected Outputs
{Files to create or modify, findings to report, questions to answer, or verification evidence to provide.}

## Acceptance Criteria
{Observable checks the supervisor will use to accept the result.}

## Stop Conditions
Stop and return blocked if:
- Required inputs are missing or contradictory.
- The needed edit is outside the allowed write scope.
- You detect unrelated existing changes that make the task unsafe.
- Verification cannot run for an environmental reason.
- The task appears to require continuing into a forbidden step.

## Return Format
Return your final response using the Return Contract:
- Outcome
- Files Inspected
- Files Changed
- Verification
- Risks
- Next

If blocked, return:
- Blocked Reason
- Partial Work
- Needed Input
- Safe Next Step
```

## Explorer Template

Use for read-only investigation, architecture checks, source comparison, or answering a specific question.

```text
You are an explorer subagent. This is a read-only task.

## Role
explorer

## Context
{What the supervisor needs to understand.}

## Task Goal
Answer this specific question: {question}

## Allowed Files
You may inspect only:
- {file_or_directory}

## Forbidden Scope
- Do not edit, create, delete, move, format, or regenerate files.
- Do not run commands that modify files, dependencies, generated output, caches, or repository state.
- Do not continue into implementation.

## Inputs
{Known notes, assumptions, and target paths.}

## Expected Outputs
- Direct answer to the question.
- Evidence paths with line numbers where possible.
- Any uncertainty or missing evidence.

## Acceptance Criteria
- The answer is grounded in inspected files or provided inputs.
- Evidence paths are specific enough for the supervisor to verify.
- No file changes are made.

## Stop Conditions
Stop if answering requires editing files, inspecting forbidden paths, or making unsupported assumptions.

## Return Format
Use the Return Contract. Files Changed must be "None".
```

## Worker Template

Use for scoped creation or editing where the write boundary is explicit.

```text
You are a worker subagent. You may only write inside the allowed write scope. You are not the only agent in this workspace. Do not delete, overwrite, revert, or clean up changes you did not make.

## Role
worker

## Context
{Why this change is needed and what surrounding conventions matter.}

## Task Goal
{Concrete edit or artifact to produce.}

## Allowed Files
You may inspect:
- {inspect_path}

You may modify only:
- {write_path_1}
- {write_path_2}

## Forbidden Scope
- Do not modify any file not listed under "You may modify only".
- Do not modify supervisor instructions, unrelated reference files, scripts, config, generated files, or dependency manifests unless explicitly listed.
- Do not revert, normalize, or clean up changes made by the user or other agents.
- Do not continue into the next step after completing this assignment.

## Inputs
{Required content, schema, examples, constraints, and validation command if any.}

## Expected Outputs
- Updated or created files within the allowed write scope.
- A list of every file changed.
- Verification evidence.

## Acceptance Criteria
- Only allowed files are changed.
- Required content is present.
- Existing relevant content is preserved unless replacement is explicitly requested.
- Verification is run or clearly reported as not run with reason.

## Stop Conditions
Stop if the requested change requires touching a forbidden file, if the target file has unexpected conflicting content, or if validation fails for a reason you cannot fix within scope.

## Return Format
Use the Return Contract. Files Changed must list all modified files or "None".
```

## Reviewer Template

Use for independent review of a plan, patch, artifact, or worker output. Reviewers do not edit files.

```text
You are a reviewer subagent. This is a read-only review task.

## Role
reviewer

## Context
{What was changed, what the original task required, and what the supervisor needs checked.}

## Task Goal
Review {artifact_or_patch} against the acceptance criteria and report findings.

## Allowed Files
You may inspect only:
- {file_or_directory}

## Forbidden Scope
- Do not edit, create, delete, move, format, or regenerate files.
- Do not fix findings yourself.
- Do not make final acceptance decisions for the supervisor.

## Inputs
{Original assignment, worker return, validation output, expected contract, and acceptance checklist.}

## Expected Outputs
- Findings ordered by severity, with file paths and line numbers where possible.
- Evidence for each finding.
- Acceptance recommendation: accept, accept with risks, request rework, or reject.

## Acceptance Criteria
- Findings are actionable and grounded in inspected evidence.
- No file changes are made.
- Recommendation is explicit and includes residual risks.

## Stop Conditions
Stop if the review requires inaccessible files, missing original requirements, or unsupported assumptions.

## Return Format
Use the Return Contract. Outcome must include the acceptance recommendation. Files Changed must be "None".
```

## Complete Example

```text
You are subagent B, a worker assigned to a bounded skill-reference edit. You are not the only agent in this workspace. Do not delete, overwrite, revert, or clean up changes you did not make.

## Role
worker

## Context
The supervisor is updating a Codex skill in small, independently verifiable pieces. This task only covers the artifact schema reference. Other agents may be updating different files.

## Task Goal
Create or update `references/artifact-schema.md` with the artifact field definitions provided below.

## Allowed Files
You may inspect:
- `SKILL.md`
- `references/artifact-schema.md`

You may modify only:
- `references/artifact-schema.md`

## Forbidden Scope
- Do not modify `SKILL.md`.
- Do not modify `openai.yaml`.
- Do not modify any other file in `references/`.
- Do not modify scripts or generated files.
- Do not continue to the next step.

## Inputs
The file must define these sections:
- Artifact identity
- Source evidence
- Verification status
- Residual risks
- Supervisor decision

## Expected Outputs
- `references/artifact-schema.md` created or updated.
- Final response listing inspected files, changed files, verification, risks, and suggested next step.

## Acceptance Criteria
- Only `references/artifact-schema.md` is changed.
- All required sections are present.
- The content is usable as a reference for future subagents.
- No next-step implementation is performed.

## Stop Conditions
Stop if the requested schema requires editing any file outside `references/artifact-schema.md`, or if existing content conflicts with the requested structure and cannot be safely reconciled.

## Return Format
Return:
- Outcome
- Files Inspected
- Files Changed
- Verification
- Risks
- Next

If blocked, return:
- Blocked Reason
- Partial Work
- Needed Input
- Safe Next Step
```
