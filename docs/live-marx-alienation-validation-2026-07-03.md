# Live Validation: Marx Alienated Labor And Subjectivity Loss

Date: 2026-07-03, Asia/Shanghai.

User task: find videos about Marxism, alienated labor, and the loss of
subjectivity; run the complete Knowledge Workflow where possible; record wrong
or blocked candidates.

## Outcome

The run did not reach a full source-confirmed report from a platform URL. This
is the correct gated behavior for the current environment: no tested platform
candidate yielded primary material, so the workflow stopped at degraded
acquisition outputs and did not create `video_analysis_pack.md` or
`final_report.md`.

## Candidate Ledger

| Candidate | URL | Why Considered | Route Tried | Result |
| --- | --- | --- | --- | --- |
| YouTube 1844 manuscripts alienated labor part 2 | `https://www.youtube.com/watch?v=FTFFcuO25nw` | Best direct match for Marx, 1844 manuscripts, alienated labor. | `kw.py run` URL audit; Chrome page observation; Hearsay URL ingest; JS runtime / remote components retry. | YouTube page visible in Chrome, but no visible transcript; yt-dlp blocked by bot check; Hearsay timed out; no primary material acquired. |
| YouTube 1844 manuscripts alienated labor part 1 | `https://www.youtube.com/watch?v=s329RlGgT3Y` | Companion part to the best direct match. | `kw.py run` URL audit. | Same YouTube bot-check block; no primary material acquired. |
| YouTube 1844 manuscript original-text analysis P4 | `https://www.youtube.com/watch?v=3SPa8Jyl6uk` | Shorter and focused 1844 manuscript / alienated labor candidate. | `kw.py run` URL audit. | Same YouTube bot-check block; no primary material acquired. |
| Bilibili wage labor and capital reading selection | `https://www.bilibili.com/video/BV1iT411s7uK/` | Bilibili candidate surfaced by search; related to labor and alienation. | `kw.py run` URL audit; Chrome page observation. | Page visible but no subtitle/asset observed; yt-dlp failed without usable source material; no primary material acquired. |
| Bilibili reification and alienation candidate | `https://www.bilibili.com/video/BV1Da4y1y7Vc/` | More direct Bilibili candidate about reification and alienation. | `kw.py run` URL audit. | yt-dlp failed without usable source material; no primary material acquired. |
| Articles and PDFs on alienated labor / subjectivity | CSSN, CASS, PDF articles, Wikipedia-style summaries | Useful for vocabulary and topic confirmation. | Search only. | Not selected for the video workflow because they are secondary text sources, not video primary material. |

## Search Notes

Useful query families:

- `Marx alienated labor subjectivity loss lecture video`
- `Marx 1844 manuscripts alienated labor YouTube`
- `site:youtube.com/watch Marx alienated labor subjectivity`
- `site:bilibili.com Marx labor alienation subjectivity video`
- `reification alienation Bilibili Marx labor product dominates worker`

Search issue:

- Several highly relevant results were articles or papers rather than runnable
  video sources.
- Some video search results were only recommendation snippets, not stable
  primary material.
- One Firecrawl search with full markdown scraping timed out, so search was
  retried without page scraping.

## Workflow Evidence

Primary project outputs:

- `outputs/knowledge-workflow/marx-alienated-labor-subjectivity-youtube/`
- `outputs/knowledge-workflow/marx-alienated-labor-subjectivity-youtube-js/`
- `outputs/knowledge-workflow/marx-alienated-labor-part1-youtube/`
- `outputs/knowledge-workflow/marx-alienated-labor-chelizi-youtube/`
- `outputs/knowledge-workflow/marx-alienation-bilibili-bv1it411s7uk/`
- `outputs/knowledge-workflow/marx-reification-alienation-bilibili/`

Observed statuses:

- YouTube candidates: `source_blocked`
- Bilibili candidates: `source_failed`
- `primary_material_available`: `false`
- `full_analysis_allowed`: `false`
- `video_analysis_pack.md`: not created
- `final_report.md`: not created

This verifies the source gate: the workflow did not pretend that metadata,
search snippets, visible page text, or video recommendations were a transcript.

## Chrome Observation

Chrome could open the main YouTube page and showed the title:

`YouTube title observed: Marx 1844 manuscripts, alienated labor part 2`

The visible page did not expose a transcript entry, and page asset inspection did
not reveal exportable video/subtitle/timedtext assets. A Bilibili candidate page
was also visible, but no subtitle or media asset suitable for workflow handoff
was observed.

## Skill Behavior Notes

Good behavior:

- The URL workflow returned degraded acquisition outputs instead of fabricating
  a report.
- `source_status.json` clearly named `source_blocked` or `source_failed`.
- `result_index.json` told the user to provide transcript, subtitle, local
  media, browser-derived export, or authorized cookies.
- Cookie values were not read, displayed, copied, or committed.

Issue to consider:

- `kw.py run` returns process exit code `0` for degraded URL runs. This is
  acceptable if "degraded acquisition report written" is considered a successful
  command outcome, but it can confuse release validation because no full report
  exists. Future CLI output should make the degraded outcome more prominent in
  stdout.
- For Bilibili, the platform was classified as `generic_web`, and diagnostics
  did not expose a user-friendly platform-specific reason. Future live-platform
  validation should improve Bilibili route labeling and next-action text.

## Next Required Material

To complete the full source-confirmed workflow for this theme, provide one of:

- an official subtitle file (`.srt`, `.vtt`, `.json3`);
- a manually exported transcript;
- a local audio/video file for ASR;
- a browser-derived transcript/subtitle export;
- an authorized YouTube cookies file at `work/youtube-cookies/youtube.cookies.txt`
  and rerun with `--youtube-cookies auto`.
