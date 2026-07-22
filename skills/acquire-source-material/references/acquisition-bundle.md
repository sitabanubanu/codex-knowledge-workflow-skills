# Acquisition Bundle v2

The canonical protocol is `docs/acquisition-bundle-protocol.md`.

Producer checklist:

1. Bind the project root to one `run_id`, source fingerprint, target, and
   operation.
2. Create a fresh `attempt_id` under `.kw_staging/`.
3. Store artifacts and logs only below the staged `00_acquisition/`.
4. Use relative contained artifact paths.
5. Record artifact id, type, source class, content scope, coverage, run/source
   ids, byte count, and SHA-256.
6. Persist only redacted input, metadata, commands, errors, and notes.
7. Keep bundle statuses acquisition-only: `material_acquired`,
   `partial_material_acquired`, `metadata_only`, `secondary_only`, `blocked`,
   `failed`, or `unsupported`.
8. Validate status invariants and hashes before promotion.
9. Archive the prior bundle on resume.

Do not create `source_status`, evidence claims, analysis packs, or reports in
this skill.
