# Input Adapters

Goal: convert messy user files into stable analysis inputs before interpretation.

## Native Chat JSON

Use `tools/analyze_chat.js` directly when records contain sender, content, and time fields.

Minimum normalized record:

```json
{
  "index": 0,
  "source": "chat.json",
  "date": "2024-01-01",
  "datetime": "2024-01-01 12:00:00",
  "sender": "name",
  "content": "message text",
  "type": "text"
}
```

## TXT / CSV / HTML Chat Exports

Convert to native JSON first. Preserve:

- original file path
- line number or row number
- timestamp if present
- sender if present
- content

If sender or time cannot be detected, run only `orientation` and ask the user before profile analysis.

## Markdown / Word / PDF / Excel / Reports

Use a document conversion layer before analysis:

- Prefer MarkItDown for broad office-to-Markdown conversion.
- Prefer Docling when page layout, tables, formulas, OCR, XBRL, or document structure matters.
- Prefer a custom parser when the file is already a structured export with known fields.

Normalize into document elements:

```json
{
  "element_id": "doc1_sec3_p2",
  "source": "report.pdf",
  "page": 12,
  "section": "3.2 Findings",
  "element_type": "paragraph",
  "content": "text..."
}
```

## Multi-Document Folders

Create a document map before analysis:

- file inventory
- detected format per file
- conversion status
- section count
- time/page coverage
- failed files and reason

Do not merge documents into one undifferentiated text blob. Source identity is part of the evidence.

## Adapter Failure Policy

If conversion fails:

- Mark runtime status as `RuntimeBlocked` or `PartiallySmokeTested`.
- Report the exact unsupported format or missing dependency.
- Offer the smallest next conversion path.

Never infer conclusions from a failed or partial parse without labeling the limitation.
