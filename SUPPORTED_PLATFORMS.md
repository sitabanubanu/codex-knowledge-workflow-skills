# 平台与操作矩阵

平台支持是“Provider + 操作 + 当前环境”的组合，不是对每个 URL 的成功承诺。

## 内置结构化路线

| 输入 | 操作 | 原生 Provider 路线 | 证据边界 |
| --- | --- | --- | --- |
| 本地 transcript/subtitle | `extract_transcript` | Bundle v2 本地复制与规范化 | 非空、目标匹配的 transcript 可确认 `video_content`。 |
| 本地音视频 | `extract_transcript` | Bundle v2 -> evidence-layer ASR | 媒体本身是 `pending_derivation`；派生 transcript 校验后才确认来源。 |
| 普通网页 | `read` | `curl` + Jina Reader | `article_body` 只对 `web_article` 是主材料。 |
| YouTube | `read` / `extract_transcript` | `yt-dlp` metadata、字幕、媒体；可选 OpenCLI 可见 transcript | metadata 不解锁视频分析；下载媒体进入本地 ASR。 |
| Bilibili | `read` / `extract_transcript` | `bili` detail/audio；可选 OpenCLI subtitle | search-only 能力不能冒充 transcript；audio 进入本地 ASR。 |
| GitHub | `read` | `gh` metadata + 临时 clone README | repository document 可确认 `repository`。 |
| X/Twitter status | `read` | `twitter` 或已授权 OpenCLI article | 帖子正文只确认 `social_post`，不确认嵌入视频。 |
| 小红书 note | `read` | OpenCLI、xiaohongshu MCP 或 `xhs` | note 正文只确认 `social_post`；不使用匿名网页 fallback。 |
| 查询 | `search` | `mcporter` 中的 Exa | 结果始终是 `secondary_only`，只用于选材。 |

## Provider-neutral 导入路线

RSS、Reddit、Facebook、Instagram、LinkedIn、小宇宙、V2EX、雪球以及其他授权渠道，可先通过用户有权使用的浏览器、CLI、API 或导出功能保存主材料，再运行：

```powershell
kw source import --input-file <材料> --source-url <URL> --platform <平台> --target <目标> --operation <操作> --project-root <项目目录>
```

所有导入都写相同的 Bundle v2，经过相同的范围检查、哈希验证和 Source Gate。Provider ready 不等于报告许可。

## 查看当前能力

```powershell
kw source doctor
kw source matrix
kw source plan --input <URL或查询> --target <目标> --operation <操作>
```

## 明确不支持

- 绕过 CAPTCHA、付费墙、私密访问、地区或账号权限；
- 用搜索结果冒充正文；
- 用 metadata、评论、截图或帖子 caption 冒充视频 transcript；
- 在浏览器宿主不明时猜测 Edge/Chrome 或静默切换；
- Provider 失败后继续生成正常完整报告。
