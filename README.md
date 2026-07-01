# Knowledge Workflow Project

一套给 Codex 使用的知识视频工作流。用户不需要自己记住每个脚本怎么跑；正确用法是把这三个 skill 安装到 Codex，然后直接让 Agent 按这个 workflow 处理视频、字幕、音频或文字稿。

This is a Codex skill workflow for knowledge-heavy videos, audio, subtitles, and transcripts. Users are not expected to manually orchestrate every script. The intended usage is to install the three skills into Codex and ask the Agent to run the workflow.

## 你应该怎么使用它 / How You Should Use It

### 1. 安装三个 skill / Install the three skills

推荐使用仓库根目录里的同步脚本安装和校验：

Use the sync script from the repository root to install and verify the skills:

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

这个脚本只会同步三个正式 skill，不会同步 `subagent-supervisor` 或你的其他个人 skill。

The script syncs only the three release skills. It does not sync `subagent-supervisor` or any other personal skills.

如果你不用同步脚本，也可以手动复制：

If you do not use the sync script, copy these three directories into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force .\skills\knowledge-workflow-console $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-video-decomposer $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-document-composer $env:USERPROFILE\.codex\skills\
```

正式发布包只包含这三个 skill：

The release package contains only these three skills:

- `knowledge-workflow-console`: 总控台，负责判断输入类型、选择路线、调用 runner、记录状态。
- `knowledge-video-decomposer`: 视频/音频/字幕拆解器，负责来源检查、转写、分段、claims、examples、logic、evidence audit。
- `knowledge-document-composer`: 文档生成器，负责 commitments、source reconstruction、draft、critique、revision、quality gate、final report。

`subagent-supervisor` 不属于这个项目发布包。

`subagent-supervisor` is not part of this project release.

### 2. 对 Agent 这样说 / Tell the Agent this

最推荐的用法不是“你自己运行某个脚本”，而是直接给 Codex Agent 一个任务：

The recommended usage is not to run a script by hand first, but to ask the Codex Agent to use the workflow:

```text
请使用 knowledge-workflow-console 处理这个视频链接。
先跑 doctor 检查环境，再判断是否能拿到一手 transcript、字幕或音频。
如果能拿到一手材料，就完整拆解并生成 video_analysis_pack。
然后使用 knowledge-document-composer 生成最终报告。
如果拿不到一手材料，不要伪装完整分析，只输出降级说明和下一步需要我提供什么。

链接：<video-url>
报告语言：中文
目标：给我一份可审计的知识报告，包含核心观点、论证结构、例子、claims 和 Source / Inference / Extension 区分。
```

English prompt:

```text
Use knowledge-workflow-console for this video URL.
Run doctor first, then decide whether primary transcript, subtitles, or audio can be acquired.
If primary material is available, decompose the source and build a video_analysis_pack.
Then use knowledge-document-composer to write the final report.
If primary material is not available, do not fake a full analysis. Produce a degraded acquisition report and tell me what material I need to provide.

URL: <video-url>
Final language: English
Goal: Write an auditable knowledge report with thesis, argument structure, examples, claims, and Source / Inference / Extension separation.
```

### 3. 不同输入怎么给 Agent / What To Give The Agent

你可以给：

You can provide:

- YouTube / X / 小红书 / 抖音 / 网页视频链接
- 本地 `.mp3`, `.mp4`, `.m4a`, `.webm`
- 本地 `.txt`, `.md`, `.srt`, `.vtt`, `.jsonl`, `.json`
- 已经生成的 `10_video/video_analysis_pack.md`
- 已经生成的 `20_document` planning artifacts

你不需要自己判断路线。Agent 应该先使用 `knowledge-workflow-console` 分类输入，再进入相应阶段。

You do not need to choose the route yourself. The Agent should start from `knowledge-workflow-console`, classify the input, and then run the proper stages.

## 一条完整任务会怎么跑 / What A Full Run Does

```text
User input
  -> classify input type
  -> run doctor when platform/media environment matters
  -> source acquisition and source-status gate
  -> transcript/subtitle normalization
  -> ASR if local or acquired audio/video exists
  -> subtitle and argument segmentation
  -> concept / example / claim / analogy extraction
  -> source logic reconstruction
  -> evidence audit and gap check
  -> video_analysis_pack
  -> document composer intake
  -> commitments
  -> source reconstruction
  -> claim map
  -> draft report
  -> critique
  -> revised report
  -> quality_gate.json
  -> final_report.md
```

核心原则：

Core principle:

```text
没有一手 transcript、字幕、浏览器可见 transcript 或可转写音视频时，
不能写成完整视频分析。

No primary transcript, subtitles, browser-visible transcript, or transcribable media
means no full video analysis.
```

## 用户需要准备什么 / What The User Must Prepare

### 必须准备 / Required

- Codex 本地环境。
- 本仓库的三个 skill。
- Python 可运行这些脚本。
- 对平台视频进行处理时，至少需要 `yt-dlp`。
- 处理本地音视频或 ASR 时，需要 `ffmpeg` / `ffprobe`。
- 中文 Markdown/JSON 产物必须走 UTF-8 安全写入路径。

### 按路线需要 / Required For Specific Routes

- `faster-whisper`: 没有字幕但有音频时，本地 ASR 需要。
- Node.js: YouTube player challenge 或 yt-dlp 只暴露 storyboard/images 时常需要。
- Chrome plugin: 需要页面状态、可见 transcript、pageAssets、浏览器深探时需要。
- `cookies.txt`: YouTube bot/sign-in block 或 Chrome cookie 解密失败时，需要用户手动导出。

### 必须由用户手动完成 / Manual User Steps

- 安装或批准浏览器扩展权限。
- 导出 Netscape-format `cookies.txt` 到本地 ignored 路径，例如 `work/youtube-cookies/`。
- 不要把 cookie 内容粘贴进聊天。
- 不要提交 cookie 文件。
- CAPTCHA、paywall、private video、region lock、账号权限问题，需要用户提供授权访问、文件、字幕或转写稿。

## 为什么需要这些插件和工具 / Why These Tools Are Needed

| 工具 / Tool | 在流程中的作用 / Role |
| --- | --- |
| `yt-dlp` | 平台 metadata、字幕、格式、音频获取。Platform metadata, subtitles, formats, and audio acquisition. |
| `ffmpeg` / `ffprobe` | 音视频处理和 ASR 前置处理。Audio/video handling and ASR preparation. |
| `faster-whisper` | 本地音视频转写。Local ASR for audio/video. |
| Node.js | yt-dlp YouTube player challenge 处理。YouTube player challenge support for yt-dlp. |
| Chrome plugin | 页面状态、可见 transcript、pageAssets、浏览器深探。Page state, visible transcript, pageAssets, browser deep probe. |
| `cookies.txt` | 用户授权状态下的平台访问恢复。User-authorized platform access recovery. |
| Firecrawl / Hearsay | 背景材料和辅助检查，不能替代一手 transcript/audio。Background and auxiliary context, not a replacement for primary material. |

## 直接运行脚本的方式 / Direct Script Usage

如果你不想让 Agent 自动编排，也可以手动跑。

You can also run the scripts manually.

### 环境检查 / Doctor

```powershell
python .\skills\knowledge-video-decomposer\scripts\doctor.py `
  --output-json .\outputs\doctor_report.json `
  --output-md .\outputs\doctor_report.md `
  --overwrite `
  --pretty
```

### 本地字幕或文字稿 / Local Transcript Or Subtitle

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-transcript .\sample.srt `
  --project-root .\outputs\knowledge-workflow\sample `
  --language zh-CN `
  --document-goal "写一份可审计的知识报告" `
  --final-language zh-CN
```

### 本地音视频 / Local Audio Or Video

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-media .\sample.mp4 `
  --project-root .\outputs\knowledge-workflow\sample-media `
  --language zh-CN `
  --asr-model base `
  --asr-device cpu `
  --document-goal "拆解视频论证结构"
```

### 平台 URL / Platform URL

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-url "https://www.youtube.com/watch?v=..." `
  --project-root .\outputs\knowledge-workflow\youtube-case `
  --youtube-cookies .\work\youtube-cookies\youtube.cookies.txt `
  --use-js-runtime `
  --language zh-CN `
  --document-goal "完整拆解这个视频"
```

### 生成最终报告 / Final Report

```powershell
python .\skills\knowledge-document-composer\scripts\final_report_writer.py `
  --document-root .\outputs\knowledge-workflow\sample\20_document `
  --pretty
```

`final_report.md` 只会在 `quality_gate.json.approved_for_final_report = true` 时生成。

`final_report.md` is created only when `quality_gate.json.approved_for_final_report = true`.

## 失败时应该怎么办 / What To Do When It Fails

Agent 不应该反复重试同一个失败工具。正确处理方式：

The Agent should not keep retrying the same failed tool. Correct handling:

- 如果是缺工具：先看 `doctor_report.md` 的 `Setup Requirements`。
- 如果是 YouTube bot/sign-in block：尝试用户导出的 `cookies.txt`。
- 如果是 Chrome cookie DPAPI/App-Bound 解密失败：不要循环 Chrome profile，改用用户导出的 `cookies.txt`。
- 如果只有 metadata/title/description/chapters：只能降级，不能写完整分析。
- 如果有音频但没有字幕：走 ASR。
- 如果 ASR 失败：输出工具失败说明，请用户提供 transcript、短音频、字幕或允许更长运行。

## 输出目录 / Output Layout

典型项目目录：

Typical project directory:

```text
outputs/knowledge-workflow/<project-id>/
  10_video/
    00_source/
    01_transcript/
    02_segments/
    03_inventory/
    04_logic/
    05_gap_check/
    video_analysis_pack.md
  20_document/
    composer_intake.json
    commitments.md
    source_reconstruction.md
    claim_map.json
    draft_report.md
    critique.md
    revised_report.md
    quality_gate.json
    final_report.md
  logs/
    run_state.json
    end_to_end_steps.json
    end_to_end_summary.json
```

如果来源 blocked/degraded，不应该创建完整分析目录外观，也不应该创建 `video_analysis_pack.md` 或普通 `final_report.md`。

If the source is blocked/degraded, the workflow should not create the full analysis directory shape, `video_analysis_pack.md`, or a normal `final_report.md`.

## 相比普通视频总结工具的优势 / Advantages Over Simple Summarizers

- 不把 metadata 当 transcript。
- 不把二手网页摘要当一手材料。
- 不在 YouTube/X/小红书/抖音 blocked 时编造完整内容。
- 每个 claim 都要求来源证据或明确标注不确定。
- final report 必须区分 `Source / Inference / Extension`。
- `quality_gate.json` 是机器可读最终门禁。
- 长任务可以 resume。
- 测试覆盖成功、blocked、metadata-only、ASR、final report negative gate。

English:

- Does not treat metadata as transcript.
- Does not treat secondary summaries as primary material.
- Does not fabricate full analysis when platforms block access.
- Requires evidence or uncertainty for claims.
- Final reports must separate `Source / Inference / Extension`.
- `quality_gate.json` is the machine-readable final gate.
- Long tasks support resume.
- Tests cover success, blocked, metadata-only, ASR, and negative final-report gates.

## 测试 / Tests

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
python .\tests\real_workflow_acceptance.py
```

可选真实平台 smoke：

Optional live platform smoke:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_YOUTUBE_WITH_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_YOUTUBE_WITHOUT_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_YOUTUBE_COOKIES_REQUIRED_URL='https://www.youtube.com/watch?v=...'
$env:KW_X_BLOCKED_URL='https://x.com/...'
$env:KW_XIAOHONGSHU_BLOCKED_URL='https://www.xiaohongshu.com/explore/...'
$env:KW_DOUYIN_BLOCKED_URL='https://www.douyin.com/...'
$env:KW_INVALID_FAILED_URL='https://example.invalid/not-a-video'
python .\tests\live_platform_smoke.py
```

真实平台样本定义在 `tests/fixtures/live_cases.json`。每次运行都会在 `test_outputs/live_platform_smoke/<timestamp>/` 下写入 `summary.json` 和 `suite_summary.json`，用于审计每个 URL 的 `source_status`、路线选择、是否生成 transcript、是否错误生成完整 pack。

Live platform cases are defined in `tests/fixtures/live_cases.json`. Each run writes `summary.json` and `suite_summary.json` under `test_outputs/live_platform_smoke/<timestamp>/`, including `source_status`, route choice, transcript presence, and whether a full pack was correctly withheld.

可选真实 ASR smoke：

Optional real ASR smoke:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
python .\tests\asr_integration.py
```

ASR smoke writes `test_outputs/asr_integration/<timestamp>/summary.json`.
The local end-to-end acceptance smoke writes
`test_outputs/real_workflow_acceptance/<timestamp>/summary.json` and verifies
that a confirmed local transcript reaches `video_analysis_pack.md`,
`quality_gate.json`, and `final_report.md`.

## 当前状态 / Current Status

Beta。规则层、门禁层、产物结构、runner、doctor、真实场景 smoke 已经成型。仍然需要更多真实平台样本、更多长视频 ASR 压测、更多 Chrome 深探自动化和更完整的 UI/CLI 包装。

Beta. The rules, gates, artifact schemas, runners, doctor, and smoke tests are in place. More live samples, long-video ASR stress tests, Chrome deep-probe automation, and packaging work are still needed.

## 致谢 / Acknowledgements

本项目参考和吸收了以下项目或工具的工作流思想：

This project learns from and builds around the following projects and tools:

- VideoLingo: 启发了“先获取材料，再转写，再切分，再分析，再输出”的工作流思想。
- yt-dlp: 平台 metadata、字幕、格式和音频获取的核心工具。
- faster-whisper: 本地 ASR 路径的主要参考实现。
- FFmpeg: 音视频处理基础设施。
- Codex Chrome plugin: 浏览器页面状态、可见 transcript、pageAssets 和动态页面检查。
- Firecrawl / Hearsay: 背景/辅助获取工具，但不能替代一手 transcript 或音频。

感谢这些项目提供的开源工具、工程经验和工作流启发。本项目的重点是在 Codex 内部把这些能力组织成一套可审计、可降级、可恢复的知识工作流。

Thanks to these projects for their tools and workflow inspiration. This project organizes them into an auditable, degradable, resumable Codex knowledge workflow.
