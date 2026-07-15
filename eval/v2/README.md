# Evaluation Protocol v2

This directory is the versioned, offline-first evaluation harness introduced
after the 2026-07-15 engineering pilot.

It separates:

- neutral task inputs under `inputs/`;
- workflow-only fixture construction under `harness/`;
- gold decisions under `gold/`;
- machine-readable result contracts under `schemas/`;
- runners and scorers at the protocol root.

The initial eight-task contract track is a harness acceptance test, not a
performance benchmark. It verifies that input/gold separation and structured
gate scoring work before a larger dataset or an ordinary-Agent arm is run.

## Offline contract smoke

From the repository root:

```powershell
python .\eval\v2\leakage_lint.py
python .\eval\v2\run_workflow_contract.py `
  --output-root .\test_outputs\eval_v2\workflow
python .\eval\v2\score_decisions.py `
  --results .\test_outputs\eval_v2\workflow\results.jsonl `
  --output-root .\test_outputs\eval_v2\scoring
```

Use `--allow-dirty` only for development runs. Such runs are marked
`releasable: false` in `run_manifest.json`.

## Protocol rules

1. Runners do not import or read `gold/`.
2. Scorers run only after outputs are closed.
3. Decisions come from structured fields, never `status_reason` text.
4. Each task writes an independent result before the next task starts.
5. `test_outputs/` remains untracked.
6. Live retrieval, fixed-pool ranking, fidelity, human review, and learning
   effect are separate future tracks. They must not be folded into this
   contract smoke score.
