# Knowledge Workflow Skills

[![offline-validation][offline-validation-badge]][offline-validation]

> 用 Agent-Reach 拿材料，用证据门控判断材料能不能分析，再生成可追溯、可审计的知识报告。

## 这是什么

Knowledge Workflow Skills 是一套接在 Agent-Reach 后面的可信知识生产工作流。它不是
“输入一个 URL 就编一份报告”的爬虫，也不是把搜索摘要直接当成事实的写作模板。

它把一次研究任务拆成四个可检查的阶段：

```text
获取材料 Agent-Reach
    -> Acquisition Bundle v2
    -> 目标 / 范围 Source Gate
    -> Claims 与 Evidence Audit
    -> 带 provenance 的正式报告
```

当前版本：`v0.6.0`。

## 我们解决哪些问题

很多“网页总结”工具真正难的不是把文字写出来，而是判断这段文字是否有资格被写进报告。本项目专门解决这些问题：

1. **搜索摘要被误当成一手材料**：snippet、metadata、截图或页面外壳不能自动通过 Source Gate。
2. **拿到的内容与分析目标不匹配**：帖子正文不能冒充帖子中的视频字幕；搜索结果不能冒充完整文章。
3. **旧报告污染新任务**：每次运行都有 `run_id`、`attempt_id`、来源指纹和 provenance receipt，旧产物不能因为“文件还在”就被当成新结果。
4. **材料不完整却生成完整结论**：来源被阻断、只有部分内容或只有二手材料时，系统会输出 `blocked` / `degraded` 状态和下一步，而不是伪造完整报告。
5. **结论无法回溯**：系统保存 acquisition manifest、artifact 哈希、claims、logic graph、evidence audit、claim map 和 quality gate。
6. **浏览器登录态混淆**：明确区分真实的 Edge 与 Chrome；浏览器宿主不明时，路线会阻断而不是猜测。
7. **外部工具污染当前 Python 环境**：Agent-Reach 由项目管理在独立的 `github-tools` runtime 中，不安装到 Hermes 或任意启动本项目的私有环境。
8. **事实、推断和补充混在一起**：正式写作强制区分 `Source`、`Inference`、`Extension`。

## 和 Agent-Reach 是什么关系

Agent-Reach 和本项目不是两个互相替代的爬虫。Agent-Reach 负责“尽可能拿到被授权访问的材料”，本项目负责“判断材料是否足够可信，并把它变成可交付的知识产品”。

| 维度 | Agent-Reach | Knowledge Workflow Skills |
| --- | --- | --- |
| 核心定位 | 多平台获取与路由工具 | 基于获取结果的证据门控知识工作流 |
| 主要输出 | 原始文本、字幕、媒体、诊断结果 | Acquisition Bundle、source gate、claims、审计报告、最终报告 |
| 可信判断 | 告诉你能否调用某个后端 | 判断拿到的内容是否覆盖本次目标、是否能支持结论 |
| 追溯能力 | 记录获取过程 | 记录 run、attempt、哈希、证据链和各级 receipt |
| 失败处理 | 返回获取失败或后端不可用 | 明确 blocked / degraded，并禁止伪造完整报告 |
| 浏览器边界 | 提供浏览器相关获取路线 | 强制区分 Edge/Chrome，拒绝猜测登录宿主 |
| 写作能力 | 不负责正式研究报告 | 生成 claim map、quality gate 和 Source/Inference/Extension 报告 |
| 运行环境 | 上游工具本身 | 统一管理独立 runtime，避免污染当前 agent 环境 |

### 为什么不直接使用原版 Agent-Reach

如果你的需求只是“调用某个平台、拿到原始文本或字幕”，直接使用 Agent-Reach 更简单，也更合适。

如果你的需求是“研究一个主题、判断材料是否足够、给出能被别人复核的报告”，选择本项目，因为它补上了 Agent-Reach 不负责的部分：

- 不把“命令成功”当成“证据充分”；
- 不把搜索摘要升级成一手来源；
- 不让不匹配的目标和范围通过分析；
- 不让旧文件、失败材料或局部内容伪装成完整结果；
- 不把事实、推断和扩展混成没有边界的一段话。

本项目仍然使用 Agent-Reach 的上游能力，不复制它不断变化的平台命令；你得到的是“Agent-Reach 的获取能力 + 本项目的证据与交付约束”。

## 四个用户入口

- `knowledge-workflow-console`：总控台，负责理解任务、选择目标/操作/模式、运行阶段并写结果索引。
- `agent-reach-console`：负责 doctor、能力矩阵、路由、获取和 `00_acquisition`。
- `source-gated-evidence-layer`：负责 Bundle 校验、source gate、分段、claims、logic graph、evidence audit 和降级结果。
- `knowledge-document-composer`：只从通过审查的材料生成大纲、claim map、质量门和最终报告。

`browser-host-identity` 是横切安全守卫，负责区分 Edge、Chrome、OpenCLI、cookies 和浏览器导出，不是第五个工作流阶段。

原来的 `knowledge-video-decomposer` 保留为内部兼容库，不再作为新用户的主入口。

## 三分钟开始

### 安装本地包

```powershell
python -m pip install .
kw --help
```

### 先跑离线演示

```powershell
python .\kw.py demo
```

打开：

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

### 分析本地 transcript

```powershell
python .\kw.py run `
  --input .\examples\demo_transcript\input.txt `
  --target video_content `
  --operation extract_transcript `
  --mode audit `
  --final-language zh-CN
```

### 分阶段诊断

```powershell
python .\kw.py acquire --input <URL或查询> --target <目标> --operation <操作> --project-root <项目目录>
python .\kw.py ingest --bundle <项目目录>\00_acquisition\manifest.json --project-root <项目目录>
python .\kw.py audit --project-root <项目目录>
python .\kw.py compose --project-root <项目目录>
python .\kw.py status --project-root <项目目录> --pretty
python .\kw.py result --project-root <项目目录> --pretty
```

## Agent-Reach runtime 与授权边界

项目不会把 Agent-Reach 安装到当前运行 CLI 的 Python、Hermes 或项目源码目录，而是使用共享目录：

```text
C:\Users\Socrates\github-tools\
  sources\Agent-Reach
  runtimes\agent-reach\venv
  bin\agent-reach.cmd
  manifests\agent-reach.json
```

```powershell
python .\kw.py agent-reach install --safe
agent-reach --version
python .\kw.py agent-reach doctor
python .\kw.py agent-reach matrix
```

配置和授权浏览器连接仍在 `C:\Users\Socrates\.agent-reach`。项目不会读取、显示、复制或提交 cookies、token、Authorization header、浏览器 profile 或私密登录状态。

## Source Gate 的交付规则

只有 `source_confirmed` 和 `source_partial` 可以进入正常或部分分析。以下状态会阻止正常最终报告：

```text
secondary_only
source_blocked
source_failed
degraded_report_only
metadata_only / blocked / failed / unsupported bundle
```

每次任务的统一入口是 `result_index.md`，它会告诉你：材料是否拿到、source gate 是否通过、分析是否完成、报告是否允许交付，以及关键产物在哪里。

典型项目目录：

```text
00_acquisition/manifest.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
10_video/source_analysis_pack.md
20_document/claim_map.json
20_document/quality_gate.json
20_document/final_report.md
result_index.md
```

## 我们明确不做什么

本项目不会绕过 CAPTCHA、付费墙、地区限制、账号权限或私密内容；也不会承诺任何平台永远可获取。平台反自动化、登录态、区域和账号权限仍由 Agent-Reach 的实际后端决定。获取失败时，系统会保留失败证据并降级，不会编造内容。

## 发布包与验证

源码发布包不包含 `outputs/`、`test_outputs/`、cookies、浏览器数据、私密 transcript 或媒体。维护者可以用以下命令重新生成包：

```powershell
python -m build
git archive --format=zip --output=dist\codex-knowledge-workflow-skills-v0.6.0-source.zip HEAD
```

离线验证：

```powershell
python -m py_compile kw.py kw_cli/*.py
python .\tests\knowledge_workflow_regression.py
python .\tests\real_workflow_acceptance.py
```

## 文档

- [中文用户手册](README.zh-CN.md)
- [安装说明](INSTALL.md)
- [用户手册](USER_MANUAL.md)
- [架构说明](docs/architecture.md)
- [Acquisition Bundle v2 协议](docs/acquisition-bundle-protocol.md)
- [Agent-Reach 集成指南](docs/agent-reach-integration-guide.md)
- [平台支持矩阵](SUPPORTED_PLATFORMS.md)
- [故障排查](TROUBLESHOOTING.md)
- [发布说明](RELEASE_NOTES.md)
- [变更记录](CHANGELOG.md)

[offline-validation-badge]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml/badge.svg
[offline-validation]: https://github.com/sitabanubanu/codex-knowledge-workflow-skills/actions/workflows/offline-validation.yml
