---
name: agent-reach-console
description: Acquire authorized URL, query, platform, and local material through Agent-Reach capability routing and write Acquisition Bundle v2. Use for doctor, route planning, staged attempts, retries, and bundle validation; never perform source judgment or report writing.
---

# Agent-Reach Console

Use this skill only for acquisition.

Core rule: Agent-Reach gets material; the evidence layer decides whether it is
task-primary and sufficient.

1. Resolve `analysis_target` and required `operation` before choosing a route.
2. Run `agent-reach doctor --json` and write the result under the attempt logs.
3. Require both `status: ok` and implemented operation support. An active
   search backend is not automatically a transcript backend.
4. Write `route_plan.json` before executing a platform command.
5. Acquire inside `.kw_staging/<attempt_id>/`; never assemble the current
   bundle in place.
6. Canonicalize backend JSON into a task-readable artifact. Keep redacted raw
   output as metadata only when useful.
7. Write Bundle v2 with run/attempt/bundle ids, target, operation, content
   scopes, byte counts, hashes, privacy flags, limits, and failures.
8. Validate before promotion. On resume, archive the prior bundle.
9. Hand only the promoted manifest path to `source-gated-evidence-layer`.

Never mark `source_confirmed`, run claims/evidence audit, or write a final
report. Never bypass CAPTCHA, paywalls, private access, region restrictions, or
account permissions. Never persist cookies, authorization headers, session
ids, tokens, visitor data, PO tokens, passwords, or proxy credentials.

```powershell
python kw.py agent-reach doctor
python kw.py agent-reach plan --input <url> --target <target> --operation <operation>
python kw.py acquire --input <url-or-query> --target <target> --operation <operation> --project-root <project>
python kw.py acquire --input <same-input> --target <same-target> --operation <same-operation> --project-root <project> --resume
python kw.py browser-import --input-file <exported-file> --source-url <original-url> --platform <platform> --target <target> --operation <operation> --project-root <project>
python kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
```

Use `browser-import` only after a browser-capable agent has saved actual
visible text, subtitles, audio, or video to a local file. A playable page,
screenshot, metadata record, or restricted signed URL cannot pass this
handoff.

Read `references/platform-routing.md`, `references/acquisition-bundle.md`, and
`references/usage.md`. Read `references/install.md` for setup only.
