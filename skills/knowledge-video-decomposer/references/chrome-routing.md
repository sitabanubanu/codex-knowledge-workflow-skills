# Chrome Routing Gate

本文件定义 `knowledge-video-decomposer` 在视频网页、平台页和阻断场景下何时必须使用 Chrome 检查页面状态。它是后续 agent 的执行规则，不是建议清单。

## 适用场景

在以下任一条件成立时，Chrome 是允许且优先的页面状态检查路径：

- 来源是 YouTube、Bilibili、Coursera、会员站、课程页、播客页、嵌入式视频页或其他平台页，而网页状态会影响 transcript、字幕、描述、章节、登录态或可见内容。
- 页面需要用户当前浏览器的登录态、地区状态、语言状态、订阅状态、播放器状态或已经展开的 transcript 面板。
- 页面上可能存在可见 transcript、字幕面板、描述、章节、show notes、课程讲义、资源链接或其他一手材料。
- 常规提取失败后，需要做首选的人工可见状态检查，而不是继续重复外部 extractor。
- 用户明确要求使用 Chrome、浏览器、当前登录状态或可见页面来确认来源。

Chrome 检查的目标是确认“页面实际上能看到什么”，包括标题、作者/频道、页面是否打开、是否有 transcript、是否需要登录/验证码/付费权限、是否有可下载或可复制的一手文本。

## Chrome 不等于绕过

Chrome route 不是反爬、绕过或批量抓取方案。后续 agent 必须遵守：

- 禁止要求用户或 agent 把 Chrome cookie 传给 `yt-dlp`。
- 禁止把 Chrome 已登录播放器、受限播放器流、临时播放 URL、私有 token 或浏览器会话状态交给 `yt-dlp`、ASR 下载器或其他外部 extractor。
- 禁止尝试绕过 CAPTCHA、bot check、付费墙、课程权限、地区限制或账号权限。
- 禁止把 Chrome 当成批量抓受限内容的工具。
- 禁止在需要验证码、付费、账号授权或访问控制时继续自动化点击来获取受限 transcript/audio。
- 允许记录页面状态、可见元数据、公开可见 transcript 状态和用户已经有权访问的页面事实。

如果任务目标需要绕过限制才能继续，必须停止该分支，并把来源状态交给 `source-status.md` 中的阻断状态处理。

## Chrome 可播放但没有文字稿

Chrome 能播放视频只说明浏览器可以渲染播放器，不等于 agent 已经获得可转写的本地音频文件。遇到“页面可播放，但没有可见 transcript/字幕”的情况，必须按以下顺序处理：

1. 记录页面可播放、无可见 transcript、无可采集字幕的事实。
2. 检查是否已有用户提供的本地视频/音频文件、字幕文件或 transcript。
3. 如果有本地视频/音频文件，转入 `transcription-fallback.md` 的本地 ASR 路径。
4. 如果 `yt-dlp` 能在不使用 Chrome cookie、登录态或绕过限制的情况下公开取得音频/字幕，可以转入本地 ASR 或字幕处理。
5. 如果只有 Chrome 播放器可看、但没有可导出的公开 transcript/audio，本分支必须停止，并请求用户提供一手媒体或 transcript。

禁止把“Chrome 能播放”写成 `primary_audio_asr`。只有在实际取得本地音频/视频文件并完成 ASR 后，才能把来源升级为 `primary_audio_asr`。

## Bootstrap 规则

当可用 skill 列表中存在 `chrome:control-chrome` 时，不能因为没有直接的 `chrome.*` 工具命名空间就判定 Chrome 不可用。

执行顺序：

1. 先读取 `chrome:control-chrome` skill 的 `SKILL.md`。
2. 按该 skill 的说明读取它要求的 browser documentation 或 browser-client 文档。
3. 按该 skill 的 Node/browser-client 引导方式连接和控制 Chrome。
4. 只有在 skill 缺失、文档读取失败、Chrome 连接失败、浏览器无法打开目标页或用户拒绝使用 Chrome 时，才可以判定 Chrome route 不可执行。

禁止行为：

- 禁止仅因工具列表没有 `chrome.open`、`chrome.navigate`、`chrome.*` 之类命名空间就记录 `Chrome unavailable`。
- 禁止跳过 `chrome:control-chrome` 的 bootstrap 文档直接猜测调用方式。
- 禁止在 Chrome 被触发后继续多次重复同一个已经 429/bot blocked 的 extractor。

## 触发条件

出现以下任一信号时，必须进入 Chrome route 决策，并停止同类外部提取重试：

- `yt-dlp` 返回 HTTP 429、bot confirmation、robot check、CAPTCHA、Sign in to confirm、login required、RequestBlocked 或类似平台阻断。
- `youtube_transcript_api` 返回 blocked、RequestBlocked、TooManyRequests、TranscriptsDisabled、login required 或 bot/consent/region 相关阻断。
- Hearsay URL ingestion 在平台 metadata fetch 或 URL 阶段超时，且来源是平台 URL，而不是本地音视频文件。
- 平台页 transcript 是否存在需要人工可见状态确认。
- 用户明确要求“用 Chrome 看一下”“用浏览器”“用登录态”“看页面上有没有 transcript/字幕”。

触发后应执行：

1. 记录触发原因。
2. 使用 Chrome 打开或定位目标页面。
3. 观察页面是否可打开、标题是否匹配、登录/验证码/付费状态、可见 transcript 或字幕入口。
4. 只在可见 transcript 或用户授权的一手材料可访问时，继续采集一手文本。
5. 若没有可见一手材料，转入 `source-status.md` 的阻断或降级状态。

## 停止条件

Chrome route 遇到以下任一条件必须停止，不得用更多自动化绕过：

- Chrome 页面无法打开、崩溃、连接失败或目标 URL 无法加载。
- 页面能打开但没有可见 transcript、字幕面板、可复制字幕、可下载 transcript 或其他一手文本。
- 页面要求 CAPTCHA、bot verification、付费墙、课程权限、会员权限、账号权限、地区解锁或用户未授权的登录。
- 页面状态显示视频不可用、被删除、私有、地区不可用或年龄/权限限制。
- 继续任务会要求批量抓取受限内容、传递 cookie 给外部 extractor、绕过访问控制或规避平台限制。

停止后必须记录原因，并按 `source-status.md` 选择 `source_blocked`、`source_failed`、`secondary_only` 或 `degraded_report_only`，不得伪装成完整视频分析。停止说明必须区分“页面可播放但没有可转写媒体文件”和“页面完全不可访问”。

## 输出要求

任何执行或明确跳过 Chrome route 的 workflow，都必须在 acquisition notes、metadata 或 run state 中记录以下字段：

```json
{
  "chrome_route_used": true,
  "visible_transcript_status": "available|partial|not_visible|not_checked|blocked|unknown",
  "page_state_observed": "opened|failed_to_open|login_required|captcha_required|paywalled|permission_required|video_unavailable|metadata_only|unknown",
  "why_chrome_was_or_was_not_used": ""
}
```

字段规则：

- `chrome_route_used`: 实际使用 Chrome 时为 `true`；未使用时为 `false`，并必须解释原因。
- `visible_transcript_status`: 只记录 Chrome 页面可见事实，不把 Firecrawl、搜索摘要、Podwise 或猜测写成可见 transcript。
- `page_state_observed`: 记录页面状态的最具体值；不确定时写 `unknown` 并说明不确定原因。
- `why_chrome_was_or_was_not_used`: 必须包含触发条件、bootstrap 结果、停止条件或跳过理由。

最小记录示例：

```json
{
  "chrome_route_used": true,
  "visible_transcript_status": "not_visible",
  "page_state_observed": "opened",
  "why_chrome_was_or_was_not_used": "yt-dlp returned HTTP 429, so Chrome page-state inspection was required. The page opened, but no visible transcript panel or downloadable transcript was found."
}
```

## 与来源状态门禁的关系

Chrome 能确认页面状态，但不能单独解锁完整分解。只有以下 Chrome 结果可以进入完整 `video_analysis_pack`：

- 页面上可见且可引用的 transcript 被采集，并能形成 timestamp 或 source span。
- Chrome 确认并取得平台公开字幕、官方 transcript、用户已授权页面中的一手 transcript。
- Chrome 帮助定位到本地下载或用户提供的一手 transcript/audio，且后续 transcript/audio 获取成功。

如果 Chrome 只取得标题、描述、章节、公开摘要、评论、页面截图或二手链接，最多进入 `secondary_only` 或 `degraded_report_only`，不能进入完整视频分解。
