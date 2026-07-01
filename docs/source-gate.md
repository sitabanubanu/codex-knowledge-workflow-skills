# Source Gate Summary

The source gate prevents the workflow from producing a complete analysis when
only metadata or secondary material is available.

## Full Analysis Allowed

Only when source status is:

- `source_confirmed`

Partial analysis is allowed only when:

- `source_partial` is explicitly scoped,
- gaps and source coverage are documented,
- the report visibly labels itself as partial.

## Full Analysis Forbidden

The workflow must not create a complete `video_analysis_pack.md` or full final
report for:

- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

## Primary Source Classes

- `primary_transcript`
- `primary_audio_asr`
- `browser_visible_transcript`
- `browser_derived_media`

## Secondary Context

These can support degraded reports only:

- platform metadata,
- screenshots,
- search snippets,
- Firecrawl context,
- page observation,
- third-party summaries.
