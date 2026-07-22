---
name: acquire-source-material
description: Acquire authorized URL, query, platform, browser-exported, and local source material through Knowledge Workflow's native provider routing and write a validated Acquisition Bundle v2. Use for provider doctor/matrix/route planning, staged acquisition attempts, retries, and provider-neutral source imports; never judge evidence sufficiency or write reports.
---

# Acquire Source Material

Use this skill only for acquisition.

Resolve the installed entry point with `kw version`. If `kw` is unavailable,
install the repository package; do not assume the current directory contains
`kw.py`.

Core rule: providers obtain material; `source-gated-evidence-layer` decides
whether the material is task-primary, target-compatible, and sufficient.

1. Resolve `analysis_target` and required `operation` before selecting a
   provider.
2. Run `kw source doctor` and require a ready provider that supports
   the requested operation.
3. For OpenCLI, browser cookies, or a browser export, require an explicit
   declaration of the actual Edge or Chrome host. Never infer it from a tool or
   extension name and never fall back to the other browser family.
4. Write `route_plan.json` before executing a provider command.
5. Acquire inside `.kw_staging/<attempt_id>/`; never assemble the current
   bundle in place.
6. Canonicalize provider output into task-readable artifacts and retain only
   redacted metadata when raw output is useful.
7. Write Bundle v2 with run/attempt/bundle ids, target, operation, scope,
   coverage, byte counts, hashes, privacy flags, limits, and failures.
8. Validate before promotion and archive the prior bundle on a matching resume.
9. Hand only the promoted manifest path to `source-gated-evidence-layer`.

Never mark `source_confirmed`, run evidence audit, or write a learning article
or final report. Never bypass CAPTCHA, paywalls, private access, region
restrictions, or account permissions. Never persist cookie values,
authorization headers, session ids, tokens, passwords, or proxy credentials.

```powershell
kw source doctor
kw source matrix
kw source plan --input <url> --target <target> --operation <operation>
kw acquire --input <url-or-query> --target <target> --operation <operation> --project-root <project>
kw source import --input-file <authorized-export> --source-url <url> --platform <platform> --target <target> --operation <operation> --project-root <project>
kw validate-bundle --bundle <project>\00_acquisition\manifest.json
```

Media providers may return authorized audio or video as primary `media`.
Do not transcribe it here; the evidence layer runs ASR after admission and
binds the derived transcript into the gate receipt.

Read `references/provider-routing.md`, `references/provider-contract.md`,
`references/acquisition-bundle.md`, `references/usage.md`, and
`references/external-handoff.md` when the corresponding route is used.
