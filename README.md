# Knowledge Workflow Skills

[![offline-validation][offline-validation-badge]][offline-validation]

> 从“我想学什么”出发，先找对材料，再验证材料，最后生成可追溯的学习文章或正式文档。

当前版本：`v0.7.0`。

## 这是什么

Knowledge Workflow Skills 是一套独立的、来源门控的知识获取与学习工作流。它不依赖 Agent Reach，也不会把搜索摘要、网页外壳或旧报告直接包装成新结论。

从创作者视角，完整产品由三部分组成：

1. `web-intent-scout`：理解“真正要找什么”，组织查询、来源台账、时效与风险检查，并筛选候选材料。
2. `knowledge-workflow-console`：总控台。负责获取材料、来源门控、规范化/ASR、证据审计、状态和交付路线。
3. `knowledge-learning-article`：把通过审计的材料重组成知识地图、前置关系、学习顺序、迁移方法和学习文章。

总控台内部还会调用三个职责单一的工作 Skill：

- `acquire-source-material`：直接探测原生 Provider，获取材料并写入 Acquisition Bundle v2。
- `source-gated-evidence-layer`：判断材料是否与目标匹配、是否足以分析，并构建证据链。
- `knowledge-document-composer`：在质量门通过后生成忠于来源的报告、提纲或 briefing。

`knowledge-video-decomposer` 仅保留为内部兼容脚本库，不是普通用户入口。`browser-host-identity` 是另一个独立项目，不属于这条工作流；本项目只保留“必须明确声明真实 Edge/Chrome 宿主”的安全契约。

## 工作流

```text
学习需求
  -> Web Intent Scout（需要发现或比较来源时）
  -> Source Acquisition（直连 Provider 或导入授权材料）
  -> Acquisition Bundle v2
  -> Source Gate（目标、范围、完整度、哈希）
  -> 规范化 / 本地 ASR / Claims / Evidence Audit
  -> Learning Article 或 Source-faithful Document
  -> receipts + quality gate + result_index.md
```

Web Scout 的结果只是“选材依据”，不能直接成为正文证据。所有正式结论都必须来自通过 Bundle、Source Gate 和 evidence audit 的当前材料。

## 它解决什么问题

- 搜索摘要、metadata、截图或评论被误当成一手材料。
- 帖子正文被误当成帖子内视频的完整字幕。
- 音视频还没完成 ASR，就被误判为材料失败或完整可分析。
- 材料残缺、获取失败，却仍生成看似完整的报告。
- 旧任务文件污染新任务，或者来源变化后继续使用旧证据。
- 结论无法定位到来源片段、时间戳、artifact 哈希和运行批次。
- 来源事实、模型推断和外部扩展混在一起。
- 搜索、材料获取、证据判断和写作由同一层随意越权。

项目使用 `run_id`、`attempt_id`、来源指纹、字节数、SHA-256 和分层 receipts 防止状态漂移。材料不足时会明确给出 `blocked`、`secondary_only` 或降级说明，不会伪造完整分析。

## 为什么现在不需要 Agent Reach

项目早期曾把 Agent Reach 当作获取层。`v0.7.0` 已将这一位置替换为项目自有的 Provider Registry、Route Plan 和 Bundle Writer：

| 维度 | Agent Reach | 本项目 v0.7.0 |
| --- | --- | --- |
| 主要目标 | 多平台命令与可达性 | 从需求发现到可信学习交付的完整工作流 |
| 获取方式 | 通过上游总入口路由 | 直接探测并调用 yt-dlp、curl/Jina、gh、bili、OpenCLI、mcporter 等可选 Provider |
| 稳定交接 | 以工具输出为主 | 强制输出 Acquisition Bundle v2 |
| 目标/范围判断 | 不负责下游证据许可 | Source Gate 精确判断材料能支持什么目标 |
| 证据与追溯 | 不是核心产品层 | claims、logic graph、evidence map、哈希和 receipts |
| 学习输出 | 不负责 | 知识地图、前置关系、学习路径和学习文章 |
| 失败行为 | 获取失败 | 安全阻断、降级说明、明确下一步，禁止伪报告 |
| 运行依赖 | 需要 Agent Reach runtime | 不安装、不导入、不执行 Agent Reach |

如果只想临时调用某个平台命令，独立工具可能更轻。如果目标是“找到值得学的材料，并把它可靠地变成可复核的知识产品”，本项目覆盖的链路更完整。

## 获取能力边界

内置结构化直连路线覆盖普通网页、YouTube、Bilibili、GitHub、X/Twitter、小红书和 Exa 搜索。RSS、Reddit、Facebook、Instagram、LinkedIn、小宇宙、V2EX、雪球等渠道通过统一的授权导入契约进入同一个 Bundle v2。

这不等于承诺每个 URL 都能获取。登录、反自动化、地区、账号权限和页面变化仍可能阻断 Provider。项目不会绕过 CAPTCHA、付费墙、私密访问或平台权限。

查看当前机器的真实能力：

```powershell
kw source doctor
kw source matrix
kw source plan --input <URL或查询> --target <目标> --operation <操作>
```

## 快速开始

```powershell
git clone https://github.com/sitabanubanu/codex-knowledge-workflow-skills.git
cd codex-knowledge-workflow-skills
python -m pip install -e .
kw --help
```

安装或更新 Codex Skills：

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

先跑完全离线演示：

```powershell
kw demo
kw validate
```

处理本地 transcript、字幕、音频或视频：

```powershell
kw run --input <本地文件> --target video_content --operation extract_transcript --mode audit --final-language zh-CN
```

处理 URL：

```powershell
kw run --input <URL> --target <目标> --operation <操作> --mode audit --final-language zh-CN
```

导入其他授权 Provider 或浏览器导出的主材料：

```powershell
kw source import `
  --input-file .\exports\primary.txt `
  --source-url <原始URL> `
  --platform reddit `
  --target social_post `
  --operation read `
  --project-root .\outputs\knowledge-workflow\reddit
```

## 如何读结果

每个任务以 `result_index.md` 为统一入口。关键文件通常是：

```text
00_acquisition/manifest.json
00_acquisition/logs/capability_report.json
00_acquisition/logs/route_plan.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/source_analysis_pack.md
15_learning/learning_enrichment.json
20_document/learning_article.md 或 final_report.md
20_document/*_receipt.json
result_index.md
```

只有当前来源、当前运行和当前哈希全部匹配，且质量门允许时，正式交付物才成立。

## 发布与验证

```powershell
python -m build --sdist
kw validate --include-sync
git archive --format=zip --output=dist\codex-knowledge-workflow-skills-v0.7.0-source.zip HEAD
```

完整产品以源码包发布，因为 Codex Skills、参考资料和内部脚本都属于运行时。
Python wheel 只包含 CLI 模块，不能替代完整源码包。源码包不应包含 cookies、
token、浏览器数据、私密 transcript、媒体、`outputs/` 或 `test_outputs/`。

## 文档

- [安装说明](INSTALL.md)
- [用户手册](USER_MANUAL.md)
- [平台与操作矩阵](SUPPORTED_PLATFORMS.md)
- [架构说明](docs/architecture.md)
- [原生获取层指南](docs/native-acquisition-guide.md)
- [Acquisition Bundle v2](docs/acquisition-bundle-protocol.md)
- [验证说明](docs/validation.md)
- [故障排查](TROUBLESHOOTING.md)
- [发布说明](RELEASE_NOTES.md)
- [变更记录](CHANGELOG.md)

[offline-validation-badge]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml/badge.svg
[offline-validation]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml
