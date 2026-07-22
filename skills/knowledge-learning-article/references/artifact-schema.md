# Learning Artifact Schema

## Input Gate

Require current files:

```text
00_acquisition/manifest.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/analysis_receipt.json
10_video/video_analysis_pack.md or source_analysis_pack.md
```

Allow only `source_confirmed` and visibly bounded `source_partial` inputs.

## Agent Enrichment

Optional for `brief`; expected for `standard` and `deep`:

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
      "examples": "reconstructed|none_identified_in_source",
      "argument_structure": "reconstructed"
    },
    "inventory_notes": {}
  },
  "source_framing": [
    {
      "id": "agent_framing_core_question",
      "field": "core_question|thesis|source_structure_summary",
      "text": "",
      "category": "Source|Inference",
      "support_rationale": "",
      "evidence_spans": [
        {
          "transcript_ids": ["t0001"],
          "start": 0.0,
          "end": 10.0,
          "verbatim_excerpt": ""
        }
      ]
    }
  ],
  "learning_structure_summary": "",
  "concepts": [
    {
      "id": "agent_concept_001",
      "term": "",
      "definition": "",
      "why_it_matters": "",
      "priority": "core|supporting|background",
      "prerequisites": [],
      "relationships": [],
      "linked_example_ids": [],
      "source_claim_ids": [],
      "learning_notes": "",
      "support_rationale": "",
      "category": "Source",
      "evidence_spans": [
        {
          "transcript_ids": ["t0001"],
          "start": 0.0,
          "end": 10.0,
          "verbatim_excerpt": ""
        }
      ]
    }
  ],
  "examples": [
    {
      "id": "agent_example_001",
      "name": "",
      "what_it_is": "",
      "why_introduced": "",
      "how_it_works": "",
      "what_it_supports": "",
      "role": "foundational|illustrative|counterexample|boundary",
      "linked_concept_ids": [],
      "source_claim_ids": [],
      "support_rationale": "",
      "category": "Source",
      "evidence_spans": []
    }
  ],
  "argument_nodes": [
    {
      "id": "agent_argument_001",
      "role": "question|setup|mechanism|qualification|critique|conclusion",
      "title": "",
      "summary": "",
      "source_claim_ids": [],
      "support_rationale": "",
      "category": "Source",
      "evidence_spans": []
    }
  ],
  "argument_edges": [
    {
      "from": "agent_argument_001",
      "to": "agent_argument_002",
      "relation": "supports|explains|qualifies|contrasts|leads_to"
    }
  ],
  "concept_enrichment": {
    "concept_001": {
      "priority": "core|supporting|background",
      "why_it_matters": "",
      "prerequisites": [],
      "relationships": [
        {
          "target_id": "concept_002",
          "type": "requires|enables|contrasts|causes|explains|applies",
          "explanation": ""
        }
      ],
      "linked_example_ids": [],
      "source_claim_ids": [],
      "learning_notes": ""
    }
  },
  "example_enrichment": {
    "example_001": {
      "why_introduced": "",
      "how_it_works": "",
      "what_it_supports": "",
      "role": "foundational|illustrative|counterexample|boundary",
      "source_claim_ids": []
    }
  },
  "prerequisites": [
    {
      "name": "",
      "why_needed": "",
      "minimum_mastery": "",
      "category": "Inference"
    }
  ],
  "learning_priorities": {
    "worth_learning": []
  },
  "transfer_patterns": [
    {
      "name": "",
      "pattern": "",
      "use_when": "",
      "limits": "",
      "source_claim_ids": [],
      "category": "Inference|Extension"
    }
  ],
  "learning_path": {
    "learn_first": [],
    "learn_next": [],
    "skip_for_now": [],
    "first_action": "",
    "check_question": "",
    "review_prompts": []
  },
  "uncertainties": []
}
```

Use `concept_enrichment` and `example_enrichment` to augment IDs already present
upstream. Top-level `source_framing`, `concepts`, `examples`, `argument_nodes`,
and `argument_edges` are forbidden unless `source_reanalysis.mode` is
`evidence_bound` and the contract in `evidence-reanalysis-contract.md` passes.
Free-text top-level `core_question`, `thesis`, and `source_structure_summary`
are forbidden. Evidence-bound mode requires exactly one `source_framing` row
for each of those fields. A framing row may be `Source` when the source states
it directly or `Inference` when it is a synthesis, but either category must be
anchored to admitted evidence. Never invent claim, segment, or transcript IDs.
Reanalysis concept, example, and argument rows are Source inventory; learning
inference belongs in enrichment, prerequisites, transfer patterns, and
learning-path fields.

## Produced Artifacts

```text
15_learning/
  learning_request.json
  learning_enrichment.json              # Agent-authored when used
  source_reanalysis_validation.json     # always written; fail-closed gate
  knowledge_map.json
  argument_graph.json
  concept_cards.json
  example_roles.json
  prerequisite_map.json
  transfer_patterns.json
  learning_path.json
  learning_analysis_pack.json
  learning_analysis_pack.md
  learning_analysis_receipt.json

20_document/
  learning_article_candidate.md
  learning_quality_gate.json
  learning_article.md
  learning_article_receipt.json
```

Every final receipt must copy the upstream provenance identity and bind hashes
to the current upstream receipt, output, and quality gate.
