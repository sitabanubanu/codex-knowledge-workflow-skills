# ADR 0003: Browser Bridge Before Cookie-Database Access

## Decision

For browser-backed material, Knowledge Workflow first uses an explicitly
declared Edge or Chrome OpenCLI session to obtain visible task-primary text or
transcript. It uses yt-dlp browser-cookie access only as a fallback for
YouTube.

## Context

An available yt-dlp executable does not mean it can copy an active browser's
cookie database. OpenCLI already exposes `youtube transcript` and
`xiaohongshu note` through the connected browser bridge, but the workflow had
not promoted those outputs into Acquisition Bundle v2.

## Consequences

- Browser host identity remains explicit; no Edge/Chrome fallback is allowed.
- OpenCLI output becomes a primary artifact only after canonicalization,
  hashing, and source-gate validation.
- Persistent foreground sessions are the default for these interactive reads;
  callers can release tabs with `--no-opencli-keep-tab`.
- If the browser bridge and yt-dlp both fail, the workflow remains blocked and
  does not synthesize content from metadata or page shells.

## Validation

- Offline acquisition tests cover Xiaohongshu session arguments and an
  OpenCLI YouTube transcript that bypasses yt-dlp.
- Live validation uses a user-declared Edge host and records Bundle/source-gate
  outcomes without storing credentials.
