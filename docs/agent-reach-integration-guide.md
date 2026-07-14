# Agent-Reach Integration Guide

## Purpose

Agent-Reach is the complete upstream acquisition capability layer for this
project. It owns platform selection, dependency installation, health checks,
and native commands. Knowledge Workflow owns the separate decision of whether
acquired material is task-primary, evidence-backed, and report-ready.

Do not vendor or reimplement Agent-Reach's moving platform commands here. Use
the upstream skill and CLI directly, then hand task-primary artifacts into the
source-gated workflow.

## Current Baseline

The supported upstream baseline is Agent-Reach `v1.5.0`. Verify availability
and current routing rather than trusting a static document:

```powershell
agent-reach --version
agent-reach check-update
python .\kw.py agent-reach doctor
python .\kw.py agent-reach matrix
```

`matrix` always lists all 15 upstream channels, including channels currently
in `warn` state. `doctor_status: ok` means a native acquisition route is ready;
it never means source-gate approval.

## Two Integration Paths

### Structured Adapter

Use `kw acquire` or `kw run` when the requested operation is implemented by
the repository adapter. Current structured routes cover web pages, YouTube,
Bilibili, GitHub repositories, X single-status reads, Xiaohongshu notes, and
Exa search. For YouTube with an explicitly declared, connected Edge or Chrome
host, the adapter first asks OpenCLI for the browser-visible transcript before
trying yt-dlp; this avoids treating a locked browser cookie database as the
only path to a transcript.

### Native Export And Import

For every other Agent-Reach channel, use the current upstream command chosen
by `agent-reach doctor`, save only the task-primary text, subtitle, or media
to a local file, then import it:

```powershell
python .\kw.py agent-reach import `
  --input-file .\exports\primary-material.txt `
  --source-url <original-url> `
  --platform reddit `
  --target social_post `
  --operation read `
  --browser-host edge `
  --credentialed-session `
  --project-root .\outputs\reddit-item
```

Use `--browser-host` only when the native route used OpenCLI. Use
`--credentialed-session` when an authorized browser, cookies, or login session
served the exported material. Never export cookie values, tokens, headers,
page screenshots, page shells, or search-only results as primary material.

The import command accepts all upstream platform ids: `web`, `youtube`, `rss`,
`exa_search`, `github`, `twitter`, `x`, `bilibili`, `reddit`, `facebook`,
`instagram`, `xiaohongshu`, `linkedin`, `xiaoyuzhou`, `v2ex`, and `xueqiu`.

## Full Channel Map

| Agent-Reach channel | Native capability | Knowledge Workflow path |
| --- | --- | --- |
| `web` | Public article reading | Structured adapter or native import. |
| `youtube` | Metadata, subtitles, transcription | Structured adapter or native import. |
| `rss` | RSS/Atom reading | Native export then import as `web_article`. |
| `exa_search` | Web search | Structured triage; search results never unlock a report. |
| `github` | Repository, code, issues, PRs | Structured repository route or native export/import. |
| `twitter` / `x` | Posts, articles, user posts, discovery | Structured single-status route where available; otherwise native export/import. |
| `bilibili` | Detail, search, audio, OpenCLI subtitles | Structured route or native export/import. |
| `xiaohongshu` | Notes, comments, feed | Structured note route or native export/import. |
| `reddit` | Search, posts, comments, subreddit views | Native export/import as `social_post`. |
| `facebook` | Search, profiles, feed, group list | Native export/import as `social_post` or `web_article`. |
| `instagram` | Profiles, recent posts, explore | Native export/import as `social_post`. |
| `linkedin` | Profiles, companies, jobs | Native export/import as `web_article`. |
| `xiaoyuzhou` | Podcast transcription | Native transcript import as `video_content`. |
| `v2ex` | Topics, replies, users | Native export/import as `social_post` or `web_article`. |
| `xueqiu` | Market and community data | Native export/import after explicit authorized setup. |

Read Agent-Reach's installed skill for the exact native command and fallback
chain. Its route choice is intentionally dynamic. This project does not pin an
obsolete command when Agent-Reach has selected a newer backend.

## Installation And Credentials

Use the project wrapper so the upstream package is installed in the shared
runtime, not in the current agent's Python environment:

```powershell
python .\kw.py agent-reach install --safe
agent-reach --version
python .\kw.py agent-reach doctor
```

The managed layout is:

```text
C:\Users\Socrates\github-tools\
  sources\Agent-Reach
  runtimes\agent-reach\venv
  bin\agent-reach.cmd
  manifests\agent-reach.json
```

The adapter resolves the executable from this runtime and rejects paths inside
`.hermes` or another agent-private virtual environment. `C:\Users\Socrates\.agent-reach`
remains the separate Agent-Reach configuration directory.

Review optional channel setup before applying it. The upstream `v1.5.0`
installer may attempt Chrome/Firefox cookie discovery for `twitter`,
`bilibili`, `xueqiu`, or `all`. The `kw agent-reach install` wrapper requires
`--allow-upstream-cookie-import` before such an attempt. For an Edge session,
use an explicit, user-authorized upstream command instead:

```powershell
agent-reach configure --from-browser edge
```

OpenCLI is different: install its extension in the real host browser, keep
that host logged in, and pass `--browser-host edge` or `--browser-host chrome`
to every Knowledge Workflow OpenCLI route. A tool label, extension manifest,
or generic OpenCLI profile id is not host evidence.

The structured OpenCLI routes use `--opencli-window foreground` and
`--opencli-site-session persistent` by default because interactive platforms
are more reliable when their authorized tab remains alive. Use
`--no-opencli-keep-tab` when the tab should be released after acquisition.

## Audit Boundary

Native Agent-Reach access is not an automatic report license. The imported
artifact still needs a target-compatible scope:

| Target | Required primary artifact |
| --- | --- |
| `video_content` | Transcript or subtitle, not video metadata or caption. |
| `social_post` | Actual post body, not search snippets or engagement numbers. |
| `web_article` | Article or profile body, not a result card. |
| `repository` | Repository document, not repository metadata. |
| `search_triage` | Secondary only; it cannot unlock a normal report. |

Run `kw ingest`, `kw audit`, and `kw compose` after import. When the upstream
route is unavailable, blocked by a platform, or lacks primary material, keep
the outcome blocked or degraded. Never bypass CAPTCHA, paywalls, account
permissions, private content, or regional restrictions.
