# 故障排查

## 某个 Provider 不可用

```powershell
kw source doctor
kw source plan --input <URL> --target <目标> --operation <操作>
```

只安装或修复对应 Provider，也可以提供本地主材料。项目没有 Agent Reach runtime 依赖，缺少一个 Provider 不会让其他路线失效。

## Provider 已安装但仍被阻断

Provider 名称存在不等于路线可执行。检查：

- `provider_status` 是否为 `ok`；
- `operation_supported` 是否为 `true`；
- `browser_host_ready` 是否为 `true`；
- 当前材料范围是否能满足 `analysis_target`。

Bilibili 搜索能力不能代替视频字幕；普通网页 reader 不能代替需要登录的平台 Provider。

## OpenCLI 为 warn

1. 在真实使用的 Edge 或 Chrome 中安装并连接扩展。
2. 保持该浏览器打开，并通过用户自己的授权账号登录。
3. 运行 `opencli daemon status` 和 `kw source doctor`。
4. 使用 `--browser-host edge` 或 `--browser-host chrome` 显式声明真实宿主。

不要从插件名字猜浏览器，不要静默切换浏览器，也不要未经许可关闭浏览器来解锁 cookie 数据库。

## 获取成功但没有正式报告

检查：

```text
00_acquisition/manifest.json
10_video/00_source/source_status.json
10_video/00_source/gate_receipt.json
result_index.md
```

常见安全停止状态：`metadata_only`、`secondary_only`、`source_blocked`、`source_failed`、`target_mismatch`。这些状态允许解释缺什么，但不允许生成正常完整报告。

## YouTube 没有字幕或遇到登录/机器人检查

可使用用户授权的 Netscape cookies 文件、明确的 Edge/Chrome 宿主、Node.js challenge runtime，或提供本地字幕、transcript、音频/视频。`auto` 和 `audio` 模式下载的媒体会交给 evidence layer 的 ASR，不再经过任何中间总入口。

不要把 cookie、visitor data、PO token 或代理密码写入报告和日志；持久化命令必须经过脱敏。

## 本地音视频没有继续

运行：

```powershell
kw doctor
```

确认 `ffmpeg`、`ffprobe` 和 `faster-whisper` 可用。原始媒体只表示 `pending_derivation`；非空且校验通过的派生 transcript 才能重新建立 `source_confirmed`。

## 旧报告仍在但当前状态失败

这是正常的 provenance 防护。查看 `stale_output_files_present` 和 `final_report_provenance_current`。不要重命名旧报告冒充新结果；应为当前 Bundle 重新 ingest、audit 和 compose。

## Bundle 校验失败

```powershell
kw validate-bundle --bundle <项目目录>\00_acquisition\manifest.json
```

常见原因包括路径越界、文件缺失、字节数或 SHA-256 不匹配、身份字段缺失、状态不变量冲突或未脱敏数据。不要手改哈希，重新获取或导入。

## Codex 仍显示旧获取 Skill

先确认备份存在，再运行：

```powershell
.\sync_to_codex_skills.ps1
.\sync_to_codex_skills.ps1 -VerifyOnly
```

同步脚本会安全移除旧的 `agent-reach-console`，并安装 `acquire-source-material`。

## 不应提交的内容

保持 `work/`、cookies、tokens、浏览器数据、`outputs/`、`test_outputs/`、缓存和私密日志在 Git 之外。
