# Architecture

Knowledge Workflow is a three-skill Codex package with a thin repository CLI.

```text
kw.py / knowledge-workflow-console
  -> preflight
  -> source gate
  -> knowledge-video-decomposer
  -> evidence audit
  -> video_analysis_pack.md
  -> knowledge-document-composer
  -> quality_gate.json
  -> final_report.md
  -> result_index.md
```

## Skill Responsibilities

### knowledge-workflow-console

- classify input,
- choose route and mode,
- run preflight,
- call end-to-end runner,
- write status summary and result index.

### knowledge-video-decomposer

- source acquisition state,
- transcript normalization,
- ASR route,
- segmentation,
- inventory,
- source logic,
- evidence audit,
- video analysis pack.

### knowledge-document-composer

- source gate for document planning,
- commitments,
- source reconstruction,
- claim map,
- final report writer,
- quality gate.

## Product CLI

`kw.py` is intentionally thin. It wraps existing stage scripts and should not
reimplement source gating, ASR, evidence audit, or report quality checks.
