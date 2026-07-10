# Platform Routing

First-version supported routes:

| Platform | Acquisition route | Bundle status expectation |
| --- | --- | --- |
| Web page | Jina Reader route through `curl https://r.jina.ai/<URL>` | Usually `secondary_only`; can be primary only when the page itself is the source being analyzed. |
| YouTube | `yt-dlp` metadata and subtitle routes, selected/checked through Agent-Reach doctor | `material_acquired` when subtitles are saved; otherwise `metadata_only`, `blocked`, or `failed`. |
| Bilibili | `bili-cli` metadata/search/detail route, selected/checked through Agent-Reach doctor | Usually `metadata_only` unless subtitles/transcript are acquired by a supported backend. |
| GitHub | `gh` repo metadata/readme route | `material_acquired` when README/source text is acquired for repo analysis. |
| Local file | Local bundle builder, no Agent-Reach dependency | `material_acquired` for transcript/subtitle; pending/degraded for audio/video until ASR creates transcript. |
| Xiaohongshu | Agent-Reach active backend only: OpenCLI, xiaohongshu-mcp, or xhs-cli. If none is active, write a blocked bundle with setup steps. | `material_acquired` when note text is returned by an authorized backend; otherwise `blocked` or `failed`. Note text is not an embedded-video transcript. |
| Twitter/X | Agent-Reach active backend only: twitter-cli for single tweets, OpenCLI for documented search/article/user-posts routes, or legacy backend when explicitly active. If none is active, write a blocked bundle with setup steps. | `material_acquired` when tweet/post text is returned by an authorized backend; otherwise `blocked` or `failed`. Tweet text is not an embedded-video transcript. |

Explicitly not supported in this integration:

- anonymous Jina/curl as the primary route for login/session platforms such as
  Xiaohongshu, Twitter/X, Reddit, Facebook, or Instagram;
- Xiaohongshu full-content route without authorized backend/session;
- Reddit;
- Twitter/X single-status OpenCLI route unless Agent-Reach documents that
  command as available; use twitter-cli for single tweets;
- Facebook;
- Instagram;
- LinkedIn private content;
- private, paid, CAPTCHA-gated, region-limited, or permission-restricted content.

When unsupported or blocked, write a bundle anyway. The evidence layer will
produce degraded output and next actions.

Route policy:

1. Run `agent-reach doctor --json`.
2. Use the channel's `active_backend` to choose commands.
3. If a login/session platform has no active backend, stop and write
   `blocked`; do not repeatedly hit generic web readers.
4. Store `00_acquisition/logs/route_plan.json` for every URL/query run.
5. For social posts that contain video, keep the scope honest: post text can
   be primary for post analysis; video analysis still requires subtitle,
   transcript, or audio-derived transcript.
