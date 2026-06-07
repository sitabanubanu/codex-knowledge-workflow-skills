---
name: github-design-miner
description: Learn from GitHub projects by decomposing their architecture, extracting transferable design patterns, comparing them against the user's current skill/plugin/tool/project, and producing a design transfer map plus implementation brief. Use when the user asks to "学习别人的项目怎么做", "拆解 GitHub 项目架构", "借鉴同类 skill 改我的 skill", "从这些项目里提炼设计模式", "帮我完善当前插件/skill/工具", or when a github-intent-scout handoff should be deepened into a design-mining pass.
metadata:
  short-description: Mine GitHub projects for transferable design patterns
---

# GitHub Design Miner

Use this skill when the user wants to learn from GitHub projects and improve their own skill, plugin, tool, workflow, or app. This is not a recommendation skill. It studies how other projects are designed and converts useful ideas into a concrete transfer plan.

Core rule: mine for transferable design, not merely adoptable projects. Preserve the user's project's core purpose and strengths.

## Relationship To GitHub Intent Scout

This skill is independent.

- If the user has not run `github-intent-scout`, run a discovery-lite search yourself.
- If the user provides or references a `github-intent-scout` handoff, use it as seed evidence and skip broad discovery unless the handoff is stale or too thin.
- Do not re-run a full scout pass after receiving a good handoff. Deepen selected candidates only.

Use `github-intent-scout` when the user primarily asks "what can I use?" Use this skill when the user primarily asks "what can I learn and transfer?"

## Navigation

Read references only when needed:

- `references/handoff.md`: when continuing from a `github-intent-scout` handoff.
- `references/discovery-lite.md`: when no handoff exists and reference projects must be discovered.
- `references/decomposition-template.md`: when deep-reading a selected reference project.
- `references/pattern-library.md`: when extracting reusable design patterns.
- `references/transfer-map.md`: when mapping external patterns to the user's current project.

## Required Inputs

Try to identify:

1. The user's current project/skill/plugin/tool to improve.
2. The improvement goal: reliability, commercial polish, extensibility, UX, evidence discipline, architecture, safety, installability, or another target.
3. Non-goals: what should not change.
4. Reference candidates: from user, GitHub search, or scout handoff.

If the current project is not available, you can still produce a pattern library, but mark the transfer map as `CurrentProjectUnverified`.

## Workflow

### Phase 1: Current Project Map

Read the user's project before proposing changes when possible.

Create a compact map:

- goal and audience
- current workflow
- file/resource structure
- inputs and outputs
- current strengths
- current gaps
- constraints and non-goals
- "preserve the soul": the core idea that should not be overwritten

### Phase 2: Handoff Or Discovery

If a scout handoff exists, parse:

- user intent
- answer shape
- serious candidates
- checked files
- verified claims
- weak claims
- promising patterns
- remaining unknowns

Then choose deep-dive targets.

If no handoff exists, run discovery-lite:

- Search 2-4 query families: literal, mechanism, ecosystem, evidence/code.
- Include direct peers, adjacent domains, strong components, mature platforms, low-star POCs with useful structure, and counterexamples.
- Inspect source artifacts beyond README for selected references.

### Phase 3: Reference Project Decomposition

For each selected reference project, decompose:

- problem solved
- core mechanism
- input and output model
- module boundaries
- intermediate artifacts
- validation and tests
- error handling
- user confirmation or review loop
- data/privacy boundary
- product delivery shape
- implementation evidence
- what not to copy

Use `references/decomposition-template.md` for the detailed table.

### Phase 4: Pattern Extraction

Extract patterns across projects, not just project summaries.

Common pattern families:

- input adapters
- task routing
- analyzer modules
- evidence ledger
- claim-vs-implementation checks
- quality gates
- runtime smoke tests
- correction/versioning
- two-stage confirmation
- export/delivery
- privacy and safety boundary
- plugin/skill packaging

Use `references/pattern-library.md`.

### Phase 5: Gap Analysis

Compare patterns to the current project:

- already strong
- present but weak
- missing and worth adding
- present externally but unsuitable
- dangerous because it would damage the original project

### Phase 6: Design Transfer Map

Produce a transfer map:

```text
External logic -> Transferable pattern -> Current project landing point -> Priority -> Risk -> Validation
```

Use `references/transfer-map.md`.

### Phase 7: Implementation Brief

If the user wants changes, provide a brief that can hand off to an editing/skill-creation workflow:

- files to modify
- files to add
- logic to preserve
- logic to avoid
- validation steps
- open risks

Do not edit files unless the user explicitly asks to implement the changes in the current turn.

## Output Contract

For a complete design-mining pass, return:

1. `Current Project Map`
2. `Reference Projects`
3. `Architecture Decomposition`
4. `Pattern Library`
5. `Gap Analysis`
6. `Design Transfer Map`
7. `Implementation Brief`
8. `Non-Goals And Risks`

For a small pass, return only:

- what was studied
- transferable patterns
- what applies to the user's project
- what should not be copied
- next implementation steps

## Boundaries

- Do not optimize for stars or direct installability; this skill values transferable design.
- Do not recommend adopting a project unless the user's question shifts back to adoption.
- Do not rewrite the user's project around a reference project's worldview.
- Do not trust README-only architecture claims; inspect implementation artifacts when claims matter.
- Do not produce a migration plan without first naming the current project's existing strengths.
