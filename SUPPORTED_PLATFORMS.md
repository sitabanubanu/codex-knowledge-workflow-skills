# Supported Platforms

This project no longer treats platform support as a built-in crawler matrix.
Agent-Reach is the acquisition layer; this project is the source-gated evidence
layer.

## First Integration

| Input | Acquisition route | Evidence rule |
| --- | --- | --- |
| Local transcript | Local bundle | Can become `source_confirmed` when non-empty. |
| Local subtitle | Local bundle | Can become `source_confirmed` when non-empty. |
| Local audio/video | Local bundle | Pending/degraded until ASR creates transcript. |
| Web page | Agent-Reach/Jina Reader route | Usually secondary unless the page itself is the primary source. |
| YouTube | Agent-Reach-selected yt-dlp route | Full analysis only when subtitles/transcript/ASR transcript are acquired. |
| Bilibili | Agent-Reach-selected bili-cli route | Metadata alone stays `secondary_only` or degraded. |
| GitHub | Agent-Reach-selected gh route | README/source text can be primary for repository analysis. |
| Xiaohongshu | Agent-Reach/OpenCLI backend when configured; otherwise Jina fallback only | Fallback page text stays `secondary_only`; login/CAPTCHA/blocked responses stay blocked or failed. |
| Twitter/X | Agent-Reach/OpenCLI backend when configured; otherwise Jina fallback only | Fallback page text stays `secondary_only`; 403/abuse/login responses stay blocked or failed. |

## Explicitly Not First-Version Targets

- OpenCLI deep integration
- Reddit
- Xiaohongshu full-content route without authorized backend/session
- Twitter/X logged-in state
- Facebook
- Instagram
- LinkedIn private content
- CAPTCHA, paywall, private, region-locked, or unauthorized content

Unsupported or blocked inputs should still produce an acquisition bundle and a
degraded result index.

## Platform Status Versus Source Status

Agent-Reach `active_backend` only says which acquisition route is available. It
does not prove material is trustworthy.

The evidence layer decides:

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`
