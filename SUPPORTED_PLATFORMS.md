# Supported Platforms and Operations

Platform support is an operation-specific capability, not a promise that every
URL can be fetched.

The adapter executes a route only when Agent-Reach doctor reports the active
backend as `status: ok` and this repository implements the requested operation.

| Input | Implemented operation | Current adapter route | Evidence boundary |
| --- | --- | --- | --- |
| Local transcript/subtitle | `extract_transcript` | local Bundle v2 copy | Non-empty transcript scope can confirm `video_content`. |
| Local audio/video | `extract_transcript` | local bundle, then ASR | Media alone is degraded; a hashed ASR transcript can confirm the source. |
| Ordinary web page | `read` | Jina Reader selected by Agent-Reach | `article_body` is primary only for target `web_article`. |
| YouTube | `extract_transcript`, `read` | yt-dlp metadata/subtitles; Agent-Reach transcription fallback | Only subtitle/transcript scope unlocks `video_content`; metadata never does. |
| Bilibili | `extract_transcript` with ready OpenCLI; `read`/`extract_transcript` with ready bili-cli | OpenCLI subtitle JSON, or bili-cli detail/audio plus Agent-Reach transcription | The public Bilibili search API is search-only and is blocked for transcript extraction. |
| GitHub repository | `read` | gh metadata and temporary clone for README | Repository document scope can confirm target `repository`. |
| Xiaohongshu note | `read` | ready OpenCLI, xiaohongshu-mcp, or xhs-cli | Note text confirms `social_post`; it does not confirm an embedded video. No anonymous Jina fallback is used. |
| X/Twitter status | `read` with ready twitter-cli | twitter-cli single-status route | Tweet text confirms `social_post`; it does not confirm embedded media. OpenCLI search support is not treated as a single-status reader. |
| Query | `search` | Exa through mcporter | Search results remain `secondary_only` and are for triage. |

## Browser-Assisted Acquisition

OpenCLI can use an existing authorized Chromium-browser session when its extension is
installed, connected, and doctor reports `status: ok`. If doctor reports
`warn`, the run is blocked rather than pretending the browser route worked.

A Codex browser-control session may be used manually to inspect or export
authorized visible material. The exported text, subtitle, or media must still
enter through a bundle artifact. Browser metadata, screenshots, and page shell
state do not become Source automatically.

## Deliberately Unsupported

- CAPTCHA bypass;
- paywall bypass;
- private or unauthorized content;
- region or account-permission bypass;
- using a search backend as a content extractor;
- treating metadata, comments, snippets, screenshots, or post captions as a
  video transcript;
- automatic single-status X reading through OpenCLI until Agent-Reach exposes
  and documents a stable command used by this adapter.

Unsupported, unhealthy, or capability-mismatched routes still produce a valid
blocked or degraded acquisition bundle with an explicit next action.
