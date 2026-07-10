# Knowledge Workflow Skills 中文说明

Agent-Reach 负责拿材料；
本项目负责判断材料够不够可信；
有一手材料才分析，没证据就降级。

这个仓库不是万能爬虫，也不是随手总结视频的工具。它的目标是把
Agent-Reach acquisition、一手材料 source gate、证据审计和可追溯报告生成
接成一个本地工作流。

## 新结构

```text
Agent-Reach acquisition
  -> acquisition_bundle
  -> source-gated evidence
  -> auditable report generation
```

职责拆分：

- `agent-reach-console`：只负责获取，写 `00_acquisition/manifest.json`。
- `source-gated-evidence-layer`：只负责验证材料、生成 `source_status.json`、证据审计和降级输出。
- `knowledge-document-composer`：只负责从已审计 pack 写报告，不补证据。
- `knowledge-video-decomposer`：保留 transcript、ASR、segment、inventory、logic、evidence audit、pack builder 等核心脚本；旧平台获取路线降级为 legacy。

## 快速开始

先跑本地 transcript demo，不要一上来就用平台 URL：

```powershell
python .\kw.py demo
```

看结果：

```text
outputs/knowledge-workflow/demo-transcript/result_index.md
```

本地文件：

```powershell
python .\kw.py run --input .\examples\demo_transcript\input.txt --mode audit --language en --final-language en
```

URL：

```powershell
python .\kw.py agent-reach doctor
python .\kw.py run --input https://example.com/page --mode audit
```

命令行会显示：

- acquisition status
- source status
- full report allowed
- result_index path

## acquisition_bundle

稳定中间协议：

```text
00_acquisition/
  manifest.json
  artifacts/
  logs/
```

Evidence layer 只读 manifest，不直接抓平台。协议见：

```text
docs/acquisition-bundle-protocol.md
```

## Source Gate

只有这些状态可以进入正常或部分分析：

- `source_confirmed`
- `source_partial`

这些状态不能生成正常 `final_report.md`：

- `secondary_only`
- `source_blocked`
- `source_failed`
- `degraded_report_only`
- `metadata_only`
- `blocked`
- `failed`
- `unsupported`

没有一手 transcript、subtitle、ASR transcript 或任务所需的一手正文，就只写降级说明和下一步建议。

## 安全边界

本项目不绕过 CAPTCHA、付费墙、私密内容、地区限制或账号权限限制。

不要读取、展示、复制或提交：

- cookie 值
- token
- Authorization header
- 私密登录态
- `work/`
- `outputs/`
- `test_outputs/`
- 私密日志

manifest 可以记录是否使用 cookies，但不能记录 cookies 内容。
