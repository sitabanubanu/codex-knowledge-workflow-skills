# Acquisition Bundle Protocol

`acquisition_bundle` is the stable handoff between the Agent-Reach acquisition
layer and the Knowledge Workflow evidence layer.

Agent-Reach gets the material. Knowledge Workflow decides whether the material
is trustworthy. No primary material, no fake report.

## Directory

```text
00_acquisition/
  manifest.json
  artifacts/
    transcript.vtt
    transcript.md
    page.md
    metadata.json
    audio.wav
  logs/
    agent_reach_doctor.json
    route_plan.json
    commands.jsonl
    acquisition_notes.md
```

The exact artifact filenames can vary, but `manifest.json` must list every
artifact that the evidence layer may inspect.

## `manifest.json`

Required fields:

- `schema_version`: Protocol version. Current value: `1`.
- `created_at`: UTC ISO timestamp.
- `input`: Original user input or normalized local path.
- `source_url`: Source URL when applicable; empty for local-only bundles.
- `source_id`: Stable source id when available, such as a video id, repo id, or
  local file stem.
- `platform`: `web`, `youtube`, `bilibili`, `github`, `x`,
  `xiaohongshu`, `local_file`, `search`, `rss`, or `unknown`.
- `acquisition_layer`: `agent-reach`, `local_file`, or another explicit
  acquisition controller name.
- `active_backend`: Active Agent-Reach backend or local builder name.
- `status`: One of the protocol status values below.
- `artifacts`: List of artifact objects.
- `metadata`: Non-secret metadata about the acquisition and source.
  For Agent-Reach-backed bundles, include or write a companion route plan that
  records the detected channel, doctor status, active backend, preferred
  command family, and authorized setup steps.
- `privacy`: Privacy and secret-handling flags.
- `limits`: Known limits of the acquired material.
- `failures`: Errors, blockers, or failed routes.
- `next_action`: User-safe next step.

Recommended artifact fields:

- `path`: Path relative to `00_acquisition`.
- `type`: One of the artifact types below.
- `source_class`: One of the source classes below.
- `mime_type`: Optional media type.
- `language`: Optional language label.
- `description`: Short non-secret description.
- `bytes`: Optional file size in bytes.
- `sha256`: Optional content hash.
- `created_by`: Tool or route that created it.

## Status Values

- `material_acquired`: Primary material is present.
- `partial_material_acquired`: Partial primary material is present.
- `metadata_only`: Only metadata was acquired.
- `secondary_only`: Only secondary/background material was acquired.
- `blocked`: Acquisition was blocked by permissions, CAPTCHA, bot checks,
  login, private content, paywall, region controls, or similar barriers.
- `failed`: Acquisition failed because of tool, network, runtime, or parsing
  error.
- `unsupported`: No supported acquisition route exists in this version.

## Artifact Types

- `transcript`
- `subtitle`
- `page_markdown`
- `page_text`
- `audio`
- `video`
- `metadata`
- `search_result`
- `comments`
- `unknown`

## Source Classes

- `primary`
- `partial_primary`
- `secondary`
- `metadata_only`
- `unknown`

## Source Class Rules

- A transcript, subtitle, ASR transcript, or authorized local audio-derived
  transcript can be `primary`.
- A transcript or subtitle covering only a known portion of the source can be
  `partial_primary`.
- Original webpage body can be `primary` or `secondary` depending on the task.
  A first-party article page may be primary for an article analysis; a video
  landing page is usually secondary for video-content analysis unless it
  contains the transcript.
- Social post/note text acquired through a documented, authorized
  Agent-Reach backend such as `twitter-cli`, OpenCLI, `xiaohongshu-mcp`, or
  `xhs-cli` can be primary for the post/note text. It is not a primary video
  transcript unless the artifact itself contains subtitles, transcript text, or
  audio-derived transcription.
- Search results, titles, descriptions, metadata, and comments do not support a
  full video analysis by default.
- `metadata_only` cannot enter a full report.
- `unknown` must become degraded output or `needs_review`; it must not be
  upgraded to Source claims.

## Privacy

Required privacy fields:

- `cookies_used`: Boolean.
- `browser_session_used`: Boolean.
- `secrets_redacted`: Boolean.
- `contains_user_private_data`: Boolean.

Security requirements:

- `commands.jsonl` must not record cookie values, tokens, Authorization headers,
  session ids, or private account secrets.
- `manifest.json` may record whether cookies were used, but never cookie
  contents.
- Logs must not contain private material full text unless the user explicitly
  provided that material and it is intentionally stored under `artifacts/`.
- Route plans may name commands and setup actions, but must use placeholders
  for cookie, token, session, and authorization values.
- Failed or blocked bundles still need a manifest so the evidence layer can
  produce an auditable degraded result.

## Agent-Reach Route Policy

The acquisition layer must follow Agent-Reach's channel model:

1. Run `agent-reach doctor --json`.
2. Map the source platform to the doctor channel, such as `x` -> `twitter` and
   search -> `exa_search`.
3. Use the reported `active_backend` and the command family documented by
   Agent-Reach for that backend.
4. For login/session platforms such as Twitter/X and Xiaohongshu, do not make
   anonymous Jina/curl the main fallback. If no active backend exists, write a
   `blocked` bundle with the install/login route instead.
5. For video-bearing sources, distinguish post/page text from video content:
   post text can be primary for post analysis; video analysis still requires a
   subtitle, transcript, or audio-derived transcript.

## Source Gate Mapping

The evidence layer maps bundle status to `source_status.json`:

| Bundle state | Source status |
| --- | --- |
| `material_acquired` + primary artifact | `source_confirmed` |
| `partial_material_acquired` + partial primary artifact | `source_partial` |
| `metadata_only` | `secondary_only` or `degraded_report_only` |
| `secondary_only` | `secondary_only` |
| `blocked` | `source_blocked` |
| `failed` | `source_failed` |
| `unsupported` | `degraded_report_only` |

`source_confirmed` and `source_partial` are the only states that can enter
normal or partial decomposition.
