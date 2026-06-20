# Research Brief

Use this reference after the initial intent map and before building query families.

Purpose: define the user's adoption decision, scope the search branch, and decide whether to run an orientation pass before deep verification.

## Core Rule

Do not spend deep search effort until the task direction is clear enough that the candidate class will not change materially.

## Search Rhythm

Use two stages when the direction is broad or ambiguous:

1. `orientation run`: map possible answer shapes and task branches with 1-2 broad search rounds.
2. `focused deep run`: after the direction is clear, run evidence-backed discovery, code search, family mapping, claim checks, scoring, and adoption recommendation.

Skip orientation only when the user already gave a narrow target, exact constraints, or explicitly asked you to proceed without questions. If skipping orientation for a broad request, state assumptions before searching and name branches that are out of scope.

## Task Direction Check

Check broad terms before deep searching:

| Broad term | Direction questions |
|---|---|
| `document analysis` | Existing documents or generating new content? Single document or many documents? Q&A, extraction, summary, comparison, or formal review? |
| `research` | Literature discovery, analysis of an existing library, automatic paper generation, experiment workflow, or writing support? |
| `skill/plugin` | Must be installable in one host, or is a library/platform/MCP/workflow acceptable? |
| `chat/history/memory` | Personal self-analysis, relationship analysis, workplace memory, or generic conversation statistics? |
| `agent` | Prompt/workflow agent, coding agent, MCP tool, runtime protocol, or multi-agent framework? |

Prefer questions that determine:

- Existing material analysis vs. new content generation.
- Q&A/retrieval vs. structured synthesis/reporting.
- Single-file vs. multi-file/corpus workflow.
- Local/privacy-first vs. cloud/API acceptable.
- Required host/tool vs. any agent ecosystem.

Ask a clarifying question only when all likely branches are materially different and a reasonable assumption would waste substantial work. Otherwise state the assumption and search multiple branches.

## Orientation Run

Use orientation when:

- The user's request has multiple strong branches.
- Literal terms are broad, such as `document`, `agent`, `research`, `memory`, `plugin`, or `skill`.
- The user will likely spend time installing or adopting the result.
- Private/local data or high-stakes accuracy matters.
- Direct search terms are likely to collide with unrelated ecosystems.

Orientation procedure:

1. Run 1-2 broad searches across literal terms, mechanism terms, and evidence terms.
2. Report 2-5 candidate directions with 1-2 representative projects each.
3. Name likely wrong branches and why.
4. Ask up to 3 concise direction questions.
5. After the user answers, start the focused run.

If the user explicitly requests a full run without questions, include this instead of stopping:

```text
Search Assumptions:
- I will treat "<term>" as <chosen branch>, not <excluded branch>.
- I will include <allowed answer shapes>, not only <too-narrow shape>.
- I will prioritize <privacy/install/runtime constraint> where possible.
```

## Research Brief Fields

Before scoring serious projects, maintain a compact brief:

| Field | Notes |
|---|---|
| User decision | What adoption or comparison decision the user will make. |
| Primary branch | The answer branch being searched first. |
| Adjacent branches | Branches worth checking to avoid missing better shapes. |
| Out of scope | Branches intentionally excluded. |
| Must-verify facts | Claims that would change the recommendation if false. |
| Risk boundary | Privacy, cost, runtime, host, license, or maintenance constraints. |

