# Platform and Operation Routing

Route on four facts: platform, analysis target, requested operation, and the
Knowledge Workflow provider capability report.

| Platform | Implemented operation/backend | Honest result boundary |
| --- | --- | --- |
| Web | `read` / ready Jina Reader | Article body is primary only for `web_article`. |
| YouTube | `extract_transcript` / declared Edge or Chrome + connected OpenCLI transcript, then yt-dlp subtitle, then yt-dlp media for evidence-layer ASR | Browser-visible or downloaded transcript is primary; metadata never unlocks video analysis. |
| Bilibili | `extract_transcript` / ready OpenCLI; `read` or extraction / ready bili-cli | Bilibili search API cannot extract content. |
| GitHub | `read` / ready gh CLI | Repository README can be task-primary. |
| Xiaohongshu | `read` / ready OpenCLI, xiaohongshu-mcp, or xhs-cli | Note text is `social_post_text`, not embedded-video transcript. |
| X post text | `read` / ready twitter-cli or OpenCLI `twitter article` for a single status | OpenCLI search alone is not a single-status reader. |
| X embedded video | `extract_transcript` / yt-dlp subtitle, then yt-dlp media for evidence-layer ASR | Post text and metadata do not satisfy a video-content target. |
| Search | `search` / ready Exa via mcporter | Search results remain secondary. |

Rules:

1. `active_backend` without provider `status: ok` is not ready.
2. A ready backend without an implemented operation is a capability mismatch.
3. Capability mismatch writes a blocked bundle and does not call a nearby
   command family.
4. Login/session platforms never fall through to anonymous Jina/curl.
5. OpenCLI requires a connected or installed extension, an open authorized
   Edge or Chrome host, provider `status: ok`, and an explicit
   `--browser-host edge|chrome`.
   A generic extension or control-plugin name is not host evidence.
6. For yt-dlp browser access, pass the actual host through
   `--youtube-browser edge|chrome`. It must match `--browser-host` when both
   flags are used.
7. Browser-visible material must be exported into an artifact before ingest.
8. Never bypass CAPTCHA, paywalls, private content, regions, or permissions.
9. Structured OpenCLI acquisition uses a persistent foreground site session by
   default. `--no-opencli-keep-tab` releases the tab after acquisition when a
   persistent visible tab is not useful.

For channels without a structured adapter, save authorized task-primary
material locally and hand it off with `kw source import`. Never substitute a
generic web shell, screenshot, or search snippet for the requested scope.
