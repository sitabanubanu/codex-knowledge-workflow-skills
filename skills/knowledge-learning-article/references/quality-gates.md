# Learning Article Quality Gates

Block final delivery when any condition fails:

- upstream provenance is stale or hash-mismatched;
- source status is not `source_confirmed` or bounded `source_partial`;
- upstream source claims are missing;
- concepts, examples, or argument segments are empty, unanchored, or heuristic
  without approved evidence-bound reanalysis;
- evidence-bound `core_question`, `thesis`, or `source_structure_summary` is
  supplied as free text, omitted, duplicated, or lacks admitted-source anchors;
- a reanalysis Source row cites a missing ID, mismatched range, non-verbatim
  excerpt, dangling linked ID, or lacks a support rationale;
- the declared source artifact, enrichment, validation artifact, or receipt hash
  is stale;
- evidence-bound reanalysis is not disclosed near the article opening;
- Agent-created learning priorities, relationships, prerequisites, transfer
  methods, or practice steps are not visibly disclosed as Inference or Extension;
- partial scope is not visible;
- the article omits required learning functions;
- selected concepts disappear from the article, or no validated concept exists;
- timestamps are used as main headings;
- examples are named without explaining their instructional or argumentative role;
- the article lacks a concrete first action or understanding check;
- Source, Inference, and Extension are blurred;
- requested language or UTF-8 encoding is broken;
- the article is too shallow to connect concepts, examples, reasoning, and action.

Warn, but do not automatically block, when `standard` or `deep` output uses only
the deterministic baseline after the upstream semantic inventory has passed.
Never replace an incomplete semantic inventory with an unverified fallback.

Deliver only when:

```json
{
  "approved_for_learning_article": true,
  "blocking_gates": []
}
```

and `learning_article_receipt.json` binds the current learning receipt, article,
and quality gate hashes.
