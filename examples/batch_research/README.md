# Batch Research Example

This example shows the intended batch shape without relying on platform URLs.
It reuses the local demo transcript so the first batch run is deterministic.

```powershell
python .\kw.py batch `
  --input .\examples\batch_research\batch_links.csv `
  --output-root .\outputs\knowledge-workflow\batch-demo
```

Outputs:

```text
outputs/knowledge-workflow/batch-demo/
  batch_status.csv
  batch_items.json
  batch_summary.md
  recommended_watch_order.md
  comparative_report.md
  001/
  002/
```

`batch_summary.md` is the human index. `batch_items.json` and
`batch_status.csv` are the machine-readable status views. The comparative
report compares readiness and source-gate status; it does not invent
cross-source claims.
