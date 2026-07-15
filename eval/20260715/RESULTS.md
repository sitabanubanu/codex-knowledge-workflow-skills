# Knowledge Workflow evaluation results — 2026-07-15

Project: `E:\git\codex-skills-backup`

Version: `v0.6.0`
Commit: `5fddb2e`

## Experiment 1 — search quality

Ten frozen learning needs, five final candidates per arm, 50 candidates per arm.

| Metric | Ordinary Agent | Knowledge Workflow |
|---|---:|---:|
| Average valid candidates in top 5 | 4.00 | 5.00 |
| Top 3 contains at least one strong match | 90.0% | 100.0% |
| Candidates with complete original material | 36.0% | 84.0% |
| Clearly irrelevant or unobtainable | 50.0% | 0.0% |
| Average processing time | 411.0s | 198.6s |

Scores use the frozen 10-point rubric. “Complete original material” requires an explicit full-text or full-transcript check. Partial material is not counted as complete. The score is machine-assisted candidate screening; it still needs an independent human relevance/depth review before being used as a résumé claim.

## Experiment 2 — material sufficiency, 20-task minimum set

The valid ordinary arm is `ordinary_v2`; the first ordinary arm was discarded because it could see gold labels in the original manifest.

| Metric | Ordinary Agent | Knowledge Workflow |
|---|---:|---:|
| Strict result accuracy | 95.0% (19/20) | 85.0% (17/20) |
| Safe result rate | 100.0% (20/20) | 100.0% (20/20) |
| Material-insufficiency error pass rate | 0.0% (0/10) | 0.0% (0/10) |
| End-to-end completion on complete material | 100.0% (10/10) | 80.0% (8/10) |
| Conclusion traceability | 74.1% (43/58) | 100.0% (33/33) |
| Unsupported-claim rate | 25.9% (15/58) | 0.0% (0/33) |
| Average processing time | 42.9s | 3.2s |

“Safe result” treats a material-deficiency explanation as safe when it does not authorize a full report. The Workflow strict misses are KW-17—KW-19: the product safely downgraded target mismatches to a material-deficiency explanation, while the frozen gold label requested `must_stop`.

The two media tasks KW-04 and KW-05 exposed a real product defect: ASR creates a `source_status.json` without `failed_probes`; the downstream transcript-segment validation then fails even though the ASR transcript is available and the source gate says `source_confirmed`. This is why Workflow end-to-end completion is 8/10.

## Experiment 3 — report fidelity

The 10 complete materials were paired with the two report arms and a source-grounded machine pre-review was run.

| Machine-assisted pre-review | Ordinary Agent | Knowledge Workflow |
|---|---:|---:|
| Report exists | 100.0% | 80.0% |
| Core-claim coverage proxy | 67.5% | 55.0% |
| Traceability | 82.4% | 100.0% |
| Unsupported-claim rate | 17.6% | 0.0% |

The coverage figure is a term-matching screening proxy, not a semantic human score. The blind review packet was created, but the three model-assisted reviewers timed out on the long reports; no artificial human-review number is reported.

## Experiment 4 — learning effect

Not run. The active-question, practice, and user-recall modules are not complete, so no learning-gain or retention result is claimed.

## Verification

- `kw.py doctor --json`: exit 0, expected route warnings only.
- `kw.py validate --dry-run`: exit 0.
- `tests/real_workflow_acceptance.py`: exit 0.
- `tests/knowledge_workflow_regression.py`: 19 PASS, exit 0.

Detailed machine records are in `test_outputs/eval_20260715/`; the evaluation scripts and frozen inputs are in this directory.
