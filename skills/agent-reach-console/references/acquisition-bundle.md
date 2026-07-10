# Acquisition Bundle

This skill writes the protocol defined in:

```text
docs/acquisition-bundle-protocol.md
```

Rules for this skill:

- Always create `00_acquisition/manifest.json`.
- Store acquired files under `00_acquisition/artifacts/`.
- Store doctor output, command summaries, and notes under
  `00_acquisition/logs/`.
- `commands.jsonl` records command arguments and exit codes only, with secrets
  redacted.
- `manifest.json` records whether cookies or browser sessions were used, never
  their contents.
- The bundle status must reflect acquisition only:
  `material_acquired`, `partial_material_acquired`, `metadata_only`,
  `secondary_only`, `blocked`, `failed`, or `unsupported`.
- Do not convert bundle status into `source_status`; that belongs to
  `source-gated-evidence-layer`.
