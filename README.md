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
  -> Acquisition Bundle v2
  -> target/scope source gate
  -> evidence audit
  -> provenance-checked report
```

## What Changed In v0.6

The old `knowledge-video-decomposer` carried too much: platform acquisition,
cookies, yt-dlp, Chrome probes, source gate, evidence audit, and pack building.
The user-facing architecture is now four layers:

- `knowledge-workflow-console`: product controller for routing, preflight,
  stages, status, and result index.
- `agent-reach-console`: acquisition controller. It installs/checks
  Agent-Reach, calls current upstream tools, and writes `00_acquisition`.
- `source-gated-evidence-layer`: evidence controller. It validates bundles,
  builds `source_status.json`, runs evidence audit, and blocks fake reports.
- `knowledge-document-composer`: report controller. It writes only from
  source-gated packs and keeps Source / Inference / Extension separate.

Cross-cutting guard: `browser-host-identity` keeps Edge and Chrome sessions
separate for every browser-backed route. It is a shared policy skill, not a
fifth workflow stage.

`knowledge-video-decomposer` remains an internal compatibility library for
normalization, ASR, segmentation, inventory, logic, audit, and pack building.
It is not synced as a user-facing skill. Legacy URL acquisition scripts remain
in that library but are not the primary route.

Bundle v2 adds run identity, analysis target, operation capability checks,
artifact scope, hashes, staged attempts, retry history, centralized redaction,
and downstream provenance receipts. A stale report can no longer become
`success` merely because the file still exists.

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
python .\kw.py run --input https://example.com/page --target web_article --operation read --mode audit
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
    00_source/gate_receipt.json
    analysis_receipt.json
  20_document/
    composer_receipt.json
    final_report_receipt.json
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
python .\kw.py agent-reach matrix
python .\kw.py agent-reach plan --input <url> --target video_content --operation extract_transcript
python .\kw.py acquire --input <url> --target video_content --operation extract_transcript --project-root <project>
python .\kw.py agent-reach import --input-file <primary.txt> --source-url <original-url> --platform reddit --target social_post --operation read --project-root <project>
python .\kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python .\kw.py audit --project-root <project>
python .\kw.py compose --project-root <project>
python .\kw.py run --input <url-or-file> --mode audit
python .\kw.py status --project-root <project>
python .\kw.py result --project-root <project>
python .\kw.py validate
```

Reuse an existing project root only for the exact same source, target, and
operation, and only with `--resume`. Prior bundles and downstream outputs are
archived instead of silently reused.

## Skills

- `knowledge-workflow-console`: product routing, preflight, status, result index.
- `agent-reach-console`: acquisition controller and bundle writer.
- `source-gated-evidence-layer`: bundle validation, source gate, evidence audit.
- `knowledge-document-composer`: claim map, final writer, quality gate.

Internal library: `knowledge-video-decomposer`.

## Safety

This project does not bypass CAPTCHA, paywalls, private content, region limits,
or account permissions. It does not read, display, copy, or commit cookies,
tokens, Authorization headers, or private login state. Bundles may record
whether cookies were used, never their values.

A control plugin name does not prove which browser owns the active login
state. Chrome and Edge are separate hosts. For OpenCLI, declare the real host
with `--browser-host edge` or `--browser-host chrome`; the route blocks rather
than guessing. For yt-dlp browser cookies, pass the same host through
`--youtube-browser edge|chrome`. See `browser-host-identity` for the shared
agent rule.

When an authorized browser session has produced a citeable local artifact,
handoff through Bundle v2:

```powershell
python .\kw.py browser-import `
  --input-file .\exports\visible-post.txt `
  --source-url <original-url> `
  --platform x `
  --target social_post `
  --operation read `
  --browser-host edge `
  --project-root .\outputs\browser-post
```

For an end-to-end run, use `kw run --browser-source-url <original-url>
--browser-platform <platform>`. The legacy `chrome-probe` command records an
observation only; it is not the current acquisition handoff.

Do not commit:

- `work/`
- cookies or tokens
- `outputs/`
- `test_outputs/`
- `__pycache__/`
- private logs

## Tests

```powershell
python -m py_compile kw.py kw_cli/*.py
python .\kw.py demo
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
python .\tests\test_acquisition_bundle_schema.py
python .\tests\test_local_bundle_ingest.py
python .\tests\test_agent_reach_acquire_offline.py
python .\tests\test_agent_reach_native_export.py
python .\tests\test_source_gate_from_bundle.py
python .\tests\test_no_fake_report_from_agent_reach_failures.py
python .\tests\test_run_provenance.py
python .\tests\test_browser_export_flow.py
```

## More Documentation

- [Architecture](docs/architecture.md)
- [ADR 0001](docs/adr/0001-agent-reach-acquisition-layer.md)
- [ADR 0003](docs/adr/0003-acquisition-bundle-v2-run-provenance.md)
- [Agent-Reach integration guide](docs/agent-reach-integration-guide.md)
- [Acquisition bundle protocol](docs/acquisition-bundle-protocol.md)
- [Installation](INSTALL.md)
- [User manual](USER_MANUAL.md)
- [Supported platforms](SUPPORTED_PLATFORMS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Roadmap](ROADMAP.md)
- [Release notes](RELEASE_NOTES.md)

[offline-validation-badge]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml/badge.svg
[offline-validation]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml
