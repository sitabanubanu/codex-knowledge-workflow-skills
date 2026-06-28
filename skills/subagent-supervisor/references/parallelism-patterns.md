# Parallelism Patterns

## When parallel is safe

Parallelize only when each subagent can work with clear ownership and the supervisor can integrate the results:

- Different files or disjoint write scopes.
- Different problems that do not share mutable state.
- Research plus implementation, when research can inform but does not block the initial bounded edit.
- Execution plus independent review, when the reviewer inspects an existing artifact or completed patch.
- Multiple independent reviewers checking the same artifact without writing to it.

## When serial is required

Run work in sequence when ordering, scope, or judgment affects the next step:

- Agents would edit the same file or shared generated artifact.
- Downstream work depends on upstream decisions, APIs, schemas, or file shape.
- The target may change based on intermediate findings.
- User confirmation is required before continuing.
- The boundary is unclear, contested, or likely to expand.

## Patterns

### Divide and Conquer

Split a large task by disjoint files, modules, sections, or deliverables. Assign one owner per write surface, then have the supervisor integrate and verify.

### Independent Review

Send one or more reviewers to inspect the same artifact read-only. Compare findings, discard unsupported claims, and keep acceptance with the supervisor.

### Research + Implementation

Run an explorer on source discovery or constraints while a worker handles a bounded implementation that does not depend on the explorer's unresolved findings. Integrate only after both return.

### Execute + Verify

Assign a worker to produce or modify an artifact, then assign a reviewer or keep supervisor verification separate. The reviewer should inspect the artifact, not the worker's reasoning alone.

### Candidate Comparison

Use explorers to evaluate separate options, repositories, designs, vendors, or approaches under the same scoring criteria. The supervisor compares evidence and chooses the next action.

## Conflict controls

- Use disjoint write sets for concurrent workers.
- Do not allow shared file writes across parallel agents.
- Keep integration supervisor-owned.
- Make each prompt state ownership, forbidden scope, return contract, and stop condition.
- If a conflict appears, stop parallel work for that surface and serialize integration.
