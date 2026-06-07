# BSOD Analyzer / 蓝屏自动诊断

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-orange)](https://github.com/sitabanubanu/bsod-analyzer)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Knowledge Base](https://img.shields.io/badge/BugCheck%20KB-62%20codes-blue)](BugcheckKB.json)
[![Drivers DB](https://img.shields.io/badge/Known%20Bad%20Drivers-8%20drivers-red)](KnownBadDrivers.json)

[English](#english) | [中文](#中文)

---

# English

## The Problem

You get a blue screen. You search the STOP code online. Every result tells you:

> "Update your drivers." "Run sfc /scannow." "Check your RAM."

None of them tell you **which** driver. None of them look at the crash dump. None of them find the 64+ remnants left behind by software you uninstalled months ago. None of them tell you that Ntfs.sys appearing in the stack trace actually means it's the **victim**, not the culprit.

You end up reinstalling Windows. Or you hire someone. Or you just live with the random crashes.

**BSOD Analyzer fixes this.** It's an AI agent skill that does what a trained Windows debugger would do -- but automatically, in minutes, without you needing to learn WinDbg.

## What Makes This Different

There are dozens of BSOD tools. Here's what each does and what this skill adds:

| Tool | What It Does | What It Doesn't Do |
|------|-------------|-------------------|
| **BlueScreenView** (NirSoft) | Shows which .sys file was in the crash bucket, 61KB portable | Can't read the dump if you're not admin. No stack analysis. No pool tag decode. No cleanup. |
| **WhoCrashed** (Resplendence) | GUI wrapper around Microsoft's dbgeng.dll. One-click dump analysis. | Home edition doesn't do stack traces. Doesn't audit your system for remnants. Doesn't clean anything. |
| **bluskreener** (GitHub community) | Knowledge-base driven BSOD triage. Cross-references BugCheck codes against a JSON database. | Relies on dumpchk.exe which most systems don't have. BugCheck extraction failed on our test machine. Driver KB has only 5 entries. |
| **WinDbg / cdb** (Microsoft) | The gold standard. `!analyze -v`, `!pooltag`, `!uniq`, `!blackbox`. Everything. | Requires expertise. No cleanup. No verification loop. You have to know what to type. |
| **Sysinternals ProcDump** | Proactive crash capture. Creates dumps on CPU spikes, memory thresholds, thread counts. | Not an analysis tool. Completely different category. |

**BSOD Analyzer combines all of their strengths:**

| Capability | BlueScreenView | WhoCrashed | bluskreener | WinDbg | **This Skill** |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Read dump without admin | No | No | No | No | **Yes (event log fallback)** |
| BugCheck code + meaning | Partial | Yes | Partial | Yes | **Yes (62-code KB)** |
| Stack trace analysis | No | Pro only | No | Yes | **Yes** |
| Pool tag decode | No | No | No | Yes | **Yes (hex->ASCII->search)** |
| Unloaded module detection | No | No | No | Yes | **Yes (!uniq)** |
| Driver timestamp audit | No | No | No | Yes | **Yes (flags future/corrupt dates)** |
| System audit (18 locations) | No | No | No | No | **Yes (drivers, COM, PnP, CloudStore, firewall)** |
| Ghost driver detection | No | No | No | No | **Yes** |
| Known-bad driver version matching | No | No | 5 drivers | No | **8 drivers (growing)** |
| Cleanup plan + execute | No | No | No | No | **Yes (plan-only, user confirms)** |
| Verification loop | No | No | No | No | **Yes (re-audit after reboot)** |
| 4-layer report | No | No | No | No | **Yes** |
| AI agent native | No | No | No | No | **Yes** |

## Real Results

> **Machine:** Consumer laptop, Windows 11 24H2, 16GB RAM, NVMe SSD
> **Situation:** 4 BSODs in 9 days. STOP codes: 0x13A, 0x1A, 0xC2, 0x1E -- four different codes, one hidden root cause.
> **What the skill found:**
> - 64+ driver and registry remnants from uninstalled applications (months-old leftovers)
> - A VPN tunnel driver and Modern Standby sleep/wake cycles silently corrupting kernel memory
> - After 3 memory-corruption crashes masked the true culprit, the 4th crash directly caught a GPU driver (installed the same day as the first BSOD) triggering a General Protection Fault in the video scheduler
> - BugCheck 0xC2: Filesystem driver was the VICTIM, not the culprit -- detected corruption from another component
> **Result:** Remnants removed, sleep mode fixed, GPU driver identified. Observation underway.

## Who This Is For

- **Regular users** who get a BSOD and want to know what's actually wrong -- not "try updating drivers"
- **IT support** who need to diagnose multiple machines without spending 2 hours on each
- **AI agent users** (Claude Code, Codex) who want a one-click diagnosis pipeline

## How It Works

```
Stage 0  INTAKE        What have you already tried? (no repeated fixes)
Stage 1  PREFLIGHT      Permissions, tools, dumps, BitLocker, HVCI
Stage 2  TRIAGE         Event logs, multi-dump patterns, recent changes
Stage 3  ANALYZE        WinDbg deep analysis, pool tag decode, stack interpretation
Stage 4  AUDIT          18-point system scan for driver remnants
Stage 5  CLEANUP PLAN   Generated plan. Won't execute without your confirmation.
Stage 6  PREVENTION     Crash dump config, restore points, Verifier warnings
Stage 7  REPORT         4-layer: Facts -> Conclusions -> Downgraded -> Blocked
```

## File Structure

```
bsod-analyzer/
├── SKILL.md              <- Main skill file (the AI agent reads this)
├── BugcheckKB.json        <- 62 BugCheck codes with meanings and diagnostic tips
├── KnownBadDrivers.json   <- 8 driver version ranges with known BSOD bugs
└── README.md              <- You are here
```

**How they work together:** `SKILL.md` is the engine -- the 7-stage diagnosis pipeline. The two `.json` files are its **reference data**. When the skill runs, it loads both JSON files, cross-references the crash against 62 known BugCheck codes, and checks every driver on your system against 8 known-bad version ranges. Every resolved case adds to these knowledge bases.

## Installation

**One-click download (recommended):**

Go to [Releases](https://github.com/sitabanubanu/bsod-analyzer/releases) and download `bsod-analyzer.zip`. Unzip and copy the whole folder:

```bash
# Claude Code
cp -r bsod-analyzer ~/.claude/skills/

# Codex  
cp -r bsod-analyzer ~/.codex/skills/
```

**Or clone directly:**

```bash
git clone https://github.com/sitabanubanu/bsod-analyzer.git ~/.claude/skills/bsod-analyzer
```

Then say: "My computer keeps blue screening. Diagnose it."

## Requirements

**Zero-dependency fallback.** Four degradation levels:

| Level | Needs | Capability |
|-------|-------|-----------|
| FULL | Admin + WinDbg | Complete stack analysis, pool tags, blackbox data |
| LITE | WinDbg only | Stack analysis (no admin needed for dump copy) |
| USER | Nothing | Event log BugCheck codes + system audit |
| REPORT | Nothing | Even if everything fails, tells you exactly what admin command to run |

---

# 中文

## 解决了什么痛点

你蓝屏了。上网搜 STOP 码，每条结果都告诉你：

> "更新驱动。" "运行 sfc /scannow。" "检查内存。"

没有一条告诉你**具体是哪个驱动**。没有一条去看你的 crash dump。没有一条发现你三个月前卸载的软件留了 64 个内核残骸还在系统里。没有一条告诉你堆栈里的 Ntfs.sys 其实是**受害者**，不是真凶。

最后的结局往往是重装系统。或者找个懂的人花钱修。或者忍了。

**BSOD Analyzer 就是解决这个的。** 它是一个 AI agent skill，自动做专业 Windows 调试人员才会做的事——几分钟出结果，不需要你懂 WinDbg。

## 跟市面上的工具比，为什么要用这个

蓝屏工具有很多。但每一种都只做了一半：

| 工具 | 能做什么 | 缺什么 |
|------|---------|--------|
| **BlueScreenView** (NirSoft) | 61KB 便携，告诉你哪个 .sys 在崩溃桶里 | 没管理员读不了 dump。不分析栈。不解码池标签。不清理。 |
| **WhoCrashed** (Resplendence) | 封装了微软 dbgeng.dll，一键分析 dump | 家庭版没有栈回溯。不审计系统残留。不清垃圾。 |
| **bluskreener** (GitHub 开源) | 知识库驱动的蓝屏分类，JSON 数据库查 BugCheck 码 | 依赖 dumpchk.exe（多数电脑没有）。实测连 BugCheck 码都没提到。驱动库只有 5 条。 |
| **WinDbg / cdb** (微软官方) | 最强。`!analyze -v`、`!pooltag`、`!uniq`、`!blackbox` | 需要专业知识和经验。不会清理。不会验证。全靠你敲命令。 |
| **Sysinternals ProcDump** (微软) | 主动监控，CPU/内存/线程数触发自动抓 dump | 不是分析工具。另一个品类。 |

**BSOD Analyzer 把以上所有工具的优点合在一起，补上了它们都缺的东西：**

| 能力 | BlueScreenView | WhoCrashed | bluskreener | WinDbg | **本 Skill** |
|-----------|:---:|:---:|:---:|:---:|:---:|
| 没管理员也能读 dump | 否 | 否 | 否 | 否 | **是（事件日志降级）** |
| BugCheck 码 + 含义 | 部分 | 是 | 部分 | 是 | **是（62 条知识库）** |
| 栈回溯分析 | 否 | 仅 Pro | 否 | 是 | **是** |
| 池标签解码 | 否 | 否 | 否 | 是 | **是（hex->ASCII->搜索）** |
| 已卸载模块检测 | 否 | 否 | 否 | 是 | **是 (!uniq)** |
| 驱动时间戳审计 | 否 | 否 | 否 | 是 | **是（标记未来/损坏日期）** |
| 18 点位系统审计 | 否 | 否 | 否 | 否 | **是** |
| 幽灵驱动检测 | 否 | 否 | 否 | 否 | **是** |
| 已知坏驱动版本匹配 | 否 | 否 | 5 条 | 否 | **8 条（持续增长）** |
| 清理计划 + 执行 | 否 | 否 | 否 | 否 | **是（只出计划，确认后才执行）** |
| 重启后验证 | 否 | 否 | 否 | 否 | **是** |
| 四层分层报告 | 否 | 否 | 否 | 否 | **是** |
| AI agent 原生 | 否 | 否 | 否 | 否 | **是** |

## 真实案例

> **机器：** 消费级笔记本，Windows 11 24H2，16GB 内存，NVMe SSD
> **情况：** 9 天 4 次蓝屏。STOP 码：0x13A、0x1A、0xC2、0x1E——四个不同的码，一个隐藏的真凶。
> **Skill 发现了什么：**
> - 已卸载应用 64+ 项驱动和注册表残骸（数月前的残留）
> - VPN 隧道驱动 + Modern Standby 待机唤醒在后台反复写坏内核内存
> - 前 3 次内存损坏型蓝屏掩盖了真凶，第 4 次蓝屏直接抓到 GPU 驱动触发 General Protection Fault——该驱动恰好与第一次蓝屏同日安装
> - 0xC2 蓝屏里，文件系统驱动是受害者，不是真凶——检测到了其他组件写坏的池内存
> **结果：** 残骸清除，睡眠模式修复，GPU 驱动定位。正在观察中。

## 适用人群

- **普通用户：** 蓝屏了想知道到底什么坏了——不是"试试更新驱动"
- **IT 运维：** 需要批量诊断多台机器，不想每台花两小时
- **AI agent 用户：** Claude Code / Codex 一键加载，自动诊断

## 四层降级（零依赖也能跑）

| 级别 | 需要 | 能做什么 |
|------|------|---------|
| FULL | 管理员 + WinDbg | 完整栈分析、池标签、黑匣子数据 |
| LITE | WinDbg | 栈分析（不需要管理员复制 dump） |
| USER | 无 | 事件日志 BugCheck 码 + 系统审计 |
| REPORT | 无 | 全失败也能告诉你用管理员跑哪条命令 |

## 文件结构

```
bsod-analyzer/
├── SKILL.md              <- 主 Skill 文件（AI agent 读取这个）
├── BugcheckKB.json        <- 62 条 BugCheck 码含义和诊断指南
├── KnownBadDrivers.json   <- 8 条已知问题驱动的版本范围
└── README.md              <- 你正在看的
```

**它们怎么配合：** `SKILL.md` 是引擎，跑 7 阶段诊断流水线。两个 `.json` 是它的**参考数据库**。跑的时候自动加载，把崩溃信息跟 62 条 BugCheck 码交叉对比，把系统上的每个驱动跟 8 条已知坏版本范围对比。每修好一台电脑，知识库就多一条。

## 安装

**一键下载（推荐）：**

去 [Releases](https://github.com/sitabanubanu/bsod-analyzer/releases) 下载 `bsod-analyzer.zip`，解压后把整个文件夹复制进去：

```bash
# Claude Code
cp -r bsod-analyzer ~/.claude/skills/

# Codex
cp -r bsod-analyzer ~/.codex/skills/
```

**或者直接 clone：**

```bash
git clone https://github.com/sitabanubanu/bsod-analyzer.git ~/.claude/skills/bsod-analyzer
```

然后说："我电脑老是蓝屏，帮我诊断一下。"

---

---

## Companion Skill: Skill Builder / 配套 Skill

This project was built using **[skill-builder](https://github.com/sitabanubanu/bsod-analyzer)** — a meta-skill that turns troubleshooting conversations into reusable AI agent skills. If you've solved a complex problem and want to capture the solution for others, skill-builder walks you through the same 5-stage method that produced BSOD Analyzer:

1. Extract raw material from the conversation (timeline + mistakes + tool discoveries)
2. Group actions into stages with clear inputs/outputs
3. Learn from the community to fill blind spots in your own experience
4. Cross-validate with another agent until they reach the same conclusion
5. Package and publish with comparison tables and real case studies

This project is proof the method works.

---

## Contributing / 贡献

The knowledge bases grow with every resolved case. If your BSOD code or driver isn't in the KB, add it and submit a PR. The files are plain JSON -- no programming needed.

知识库随每个案例增长。如果你的蓝屏码或问题驱动不在库里，加进去提 PR。JSON 不需要编程。

## License

MIT
