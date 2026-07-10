# Platform and Operation Routing

Route on four facts: platform, analysis target, requested operation, and
Agent-Reach doctor result.

| Platform | Implemented operation/backend | Honest result boundary |
| --- | --- | --- |
| Web | `read` / ready Jina Reader | Article body is primary only for `web_article`. |
| YouTube | `extract_transcript` / ready yt-dlp, then Agent-Reach transcription fallback | Metadata never unlocks video analysis. |
| Bilibili | `extract_transcript` / ready OpenCLI; `read` or extraction / ready bili-cli | Bilibili search API cannot extract content. |
| GitHub | `read` / ready gh CLI | Repository README can be task-primary. |
| Xiaohongshu | `read` / ready OpenCLI, xiaohongshu-mcp, or xhs-cli | Note text is `social_post_text`, not embedded-video transcript. |
| X | `read` / ready twitter-cli for a single status | OpenCLI search capability is not a single-status reader. |
| Search | `search` / ready Exa via mcporter | Search results remain secondary. |

Rules:

1. `active_backend` without doctor `status: ok` is not ready.
2. A ready backend without an implemented operation is a capability mismatch.
3. Capability mismatch writes a blocked bundle and does not call a nearby
   command family.
4. Login/session platforms never fall through to anonymous Jina/curl.
5. OpenCLI requires its Chrome extension, an open browser, authorized login,
   and doctor `status: ok`.
6. For yt-dlp browser access, distinguish the extension/control surface from
   the real host browser. Pass `--youtube-browser edge` for Edge or
   `--youtube-browser chrome` for Chrome; never guess from the plugin name.
7. Browser-visible material must be exported into an artifact before ingest.
8. Never bypass CAPTCHA, paywalls, private content, regions, or permissions.
