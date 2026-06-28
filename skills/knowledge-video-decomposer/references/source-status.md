# Source Status Gate

本文件定义 `knowledge-video-decomposer` 的来源获取状态机。后续 agent 必须先判定来源状态，再决定是否允许进入完整 `video_analysis_pack`。

## 状态枚举

`source_status` 只能使用以下机器可执行枚举值：

- `source_confirmed`
- `source_partial`
- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`

禁止新增临时状态来绕过门禁。需要补充细节时，写入 `status_reason`、`source_classes`、`failed_probes`、`next_step` 或 acquisition notes。

## 硬门禁

- 只有 `source_confirmed` 可以直接进入完整 `video_analysis_pack`。
- `source_partial` 只有在材料范围、缺口、时间段、来源类型和置信度被明确标注时，才可以进入标注 partial 的 `video_analysis_pack`；禁止呈现为完整视频分析。
- `secondary_only` 不能伪装成完整视频分析，不能写 speaker logic reconstruction。
- `degraded_report_only` 只能生成降级说明或来源获取报告，不能生成完整视频分析包。
- `source_blocked` 和 `source_failed` 必须停止完整分解，或请求用户提供本地文件、transcript、audio、授权页面访问，或明确允许本地方案。
- 没有一手 transcript/audio/browser-visible transcript 时，document composer 只能写“基于可见页面/二手资料的降级说明”，禁止写 speaker logic reconstruction、完整 argument flow 或完整 source logic。

## 来源类别

允许作为完整分解依据的一手来源：

- `primary_transcript`: 官方字幕、平台 transcript、用户提供 transcript、可靠字幕文件。
- `primary_audio_asr`: 从用户提供或合法取得的音视频文件转写出的 ASR transcript。
- `browser_visible_transcript`: Chrome 页面中用户可见、可复制、可引用的 transcript 或字幕文本。

只能作为背景或降级材料的二手/辅助来源：

- `platform_metadata`: 标题、频道、发布时间、简介、章节、页面可见 metadata。
- `secondary_summary`: Podwise、网页摘要、课程页摘要、第三方笔记。
- `search_snippet`: 搜索结果片段。
- `firecrawl_context`: Firecrawl 抓取的网页正文、描述、公开页面上下文。
- `page_observation`: Chrome 看到的页面状态、按钮、提示、权限状态、截图性事实。

Firecrawl、网页搜索、Podwise、第三方摘要和普通页面描述只能补充背景、识别视频、建立 source ledger 或生成降级报告；它们不能替代一手 transcript/audio，不能解锁完整 decomposition。

## 状态定义

### `source_confirmed`

进入条件：

- 已取得完整或足够完整的一手 transcript/audio-derived transcript。
- transcript 有可追溯来源：平台字幕、用户文件、Chrome 可见 transcript、合法本地音视频 ASR 或用户提供材料。
- 能为主要 claims、examples、concepts、logic 提供 timestamp、transcript ID 或 source span。
- acquisition notes 记录了工具、来源、语言、置信度和主要失败分支。

允许输出：

- 完整 `video_analysis_pack`。
- `01_transcript`、`02_segments`、`03_inventory`、`04_logic`、`05_gap_check` 等标准 artifacts。
- source-faithful speaker logic reconstruction。

禁止输出：

- 禁止把二手摘要写成一手 transcript。
- 禁止隐藏 transcript 缺口或把低质量 ASR 称为 complete/verbatim。

下一步：

- 进入 segmentation、inventory、logic reconstruction、gap check 和完整 pack。

### `source_partial`

进入条件：

- 已取得一手来源，但存在明确缺口，例如只覆盖部分时间段、字幕语言不完整、ASR 质量偏低、timestamps 缺失、片段缺页或 transcript 被截断。
- 缺口范围可描述，并且剩余材料仍足以支持有限的视频内容分解。
- acquisition notes 明确标注 partial 原因、覆盖范围、不能支持的分析范围。

允许输出：

- 标注 partial 的 `video_analysis_pack`。
- 有 evidence span 的局部 segmentation、inventory、logic notes。
- 明确写出“仅覆盖已取得 transcript/audio 范围”的 source logic summary。

禁止输出：

- 禁止写成完整视频全量分析。
- 禁止补写缺失段落的 speaker logic。
- 禁止用 Firecrawl、Podwise、搜索结果填补缺失 transcript 后仍称为 source-faithful。

下一步：

- 优先请求用户提供缺失 transcript/audio 或允许本地 ASR。
- 若用户接受 partial，继续有限 decomposition，并在每个下游 artifact 标注 partial。

### `secondary_only`

进入条件：

- 没有取得一手 transcript/audio/browser-visible transcript。
- 仅有 Firecrawl、网页搜索、Podwise、页面简介、标题、章节、show notes、搜索片段、评论、第三方摘要或平台 metadata。
- 这些材料可以识别视频主题或背景，但不能逐句追溯 speaker 表达。

允许输出：

- `acquisition_failure_report.md`。
- `degraded_source_notes.md`。
- 基于二手资料的背景说明、来源 ledger、可见页面摘要、下一步建议。

禁止输出：

- 禁止生成完整 `video_analysis_pack`。
- 禁止写 `04_logic/source_logic.md` 形式的 speaker logic reconstruction。
- 禁止断言 speaker 的完整论证链、概念定义、例子作用或措辞。
- 禁止把二手摘要标注为 transcript、primary source 或 source-confirmed evidence。

下一步：

- 请求用户提供 transcript、本地音视频文件、授权页面访问，或允许本地 ASR/Chrome 检查。
- 如果用户只需要降级报告，转为 `degraded_report_only`。

### `source_blocked`

进入条件：

- 平台或页面明确阻断一手来源获取：HTTP 429、bot check、CAPTCHA、login required、paywall、permission required、private video、region block、age restriction、课程权限或账号权限。
- Chrome route 也无法取得可见一手 transcript，或停止条件被触发。
- 继续获取会要求绕过访问控制、传 cookie、绕验证码、批量抓受限内容或违反用户授权边界。

允许输出：

- 阻断说明。
- 已观察到的页面状态记录。
- 请求用户提供文件、transcript、audio、授权访问或替代来源。
- 明确的失败路径和下一步选项。

禁止输出：

- 禁止继续重复同一个 blocked extractor。
- 禁止切到 Firecrawl/搜索后把二手资料写成完整分析。
- 禁止要求 cookie 给 `yt-dlp` 或尝试绕过 CAPTCHA/付费墙。

下一步：

- 停止完整 decomposition。
- 请求用户提供一手材料或明确授权的本地文件路径。
- 如用户允许只做降级说明，则转为 `degraded_report_only`。

### `source_failed`

进入条件：

- 没有外部权限阻断，但工具链失败导致无法取得一手 transcript/audio：文件损坏、格式不支持、本地 ASR 失败、Hearsay 失败、模型加载失败、下载失败、解析失败、超出时间预算。
- 已按 acquisition probe 成本限制尝试允许路径，但没有得到可用一手材料。

允许输出：

- 工具失败报告。
- acquisition notes、failed probes、可复现错误摘要。
- 请求用户提供替代文件、较短片段、已有 transcript 或允许更长本地运行。

禁止输出：

- 禁止根据 metadata 或搜索摘要继续写完整视频分析。
- 禁止无界重试同一工具。
- 禁止把“工具失败”写成“内容已分析完成”。

下一步：

- 停止完整 decomposition。
- 给出最小下一步：用户提供 transcript/audio、本地文件，或批准更长 ASR/替代工具。

### `degraded_report_only`

进入条件：

- 用户接受没有一手 transcript/audio 的降级说明，或当前任务目标只是说明来源获取失败、页面状态、背景资料和后续方案。
- 上游状态通常来自 `secondary_only`、`source_blocked` 或 `source_failed`。

允许输出：

- 降级报告。
- 来源获取失败说明。
- 基于可见页面/二手资料的背景摘要，且每段明确标注材料来源。
- 后续 acquisition 建议。

禁止输出：

- 禁止输出完整 `video_analysis_pack`。
- 禁止写 speaker logic reconstruction。
- 禁止使用“完整分解”“完整分析”“source-confirmed”等措辞。
- 禁止把二手资料与一手 transcript 混写为同一证据层级。

下一步：

- 结束降级流程，或等待用户提供一手材料后重新进入 acquisition。

## Acquisition Probe 成本限制

每个来源 acquisition probe 必须有最大时间、重试次数、切换路径和失败记录。后续 agent 不得无限等待 Hearsay、反复运行 `yt-dlp`，或在同一阻断信号上循环。

默认上限：

- 平台 metadata/caption 快速检查：每个工具最多 1 次正常尝试，最多 1 次参数修正重试；总时长目标不超过 2 分钟。
- `yt-dlp`：遇到 HTTP 429、bot confirmation、CAPTCHA、login required、RequestBlocked 后立即停止该 extractor，切换 Chrome route；不得反复重试同一 URL。
- `youtube_transcript_api`：遇到 blocked、TooManyRequests、TranscriptsDisabled、login/consent/region/bot 相关失败后最多记录 1 次，不再循环。
- Chrome route：按 `chrome-routing.md` 执行一次页面状态检查；页面打不开、无可见 transcript 或触发验证码/付费/权限后停止。
- Hearsay URL ingestion：平台 URL metadata fetch 超时后最多记录 1 次；如果已经有平台阻断信号，不再重复 Hearsay URL ingestion。
- 本地 ASR：根据 `transcription-fallback.md` 选择模型和 timeout；超时后只允许按用户目标降级模型或请求更长运行时间，不得静默无限等待。
- Firecrawl/网页搜索/Podwise：只作为 secondary/context probe；成功也不能改变 `secondary_only` 为 `source_confirmed`。

每个 probe 失败必须记录：

```json
{
  "probe": "yt-dlp|youtube_transcript_api|Chrome|Hearsay|local_asr|Firecrawl|search|Podwise|other",
  "source_class_attempted": "primary_transcript|primary_audio_asr|browser_visible_transcript|platform_metadata|secondary_summary|search_snippet|firecrawl_context",
  "max_time_seconds": 0,
  "attempts": 0,
  "result": "success|partial|blocked|failed|timeout|skipped",
  "failure_reason": "",
  "next_route": ""
}
```

## 状态记录模板

每次 acquisition 决策必须写出机器可读摘要，至少包含：

```json
{
  "source_status": "source_confirmed|source_partial|secondary_only|source_blocked|source_failed|degraded_report_only",
  "can_enter_full_decomposition": false,
  "can_enter_document_composer": false,
  "allowed_report_type": "full_video_analysis_pack|partial_video_analysis_pack|acquisition_failure_report|degraded_source_report",
  "source_classes": [],
  "primary_material_available": false,
  "status_reason": "",
  "failed_probes": [],
  "next_step": ""
}
```

`can_enter_full_decomposition` 规则：

- `source_confirmed`: `true`
- `source_partial`: 只有在 partial 范围足够标注且用户目标允许时为 `true`
- `secondary_only`: `false`
- `source_blocked`: `false`
- `source_failed`: `false`
- `degraded_report_only`: `false`

`can_enter_document_composer` 规则：

- 完整报告：只允许 `source_confirmed`。`source_partial` 只能进入清楚标注范围和缺口的 partial 文档，不能写成完整报告。
- 降级说明：允许 `secondary_only`、`source_blocked`、`source_failed`、`degraded_report_only`。
- 没有一手 transcript/audio 时，document composer 的 `allowed_report_type` 必须是 `degraded_source_report` 或 `acquisition_failure_report`。

## 文档写作门禁

交给 `knowledge-document-composer` 前必须执行以下判断：

1. 如果 `source_status` 是 `source_confirmed`，允许写完整 source-faithful 文档。
2. 如果 `source_status` 是足够标注的 `source_partial`，只能写 partial 文档，必须保留缺口和范围说明。
3. 如果 `source_status` 是 `secondary_only`、`source_blocked`、`source_failed` 或 `degraded_report_only`，只能写“基于可见页面/二手资料的降级说明”。
4. 没有一手 transcript/audio/browser-visible transcript 时，禁止写 speaker logic reconstruction、完整 argument graph、完整 claims inventory 或完整 source logic。
5. 降级报告必须在标题、摘要和来源说明中标注 degraded，不得使用完整分析包的外观混淆状态。

任何 agent 如果无法确定当前状态，必须选择更保守的状态，并请求用户提供一手材料或允许下一步 acquisition；不得默认进入完整分解。
