# User Manual

## Read The Result Index First

Every project should end with:

```text
result_index.md
logs/result_index.json
```

The result index tells you:

- acquisition status;
- source status;
- whether primary material exists;
- whether a full report is allowed;
- where the final report or degraded output is;
- what the next safe action is.

## URL Workflow

```powershell
python .\kw.py agent-reach doctor
python .\kw.py run --input <url> --mode audit
```

Internal route:

```text
URL
  -> agent-reach-console
  -> 00_acquisition/manifest.json
  -> source-gated-evidence-layer
  -> source_status.json
  -> evidence audit if allowed
  -> document composer if allowed
```

If the URL only yields metadata, search snippets, comments, or page context, the
workflow must stop degraded. That is success for the safety gate, not a failure
to be patched around.

## Local File Workflow

```powershell
python .\kw.py run --input .\my-transcript.vtt --mode audit
```

The CLI builds a local acquisition bundle, then ingests it. Non-empty transcript
and subtitle files can become `source_confirmed`.

Local audio/video is copied into the bundle but remains pending/degraded until
ASR creates a transcript.

## Acquisition Bundle Workflow

Advanced users can run the stages separately:

```powershell
python .\kw.py acquire --input <url> --project-root <project>
python .\kw.py validate-bundle --bundle <project>\00_acquisition\manifest.json
python .\kw.py ingest --bundle <project>\00_acquisition\manifest.json --project-root <project>
python .\kw.py audit --project-root <project>
python .\kw.py compose --project-root <project>
```

The manifest is the contract. Do not feed raw Agent-Reach output directly to
the composer.

## Blocked Or Degraded Results

A blocked/degraded run should answer:

1. What was acquired?
2. What is missing?
3. Why is complete analysis not allowed?
4. What can you provide next?

Typical next actions:

- provide a transcript;
- provide a subtitle file;
- provide authorized local audio/video for ASR;
- resolve platform access manually;
- accept a clearly labeled non-primary triage.

## Full Report Conditions

`final_report.md` is allowed only when:

- source status is `source_confirmed` or `source_partial`;
- evidence audit has no blocking errors;
- `claim_map.json` has accepted Source claims;
- the final report separates Source / Inference / Extension;
- partial sources are labeled partial.

The composer must not turn metadata into Source claims.
