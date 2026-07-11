---
name: browser-host-identity
description: Distinguish the actual Microsoft Edge and Google Chrome host for browser sessions, cookies, extensions, OpenCLI, browser exports, and browser-control tasks. Use whenever a request mentions Chrome, Edge, a browser extension, cookies, login state, OpenCLI, or a browser-visible export; prevent fallback to the other browser and record the selected host.
---

# Browser Host Identity

Treat Edge and Chrome as separate hosts with separate profiles, cookies,
extensions, and login state. A Chromium-compatible extension, a tool named
"Chrome", a generic OpenCLI profile ID, or the system default browser is not
host evidence.

1. Read `references/host-identity-protocol.md` before any browser/session
   operation.
2. Honor an explicit user choice exactly: Chrome means Chrome only; Edge means
   Edge only. Never open or fall back to the other host.
3. When the host is not explicit, inspect the actual visible browser or ask
   for the host before accessing login state, cookies, or an extension. Do not
   infer it from a control surface name.
4. Record `browser_host` as `edge` or `chrome` and record whether it was
   user-declared or directly verified. If it remains unknown, stop the
   browser-session route or mark the export as `not_provided`.
5. For Knowledge Workflow OpenCLI acquisition, pass `--browser-host edge` or
   `--browser-host chrome`. The adapter blocks an OpenCLI route with no host.
6. For yt-dlp browser cookies, pass the same host through
   `--youtube-browser edge|chrome`; conflicting host flags are an error.
7. Never read, display, copy, or persist cookie values, session IDs, tokens,
   passwords, or private headers.

Use an in-app browser only as its own surface; it is never evidence that an
Edge or Chrome login session is available. Read the reference for conflict,
verification, and handoff rules.
