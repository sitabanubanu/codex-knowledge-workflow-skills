# Knowledge Workflow Skills User Manual

这份说明书面向“要让 Codex Agent 使用本项目的人”。如果你只是想分析一个视频，不需要自己逐个运行所有脚本；把三个 skill 安装好，然后让 Agent 使用 `knowledge-workflow-console` 作为入口。

This manual is for users who want a Codex Agent to use this project. If you only want to analyze a video, you do not need to run every script manually. Install the three skills and ask the Agent to start with `knowledge-workflow-console`.

## 1. 安装 / Installation

从 release zip 解压后，把三个 skill 目录复制到 Codex skill 目录：

After extracting the release zip, copy these three skill folders into your Codex skills directory:

```powershell
Copy-Item -Recurse -Force .\skills\knowledge-workflow-console $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-video-decomposer $env:USERPROFILE\.codex\skills\
Copy-Item -Recurse -Force .\skills\knowledge-document-composer $env:USERPROFILE\.codex\skills\
```

不要安装 `subagent-supervisor`；它不属于这个发布包。

Do not install `subagent-supervisor`; it is not part of this release package.

## 2. 第一次使用前 / Before First Use

先让 Agent 或你自己运行 doctor：

Ask the Agent to run doctor, or run it yourself:

```powershell
python .\skills\knowledge-video-decomposer\scripts\doctor.py `
  --output-json .\outputs\doctor_report.json `
  --output-md .\outputs\doctor_report.md `
  --overwrite `
  --pretty
```

重点看 `doctor_report.md` 里的 `Setup Requirements`：

Check `Setup Requirements` in `doctor_report.md`:

- `yt-dlp`: 平台 URL 获取所需。
- `ffmpeg` / `ffprobe`: 本地音视频和 ASR 所需。
- `faster-whisper`: 没有字幕但有音频时转写所需。
- `Node.js`: YouTube player challenge 常用。
- Chrome plugin: 页面状态、可见 transcript、pageAssets 检查所需。
- `cookies.txt`: YouTube bot/sign-in block 或 Chrome cookie 解密失败时，由用户手动导出。
- Python UTF-8: 中文 Markdown/JSON 稳定写入所需。

## 3. 推荐的 Agent 指令 / Recommended Agent Prompt

把下面这段复制给 Codex Agent，然后替换链接和目标：

Copy this to the Codex Agent and replace the URL and goal:

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

English version:

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

## 4. 支持的输入 / Supported Inputs

- 平台链接：YouTube, X, 小红书, 抖音, 普通网页视频。
- 本地媒体：`.mp3`, `.mp4`, `.m4a`, `.webm`。
- 字幕/文字稿：`.txt`, `.md`, `.srt`, `.vtt`, `.jsonl`, `.json`。
- 已生成的 `10_video/video_analysis_pack.md`。
- 已生成的 `20_document` planning artifacts。

## 5. 工作流会做什么 / What The Workflow Does

```text
Input
  -> classify input
  -> doctor and source acquisition
  -> source-status gate
  -> transcript/subtitle normalization or ASR
  -> segmentation
  -> concepts/examples/claims/analogies
  -> source logic
  -> evidence audit
  -> video_analysis_pack
  -> document planning
  -> draft
  -> critique
  -> revised report
  -> quality_gate.json
  -> final_report.md
```

核心规则：

Core rule:

```text
没有一手 transcript、字幕、浏览器可见 transcript 或可转写音视频时，
不能写成完整视频分析。

No primary transcript, subtitles, browser-visible transcript, or transcribable media
means no full video analysis.
```

## 6. 常见失败和处理 / Common Failures

- 只有标题、简介、章节或网页 metadata：只能降级，不能写完整报告。
- YouTube bot/sign-in block：需要用户导出 `cookies.txt`。
- Chrome cookie DPAPI/App-Bound 解密失败：不要循环 Chrome profile，改用用户导出的 `cookies.txt`。
- 没有字幕但有音频：走 ASR。
- ASR 失败：提供 transcript、字幕、短音频，或允许更长运行时间。
- CAPTCHA、paywall、private、region lock、账号权限：需要用户提供授权访问或一手材料。

## 7. 手动脚本入口 / Manual Script Entrypoints

本地 transcript/subtitle：

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-transcript .\sample.srt `
  --project-root .\outputs\knowledge-workflow\sample `
  --language zh-CN `
  --document-goal "写一份可审计的知识报告" `
  --final-language zh-CN
```

本地音视频：

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-media .\sample.mp4 `
  --project-root .\outputs\knowledge-workflow\sample-media `
  --language zh-CN `
  --asr-model base `
  --asr-device cpu
```

平台 URL：

```powershell
python .\skills\knowledge-workflow-console\scripts\end_to_end_runner.py `
  --input-url "https://www.youtube.com/watch?v=..." `
  --project-root .\outputs\knowledge-workflow\youtube-case `
  --youtube-cookies .\work\youtube-cookies\youtube.cookies.txt `
  --use-js-runtime `
  --language zh-CN
```

最终报告：

```powershell
python .\skills\knowledge-document-composer\scripts\final_report_writer.py `
  --document-root .\outputs\knowledge-workflow\sample\20_document `
  --pretty
```

## 8. 测试 / Tests

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python .\tests\knowledge_workflow_regression.py
python .\tests\live_platform_smoke.py
python .\tests\asr_integration.py
```

默认测试不要求真实平台访问。真实平台 smoke 和真实 ASR smoke 需要额外环境变量，详见 `README.md`。

Default tests do not require live platform access. See `README.md` for optional live platform and real ASR smoke tests.
