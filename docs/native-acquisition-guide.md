# Native Acquisition Guide

## Purpose

Knowledge Workflow owns its acquisition boundary. The CLI directly probes optional Provider tools, plans an operation-specific route, writes a staged Bundle v2, validates it, and only then promotes it for evidence processing.

There is no intermediary acquisition runtime dependency.

## Commands

```powershell
kw source doctor
kw source matrix
kw source plan --input <URL或查询> --target <目标> --operation <操作>
kw acquire --input <URL或查询> --target <目标> --operation <操作> --project-root <项目目录>
```

`source doctor` reports Provider readiness. `source matrix` always lists all 15 catalogued channels and labels each as a native adapter, mixed native/export route, or external export. Neither command grants source or report permission.

## Structured adapters

The built-in adapters cover:

- public web articles through curl/Jina;
- YouTube subtitles or media through yt-dlp, with optional OpenCLI visible transcript;
- Bilibili detail/audio through bili-cli, with optional OpenCLI subtitles;
- GitHub repository metadata and README through gh;
- X/Twitter status text through twitter-cli or authorized OpenCLI;
- Xiaohongshu note text through authorized OpenCLI, MCP, or xhs-cli;
- Exa search through mcporter, always secondary-only.

Downloaded audio/video remains `media`. The evidence layer performs ASR after Bundle admission and binds the derived transcript hash to the gate receipt.

## Provider-neutral exports

For RSS, Reddit, Facebook, Instagram, LinkedIn, Xiaoyuzhou, V2EX, Xueqiu, or any route without a structured adapter, save authorized task-primary material locally and import it:

```powershell
kw source import `
  --input-file <本地材料> `
  --source-url <原始URL> `
  --platform <平台> `
  --target <目标> `
  --operation <操作> `
  --browser-host edge `
  --credentialed-session `
  --project-root <项目目录>
```

Use `--browser-host` only when a browser-backed route was actually used. `--credentialed-session` records a boolean; cookie and token values must never be persisted.

## Provider contract

Each capability item exposes:

- `status`;
- `active_backend`;
- `backends`;
- `provider_id`;
- redacted `message`;
- `browser_hosts` when relevant.

The route plan combines Provider readiness with `operation_supported` and browser-host requirements. Login-required platforms never fall through to an anonymous generic reader.

## Audit boundary

| Target | Required primary material |
| --- | --- |
| `video_content` | transcript/subtitle, or admitted media followed by successful ASR |
| `social_post` | actual post body |
| `web_article` | article body |
| `repository` | repository document |
| `search_triage` | secondary results only; cannot unlock a full report |

Provider access is never automatic report permission. Every artifact must still pass Bundle validation, target/scope gating, evidence audit and current-receipt checks.

## Safety

Do not bypass CAPTCHA, paywalls, private access, region restrictions or account permissions. Do not persist cookies, authorization headers, session ids, passwords, visitor data, proof tokens or proxy credentials. Failed routes produce a blocked or failed bundle with an explicit next action.
