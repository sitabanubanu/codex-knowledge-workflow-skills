# 安装

## 安装项目

```powershell
git clone https://github.com/sitabanubanu/codex-knowledge-workflow-skills.git
cd codex-knowledge-workflow-skills
python -m pip install -e .
kw --help
```

也可以不安装包，直接使用 `python .\kw.py ...`。

本项目不需要安装 Agent Reach。获取层直接探测可选 Provider；缺少某个平台工具只会让对应路线阻断，不会影响本地文件、其他 Provider 或证据工作流。

请从完整源码 checkout 或 source archive 运行。单独的 Python wheel 不含
Codex Skills 与内部脚本，不能替代完整项目包。

## 安装 Codex Skills

```powershell
.\sync_to_codex_skills.ps1 -DryRun
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

同步的工作流 Skills：

- `knowledge-workflow-console`
- `web-intent-scout`
- `acquire-source-material`
- `source-gated-evidence-layer`
- `knowledge-learning-article`
- `knowledge-document-composer`

同步脚本会移除旧的 `agent-reach-console`。`knowledge-video-decomposer` 仍是仓库内部兼容库；`browser-host-identity` 是独立项目，不由本工作流同步。

## 可选 Provider

只安装你实际需要的工具，并遵循各工具官方安装与授权方式：

| 用途 | 可选 Provider |
| --- | --- |
| 普通网页 | `curl` + Jina Reader |
| YouTube | `yt-dlp`；可选 OpenCLI 可见字幕路线 |
| Bilibili | `bili`；可选 OpenCLI 字幕路线 |
| GitHub | `gh` |
| X/Twitter | `twitter`；可选 OpenCLI |
| 小红书 | OpenCLI、xiaohongshu MCP 或 `xhs` |
| 搜索 | `mcporter` 中配置的 Exa |
| 本地音视频 | `ffmpeg`、`ffprobe`、`faster-whisper` |

检查实际状态：

```powershell
kw source doctor
kw source matrix
kw doctor
```

`provider_status: ok` 只说明 Provider 可调用，不代表材料已经通过 Source Gate。

## 验证安装

```powershell
kw demo
kw validate --include-sync
```

## 安全边界

- 不提交 cookies、token、Authorization headers、浏览器 profile 或私密日志。
- `manifest.json` 只能记录 `cookies_used=true/false`，不能保存 cookie 内容。
- 使用 OpenCLI、浏览器 cookies 或浏览器导出时，必须显式声明真实的 `edge` 或 `chrome` 宿主。
- 不绕过 CAPTCHA、付费墙、地区、账号或私密内容权限。
