# Knowledge Workflow Skills 中文说明

Agent-Reach 负责拿材料。

Knowledge Workflow 负责判断材料是否属于本次任务、证据是否可靠、报告是否可以交付。

没有符合任务目标的一手材料，就不生成假装完整的报告。

```text
Agent-Reach acquisition
  -> Acquisition Bundle v2
  -> target/scope source gate
  -> evidence audit
  -> provenance-checked report
```

## 当前定位

这是 Agent-Reach 后面的可信知识生产层，不是另一个万能爬虫。

现在对用户暴露四个 skill：

1. `knowledge-workflow-console`：总控台，负责路由、preflight、阶段执行、状态和结果索引。
2. `agent-reach-console`：只负责 doctor、能力规划、获取材料和写 acquisition bundle。
3. `source-gated-evidence-layer`：只负责 bundle 校验、source gate、claim、证据审计和降级输出。
4. `knowledge-document-composer`：只从通过 gate 的材料生成 claim map、quality gate 和 Source / Inference / Extension 分层报告。

另有横切的 `browser-host-identity` 守卫：所有涉及 Edge、Chrome、OpenCLI、
cookies、扩展或浏览器导出时，都必须区分真实宿主浏览器。它不是第五个工作流阶段，
不负责获取、证据审计或报告生成。

原来的 `knowledge-video-decomposer` 不再作为用户入口。它保留为内部兼容库，继续提供 transcript normalizer、ASR、segmenter、inventory、logic、evidence audit 和 pack builder。旧平台获取脚本仍在，但不再是主路线。

## v0.6 的根本变化

Acquisition Bundle v2 新增：

- `run_id`、`attempt_id`、`bundle_id`；
- `analysis_target` 和 `operation`；
- artifact 的 `content_scope`、字节数和 SHA-256；
- attempt staging，校验通过后才晋升为正式 bundle；
- `--resume` 精确匹配和历史归档；
- manifest、preflight、run state、命令日志和错误信息的统一脱敏；
- gate、analysis、composer、final report 四级 provenance receipt。

因此，旧的 transcript、analysis pack、quality gate 或 final report 即使还在磁盘上，只要不属于当前 bundle，就不会被显示为成功，也不能 export 或继续加工。

## 快速开始

先用本地 transcript 验证核心工作流：

```powershell
python .\kw.py demo
```

结果入口：

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

本地文件：

```powershell
python .\kw.py run --input .\examples\demo_transcript\input.txt --mode audit --language en --final-language en
```

普通网页：

```powershell
python .\kw.py agent-reach doctor
python .\kw.py agent-reach matrix
python .\kw.py run --input https://example.com/page --target web_article --operation read --mode audit
```

视频内容：

```powershell
python .\kw.py agent-reach plan --input <视频URL> --target video_content --operation extract_transcript
python .\kw.py run --input <视频URL> --target video_content --operation extract_transcript --mode audit
```

社交帖子正文：

```powershell
python .\kw.py run --input <帖子URL> --target social_post --operation read --mode audit
```

帖子正文与帖子里的视频是两个不同目标。`social_post_text` 可以通过 `social_post` gate，但绝不能代替 `video_transcript` 去通过 `video_content` gate。

## 完整 Agent-Reach 上游能力

项目不复制 Agent-Reach 不断变化的 15 个平台命令，而是直接使用其完整上游能力。
先运行动态矩阵确认当前可用后端；未被 `kw acquire` 结构化适配的 channel，先用
Agent-Reach 原生命令取得一手文本、字幕或媒体，再通过正式导入入口进入 source gate：

```powershell
python .\kw.py agent-reach matrix
python .\kw.py agent-reach import --input-file .\exports\primary.txt --source-url <原始URL> --platform reddit --target social_post --operation read --browser-host edge --credentialed-session --project-root <项目目录>
```

这条导入路径覆盖 Agent-Reach 的全部 channel，但不把搜索摘要、页面壳、截图或原始
metadata 当成一手材料。完整的 channel、部署和交接说明见
[Agent-Reach 集成指南](docs/agent-reach-integration-guide.md)。

## 分阶段命令

```powershell
python .\kw.py acquire --input <URL或查询> --target <目标> --operation <操作> --project-root <项目目录>
python .\kw.py validate-bundle --bundle <项目目录>\00_acquisition\manifest.json
python .\kw.py ingest --bundle <项目目录>\00_acquisition\manifest.json --project-root <项目目录>
python .\kw.py audit --project-root <项目目录>
python .\kw.py compose --project-root <项目目录>
python .\kw.py status --project-root <项目目录>
python .\kw.py result --project-root <项目目录>
```

## 外部工具统一目录

Agent-Reach 不再安装到当前运行 CLI 的 Python 环境，也不属于 Hermes 的私有
虚拟环境。项目统一使用：

```text
C:\Users\Socrates\github-tools\
  sources\Agent-Reach
  runtimes\agent-reach\venv
  bin\agent-reach.cmd
  manifests\agent-reach.json
```

安装或更新独立 runtime：

```powershell
python .\kw.py agent-reach install --safe
agent-reach --version
python .\kw.py agent-reach doctor
```

适配器会拒绝 Hermes 私有路径。Agent-Reach 的配置和授权浏览器连接仍然保留
在独立的 `C:\Users\Socrates\.agent-reach`，不会把 cookies 或 token 复制到
GitHub 工具目录。

同一个项目目录不能被静默复用。只有来源、目标和操作完全一致时，才允许显式加 `--resume`。旧 acquisition 会进入 `acquisition_history/`，旧下游结果会进入 `run_history/`。

## Source Gate

可以进入正常或部分分析：

- `source_confirmed`
- `source_partial`

不能生成正常最终报告：

- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`
- acquisition 的 `metadata_only`、`blocked`、`failed`、`unsupported`

Agent-Reach doctor 中出现 active backend 还不够。只有该后端是 `status: ok`，并且确实支持本次 operation，命令才会执行。例如 B 站搜索 API 可以搜索，但不能抽取视频字幕。

## 浏览器宿主和登录态

Chrome、OpenCLI、cookies 或浏览器 session 只能作为用户已授权的上游获取路线：

- OpenCLI 扩展没有连接时，系统应明确 blocked；
- OpenCLI 使用时必须显式声明实际宿主为 `--browser-host edge` 或
  `--browser-host chrome`；没有宿主身份时，即使 doctor 显示可用也必须 blocked；
- 浏览器可见正文、字幕或媒体必须先导出成 bundle artifact；
- 页面 metadata、截图、搜索 snippet 不能自动升级成 Source；
- 不绕过 CAPTCHA、付费墙、私密内容、地区限制或账号权限。

系统可以记录 `cookies_used: true`，但绝不读取、显示、复制或落盘 cookie 内容、token、Authorization header、visitor data、PO token 或代理密码。

浏览器控制插件叫 Chrome，不代表实际登录态一定来自 Chrome。OpenCLI 的通用
profile ID 也不能证明实际宿主。用户指定 Chrome 时只能使用 Chrome；指定 Edge
时只能使用 Edge，二者不能在失败后互相回退。本机实际使用 Edge 时，YouTube
路线必须显式传 `--youtube-browser edge`；只有实际使用 Chrome 时才传
`--youtube-browser chrome`。两个参数同时出现时必须一致，不能根据插件名称猜浏览器。

浏览器已拿到可引用的本地文件时，用正式的 Bundle v2 交接入口：

```powershell
python .\kw.py browser-import `
  --input-file .\exports\visible-post.txt `
  --source-url <原始URL> `
  --platform x `
  --target social_post `
  --operation read `
  --browser-host edge `
  --project-root .\outputs\browser-post
```

也可以用 `kw run --browser-source-url <原始URL> --browser-platform
<平台>` 直接跑完整流程。`chrome-probe` 仅保留为旧观察记录兼容命令；
它不生成 Bundle v2，也不应作为新主路径。

## 关键文档

- [架构说明](docs/architecture.md)
- [Acquisition Bundle v2 协议](docs/acquisition-bundle-protocol.md)
- [ADR 0003](docs/adr/0003-acquisition-bundle-v2-run-provenance.md)
- [Agent-Reach 集成指南](docs/agent-reach-integration-guide.md)
- [用户手册](USER_MANUAL.md)
- [平台支持矩阵](SUPPORTED_PLATFORMS.md)
- [故障排查](TROUBLESHOOTING.md)
