# Discovery Lite

Use when no `github-intent-scout` handoff exists.

This is not a full scout run. The goal is to find reference projects worth studying, not to rank adoptable tools.

## Query Families

Run 2-4 families:

- literal: the user's exact domain
- mechanism: the workflow or architecture idea
- ecosystem: skill, plugin, MCP, CLI, app, library, platform
- evidence/code: `SKILL.md`, `prompts`, `tools`, `parser`, `adapter`, `workflow`, `manifest`, `examples`

## Candidate Mix

Select 3-7 references across:

- direct peer
- adjacent domain with similar workflow
- mature platform or library
- low-star POC with visible structure
- component project
- counterexample or near miss

## Selection Criteria

Prefer projects with:

- visible implementation files
- clear input/output pipeline
- explicit intermediate artifacts
- validation or correction behavior
- reusable module boundaries
- product packaging or delivery flow

Stars are secondary. A low-star POC can be valuable if the structure is visible and transferable.

## Stop Rule

Stop discovery once you have enough diversity to extract patterns. Do not keep searching for the "best" project unless adoption is the user's goal.
