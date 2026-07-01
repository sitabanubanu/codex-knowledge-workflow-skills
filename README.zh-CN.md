# Knowledge Workflow Skills 中文说明

这是一个面向 Codex / 本地 Agent 用户的视频知识工作流。它把可取得的一手 transcript、字幕、音视频转成可审计知识资产，并且在拿不到一手材料时明确降级，而不是伪装成完整分析。

## 最适合谁

- AI 学习者
- 研究型创作者
- 需要拆长视频、课程、访谈、播客的知识工作者
- 需要 Source / Inference / Extension 分层报告的人

## 不适合什么

- 万能视频爬虫
- CAPTCHA / 付费墙 / 私密视频 / 区域限制 / 账号权限绕过
- 只想随手总结短视频的轻量消费场景

## 第一次使用

先跑本地 transcript demo，不要先测试平台 URL：

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly

python .\kw.py demo
```

跑完后先看：

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

## 核心原则

完整分析必须有一手材料：

- transcript
- 字幕
- 浏览器可见 transcript
- 可转写的本地音视频

标题、简介、截图、搜索片段、第三方摘要只能做背景，不能替代一手材料。

## 更多文档

- [Quickstart](QUICKSTART.md)
- [User Manual](USER_MANUAL.md)
- [Supported Platforms](SUPPORTED_PLATFORMS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
- [Privacy](PRIVACY.md)
