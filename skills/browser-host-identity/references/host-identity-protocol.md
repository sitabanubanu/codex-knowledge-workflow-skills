# Browser Host Identity Protocol

## Purpose

Keep Microsoft Edge and Google Chrome separate whenever an agent interacts
with a browser session, extension, cookies, visible page state, or exported
material. The target is the actual browser process holding the user-authorized
profile, not a generic tool label.

## Required Decision

Before accessing browser-backed material, establish one of these facts:

| Situation | Required action |
| --- | --- |
| User explicitly says Edge | Use Edge only. |
| User explicitly says Chrome | Use Chrome only. |
| Visible browser/process can be verified | Record that exact host and how it was verified. |
| Host is unknown | Ask before accessing login state or mark the route blocked. |
| An in-app browser is available | Treat it as a separate surface, not as Edge or Chrome. |

The host must never be inferred from a `Chrome` control-tool name, a
Chromium-compatible extension manifest, a generic OpenCLI profile ID, the
default browser, or a previous task.

## OpenCLI and Export Rules

1. `opencli doctor` can show that an extension is connected, but it does not
   identify its host browser. The agent must still record the user-declared or
   directly verified `edge` or `chrome` host.
2. A Knowledge Workflow OpenCLI route uses `--browser-host edge` or
   `--browser-host chrome`. Missing identity produces a blocked acquisition
   bundle; there is no implicit fallback.
3. A yt-dlp route that reads a browser profile uses
   `--youtube-browser edge|chrome`. It must match `--browser-host` when both
   are present.
4. A browser-visible export should include its host with
   `kw browser-import --browser-host edge|chrome`. When older callers omit it,
   the Bundle records `browser_host: unknown` and `not_provided`; it must not
   invent a host.
5. Do not switch hosts after a failure. Report the exact host, operation,
   failure, and next action instead.

## Conflict Handling

When the user asks for Chrome but the only connected extension is known to be
in Edge, do not open Edge. Report that Chrome is not connected and request a
Chrome-hosted connection or a different explicit instruction. Apply the same
rule in reverse for Edge.

When a profile database is locked, record the selected host and the lock
condition. Do not relabel it as an expired cookie and do not close the user's
browser without authorization.
