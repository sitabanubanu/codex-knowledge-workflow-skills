# Knowledge Workflow Skills

[![offline-validation][offline-validation-badge]][offline-validation]

> 从“我想学什么”出发，先搜索并选对材料，再采集一手内容，最后在证据约束下分析、学习和写作。

当前可用版本：`v0.7.1`。

项目已经移除 Agent Reach 运行时依赖；OpenCLI 仅是一个可选的浏览器采集适配器，不是总控台，也不是整条工作流的单点依赖。

## 这个项目解决什么问题

普通 Agent 很容易把“搜到了页面”误认为“拿到了内容”，再把标题、摘要、metadata、评论、截图或帖子正文扩写成一份貌似完整的报告。本项目把知识获取拆成三个互不越权的层面：

1. **搜索层**：理解需求、组织查询、比较来源，只负责决定“应该采集什么”。
2. **采集层**：通过可用 Provider 或授权导入取得材料，只负责回答“实际拿到了什么”。
3. **分析层**：检查目标、范围、完整度和来源哈希，只使用通过门控的证据生成学习文章或正式文档。

它重点防止以下问题：

- 搜索结果、网页摘要或 metadata 被当成一手材料；
- X 帖子正文被当成帖子内视频的字幕；
- 视频还没取得字幕或完成 ASR，就直接生成“视频分析”；
- 材料残缺、来源错配或采集失败，却仍然输出完整报告；
- 旧任务产物污染新任务，来源变化后继续使用旧证据；
- 来源事实、模型推断和外部补充混在一起；
- 结论无法定位到来源片段、时间戳、文件哈希和运行批次。

项目宁可返回 `blocked`、`secondary_only`、`pending_derivation` 或降级说明，也不会把缺失材料补写成来源结论。

## 三层工作流

### 第一层：搜索与意图澄清

公开入口：`web-intent-scout`

这一层把宽泛需求变成：

- 明确的搜索意图和排除项；
- 多组查询词，而不是只搜一句话；
- 候选来源台账；
- 来源类型、时效、偏差、风险和可信度检查；
- 值得进入采集层的主材料 URL 或文件。

搜索层产出的摘要、搜索片段和推荐理由只用于**选材**，不能直接成为最终文章的事实证据。若用户已经给出明确 URL 或本地材料，可以跳过这一层。

### 第二层：材料采集

公开入口：`acquire-source-material`

总控入口：`knowledge-workflow-console`

这一层根据 `platform + target + operation + 当前环境` 规划路线，通过本项目自有的 Provider Registry 获取或导入材料，并统一写成 **Acquisition Bundle v2**。

可用路线包括：

- 本地 transcript、字幕、音频和视频；
- 普通网页的 `curl` / Jina Reader；
- YouTube、X 内嵌视频的 `yt-dlp` 字幕、媒体与后续 ASR；
- Bilibili detail / audio；
- GitHub CLI 和临时仓库读取；
- X 帖子文本 Provider；
- Exa 搜索；
- 可选 OpenCLI 浏览器可见内容路线；
- 用户有权使用的浏览器、CLI、API 或平台导出文件。

采集层不判断“这个观点对不对”，也不写报告。它只记录：

- 尝试过哪些 Provider；
- 哪条路线成功或失败；
- 得到的是正文、帖子文本、字幕、媒体、metadata 还是搜索结果；
- 文件大小、SHA-256、来源 URL、浏览器宿主和授权会话声明；
- 当前材料是否完整或部分。

### 第三层：证据分析与学习交付

门控入口：`source-gated-evidence-layer`

学习入口：`knowledge-learning-article`

文档入口：`knowledge-document-composer`

这一层先检查：

- 当前材料是否对应用户真正要求分析的对象；
- `content_scope` 是否足以支持 `analysis_target`；
- Bundle、文件字节数和 SHA-256 是否仍然一致；
- 视频是否已有可验证字幕，或是否仍在等待本地 ASR；
- claims、evidence map 和 provenance receipts 是否完整。

通过后才会生成：

- 知识地图和概念关系；
- 前置知识与学习顺序；
- 论证结构、可迁移方法和复习问题；
- 证据锚定的学习文章；
- 忠于来源的报告、提纲、 briefing 或研究笔记。

`knowledge-video-decomposer` 只作为内部兼容脚本库继续被调用，不是新的普通用户入口。`browser-host-identity` 是独立项目；本仓库只遵守它定义的 Edge/Chrome 宿主安全契约。

```text
学习需求
  │
  ├─ 已有明确 URL / 文件 ───────────────────────┐
  │                                             │
  └─ Web Intent Scout：搜索、比较、选材           │
                                                ▼
  Acquire Source Material：Provider 路由 / 授权导入
                                                │
                                                ▼
                                  Acquisition Bundle v2
                                                │
                                                ▼
  Source Gate：目标、范围、完整度、哈希、ASR、证据审计
                                                │
                            ┌───────────────────┴───────────────────┐
                            ▼                                       ▼
                  Learning Article                    Source-faithful Document
                            └───────────────────┬───────────────────┘
                                                ▼
                              receipts + quality gate + result_index.md
```

三层之间通过文件化契约交接。上一层“运行成功”不代表下一层自动放行：搜索成功不等于采集成功，采集成功也不等于材料足以生成完整报告。

## 与普通 Agent、Agent Reach 的差异

| 维度 | 普通 Agent 对话 | Agent Reach | 本项目 v0.7.1 |
| --- | --- | --- | --- |
| 主要目标 | 快速回答或总结 | 让 Agent 调用多个平台工具 | 把学习需求变成可复核的知识产品 |
| 搜索 | 常混在回答过程中 | 取决于上游工具 | 独立的意图、查询、来源台账和风险检查 |
| 采集 | 页面可见信息常直接进入回答 | 统一路由平台命令 | 自有 Provider Registry、Route Plan、Bundle Writer |
| 层间契约 | 通常没有 | 以工具返回为主 | 强制 Acquisition Bundle v2 |
| 目标与范围 | 容易混淆帖子、视频和评论 | 不负责下游证据许可 | Source Gate 精确判断材料能支持什么 |
| 视频无字幕 | 可能依据简介总结 | 取决于平台工具 | 字幕路线失败后可下载授权媒体并本地 ASR |
| 证据追溯 | 依赖回答中的链接 | 不是核心产品层 | claims、evidence map、SHA-256 和分层 receipts |
| 学习产品 | 通常是一篇总结 | 不负责 | 知识地图、前置关系、学习路径和学习文章 |
| 失败行为 | 可能继续推断 | 返回工具失败 | 阻断、降级、列出缺失条件，禁止伪报告 |
| Agent Reach 依赖 | 无 | 必需 | 不安装、不导入、不执行 Agent Reach |

这不是“所有场景都优于 Agent Reach”的宣称。只想临时执行一个平台命令时，Agent Reach 或单独的 CLI 可能更轻；如果目标是**搜索值得学的材料、取得一手内容、验证证据范围，再形成可复核的学习成果**，本项目覆盖的是更长且更严格的链路。

## OpenCLI：真实状态、作用和限制

OpenCLI 在本项目中只是**可选浏览器采集适配器**，用于读取已经由用户授权、且能在真实浏览器页面中看到的内容。它不是 Agent Reach，也不控制搜索层、Source Gate、ASR 或学习写作。

本次 `v0.7.1` 发布前，维护环境中的 `opencli doctor` 显示 daemon、扩展和连接均正常。此前出现过的具体故障是扩展目录缺失/断连；那会使 OpenCLI 路线无法执行，但不代表整条 Knowledge Workflow 或 OpenCLI 的所有核心能力永久损坏。

需要特别区分：

- **OpenCLI connected**：只证明 daemon 与某个浏览器扩展建立了连接；
- **浏览器宿主已确认**：需要用户明确提供 `--browser-host edge` 或 `--browser-host chrome`；
- **页面可读取**：还要求真实登录、权限、页面状态和目标内容都满足条件；
- **目标材料已取得**：页面正文、帖子 caption、metadata 和视频 transcript 是不同材料范围。

`opencli doctor` 不会可靠证明连接的是 Edge 还是 Chrome，因此项目不会从插件名称、默认浏览器或上次任务猜测宿主，也不会在失败后静默切换浏览器。

以下任一条件不满足，对应的 OpenCLI 路线就会停止：

1. OpenCLI daemon 未运行；
2. 扩展未安装、未重新加载或已经断连；
3. 没有显式声明真实 `--browser-host`，或声明与实际宿主不一致；
4. 当前浏览器没有所需登录状态、账号权限或地区访问能力；
5. 页面只显示 metadata、caption 或播放器外壳，没有目标正文/字幕；
6. 页面要求 CAPTCHA、付费、私密访问或额外人工确认；
7. 前台标签页、站点 session 生命周期或页面加载状态不满足 Provider 要求。

即使 OpenCLI 不可用，本地文件、公开网页、GitHub、公开 `yt-dlp`、授权媒体导入和本地 ASR 仍可独立运行。项目只阻断受影响的浏览器路线，不会把一个可选 Provider 的故障伪装成整个工作流失效。

另一个容易混淆的问题是 `yt-dlp --cookies-from-browser` 的 cookie 数据库锁：它与 OpenCLI 扩展连接是两套机制。浏览器正在使用 cookie 数据库时，yt-dlp 可能读取失败。项目不会擅自关闭用户浏览器；可以改用用户导出的 Netscape `cookies.txt`，或者在公开内容允许时使用不带登录态的路线。

## 最容易漏掉、漏掉就无法继续的条件

### 1. 必须说明“分析什么对象”

同一个 URL 可能包含多个对象，URL 本身不等于目标。

| 用户真正要的内容 | `--target` | `--operation` | 足以放行的主材料 |
| --- | --- | --- | --- |
| 网页正文 | `web_article` | `read` | `article_body` |
| X/小红书帖子文字 | `social_post` | `read` | `social_post_text` |
| YouTube/Bilibili/X 内嵌视频 | `video_content` | `extract_transcript` | `video_transcript`，或可交给 ASR 的媒体 |
| GitHub 仓库内容 | `repository` | `read` | `repository_document` |
| 只做候选资料搜索 | `search_triage` | `search` | `search_result`，但只能用于选材 |

例如，对 X URL 使用 `--target social_post --operation read`，得到的是帖子文字；这不会自动解锁内嵌视频分析。要分析视频，必须改成 `--target video_content --operation extract_transcript`。

### 2. 必须提供一手材料，而不是“相关信息”

以下内容不能替代目标主材料：

- 搜索结果不能替代网页正文；
- 标题、简介和 metadata 不能替代视频 transcript；
- 帖子正文不能替代帖子内嵌视频；
- 评论、截图和二手转述不能替代原文；
- 播放器存在不能证明字幕存在；
- 音视频文件本身还不是文字证据，它首先是 `pending_derivation`。

没有字幕的视频只有在授权媒体成功取得、ASR 环境可用并生成通过校验的 transcript 后，才会变成 `source_confirmed`。

### 3. 浏览器路线必须声明真实宿主

凡是使用 OpenCLI 或浏览器导出，都必须明确：

```powershell
--browser-host edge
```

或：

```powershell
--browser-host chrome
```

yt-dlp 读取 YouTube 浏览器 cookies 时使用 `--youtube-browser`。如同时使用 OpenCLI 和 yt-dlp 浏览器 cookies，两个参数必须指向同一个真实宿主：

```powershell
--browser-host edge --youtube-browser edge
```

不要根据“扩展装在哪里”或“平常用哪个浏览器”猜测。

### 4. 登录和权限必须真实存在

私密帖子、年龄限制、地区限制、账号可见内容或需要登录的平台，必须由用户在所声明的真实浏览器中完成授权。项目不会：

- 绕过 CAPTCHA、付费墙或平台权限；
- 把另一个浏览器的 cookie 当作当前宿主；
- 在授权路线失败后静默退回匿名抓取私密内容；
- 把 cookie、token、visitor data 或 PO token 写进报告。

### 5. 搜索层不会自动成为证据层

`web-intent-scout` 找到候选页面后，还必须把选中的原始 URL 或文件交给采集层。只保存搜索摘要、搜索结果页或 Agent 的推荐文字，分析层会正确返回 `secondary_only`。

### 6. 学习文章可能需要一次 Agent 语义补全

`brief` 深度可以走完全确定性的基础路线。`standard` / `deep` 若发现概念、前置关系或论证图仍不完整，总控台会写出：

```text
15_learning/learning_enrichment_request.json
```

这不是采集失败。它表示程序已经完成来源验证，但需要 Agent **仅依据已验收材料**生成 `learning_enrichment.json`。未提供该文件时，系统不会用启发式模板假装完成深度学习文章。

### 7. `--resume` 只能续跑同一个任务身份

同一个 `project-root` 不能混用不同的来源、目标或操作。`--resume` 只用于继续同一 `source_url + target + operation`。如果从“读 X 帖子”改为“分析 X 内嵌视频”，应使用新的项目目录。

手工修改 transcript 或替换来源文件会使旧 receipt 失效；应重新 ingest、audit 和 compose，不能沿用旧报告。

## 推荐使用顺序

### 1. 先检查当前机器实际具备什么能力

```powershell
kw doctor
kw source doctor
kw source matrix
kw source plan --input <URL或查询> --target <目标> --operation <操作>
```

`Provider ready` 只代表命令和环境初步可用，不代表任意 URL、登录态或目标范围一定成功。

### 2. 本地 transcript、字幕、音频或视频

```powershell
kw run `
  --input <本地文件> `
  --target video_content `
  --operation extract_transcript `
  --mode audit `
  --deliverable learning_article `
  --final-language zh-CN
```

音频/视频需要 `ffmpeg`、`ffprobe` 和可导入的 `faster-whisper`。先运行 `kw doctor` 查看。

### 3. 普通网页或 GitHub 仓库

```powershell
kw run `
  --input <URL> `
  --target web_article `
  --operation read `
  --mode audit `
  --deliverable both `
  --final-language zh-CN
```

GitHub 仓库把 `--target` 改成 `repository`。

### 4. YouTube 视频

公开字幕或公开媒体路线：

```powershell
kw run `
  --input <YouTube URL> `
  --target video_content `
  --operation extract_transcript `
  --platform-mode auto `
  --mode audit `
  --deliverable learning_article `
  --final-language zh-CN
```

需要已授权 Edge 会话时：

```powershell
kw run `
  --input <YouTube URL> `
  --target video_content `
  --operation extract_transcript `
  --platform-mode auto `
  --browser-host edge `
  --youtube-browser edge `
  --mode audit `
  --deliverable learning_article
```

如果页面本身没有字幕，OpenCLI 无法凭空生成字幕。采集层必须取得授权媒体，随后由本地 ASR 派生 transcript。

### 5. X 帖子文字与内嵌视频

只读帖子文字：

```powershell
kw run --input <X URL> --target social_post --operation read --mode audit
```

分析帖子内嵌视频：

```powershell
kw run `
  --input <X URL> `
  --target video_content `
  --operation extract_transcript `
  --platform-mode auto `
  --mode audit `
  --deliverable learning_article
```

两条命令的目标、Provider 路线和可接受材料范围不同，不能互相替代。

### 6. 导入用户已经取得的授权材料

```powershell
kw source import `
  --input-file .\exports\primary.txt `
  --source-url <原始URL> `
  --platform x `
  --content-scope video_transcript `
  --target video_content `
  --operation extract_transcript `
  --browser-host edge `
  --credentialed-session `
  --project-root .\outputs\knowledge-workflow\x-video
```

只有材料确实来自浏览器授权会话时才使用 `--credentialed-session`；只有确实知道真实宿主时才写 `--browser-host`。

### 7. 完成学习层接力

当总控台请求语义补全后，让 Agent 读取已验收的分析包与 enrichment request，生成证据锚定的 JSON，再执行：

```powershell
kw learn `
  --project-root <任务目录> `
  --enrichment <任务目录>\15_learning\learning_enrichment.json `
  --depth standard
```

## 安装与更新

```powershell
git clone https://github.com/sitabanubanu/codex-knowledge-workflow-skills.git
cd codex-knowledge-workflow-skills
python -m pip install -e .
kw version
kw --help
```

安装或更新 Codex Skills：

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

先跑完全离线演示和验证：

```powershell
kw demo
kw validate --include-sync
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
15_learning/learning_enrichment_request.json
15_learning/learning_enrichment.json
20_document/learning_article.md 或 final_report.md
20_document/*_receipt.json
result_index.md
```

只有当前来源、当前运行和当前哈希全部匹配，且质量门允许时，正式交付物才成立。

常见状态含义：

| 状态 | 含义 | 下一步 |
| --- | --- | --- |
| `source_confirmed` | 目标主材料已确认 | 可进入审计与交付 |
| `pending_derivation` | 已有媒体，等待 ASR 派生 transcript | 完成 ASR 后重新建 Gate |
| `secondary_only` | 只有搜索结果或二手材料 | 采集原始正文/字幕 |
| `target_mismatch` | 材料存在，但不是用户要求分析的对象 | 改目标或重新采集 |
| `source_blocked` | 权限、环境或 Provider 阻断 | 按 route plan 修复或授权导入 |
| `source_failed` | 采集未得到可验证材料 | 更换合法路线或提供本地材料 |

## 能力边界与非目标

- 不承诺每个 URL 都能获取；平台页面、登录、反自动化、地区和账号权限会变化；
- 不绕过 CAPTCHA、付费墙、私密访问或平台权限；
- 不把搜索摘要、metadata、评论、截图或 caption 冒充目标正文/字幕；
- 不在浏览器宿主未知时猜 Edge/Chrome；
- 不因一个 Provider 失败而删掉安全门或伪造完整报告；
- 不把当前离线回归结果宣传成已经证明优于普通 Agent 的大规模 A/B 实验；
- Python wheel 只包含 CLI 模块，完整产品还需要仓库中的 Skills、参考资料和内部脚本。

## 发布与验证

```powershell
python -m build --sdist
kw validate --include-sync
git archive --format=zip --output=dist\codex-knowledge-workflow-skills-v0.7.1-source.zip HEAD
```

源码包不应包含 cookies、token、浏览器数据、私密 transcript、媒体、`outputs/`、`test_outputs/` 或本机缓存。

## 进一步文档

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
