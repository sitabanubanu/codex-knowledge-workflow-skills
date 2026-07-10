# Troubleshooting

## Agent-Reach Is Missing

```powershell
python -m pip install https://github.com/Panniantong/Agent-Reach/archive/main.zip
agent-reach install --env=auto --safe
agent-reach doctor --json
```

Or:

```powershell
python .\kw.py agent-reach install --safe
python .\kw.py agent-reach doctor
```

Missing Agent-Reach produces a failed bundle and `source_failed`; it never
falls through to a fake successful report.

## Active Backend Exists but Acquisition Is Blocked

An active backend name is not enough. Check:

```powershell
python .\kw.py agent-reach plan --input <url> --target <target> --operation <operation>
```

The route needs both `active_backend_ready: true` and
`operation_supported: true`. Typical mismatches:

- Bilibili search API cannot extract a transcript;
- X OpenCLI search support is not a stable single-status reader;
- a web reader cannot satisfy a login-required platform route.

Use a supported backend or provide task-primary local material.

## OpenCLI Reports `warn`

Agent-Reach commonly reports `warn` when OpenCLI is installed but its Chrome
extension is absent or disconnected.

1. Install the OpenCLI Chrome extension from the URL shown by doctor.
2. Keep Chrome open.
3. Sign in to the platform with your own authorized account.
4. Run `opencli doctor` and `agent-reach doctor --json` again.

The control plugin may be named Chrome while the extension and login state are
actually running in Microsoft Edge. Check the real browser process before
using yt-dlp. Use `--youtube-browser edge` for Edge and
`--youtube-browser chrome` for Chrome. If yt-dlp reports that it cannot copy
the cookie database, the selected browser is still running and holding the
profile lock; do not call the cookies stale and do not close the browser
without user approval.

The workflow remains blocked until doctor reports `status: ok`. It does not
bypass CAPTCHA, account permissions, private content, or paywalls.

## Acquisition Succeeded but No Full Report Exists

Inspect:

```text
00_acquisition/manifest.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
result_index.md
```

Safe stopping states include:

- `metadata_only` -> `secondary_only`;
- `blocked` -> `source_blocked`;
- `failed` -> `source_failed`;
- target/scope mismatch -> `degraded_report_only`.

For example, an X or Xiaohongshu caption may be valid `social_post_text` but
still cannot satisfy `video_content`.

## Old Report Exists but Status Is Not Success

This is expected when provenance is stale. `status_summary.json` and
`result_index.md` report:

```text
stale_output_files_present: true
final_report_provenance_current: false
```

Run ingest, audit, and compose for the current bundle. Do not rename an old
report back into place. Previous results are preserved under `run_history/`.

## Project Root Already Belongs to a Run

Use a new project root, or retry only the exact same source, target, and
operation:

```powershell
python .\kw.py run ... --project-root <same-project> --resume
```

Resume fails after a local file changes, or when target/operation differs. This
prevents output mixing.

## YouTube Bot Check, Sign-In, or Missing Subtitles

Allowed options include an authorized Netscape cookies file, Node.js runtime,
remote EJS components, client/extractor parameters, proxy, impersonation, and
Agent-Reach transcription fallback. See `kw run --help`.

Never paste cookie or token contents into logs or reports. The CLI passes
sensitive values to the upstream process but redacts persisted commands,
manifests, preflight, run state, and errors.

If access still fails, provide subtitles, transcript, or authorized local
media. Record blocked status rather than looping around platform controls.

## Bilibili Is Search-Only

The default public search API can find videos but cannot obtain their content.
For transcript extraction, Agent-Reach doctor must select a ready OpenCLI or
bili-cli route implemented by this adapter. Otherwise provide subtitles or
local media.

## Empty Transcript or Local Media Without ASR

An empty transcript becomes failed/degraded and cannot create an analysis pack.
Local media remains degraded until ASR produces a non-empty hashed transcript.

## Bundle Validation Fails

```powershell
python .\kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
```

Common causes are an escaping/absolute artifact path, missing file, byte/hash
mismatch, missing v2 identity fields, status invariant violation, or
unredacted secret-like manifest data. Do not hand-edit hashes; rerun acquisition.

## Do Not Commit

```powershell
git status --short
```

Keep `work/`, cookies, tokens, outputs, test outputs, caches, and private logs
out of Git.
