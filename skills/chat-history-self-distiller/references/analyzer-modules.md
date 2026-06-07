# Analyzer Modules

Use these modules as lenses. They are not separate tools yet; they define repeatable analysis logic.

## Profile Analyzer

Use for one target person.

Evidence:

- sender-specific profile
- first/last/quarterly samples
- long messages
- behavior patterns from `_analysis/behavior_patterns.json`
- keyword hits
- cross-validation across months

Sequence-based behavior evidence is useful when keywords are weak. Use it for patterns such as short emotion -> long analysis, self-mockery -> silence, unanswered ping/question -> self-continuation, or conflict cue -> rationalization. Treat these as clues that need interpretation, not automatic personality labels.

Avoid:

- diagnosing
- turning one emotional quote into a stable trait
- ignoring alias uncertainty

## Relationship Analyzer

Use for interactions between people.

Look for:

- who initiates topics
- who repairs conflict
- who asks, avoids, explains, jokes, or escalates
- response delay or silence patterns when available
- themes that appear only between specific pairs

Every relationship claim should mention whose messages support it.

## Theme Evolution Analyzer

Use for recurring topics and change over time.

Process:

1. identify candidate themes from stats, keywords, and samples
2. group evidence by month or period
3. compare early, middle, and recent expressions
4. mark stable, fading, intensifying, or transformed themes

## Conflict Detector

Use for contradictions or tensions.

Conflict types:

- direct contradiction
- numerical/date mismatch
- procedural or decision conflict
- value tension
- self-description vs. behavior mismatch

Output fields:

- claim A
- claim B
- sources/dates
- conflict type
- severity
- confidence
- possible resolution or uncertainty

## Duplication / Repetition Detector

Use for repeated topics, repeated arguments, or duplicated document content.

Classify:

- exact repetition
- near repetition
- thematic recurrence
- unresolved loop

For chat analysis, repeated emotional themes are not automatically "problems"; describe the pattern and evidence.

## Inconsistency Detector

Use for terminology, scope, tone, or version drift.

Good for:

- reports and policies
- multi-document folders
- long-running plans
- conversations where the same concept changes name or meaning

## Timeline Builder

Use when order matters.

Each event needs:

- date/time or period
- source
- event statement
- confidence
- unresolved gaps

## Claim Extractor

Use when the user asks for facts, promises, decisions, preferences, or beliefs.

Each claim needs:

- claim text
- claim type
- source quote
- date/section
- confidence
- whether it is user-confirmed, evidence-only, or contradicted
