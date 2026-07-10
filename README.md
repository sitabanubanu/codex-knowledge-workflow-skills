# Knowledge Workflow Skills

[![offline-validation][offline-validation-badge]][offline-validation]

Agent-Reach gets the material.
Knowledge Workflow decides whether the material is trustworthy.
No primary material, no fake report.

This repository is a Codex skill package and local CLI for source-gated
knowledge work. It connects an acquisition layer to an evidence layer and then
to auditable report generation.

```text
Agent-Reach acquisition
  -> acquisition_bundle
  -> source-gated evidence
  -> auditable report generation
```

## What Changed In v0.6

The old `knowledge-video-decomposer` carried too much: platform acquisition,
cookies, yt-dlp, Chrome probes, source gate, evidence audit, and pack building.
The architecture is now split:

- `agent-reach-console`: acquisition controller. It installs/checks
  Agent-Reach, calls current upstream tools, and writes `00_acquisition`.
- `source-gated-evidence-layer`: evidence controller. It validates bundles,
  builds `source_status.json`, runs evidence audit, and blocks fake reports.
- `knowledge-document-composer`: report controller. It writes only from
  source-gated packs and keeps Source / Inference / Extension separate.

Legacy URL acquisition scripts remain available for compatibility, but they are
not the primary route.

## Three-Minute Start

Run the local transcript demo first. It avoids platform instability and proves
the source-gated core:

```powershell
python .\kw.py demo
```

Open:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

For an explicit local file:

```powershell
python .\kw.py run --input .\examples\demo_transcript\input.txt --mode audit --language en --final-language en
```

For URL acquisition:

```powershell
python .\kw.py agent-reach doctor
python .\kw.py run --input https://example.com/page --mode audit
```

Every run should tell you:

- acquisition status;
- source status;
- whether a full report is allowed;
- `result_index.md` path.

## Acquisition Bundle

The stable handoff is:

```text
outputs/knowledge-workflow/<project>/
  00_acquisition/
    manifest.json
    artifacts/
    logs/
  10_video/
    00_source/source_status.json
  20_document/
  30_final/
```

See [docs/acquisition-bundle-protocol.md](docs/acquisition-bundle-protocol.md).

Short term, the evidence stage still writes `10_video` for compatibility. It
will move toward `10_source` in a later migration.

## Source Gate

Normal report generation is allowed only for:

- `source_confirmed`
- `source_partial`

These are blocked from normal final reports:

- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`
- bundle `metadata_only`
- bundle `blocked`
- bundle `failed`
- bundle `unsupported`

When blocked, the workflow writes degraded status and next actions instead of a
fake complete analysis.

## CLI

```powershell
python .\kw.py agent-reach install --safe
python .\kw.py agent-reach doctor
python .\kw.py acquire --input <url> --project-root <project>
python .\kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python .\kw.py audit --project-root <project>
python .\kw.py compose --project-root <project>
python .\kw.py run --input <url-or-file> --mode audit
python .\kw.py status --project-root <project>
python .\kw.py result --project-root <project>
python .\kw.py validate
```

## Skills

- `knowledge-workflow-console`: product routing, preflight, status, result index.
- `agent-reach-console`: acquisition controller and bundle writer.
- `source-gated-evidence-layer`: bundle validation, source gate, evidence audit.
- `knowledge-video-decomposer`: legacy-compatible decomposition scripts and pack builder.
- `knowledge-document-composer`: claim map, final writer, quality gate.

## Safety

This project does not bypass CAPTCHA, paywalls, private content, region limits,
or account permissions. It does not read, display, copy, or commit cookies,
tokens, Authorization headers, or private login state. Bundles may record
whether cookies were used, never their values.

Do not commit:

- `work/`
- cookies or tokens
- `outputs/`
- `test_outputs/`
- `__pycache__/`
- private logs

## Tests

```powershell
python -m py_compile kw.py kw_cli/main.py kw_cli/bundle.py kw_cli/agent_reach_adapter.py kw_cli/ingest.py
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
python .\tests\test_acquisition_bundle_schema.py
python .\tests\test_local_bundle_ingest.py
python .\tests\test_agent_reach_acquire_offline.py
python .\tests\test_source_gate_from_bundle.py
python .\tests\test_no_fake_report_from_agent_reach_failures.py
```

## More Documentation

- [Architecture](docs/architecture.md)
- [ADR 0001](docs/adr/0001-agent-reach-acquisition-layer.md)
- [Acquisition bundle protocol](docs/acquisition-bundle-protocol.md)
- [Installation](INSTALL.md)
- [User manual](USER_MANUAL.md)
- [Supported platforms](SUPPORTED_PLATFORMS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Roadmap](ROADMAP.md)
- [Release notes](RELEASE_NOTES.md)

[offline-validation-badge]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml/badge.svg
[offline-validation]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml
