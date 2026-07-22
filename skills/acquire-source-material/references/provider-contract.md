# Native Provider Contract

Each provider probe returns a channel object with:

- `status`: `ok`, `warn`, `off`, `error`, or `external_export`;
- `active_backend`: the backend selected for execution, empty unless ready;
- `backends`: ordered candidates;
- `provider_id`: stable implementation identifier;
- `message`: a redacted readiness explanation;
- `browser_hosts`: detected Edge/Chrome hosts when a browser bridge is used.

Execution is allowed only when the selected channel is `ok`, the backend
supports the requested operation, and required browser-host identity is
explicit and compatible with the probe.

Provider implementations may fetch or import material and write acquisition
metadata. They must not:

- decide `source_status`;
- classify a mismatched scope as sufficient;
- write claims, analysis packs, learning artifacts, or reports;
- persist secrets or unrestricted raw session output;
- silently fall through from a login-required platform to an anonymous page
  reader.

The provider result must be canonicalized into Bundle v2. Bundle validation,
not process exit status, determines whether an attempt can be promoted.

Media acquisition and transcription are intentionally separate. A provider
may produce primary `audio` or `video` with scope `media`; after promotion, the
evidence layer may derive a transcript and bind its hash into the gate receipt.
