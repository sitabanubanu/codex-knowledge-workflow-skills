# Evidence-Bound Source Reanalysis Contract

Use this contract only when the upstream source gate and analysis receipt are
current but the semantic inventory is empty, unanchored, incomplete, or limited
to heuristic time chunks.

## Hard boundary

- No admitted primary material or normalized source artifact: block.
- No evidence-grounded upstream source claims: block and repair upstream.
- Missing semantic inventory without a declared reanalysis contract: block.
- Never create Source content from general knowledge, plausibility, a title, or
  an empty field.

## Required declaration

Add `source_reanalysis` to `learning_enrichment.json`:

```json
{
  "source_reanalysis": {
    "mode": "evidence_bound",
    "reason": "upstream_semantic_inventory_incomplete",
    "source_artifact": "10_video/01_transcript/clean_transcript.jsonl",
    "scopes": ["source_framing", "concepts", "examples", "argument_structure"],
    "inventory_outcomes": {
      "source_framing": "reconstructed",
      "concepts": "reconstructed",
      "examples": "reconstructed",
      "argument_structure": "reconstructed"
    },
    "inventory_notes": {}
  }
}
```

`source_artifact` must be project-relative, remain inside the workflow project,
and contain UTF-8 JSONL rows with stable `id` plus `text` or
`normalized_text`. Timed rows should include `start` and `end`.

`examples` may use `none_identified_in_source` only after the admitted source
has been reviewed. In that case, add a concrete explanation under
`inventory_notes.examples` and do not add example rows.

## Required evidence rows

Evidence-bound mode also requires exactly three `source_framing` rows: one each
for `core_question`, `thesis`, and `source_structure_summary`. Do not provide
those fields as unvalidated top-level free text. A framing row may use
`category: Source` when stated directly or `category: Inference` when it
synthesizes several source passages. In both cases it must remain traceable to
the admitted source.

Every source-framing row, reanalysis concept, example, and argument node must
contain:

- an `agent_framing_*`, `agent_concept_*`, `agent_example_*`, or
  `agent_argument_*` ID;
- an allowed category (`Source` for inventory rows; `Source` or `Inference` for
  framing rows);
- source-specific content fields rather than generated defaults;
- `support_rationale`, explaining why the cited material supports the row;
- at least one `evidence_spans` entry;
- real `transcript_ids` found in the declared source artifact;
- a range covering the referenced rows when source timing exists;
- `verbatim_excerpt`, copied from the referenced rows.

The deterministic validator confirms artifact identity, ID existence, time
coverage, verbatim presence, linked-ID integrity, and rationale presence. The
Agent remains responsible for semantic judgment: read the referenced material
and ensure the rationale actually supports the claim.

## Output and disclosure

Write `15_learning/source_reanalysis_validation.json`. Continue only when
`approved_for_learning_analysis` is true. Bind the validation artifact, source
artifact hash, enrichment hash, and upstream analysis receipt into the learning
receipt. Disclose evidence-bound reanalysis near the article opening.

Source reanalysis restores a missing semantic inventory from admitted evidence.
It does not repair acquisition, source status, missing claims, or absent primary
material.
