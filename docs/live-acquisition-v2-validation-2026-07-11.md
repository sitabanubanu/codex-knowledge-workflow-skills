# Live Acquisition Bundle v2 Validation - 2026-07-11

This validation used one Xiaohongshu post, one X post, and one YouTube video.
The detailed runtime reports remain under
`test_outputs/live-v2-20260710/content-report.md` and `process-report.md`.

## Outcome

- Xiaohongshu and X were blocked by the Agent-Reach/OpenCLI readiness gate.
- Authorized browser-visible post text from an Edge-hosted session was exported locally and imported through
  the new Browser Export Bundle v2 path.
- Both social-post runs completed ingest, evidence audit, composition, quality
  gate, and final provenance receipt.
- YouTube remained blocked after bot-check, an initial incorrect attempt to
  use Chrome instead of the active Edge profile, an Edge profile-lock failure,
  an indefinitely loading transcript panel, and no exportable subtitle/media
  asset. This run does not establish that the prior cookies were stale.
- No YouTube content report was manufactured from metadata, comments, or
  isolated visible caption lines.

## Product Fixes From The Run

- Added `kw browser-import` and end-to-end browser-export options on `kw run`.
- Added target-aware direct-source claim handling for non-video documents.
- Prevented raw browser-exported media from masquerading as a transcript.
- Made browser-export run identity stable across sensitive URL-token rotation.
- Forced UTF-8 child-process output for acquisition and ingest commands.
- Added explicit `--youtube-browser edge|chrome` routing so the browser-control
  surface cannot be mistaken for the browser that owns the login state.

## Remaining Boundary

The repository now has a formal browser-to-bundle handoff, but it does not
automatically save arbitrary browser-visible transcript panels. YouTube still
requires an actual subtitle, transcript, or local media artifact before the
evidence layer can proceed.

## Validation

`python kw.py validate --include-sync` passed all 12 checks, including the
browser-export flow and installed-skill equality verification.
