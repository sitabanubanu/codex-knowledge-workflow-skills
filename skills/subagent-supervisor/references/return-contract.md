# Return Contract

Every subagent final response must be concise, evidence-based, and complete enough for the supervisor to verify without trusting the summary alone.

## Required Final Response

Subagents must return these fields:

- Outcome: State what was completed, reviewed, found, or not completed.
- Files Inspected: List every file or artifact inspected. Use "None" if no files were inspected.
- Files Changed: List every file changed. Use "None" for explorer and reviewer tasks.
- Verification: Report verification using the verification categories below.
- Risks: State remaining risk. This field cannot be empty; write "No known risks" if none are known.
- Next: Suggest safe next steps only. Do not execute the next step unless it was explicitly assigned.

## Blocked Response

If blocked, subagents must return these fields instead of pretending the task is complete:

- Blocked Reason: The specific condition that prevents completion.
- Partial Work: What was inspected, attempted, drafted, or completed before stopping.
- Needed Input: The missing decision, file, permission, clarification, dependency, or artifact.
- Safe Next Step: The narrowest safe action the supervisor can take next.

## Verification Categories

Use one or more of these categories in the Verification field:

- not run: No verification was run. Include the reason.
- command run: A command was run. Include the exact command and summarize the result.
- file inspected: A file or artifact was opened or checked. Include the path.
- content checked: Specific required content was checked. State what was checked and whether it passed.

## Rules

- Risks cannot be blank. If there are no known risks, write "No known risks".
- Next is advisory only. A subagent must not silently continue into follow-up work.
- Files Changed must include only files actually changed by the subagent.
- Do not claim verification that was not performed.
- If validation fails, report the failure under Verification and include the remaining risk.
