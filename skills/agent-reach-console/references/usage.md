# Usage

## Plan First

```powershell
python kw.py agent-reach doctor
python kw.py agent-reach plan --input <url> --target <target> --operation <operation>
```

Execute only when `capability_ready` is true.

## Acquire

```powershell
python kw.py acquire --input <url> --target <target> --operation <operation> --project-root <project>
```

For YouTube browser-backed acquisition, select the browser that actually owns
the login state:

```powershell
python kw.py acquire --input <youtube-url> --target video_content --operation extract_transcript --youtube-browser edge --project-root <project>
```

Use `chrome` only when Chrome is the real host browser. A control plugin named
Chrome may still be installed and running inside Edge.

For queries:

```powershell
python kw.py acquire --query --input "<query>" --target search_triage --operation search --project-root <project>
```

For the same source, target, and operation:

```powershell
python kw.py acquire ... --project-root <same-project> --resume
```

Without `--resume`, project-root reuse fails. Resume writes a new staged
attempt, validates it, archives the old bundle, and promotes the new bundle.

## Local Material

Local transcript, subtitle, audio, or video bypasses Agent-Reach execution but
uses the same Bundle v2 and run identity:

```powershell
python kw.py run --input .\input.vtt --target video_content --operation extract_transcript --mode audit
```

Local media remains degraded until ASR creates a usable transcript.

## Handoff

The only handoff is:

```text
<project>\00_acquisition\manifest.json
```

Pass it to `source-gated-evidence-layer`. Never send raw backend output to the
composer.
