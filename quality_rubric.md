# Quality Rubric

Use this rubric to evaluate generated reports and templates. It is intentionally
source-gate aligned: a polished report is not good if it is unsupported.

| Dimension | Pass Criteria |
| --- | --- |
| Source faithfulness | Major claims are tied to transcript spans, source logic, or approved pack artifacts. |
| Source / Inference / Extension separation | The report visibly separates what the source says, what the workflow infers, and what it extends. |
| Claim quality | Claims are concrete, non-duplicative, and not upgraded from metadata or secondary context. |
| Examples and analogies | Examples and analogies preserve their source context and are not invented as source facts. |
| Uncertainty | Gaps, partial coverage, ASR uncertainty, and degraded routes are explicitly labeled. |
| Reusability | Output can be reused as notes, a brief, a script, a prompt pack, or knowledge-base material. |
| Safety and privacy | No cookies, tokens, private account data, or unsupported access claims appear in outputs. |

## Scoring

- `pass`: meets the criterion.
- `partial`: useful but has visible gaps or weak evidence.
- `fail`: violates the source gate, hides uncertainty, or mislabels evidence.

Do not approve a full report if Source / Inference / Extension separation is
missing or if a complete analysis was created without primary material.
