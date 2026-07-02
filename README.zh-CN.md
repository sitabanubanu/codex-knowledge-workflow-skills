# Knowledge Workflow Skills 中文说明

Knowledge Workflow Skills 是一个面向 Codex / 本地 Agent 用户的本地知识工作流。

它把长视频、课程、访谈、播客、演讲、字幕、音视频和文字稿，转换成有来源、有边界、
可审计、可复用的知识资产。

它不是普通“视频总结器”，也不是平台爬虫。它最重要的规则是：

**先确认一手材料，再生成完整报告。**

如果只有标题、简介、截图、网页摘要、搜索片段或第三方总结，它可以写降级说明，
但不能伪装成完整视频分析。

## 这是什么

这是三个 Codex skill 和一个本地 CLI 入口组成的工作流：

- `knowledge-workflow-console`：识别输入、做 preflight、调度完整流程。
- `knowledge-video-decomposer`：获取和整理一手材料，生成结构化分析包。
- `knowledge-document-composer`：在 source gate 允许后生成最终报告。

当前入口是：

```powershell
python .\kw.py demo
python .\kw.py run --input <file-or-url> --mode audit
```

最终输出通常从这里开始看：

```text
outputs/knowledge-workflow/<project>/result_index.md
```

## 适合谁

适合这些用户：

- AI 学习者
- 研究型创作者
- 需要拆长视频、课程、访谈、播客的知识工作者
- 需要 Source / Inference / Extension 分层报告的人
- 想把视频内容沉淀成笔记、研究简报、脚本、prompt 或行动计划的人
- 使用 Codex 或本地 Agent 作为研究助手的人

## 不适合谁

不适合这些场景：

- 万能视频爬虫
- CAPTCHA / 付费墙 / 私密视频 / 区域限制 / 账号权限绕过
- 只想随手总结短视频的轻量消费场景
- 想只靠标题、简介、搜索结果就生成完整观点拆解的场景
- 不能接受 blocked / degraded 状态的场景

## 和普通视频总结器有什么区别

普通视频总结器常见问题是：拿不到原文也会给你一篇看起来完整的总结。

这个项目的策略相反：

- 有 transcript、字幕、ASR 或浏览器可见 transcript，才允许完整分析。
- 只有 metadata 或二手资料时，只允许降级说明。
- 报告必须区分：
  - Source：原材料明确说了什么。
  - Inference：基于 Source 可以合理推断什么。
  - Extension：面向用户目标可以延伸什么建议或产物。
- 失败时必须说明失败在哪里，以及下一步该提供什么材料。

这让输出更慢一点，但更可审计，也更适合长期知识工作。

## 三分钟跑通

先跑本地 transcript demo，不要先测试平台 URL：

Windows：

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly

python .\kw.py demo
```

macOS / Linux：

```bash
./sync_to_codex_skills.sh --dry-run
./sync_to_codex_skills.sh
./sync_to_codex_skills.sh --verify-only

python kw.py demo
```

跑完后先看：

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

如果 `result_index.md` 显示 `success`，说明本地 transcript 工作流已经跑通。

## 支持哪些输入

最稳定：

- 本地 transcript：`.txt`、`.md`、`.jsonl`、`.json`
- 本地字幕：`.srt`、`.vtt`

可用但需要额外依赖：

- 本地音频 / 视频：`.mp3`、`.mp4`、`.m4a`、`.webm`、`.wav`、`.mov`、`.opus`
- 需要 ffmpeg / ffprobe 和 ASR 环境。

平台 URL：

- YouTube 公公开视频：best effort。
- X / 小红书 / 抖音等平台：经常 blocked 或 degraded。
- 私密、付费墙、CAPTCHA、区域限制、账号权限页面：不是绕过目标。

平台 URL 成功时可以继续；失败时应提供 transcript、字幕、本地音视频，或在授权前提下提供
用户导出的 cookies 文件。

## 失败时会发生什么

失败不等于乱写报告。

工作流会写出状态，例如：

- `source_confirmed`：有一手材料，可以进入完整分析。
- `source_partial`：有一手材料但范围不完整，只能写明确标注的部分分析。
- `secondary_only`：只有二手材料，不能写完整视频分析。
- `source_blocked`：平台或页面阻止了一手材料获取。
- `source_failed`：工具链失败，例如下载、解析或 ASR 失败。
- `degraded_report_only`：只允许降级说明。

用户应先看：

```text
result_index.md
10_video/00_source/source_status.json
```

## 示例输出

成功运行后，典型目录是：

```text
outputs/knowledge-workflow/<project>/
  result_index.md
  10_video/
    00_source/source_status.json
    01_transcript/clean_transcript.jsonl
    05_gap_check/evidence_audit.json
    video_analysis_pack.md
  20_document/
    claim_map.json
    quality_gate.json
    final_report.md
```

建议阅读顺序：

1. `result_index.md`
2. `20_document/final_report.md`
3. `10_video/video_analysis_pack.md`
4. `20_document/quality_gate.json`

## 核心原则

完整分析必须有一手材料：

- transcript
- 字幕
- 浏览器可见 transcript
- 可转写的本地音视频

标题、简介、截图、搜索片段、第三方摘要只能做背景，不能替代一手材料。

## 隐私和安全边界

这个项目优先保护本地材料和账号边界：

- 不自动扫描 Downloads。
- 不自动扫描浏览器目录。
- 不全盘搜索 cookies。
- 不读取、展示、复制或提交 cookie 值。
- `--youtube-cookies auto` 只代表固定忽略路径：

```text
work/youtube-cookies/youtube.cookies.txt
```

它不是自动搜索模式。

项目不会尝试绕过：

- CAPTCHA
- 付费墙
- 私密视频
- 区域限制
- 账号权限障碍
- 平台访问控制

## 常见问题

### 为什么建议先跑本地 demo？

因为本地 transcript demo 不依赖平台、cookies、浏览器登录态或 ASR 环境。
它可以先证明核心 workflow、source gate、final report 和 result index 都能工作。

### 怎么判断当前环境能跑哪条路线？

先运行：

```powershell
python .\kw.py doctor
```

默认输出会给出简短的路线可用性摘要。需要完整 JSON 时加 `--pretty`，需要留档的 Markdown
诊断报告时加 `--output-md doctor.md`。

### YouTube URL 一定能成功吗？

不能。

YouTube 和其他平台可能因为 bot check、HTTP 429、登录态、字幕不可用、播放器变化、
地区或账号权限而失败。这个项目只能 best effort 获取一手材料，并在失败时给出诊断。

### 只有网页简介能不能写完整分析？

不能。

网页简介、标题、搜索片段、第三方总结只能作为背景，不能替代 transcript、字幕或 ASR。

### cookies 怎么处理？

只有在你有权限访问同一页面时，才考虑使用用户导出的 Netscape `cookies.txt`。
不要把 cookie 内容粘贴进聊天、issue、日志或提交历史。

### 中文报告乱码怎么办？

优先使用项目脚本和 UTF-8 写入路径。避免用 PowerShell 重定向或命令行字符串写入长中文文档。
如果遇到乱码，先看 `TROUBLESHOOTING.md`。

## 更多文档

- [Quickstart](QUICKSTART.md)
- [Installation](INSTALL.md)
- [User Manual](USER_MANUAL.md)
- [Supported Platforms](SUPPORTED_PLATFORMS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
- [Privacy](PRIVACY.md)
