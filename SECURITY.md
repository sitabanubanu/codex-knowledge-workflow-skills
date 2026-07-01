# Security Policy

This project processes local files, browser-observed page state, transcripts,
media files, and optional user-exported cookies. Treat workflow inputs and
outputs as sensitive unless you have explicitly decided they are public.

## What Not To Commit

Never commit:

- `cookies.txt` or any browser cookie export,
- browser profile directories,
- access tokens, API keys, account identifiers, or session material,
- private videos, private transcripts, paywalled course files, or proprietary
  recordings,
- raw local outputs from real user workflows unless intentionally sanitized.

The repository ignores generated `outputs/`, `test_outputs/`, `dist/`, caches,
logs, and Python bytecode. If you add a new output location, update
`.gitignore` before running real workflows.

## Cookies And Browser Identity

Cookies are only for user-authorized access to pages the user can already view.
They are not a bypass mechanism. Do not paste cookie contents into chat,
issues, logs, Markdown reports, or commit history.

Use a user-exported Netscape `cookies.txt` only when the user understands the
risk and has permission to access the source. Store it outside the repository
or in an ignored local path.

## Platform Boundaries

This project does not attempt to bypass:

- CAPTCHA,
- paywalls,
- private videos,
- region restrictions,
- account permission barriers,
- access-control systems,
- platform anti-abuse controls.

When first-hand material cannot be acquired safely, the workflow should write a
blocked or degraded result instead of fabricating a complete analysis.

## Reporting Security Issues

Do not open a public issue that includes credentials, cookies, private URLs, or
private source material. Open a minimal report that describes the affected file
or workflow and omit secrets. If private disclosure is needed, contact the
repository owner through a private channel before sharing details.
