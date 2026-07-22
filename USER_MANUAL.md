# 用户手册

## 先从总控台开始

```powershell
kw run --input <URL或文件> --target <目标> --operation <操作> --mode audit
```

常见目标：

| target | 需要的主材料 |
| --- | --- |
| `video_content` | 字幕、transcript，或可进入本地 ASR 的音视频 |
| `social_post` | 帖子正文 |
| `web_article` | 文章正文 |
| `repository` | README 或仓库文档 |
| `search_triage` | 搜索结果，仅用于选材 |

帖子正文不能替代帖子中视频的 transcript；搜索结果不能直接解锁正式报告。

## 三段产品流程

1. 需要“先找资料”时，使用 `web-intent-scout` 建立意图图、查询族、来源台账和候选清单。
2. 将选中的 URL、查询或本地材料交给 `knowledge-workflow-console`。总控台获取材料、运行 Source Gate 和证据审计。
3. 选择 `knowledge-learning-article` 生成学习文章，或选择 `knowledge-document-composer` 生成忠于来源的正式文档。

## 运行前检查获取路线

```powershell
kw source doctor
kw source matrix
kw source plan --input <URL> --target <目标> --operation <操作>
```

路线只有在 Provider ready、操作受支持、浏览器宿主要求满足时才会执行。

## 分阶段运行

```powershell
kw acquire --input <URL或查询> --target <目标> --operation <操作> --project-root <项目目录>
kw validate-bundle --bundle <项目目录>\00_acquisition\manifest.json
kw ingest --bundle <项目目录>\00_acquisition\manifest.json --project-root <项目目录>
kw audit --project-root <项目目录>
kw compose --project-root <项目目录>
kw status --project-root <项目目录> --pretty
kw result --project-root <项目目录> --pretty
```

## 导入其他渠道的授权材料

当渠道没有内置结构化直连时，先通过用户有权使用的浏览器、CLI、API 或导出功能把主材料保存到本地，再执行：

```powershell
kw source import `
  --input-file <本地主材料> `
  --source-url <原始URL> `
  --platform <平台> `
  --target <目标> `
  --operation <操作> `
  --project-root <项目目录>
```

只有正文、subtitle、transcript、音频或视频等目标兼容材料可以作为主材料。metadata、截图、搜索摘要和页面外壳仍不能通过正常报告许可。

## YouTube 与媒体

`kw run` 和 `kw acquire` 支持 `--youtube-cookies`、`--youtube-browser edge|chrome`、`--ytdlp`、`--node`、字幕语言、JS runtime 和超时等参数。

- `probe`：只读 metadata。
- `subtitles`：只尝试字幕。
- `audio`：获取音频，交给 evidence layer 的本地 ASR。
- `auto`：先字幕，再获取媒体并进入 ASR。

获取层不会自行把原始音频标为 transcript；只有 ASR 成功、派生文本哈希被 gate receipt 绑定后，流程才继续。

## Resume 与历史

同一项目目录绑定一个来源、目标和操作。只有完全匹配时才可：

```powershell
kw run ... --project-root <原项目目录> --resume
```

旧尝试会进入 `acquisition_history/` 和 `run_history/`。来源文件变化、目标变化或操作变化时请使用新目录。

## 交付条件

正式学习文章或报告需要：

- 当前 Bundle v2 校验通过；
- SourceStatus 合约允许进入分析；
- evidence audit 无阻断问题；
- gate、analysis、composer/learning 和 final receipt 的哈希都与当前文件一致；
- 对应 quality gate 批准交付。

每次先打开 `result_index.md`。它会说明当前可交付物、阻断原因、过期文件和下一步。
