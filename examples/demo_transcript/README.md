# Demo Transcript Example

This example is the recommended first run. It uses a local transcript so the workflow can prove the source gate, evidence audit, document planning, final report, and result index without depending on platform access.

Run from this directory:

```powershell
.\run.ps1
```

Or from the repository root:

```powershell
python .\kw.py run --input .\examples\demo_transcript\input.txt --project-root .\outputs\knowledge-workflow\demo-transcript --mode audit --language en --final-language en
```

Start with:

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

The files under `expected_outputs/` are compact examples of the shape of a successful run. Real output may contain different timestamps, hashes, and extracted claims.
