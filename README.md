# Knowledge Workflow Project

一套给 Codex 使用的知识视频工作流 skill 包。它的目标不是把视频粗略总结成几段话，而是把视频链接、本地音视频、字幕、转写稿或网页视频，转成可审计、可恢复、可降级说明的结构化知识产物，再进入报告写作。

This is a Codex skill workflow for knowledge-heavy video and transcript analysis. It is not a simple video summarizer. It turns video URLs, local media, subtitles, transcripts, or video pages into auditable structured knowledge artifacts, then composes source-grounded reports.

## 项目组成 / Project Layout

发布范围只包含知识工作流本身：

The published workflow contains only the knowledge workflow components:

- `skills/knowledge-workflow-console`: 总控台，负责输入分类、路由、阶段编排、输出目录和端到端 runner。
- `skills/knowledge-video-decomposer`: 视频/音频/字幕/转写拆解器，负责来源检查、转写、分段、概念/例子/claim/逻辑抽取、证据审计和 `video_analysis_pack`。
- `skills/knowledge-document-composer`: 文档生成器，负责从分析包进入 commitments、source reconstruction、draft、critique、revision、source audit 和 final report。
- `tests/`: 离线回归、真实场景 smoke、ASR 集成 smoke 和 fixtures。

`subagent-supervisor` 不属于这个发布包。它曾用于开发期审查协作，但不作为本工作流的正式组成部分提交。

`subagent-supervisor` is not part of this release package. It was useful during development review, but it is not part of the final workflow distribution.

## 相比其他项目的优势 / Advantages

很多视频工具以“抓到一点文本然后总结”为核心。本项目的重点是工作流可靠性和证据边界。

Many tools stop at "extract some text and summarize it." This project focuses on workflow reliability and evidence boundaries.

- 来源门禁：没有一手 transcript、字幕、浏览器可见转写或可转写音视频时，不允许伪装成完整分析。
- 可降级：YouTube、X、小红书、抖音等平台被挡住时，输出 blocked/degraded 说明，而不是编造内容。
- 证据审计：claim、example、logic node 必须能回到 transcript span 或明确标注缺口。
- 完整闭环：从 acquisition、transcript、segments、inventory、logic、gap check 到 `video_analysis_pack`，再到 final report audit。
- 可恢复：端到端 runner 记录 `run_state.json`，支持长任务 resume。
- 环境 doctor：运行前检查 yt-dlp、ffmpeg、faster-whisper、Node、Chrome plugin、cookies 文件、Python 编码和 UTF-8 写入。
- 真实测试集：不仅测 happy path，也测 metadata-only、blocked、degraded、ASR resume、final report negative gate。

English summary:

- Source gate: no primary material means no fake full report.
- Degraded paths: blocked platforms produce acquisition reports, not fabricated analysis.
- Evidence audit: claims, examples, and logic nodes must trace back to source spans or disclose gaps.
- End-to-end loop: acquisition -> transcript -> segmentation -> inventory -> logic -> audit -> analysis pack -> final report.
- Resume support: long runs write machine-readable state.
- Doctor check: toolchain and setup checks before platform work.
- Realistic tests: success, blocked, metadata-only, ASR, and final-report failure paths are covered.

## 工作流 / Workflow

```text
Input
  -> classify source
  -> acquisition / source gate
  -> transcript or subtitle normalization
  -> ASR when local/acquired audio exists
  -> subtitle + argument segmentation
  -> concepts / examples / claims / analogies
  -> source logic reconstruction
  -> evidence audit and gap check
  -> video_analysis_pack
  -> document planning artifacts
  -> draft
  -> critique
  -> revised report
  -> machine-readable quality_gate.json
  -> final_report.md
```

核心规则：

Core rule:

```text
Chrome 无 transcript 不是终点；
Chrome 无 transcript 且无法产出可转写的一手媒体，才进入降级或请求用户补充材料。

No transcript in Chrome is not the end.
Only no transcript plus no primary media/transcript route should degrade or request user material.
```

## 使用方式 / How To Use

### 1. 安装 skills / Install skills

把本仓库中的知识工作流 skill 复制到 Codex skill 目录：

Copy the workflow skills into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force .\skills\knowledge-workflow-console $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-video-decomposer $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-document-composer $env:USERPROFILE\.codex\skills\
```

### 2. 先跑 doctor / Run doctor first

```powershell
python .\skills\knowledge-video-decomposer\scripts\doctor.py `
  --output-json .\outputs\doctor_report.json `
  --output-md .\outputs\doctor_report.md `
  --overwrite `
  --pretty
```

看 `setup_requirements`：

Check `setup_requirements`:

- `yt-dlp`: 平台 URL 获取 metadata、字幕、音频所需。
- `ffmpeg` / `ffprobe`: 本地音视频和 ASR 路径所需。
- `faster-whisper`: 没有字幕但有音频时做本地 ASR。
- `Node.js`: yt-dlp 遇到 YouTube player challenge 时常需要。
- Chrome plugin: 页面状态、可见 transcript、pageAssets、浏览器探测所需。
- `cookies.txt`: YouTube bot/sign-in block 或 Chrome cookie 解密失败时，由用户手动导出的 Netscape cookies 文件。
- Python UTF-8: 中文 Markdown/JSON 稳定写入所需。

### 3. 本地 transcript/subtitle / Local transcript or subtitle

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-transcript .\sample.srt `
  --project-root .\outputs\knowledge-workflow\sample `
  --language zh-CN `
  --document-goal "写一份可审计的知识报告" `
  --final-language zh-CN
```

支持 `.txt`, `.md`, `.srt`, `.vtt`, `.jsonl`, `.json`。

Supported inputs: `.txt`, `.md`, `.srt`, `.vtt`, `.jsonl`, `.json`.

### 4. 本地音视频 / Local audio or video

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-media .\sample.mp4 `
  --project-root .\outputs\knowledge-workflow\sample-media `
  --language zh-CN `
  --asr-model base `
  --asr-device cpu `
  --document-goal "拆解视频论证结构"
```

如果已有 ASR JSONL，可用 `--asr-jsonl` 跳过真实模型转写。

If you already have ASR JSONL, pass `--asr-jsonl` to resume without running the model.

### 5. 平台 URL / Platform URL

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-url "https://www.youtube.com/watch?v=..." `
  --project-root .\outputs\knowledge-workflow\youtube-case `
  --youtube-cookies .\work\youtube-cookies\youtube.cookies.txt `
  --use-js-runtime `
  --language zh-CN `
  --document-goal "完整拆解这个视频"
```

URL 路径会先尝试字幕，再尝试音频 + ASR。如果只有标题、简介、章节、页面 metadata，则停在 degraded acquisition，不创建完整分析包。

The URL path tries subtitles first, then audio plus ASR. If it only gets title, description, chapters, or page metadata, it stops at degraded acquisition and does not create a full analysis pack.

### 6. 最终报告 / Final report

当 `20_document` planning artifacts 已存在后：

After `20_document` planning artifacts exist:

```powershell
python .\skills\knowledge-document-composer\scripts\final_report_writer.py `
  --document-root .\outputs\knowledge-workflow\sample\20_document `
  --pretty
```

它会写：

It writes:

```text
draft_report.md
critique.md
revised_report.md
quality_gate.json
quality_check.md
final_report.md
```

`final_report.md` 只在 `quality_gate.json.approved_for_final_report = true` 时生成。

`final_report.md` is created only when `quality_gate.json.approved_for_final_report = true`.

## 手动准备项 / Manual Preparation

用户必须手动完成的事项：

User-owned manual steps:

- 安装或批准浏览器插件权限。Agent 不应代替用户点击扩展权限确认。
- 导出 Netscape-format `cookies.txt`，只放在本地 ignored 路径，例如 `work/youtube-cookies/`。
- 不要把 cookie 内容粘贴进聊天，不要提交 cookie 文件。
- CAPTCHA、paywall、private video、region lock、账号权限问题，需要用户提供授权访问、文件、字幕或转写稿。

Manual steps that must stay with the user:

- Install or approve browser extension permissions.
- Export Netscape-format `cookies.txt` into a local ignored path.
- Never paste cookie values into chat or commit cookie files.
- CAPTCHA, paywall, private, region, or account-permission issues require user-provided access or primary material.

## 测试 / Tests

默认离线测试：

Default offline tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
```

可选真实平台 smoke：

Optional live platform smoke:

```powershell
$env:KW_LIVE_PLATFORM_SMOKE='1'
$env:KW_YOUTUBE_WITH_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_YOUTUBE_WITHOUT_SUBTITLES_URL='https://www.youtube.com/watch?v=...'
$env:KW_X_BLOCKED_URL='https://x.com/...'
$env:KW_XIAOHONGSHU_BLOCKED_URL='https://www.xiaohongshu.com/explore/...'
$env:KW_DOUYIN_BLOCKED_URL='https://www.douyin.com/...'
python .\tests\live_platform_smoke.py
```

可选真实 ASR smoke：

Optional real ASR smoke:

```powershell
$env:KW_REAL_ASR_SMOKE='1'
$env:KW_REAL_ASR_MP3='C:\path\sample.mp3'
$env:KW_REAL_ASR_MP4='C:\path\sample.mp4'
python .\tests\asr_integration.py
```

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
- Firecrawl / Hearsay: 作为背景/辅助获取工具，但不能替代一手 transcript 或音频。

感谢这些项目提供的开源工具、工程经验和工作流启发。本项目的重点是在 Codex 内部把这些能力组织成一套可审计、可降级、可恢复的知识工作流。

Thanks to these projects for their tools and workflow inspiration. This project focuses on organizing them into an auditable, degradable, resumable Codex knowledge workflow.
