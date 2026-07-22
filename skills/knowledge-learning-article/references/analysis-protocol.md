# Learning Analysis Protocol

## Purpose

Convert audited source material into two distinct structures:

1. `source_structure`: how the source actually develops its content.
2. `learning_structure`: the order that best helps this reader understand and use it.

Never present the second structure as if it were the author's original order.

## Pass 1: Local Extraction

Work from semantic segments rather than fixed time windows. For long material,
retain overlap at topic transitions so cross-boundary concepts are not lost.

For each segment, extract only what the evidence supports:

- source claims and confidence;
- concepts and source-local definitions;
- processes and decision points;
- causal, contrast, dependency, and example-to-claim relationships;
- examples, analogies, failures, counterexamples, and turning points;
- evidence anchors and unresolved gaps.

## Pass 2: Global Knowledge Synthesis

Merge repeated topics across distant timestamps. Deduplicate concepts while
preserving every evidence anchor. Build:

- core and supporting concepts;
- concept relationships;
- argument graph;
- process or decision structure;
- example roles;
- source limitations.

Do not turn repeated mentions into separate chapters merely because their
timestamps differ.

## Pass 3: Learning Reconstruction

Use the learner's goal and level to derive:

- prerequisites and minimum mastery;
- what is worth learning deeply;
- what is supporting context;
- what can be skipped for now;
- recommended learning order;
- transferable patterns and their limits;
- one concrete first action;
- one focused understanding check.

Classify source-grounded facts as `Source`. Classify reconstructed relationships,
prerequisites, and learning order as `Inference` unless the source explicitly
states them. Classify added application, practice, critique, or outside knowledge
as `Extension`.

## Agent Enrichment

For standard or deep output, write `15_learning/learning_enrichment.json` using
the schema in `artifact-schema.md`. Use stable upstream IDs when augmenting
existing rows. Relationships, prerequisites, learning order, critique, and
practice remain `Inference` or `Extension` unless the admitted source states them.

Before enrichment, inspect source claims, concepts, examples, and argument
segments. If claims are missing, block and return upstream. If another semantic
inventory is empty, unanchored, or heuristic, either return upstream or enter
the explicit evidence-bound mode in `evidence-reanalysis-contract.md`. Never
silently continue from an empty inventory.

Evidence-bound mode must reconstruct `core_question`, `thesis`, and
`source_structure_summary` as `agent_framing_*` evidence rows and may add
`agent_concept_*`, `agent_example_*`, and `agent_argument_*` Source rows only
after returning to the admitted normalized source. Every row requires real
source IDs, covering ranges when timing exists, a verbatim excerpt, and a
support rationale. Framing synthesis must be labeled `Inference`; direct source
wording may be `Source`. Preserve actual source sequence; semantic
re-segmentation is not permission to rewrite the author's logic.

Strong enrichment answers:

- What problem does each concept solve?
- Which concept unlocks another concept?
- Why was each example introduced?
- What does the example support, and what does it not prove?
- What would a novice misunderstand?
- What is the smallest useful first learning step?
- Which exact admitted-source excerpt anchors every reconstructed Source row?
- Why does that excerpt support the row rather than merely mention the topic?
