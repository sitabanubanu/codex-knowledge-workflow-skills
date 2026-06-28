# Rework Protocol

## When to Ask Same Agent to Rework

Ask the same agent to rework when the problem is small, the boundary is clear, and the same Agent already understands the context. This is appropriate for missing details, minor formatting problems, narrow validation gaps, or one scoped correction.

## When to Replace Agent

Replace the agent when there is serious scope violation, repeated failure, poor quality, or a need for independent review. Replacement is also appropriate when continued rework would risk overwriting valid work or hiding unresolved defects.

## Rework Prompt Requirements

A rework prompt must include:

- The acceptance issues found.
- The only allowed modification scope.
- A clear instruction not to redo parts that already passed.
- The new acceptance standard.
- The required return format.

## Rework Loop Limit

Limit rework to at most 1-2 rounds. If the same issue remains after that, the supervisor should intervene directly, narrow the task further, or replace the agent.

## Closure Rule

After the work passes acceptance, close the agent. If the work fails, close the agent or record the reason it cannot be closed yet, including the remaining risk and owner for the next step.
