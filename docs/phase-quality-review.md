# Phase Quality Review

This file records product-intent reviews for phases 4-12. Each phase is checked
against its original design intent, not only against whether files exist.

## Phase 4 - Trust Structure

### Intent

Give users confidence around licensing, security, privacy, supported inputs, and
failure handling.

### Evidence

- `LICENSE`
- `SECURITY.md`
- `PRIVACY.md`
- `SUPPORTED_PLATFORMS.md`
- `TROUBLESHOOTING.md`

### Review

Pass. The files define use rights, cookie boundaries, privacy-sensitive output
locations, honest platform support, and operational failure paths. This directly
supports the original goal: users should know whether they can trust the tool
before running it.

## Phase 5 - Documentation Split

### Intent

Move dense internal documentation into focused user-facing pages and make the
manual readable.

### Evidence

- `README.md`
- `README.zh-CN.md`
- `QUICKSTART.md`
- `USER_MANUAL.md`
- `docs/architecture.md`
- `docs/source-gate.md`
- `docs/output-layout.md`

### Review

Pass. README is now a product entry page, Quickstart owns the first run,
USER_MANUAL is a normal manual, and architecture/source-gate/output-layout have
dedicated pages. This reduces first-read friction without changing the workflow
contract.

## Phase 6 - GitHub Presentation

### Intent

Make the project discoverable and understandable from GitHub before users read
the whole README.

### Evidence

- `docs/github-about.md`
- GitHub repository description updated.
- GitHub topics updated: `codex`, `openai-codex`, `ai-agent`,
  `video-analysis`, `knowledge-workflow`, `transcript`, `yt-dlp`, `ffmpeg`,
  `whisper`, `research-tool`.

### Review

Pass. The repository now has a concise description and relevant topics. This
serves the original goal of making the product visible and easier to understand
from GitHub search and the repository header.

## Phase 7 - Release Refresh Preparation

### Intent

Refresh the release surface so the product entry work can be packaged without
including generated outputs or private material.

### Evidence

- `RELEASE_NOTES.md`
- `CHANGELOG.md`
- `ROADMAP.md`
- `docs/release-process.md`
- `dist/codex-knowledge-workflow-skills-v0.3-product-entry-alpha.zip`

### Review

Pass with publication caveat. The local release package is prepared and release
notes describe the product-entry alpha. GitHub release publication remains a
separate owner-approved action after commit/tag/push.

## Phase 8 - Quality Evaluation

### Intent

Go beyond "files exist" and add a way to evaluate whether outputs are faithful,
separated by evidence tier, and safe.

### Evidence

- `quality_rubric.md`
- `golden_samples/source_gate_demo/`
- `kw.py quality`

### Review

Pass for first implementation. The rubric defines human quality dimensions, the
golden sample fixes expected claims and non-claims, and `kw.py quality` writes a
source-gate-aligned review. Later versions can add deeper automated scoring.

## Phase 9 - Batch Research Workflow

### Intent

Move from single-video workflow toward multi-source research: batch status,
summary, recommended order, and comparative report.

### Evidence

- `kw.py batch`
- `examples/batch_research/batch_links.csv`
- `examples/batch_research/README.md`
- Generated validation output under ignored `outputs/knowledge-workflow/batch-demo/`

### Review

Pass for product-entry alpha. Batch mode runs multiple local transcript items,
writes item projects, status CSV, summary, recommended order, and comparative
report. Cross-source synthesis is still mechanical and is documented as a later
improvement.

## Phase 10 - Output Templates

### Intent

Let users turn approved workflow artifacts into different knowledge assets
instead of only one final-report format.

### Evidence

- `templates/study_notes.md`
- `templates/research_brief.md`
- `templates/creator_script.md`
- `templates/prompt_pack.md`
- `templates/action_plan.md`
- `kw.py template`

### Review

Pass. Templates are deterministic projections from approved artifacts and keep
source gate status visible. They do not invent new source claims, which preserves
the original auditability principle.

## Phase 11 - Chrome Probe Integration

### Intent

Integrate Chrome/page observations without pretending the repository controls
Chrome or that page playback equals primary material.

### Evidence

- `kw.py chrome-probe`
- `examples/chrome_probe/chrome_observation_url_only.json`
- `docs/chrome-probe-integration.md`

### Review

Pass. Chrome remains a contract-driven observation layer. URL-only observations
do not unlock `source_confirmed`; the workflow still requires exported or
fetched primary material that can be parsed or transcribed.

## Phase 12 - Real Platform And Real ASR Validation Matrix

### Intent

Make real platform and real ASR validation explicit, repeatable, and opt-in.

### Evidence

- `validation/live_platform_matrix.csv`
- `validation/real_asr_matrix.csv`
- `docs/validation.md`
- Existing opt-in tests: `tests/live_platform_smoke.py`,
  `tests/asr_integration.py`

### Review

Pass with sample caveat. The matrices define required real cases and environment
variables. Actual live coverage still requires user-provided URLs and media, so
default validation remains fixture-based and safe.
