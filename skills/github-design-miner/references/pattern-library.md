# Pattern Library

After decomposing projects, extract reusable patterns. Do not stop at project summaries.

## Pattern Record

```text
Pattern:
Source projects:
Pain solved:
Mechanism:
Required inputs:
Intermediate artifacts:
Validation:
Where it fits:
Where it fails:
Transfer cost:
Risk:
```

## Common Pattern Families

### Input Adapter

Converts messy formats into a stable internal schema.

Look for:

- parser registry
- format detection
- conversion fallback
- normalized JSON/Markdown
- source/page/line preservation

### Task Router

Routes broad user requests into specialized workflows.

Look for:

- intent classification
- slash commands
- mode tables
- question templates
- branch-specific outputs

### Analyzer Modules

Splits "analysis" into focused lenses.

Examples:

- profile analyzer
- relationship analyzer
- conflict detector
- duplication detector
- inconsistency detector
- timeline builder
- claim extractor

### Evidence Ledger

Links conclusions to sources.

Look for:

- claim IDs
- source refs
- confidence labels
- quote/date/page fields
- correction history

### Quality Gate

Prevents fluent but unsafe conclusions.

Look for:

- schema validation
- no-fabrication rules
- confidence thresholds
- minimum evidence counts
- runtime status
- privacy gate

### Two-Stage Confirmation

Separates proposal from final generation.

Look for:

- outline preview
- user approval
- correction loop
- draft vs installed/final output

### Runtime Verification

Verifies the mechanism actually runs.

Look for:

- smoke tests
- sample inputs
- deterministic scripts
- result snapshots
- dependency blockers

### Product Packaging

Makes the workflow reusable.

Look for:

- skill manifest
- plugin manifest
- CLI
- MCP tools
- UI metadata
- examples
- output folders

## Pattern Ranking

Rank patterns by:

- solves a real current-project gap
- preserves current project strengths
- low implementation cost
- high verification value
- clear user-facing improvement
- limited new dependencies
