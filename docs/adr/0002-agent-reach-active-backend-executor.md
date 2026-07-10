# ADR 0002: Agent-Reach Active Backend Executor

## Status

Accepted.

## Context

The first Agent-Reach integration wrote acquisition bundles and preserved the
source gate, but it still treated several platform routes as local wrappers:

- run `agent-reach doctor --json`;
- call our own `yt-dlp`, `bili`, `gh`, `curl/Jina`, or search command;
- for Twitter/X and Xiaohongshu, fall back to generic web reading when no
  dedicated backend was active.

That missed Agent-Reach's central design. Agent-Reach is a capability layer:
it selects, installs, diagnoses, and routes to the current best upstream
backend for each platform. For login/session platforms, the backend is often a
browser-session tool such as OpenCLI or a dedicated CLI with user-provided
authorization. Anonymous HTTP readers are not the main route.

The live URL tests exposed this mismatch:

- Xiaohongshu direct URL redirected to login and only produced a page shell.
- Twitter/X generic reading was blocked, while browser/session access exposed
  usable media subtitle assets.
- YouTube was available through `yt-dlp` generally, but a specific video still
  required sign-in/bot-check handling and could not be upgraded without
  authorized subtitles, audio, or transcript material.

## Decision

The Agent-Reach acquisition layer must execute by active backend:

1. Run `agent-reach doctor --json`.
2. Map local platform ids to Agent-Reach channel ids, for example `x` to
   `twitter`.
3. Write `00_acquisition/logs/route_plan.json`.
4. Use the channel's reported `active_backend` and documented command family.
5. For login/session platforms, do not use anonymous Jina/curl as the main
   fallback. If no active backend exists, write a `blocked` bundle with setup
   commands and login/session requirements.
6. Keep source scope explicit. Tweet or note text can be primary for a
   post/note analysis, but it is not a video transcript unless the acquired
   artifact contains subtitles, transcript text, or audio-derived transcription.

## Consequences

- `kw agent-reach install` now exposes `--channels`, so the project can request
  Agent-Reach optional channels such as `opencli` and `twitter`.
- `kw agent-reach plan --input <url>` shows the current route plan before a
  full acquisition run.
- Xiaohongshu and Twitter/X now block early when no authorized backend is
  active, instead of repeatedly hitting generic web readers.
- When `twitter-cli`, OpenCLI, `xiaohongshu-mcp`, or `xhs-cli` is active, the
  adapter can write primary post/note text artifacts into the acquisition
  bundle.
- The evidence layer remains responsible for deciding whether the acquired
  material is enough for full analysis.

## Non-Goals

- Bypassing CAPTCHA, private content, paywalls, account permissions, region
  controls, or platform access limits.
- Treating platform metadata, search snippets, login pages, or visible page
  shells as primary evidence.
- Claiming that OpenCLI or browser-session routes make scraping invisible or
  unlimited. They reduce friction by using authorized user context, but platform
  rate limits and verification prompts still apply.
