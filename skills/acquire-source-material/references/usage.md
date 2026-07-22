# Usage

## Plan First

```powershell
kw source doctor
kw source matrix
kw source plan --input <url> --target <target> --operation <operation>
```

Execute only when `capability_ready` is true.

## Acquire

```powershell
kw acquire --input <url> --target <target> --operation <operation> --project-root <project>
```

For YouTube browser-backed acquisition, select the browser that actually owns
the login state:

```powershell
kw acquire --input <youtube-url> --target video_content --operation extract_transcript --youtube-browser edge --project-root <project>
```

Use `chrome` only when Chrome is the real host browser. A control plugin named
Chrome can be running inside Edge, so declare `--browser-host edge` for
OpenCLI and never infer the host from a tool label.

## Provider-Neutral Imports

When a structured adapter is unavailable, use an authorized browser, CLI, API,
or user export to save task-primary material locally, then hand it off:

```powershell
kw source import --input-file .\exports\primary.txt --source-url <original-url> --platform reddit --target social_post --operation read --browser-host edge --credentialed-session --project-root <project>
```

This route accepts every declared external-source platform id and still enforces
Bundle v2, target/scope source gating, and evidence audit.

For queries:

```powershell
kw acquire --query --input "<query>" --target search_triage --operation search --project-root <project>
```

For the same source, target, and operation:

```powershell
kw acquire ... --project-root <same-project> --resume
```

Without `--resume`, project-root reuse fails. Resume writes a new staged
attempt, validates it, archives the old bundle, and promotes the new bundle.

## Local Material

Local transcript, subtitle, audio, or video uses the same Bundle v2 and run
identity without invoking a URL provider:

```powershell
kw run --input .\input.vtt --target video_content --operation extract_transcript --mode audit
```

Local media remains degraded until ASR creates a usable transcript.

## Handoff

The only handoff is:

```text
<project>\00_acquisition\manifest.json
```

Pass it to `source-gated-evidence-layer`. Never send raw backend output to the
composer.
