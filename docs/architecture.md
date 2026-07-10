# Architecture

Knowledge Workflow is now a source-gated acquisition-to-report workflow.

```text
kw.py / knowledge-workflow-console
  -> preflight
  -> agent-reach-console or local bundle builder
  -> 00_acquisition/manifest.json
  -> source-gated-evidence-layer
  -> 10_video/00_source/source_status.json
  -> transcript normalization / ASR / segmentation
  -> inventory / source logic
  -> evidence audit
  -> video_analysis_pack.md (compatibility)
  -> source_analysis_pack.md (migration target)
  -> knowledge-document-composer
  -> claim_map.json
  -> quality_gate.json
  -> final_report.md when approved
  -> result_index.md
```

## Responsibilities

| Layer | Owns | Does not own |
| --- | --- | --- |
| `agent-reach-console` | installation checks, doctor, upstream route selection, acquisition bundle writing | source gate, evidence audit, claims, reports |
| `source-gated-evidence-layer` | bundle validation, `source_status.json`, normalization, ASR handoff, evidence audit, pack gate, degraded output | platform fetching, cookies, raw browser state |
| `knowledge-document-composer` | Source / Inference / Extension, claim map, report outline, quality gate, final report | acquisition, source-status repair, metadata promotion |
| `knowledge-workflow-console` | product routing, preflight, status, result index | detailed acquisition, evidence analysis, prose judgment |

## Stable Handoff

The acquisition bundle is the only stable interface between acquisition and
evidence:

```text
00_acquisition/manifest.json
```

The evidence layer maps bundle status to source status. Only
`source_confirmed` and `source_partial` can enter normal or partial
decomposition.

## Compatibility

The first architecture-reset implementation still writes:

```text
10_video/
```

This avoids breaking existing tests and users. The future name is:

```text
10_source/
```

`knowledge-document-composer` accepts `source_analysis_pack.md` when present and
falls back to legacy `video_analysis_pack.md`.

## Legacy Acquisition

These old second-skill scripts are retained but no longer primary:

- `acquisition_runner.py`
- `platform_media_runner.py`
- `chrome_media_probe.py` as the main acquisition route
- YouTube cookies as the main flow
- Bilibili generic-web fallback as the main flow

They must not be used to bypass the acquisition bundle or source gate.
