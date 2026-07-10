---
name: agent-reach-console
description: Acquisition controller for Agent-Reach-backed URL, query, platform, and local-file intake. Generates acquisition bundles only; does not perform source gate, evidence audit, claim production, or final report writing.
---

# Agent-Reach Console

Use this skill as the acquisition controller.

Core rule: Agent-Reach gets material; Knowledge Workflow judges whether it can
be trusted.

Workflow:

1. Check whether `agent-reach` is installed before platform acquisition.
2. For multi-platform tasks, or whenever platform readiness is unclear, run
   `agent-reach doctor --json` and save the result under
   `00_acquisition/logs/agent_reach_doctor.json`.
3. Identify the platform and active backend from the doctor output when
   available.
4. Write `00_acquisition/logs/route_plan.json` before acquisition. The plan
   must explain the doctor channel, active backend, preferred command family,
   anonymous fallback policy, and authorized setup action when a backend is
   missing.
5. Call the current supported upstream route for the platform. For login or
   browser-session platforms, follow Agent-Reach's active backend instead of
   retrying anonymous page readers.
6. Write every result into `00_acquisition/manifest.json` following
   `references/acquisition-bundle.md`.
7. Write `00_acquisition/logs/commands.jsonl` with command summaries and exit
   codes only. Redact secrets.
8. If acquisition fails, still write a `blocked`, `failed`, or `unsupported`
   bundle.
9. Hand the manifest path to `source-gated-evidence-layer`.

Do not:

- perform source gate decisions;
- mark material `source_confirmed`;
- run evidence audit;
- generate `video_analysis_pack.md`, `source_analysis_pack.md`, or
  `final_report.md`;
- read, display, copy, or log cookie values, tokens, Authorization headers, or
  private browser session material;
- bypass CAPTCHA, paywalls, private content, region limits, account permissions,
  or platform access controls.

CLI wrappers:

```powershell
python kw.py agent-reach doctor
python kw.py agent-reach plan --input <url-or-query>
python kw.py agent-reach install --channels opencli
python kw.py agent-reach install --channels twitter
python kw.py acquire --input <url-or-query> --project-root <project>
python kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
```

Required references:

1. `references/install.md`
2. `references/platform-routing.md`
3. `references/acquisition-bundle.md`
4. `references/usage.md`
