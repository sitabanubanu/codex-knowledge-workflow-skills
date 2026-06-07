---
name: bsod-analyzer
description: Windows BSOD diagnosis. Prioritizes driver-caused crashes while checking hardware, storage, and firmware signals. Dump analysis -> audit -> cleanup plan -> prevention. Zero-dependency fallback.
---

# BSOD Analyzer

## What This Skill Covers

This skill is specifically for Windows blue screen / system crash diagnosis. It is NOT a general-purpose software debug skill.

**Before starting, load these files from the same directory as this skill:**
- `BugcheckKB.json` -- BugCheck code meanings, common causes, what to check
- `KnownBadDrivers.json` -- Driver version ranges with known issues

These are NOT optional. In the final report, state which BugCheckKB entries matched
and which KnownBadDrivers entries were checked and found not to match.

**Key differences from software bug diagnosis:**

1. **Crash artifacts ARE reproduction.** BSODs cannot and should not be intentionally triggered.
   Accept the following as proof a crash occurred: BugCheck event (ID 1001), minidump/MEMORY.DMP,
   Kernel-Power event (ID 41), abnormal shutdown event (ID 6008), Reliability Monitor entries.

2. **"Regression test" = observation window.** There is no test suite for kernel drivers.
   After a fix, the verification is time-based: observe 24-72 hours without recurrence.
   For stress verification: memory diagnostic (mdsched), disk stress, GPU stress.

3. **"Reproduce before fixing" does not apply.** Never try to trigger a BSOD on purpose.
   The dump file IS the reproduction. Analyze it, form a hypothesis, make one change, observe.

4. **Permission failures are expected.** Minidump files require admin to read.
   When blocked, CONTINUE with what you can access (event logs, Reliability Monitor,
   driver lists, disk health) and flag what needs admin in the final report.
   Do not stop the entire pipeline because of one permission error.

5. **Driver Verifier is a last resort.** It can cause boot-loop BSODs. See Stage 6.2 warnings.

## Before You Start

Read these rules first. They prevent the most common failures.

### Rule 1: Shell Detection -- Know Your Environment

Before running any command, determine your shell:

**If you are in PowerShell directly** (run `$PSVersionTable` to confirm):
- You CAN use inline commands, pipes, `$_`, `$var`, `{ }` normally
- Still prefer .ps1 files for multi-line scripts

**If you are in bash** (`echo $0` shows "bash") or you're unsure:
- Inline PowerShell is broken. The following WILL fail:
  - `$_` becomes "extglob", `$var` becomes empty
  - `{ }` becomes brace expansion, `&` becomes background
- Safe pattern: Write to .ps1 file, run with `powershell.exe -File "<path>"`
- Inside scripts: use `Write-Output`, single-quoted strings where possible

### Rule 2: Permission Self-Check First

Before any operation, verify what you can do:
```
# Test admin
net session 2>&1
# Exit 0 = admin. Exit 2 = not admin.

# Test if cdb available
where cdb 2>&1
where cdbX64.exe 2>&1
```

### Rule 3: UAC Elevation Has a 30-Second Timeout

`Start-Process -Verb RunAs` opens a Windows UAC dialog. No one may click it. If you use RunAs:
```
1. Tell user: "A UAC dialog is about to appear. Please click Yes."
2. Launch with -Wait and a 30-second timeout
3. Check if the file/change actually happened after 30 seconds
4. If NO -> do NOT retry RunAs. Use fallback:
   - For dump copy: use direct path to C:\Windows\Minidump with cdb (cdb from WindowsApps can sometimes read it)
   - For registry writes: use schtasks with SYSTEM (no UAC dialog)
   - For files: write to user-accessible locations only
```
A RunAs that hangs for 5 minutes is worse than skipping the operation.

### Rule 4: Non-English Windows Event Logs

BugCheck event messages differ by locale. Do NOT assume English format. Use BOTH patterns:
```
if ($msg -match "BugcheckCode\s*(\d+)" -or $msg -match "BugcheckCode.*?(\d+)") -> English
if ($msg -match "0x([0-9a-fA-F]{8,10})") -> Chinese/Japanese (STOP code inline in hex)
```
The hex pattern `0x([0-9a-fA-F]{8,10})` catches the STOP code regardless of language. Extract ALL numeric params after it.

### Rule 5: !uniq Module Names Are Truncated at 12 Characters

The `!uniq` command in WinDbg cuts module names to 12 characters. `NetworkPrivacyPolicy` -> `NetworkPriva`. `Microsoft.Bluetooth.Legacy.LEEnumerator` -> `Microsoft.Bl`.

When you see a name that looks exactly 12 chars and ends in a partial word:
1. Do NOT assume it's suspicious
2. Search the registry: `reg query HKLM\SYSTEM\CurrentControlSet\Services /s /f "<first-8-chars>"`
3. If a full service name appears, it's a legitimate Windows component with a truncated name
4. Only flag as suspicious if the full name also looks like a third-party driver

---

### OS Crash Feedback Sources (OS/hardware diagnosis branch)

Unlike software debugging where the feedback loop is "write test, run, see pass/fail",
Windows crash diagnosis uses these artifacts as feedback:

```
PRIMARY (direct crash evidence):
  - BugCheck event (System log, ID 1001) -- STOP code + 4 params
  - Minidump (C:\Windows\Minidump\*.dmp) -- stack, loaded modules, pool tags
  - Full kernel dump (C:\Windows\MEMORY.DMP) -- complete physical memory snapshot
  - Kernel-Power event (System log, ID 41) -- unexpected power loss / forced restart
  - Abnormal shutdown event (System log, ID 6008) -- unclean shutdown confirmation

SECONDARY (context and timeline):
  - Reliability Monitor (perfmon /rel) -- crash timeline across days
  - Application event log -- app crashes/hangs that preceded the BSOD
  - Sidecar restart logs -- engine crash-restart cycles
  - Windows Update history (Get-HotFix) -- update timeline vs crash timeline
  - Driver install/update dates (Win32_PnPSignedDriver) -- driver timeline vs crash timeline

HARDWARE HEALTH (eliminate physical causes):
  - Windows Memory Diagnostic (mdsched.exe) -- RAM integrity
  - CHKDSK result (Wininit event, ID 1001) -- disk integrity
  - SMART data (Get-PhysicalDisk | Get-Disk) -- SSD/HDD health
  - WHEA events (System log) -- hardware error architecture events
  - BIOS/firmware version vs OS version compatibility

RUNTIME VALIDATION (current state):
  - Driver Verifier status (verifier /query) -- is it already active?
  - Crash dump configuration (CrashControl registry) -- is it set to full?
  - System restore points (Get-ComputerRestorePoint) -- safety net present?
  - Page file size vs RAM -- full dump needs pagefile >= RAM
  - Disk free space -- full dump needs ~16 GB on C:
```

## Stage 0: INTAKE -- What's Already Been Tried

Before any analysis, ask or check what the user has already done. This prevents
repeating failed fixes and wasting time on already-excluded causes.

Record each item with date, result, and whether the crash recurred after:

```
INTAKE LOG:
  [DATE] Uninstalled [driver] -> result: [fixed / no change / worse / crash recurred]
  [DATE] Ran sfc /scannow -> result: [found+fixed / clean / couldn't run]
  [DATE] Ran DISM /RestoreHealth -> result: [success / failed]
  [DATE] Reset network stack (winsock/ip reset) -> result: [...]
  [DATE] Disabled XMP/overclocking -> result: [...]
  [DATE] Updated BIOS to [version] -> result: [...]
  [DATE] Reinstalled [software] -> result: [...]
  [DATE] Ran Windows Memory Diagnostic -> result: [passed / errors found]
  [DATE] Ran chkdsk -> result: [found+fixed / clean]
  [DATE] Changed [setting] -> result: [...]
```

Sources for this data (no need to ask if the info is already in conversation):
- Ask user directly: "What have you already tried?"
- Check event logs for timestamps matching known actions
- Check file timestamps in C:\Windows\Minidump for crash dates
- Check restore points for "before" snapshots

In the final report, categorize each attempt:
- CONFIRMED INEFFECTIVE: crash recurred after this action
- INCONCLUSIVE: action taken but not enough time to know
- NOT TRIED: recommended but not yet done
- DO NOT REPEAT: already tried and confirmed ineffective

## Stage 1: PREFLIGHT -- Discover What You Have

Do this first. Takes 30 seconds. Tells you exactly which path to take.

### 1.1 Permission Level
```
net session 2>&1
```
- Exit 0 -> **Admin**: can read Minidump, modify HKLM, create scheduled tasks
- Exit 2 -> **User**: skip HKLM writes, skip SYSTEM operations. Use `Start-Process -Verb RunAs` for admin.

### 1.2 Debug Tools Discovery
Run all of these, use the first one found:
```
where cdb        # Command-line debugger (Windows SDK)
where cdbX64.exe # Same, sometimes named differently  
where kd.exe     # Kernel debugger
where WinDbgX.exe
# If none found: check Microsoft Store for "WinDbg Preview"
# If no store: skip to fallback path (Stage 2.0)
```

### 1.3 Dump Environment Check

Before counting dumps, check if dumps CAN be created:
```
manage-bde -status C: 2>&1                       # BitLocker status
reg query "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" 2>&1
Get-CimInstance Win32_PageFileSetting 2>&1        # Page file location + size
Get-CimInstance Win32_ComputerSystem | Select TotalPhysicalMemory
```
Flag these blockers:
- BitLocker ON + no recovery key -> full dump may fail to write
- CrashDumpEnabled = 0 -> dumps disabled entirely
- Page file not on C: or smaller than RAM -> full dump won't fit
- Less than 20GB free on C: -> full dump may fill the disk
- Enterprise EDR/VPN/DLP filter drivers -> may intercept or suppress crash dumps
- HVCI / Memory Integrity ON -> some legacy drivers blocked, may cause different crash behavior

### 1.4 Available Dumps
```
dir C:\Windows\Minidump\*.dmp    # May need admin
dir C:\Windows\MEMORY.DMP        # Full kernel dump, may need admin
```
Count them. 0 = no dumps to analyze, switch to event log only. 1 = single dump analysis. 2+ = multi-dump pattern analysis.

If dumps are absent but crashes occurred, the dump environment check above will explain why.

### 1.5 Output: PREFLIGHT Status Card
After running the above, write this status card before proceeding:
```
PREFLIGHT STATUS:
  Admin: YES/NO
  Debugger: cdb / fallback-name / NONE
  Dumps: N files (type: minidump / full / none)
  Path chosen: [FULL] Admin+cdb / [LITE] User mode / [MINIMAL] Event log only
  BitLocker: ON/OFF (C: drive)
  Page file: OK / TOO SMALL / NOT ON C:
  HVCI/Memory Integrity: ON/OFF
  Dump capable: YES / NO + reason if no
```

---

## Stage 2: TRIAGE -- Zero-Tool Quick Scan

No debugger required. All built into Windows.

### 2.0 Fallback: If No Debugger at All
```powershell
# Event log extraction (System) -- locale-aware
Get-WinEvent -LogName System -MaxEvents 2000 | Where-Object { $_.Id -eq 1001 -or $_.Id -eq 41 -or $_.Id -eq 6008 } | ForEach-Object {
    $msg = $_.Message
    # Try both English and CJK patterns for BugCheck code
    $code = ""
    if ($msg -match 'BugcheckCode\s*(\d+)') { $code = "0x" + [Convert]::ToString([int]$Matches[1], 16).ToUpper() }
    if (-not $code -and $msg -match '0x([0-9a-fA-F]{4,10})') { $code = "0x" + $Matches[1].ToUpper() }
    Write-Output "$($_.TimeCreated) | ID=$($_.Id) | CODE=$code"
}

# Application crashes (may precede BSOD)
Get-WinEvent -LogName Application -MaxEvents 500 | Where-Object { $_.Id -eq 1000 -or $_.Id -eq 1001 } | ForEach-Object {
    $m = $_.Message -replace "[\r\n]+", " "
    if ($m -match 'Faulting|故障|Crash|Hang|BEX|APPCRASH') {
        Write-Output "$($_.TimeCreated) | $($m.Substring(0, [Math]::Min(200, $m.Length)))"
    }
}

# Reliability Monitor (GUI -- skip on repeated runs, it opens a window each time)
# perfmon /rel
```

### 2.1 Multi-Dump Pattern Recognition
If you have 2+ dumps, extract the bucket ID from each one:
```
# For each dump file:
<debugger> -z <dump> -c "!analyze -v; q" 2>&1 | findstr "FAILURE_BUCKET_ID BUGCHECK_CODE IMAGE_NAME"
```

Pattern rules (apply in order):
1. All dumps same FAILURE_BUCKET_ID -> One driver, one bug. Target that driver.
2. Same IMAGE_NAME, different BugCheck codes -> That driver is corrupting memory in multiple ways.
3. Different codes + different images, but all after a specific date -> Check what was installed/updated on that date.
4. Completely random codes and images -> Suspect hardware or shared component (storage controller, chipset driver).
5. **3+ different BugCheck codes, all kernel memory corruption, ALL on the same machine**:
   The individual victims (heap, MM, NTFS, GPU, stack, object manager) are NOT random.
   Pattern: one subsystem is corrupting memory, different detectors find it at different times.
   CHECK: BIOS version age vs OS build date -> firmware older than OS = risk.
   CHECK: Which hardware-level components can write to arbitrary physical memory?
     (NVMe via HMB, GPU via DMA, chipset/platform drivers).
   If Win10 was stable but Win11 crashes on SAME hardware -> platform incompatibility.

Only 1 dump? Skip to direct analysis.

### 2.2 Recent Change Detection
Run before touching anything:
```
# Windows updates in last 30 days
Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10

# Known bad updates to flag:
# KB5053656, KB5055523 -> 0x18B SECURE_KERNEL_ERROR on Win11 24H2
```
If any known-bad update is installed, flag it immediately.

---

## Stage 3: ANALYZE -- Deep Dump Inspection

### Path A: cdb Available (Full Analysis)

**First: get the dump file.** Minidumps in C:\Windows\Minidump require admin to read. Try in order:
1. `Copy-Item C:\Windows\Minidump\<latest>.dmp $env:TEMP\crash.dmp` -- works if admin
2. If step 1 fails with "access denied" -> use Start-Process -Verb RunAs with 30s timeout (Rule 3)
3. If RunAs times out -> try reading directly: `<cdb> -z "C:\Windows\Minidump\<latest>.dmp"` -- cdb from WindowsApps sometimes bypasses the ACL
4. If even direct read fails -> use event log path (Stage 2.0) for BugCheck info, skip stack analysis

This is the most common failure point. Do not get stuck here.

**Permission degradation flow -- use this when dump access fails:**
```
LEVEL 1 (admin available): Copy with RunAs -> analyze with cdb -> full data
LEVEL 2 (cdb bypass): cdb from WindowsApps sometimes reads Minidump directly
LEVEL 3 (user only): Extract BugCheck code from event log (Stage 2.0)
                     + sysinfo (Get-ComputerInfo, Get-PhysicalDisk, Get-HotFix)
                     + driver list (Get-WindowsDriver or driverquery /v)
                     + audit (Stage 4, user-level portions)
LEVEL 4 (write this in report if stuck):
  "BLOCKED: Cannot read C:\Windows\Minidump\*.dmp (permission denied).
   To unblock, run as admin: copy C:\Windows\Minidump\*.dmp %TEMP%\
   Then re-run analysis on %TEMP%\*.dmp"
```
At Level 3 or 4, still produce a report. Put the blocked items in Layer 4.
Do NOT stop the entire pipeline because dump access failed.

**If the dump is a FULL kernel dump (MEMORY.DMP, 16GB+): do NOT copy it.
Do NOT start with !analyze -v (it can take 30+ minutes on 16GB+ dumps).**

Lightweight-first strategy for large dumps:
```
1. vertarget          -> OS version, uptime, dump type
2. .bugcheck          -> STOP code + params (instant)
3. k 20               -> top 20 stack frames (fast)
4. lm t n             -> loaded module list with timestamps
5. !sysinfo machineid -> machine GUID, BIOS, manufacture date
6. !analyze -show     -> classifications without full stack
```
Only run `!analyze -v` if the above is insufficient AND the agent has a long timeout.
If `!analyze -v` times out, report: "Lightweight triage completed. Full symbol
analysis timed out (expected for 16GB+ dumps). Key findings from lightweight pass: [...]"

For minidumps (<100MB): !analyze -v is fine. Run immediately.

**Run analysis commands in ONE session to avoid reloading symbols:**
```
<cdb> -z <dump-path> -c "vertarget; .bugcheck; k 20; lm t n; !sysinfo machineid; !uniq; !analyze -v; q" 2>&1
```
(The lightweight commands run first, so if !analyze -v times out you still have data.)

Extract these fields from output (locale-aware patterns):
- BugCheck code: look for `BUGCHECK_CODE:` or hex STOP code `0x[cC][0-9a-fA-F]+`
- BugCheck params: `BUGCHECK_P1-P4`
- `FAILURE_BUCKET_ID`, `IMAGE_NAME`, `PROCESS_NAME`
- `STACK_TEXT` -- the full call stack

After extraction, run these additional commands:
```
<cdb> -z <dump> -c "!blackboxbsd; !blackboxntfs; !blackboxpnp; q" 2>&1
```

**WARNING: !uniq truncates module names to 12 characters.** See Rule 5.
If a name looks exactly 12 chars and appears suspicious, cross-reference with the registry
before flagging it. `NetworkPriva` is actually `NetworkPrivacyPolicy` (legitimate Windows).

### Path A Continuation: Driver Timestamp Audit

From `lm t n` output, extract every driver with a real timestamp (not "reproducible build hash"). Flag any that are:
- Older than 2022
- Future dates
- Year 1970, 1980, 1983 (corrupted timestamps)

### Path A Continuation: Pool Tag Analysis
If BUGCHECK_CODE is 0xC2, decode Arg3:
```
Arg3 hex -> split into bytes -> each byte = ASCII character -> 4-char pool tag
Example: 0x6f306c36 -> 0x6f='o' 0x30='0' 0x6c='l' 0x36='6' -> tag = "o0l6"
```
Then run:
```
<cdb> -z <dump> -c "!pooltag <Arg3>; q" 2>&1
```
If output says "not found in pooltag.txt", this tag is from an unknown third-party driver. Search: "windows driver pooltag <tag>".

### Path A Continuation: Stack Interpretation

Do NOT just report IMAGE_NAME as the culprit. Check:
- If `nt!ExFreePoolWithTag` is in the stack -> another driver corrupted a pool, nt is the detector
- If `Ntfs!*` is in the stack but BugCheck is 0xC2/0xD1/0xBE/0x50 -> Ntfs is the VICTIM, not the culprit
- If `FLTMGR!*` is in the stack -> file system filter driver issue
- If `ndis!*` or `tcpip!*` is in the stack -> network driver issue

### Path B: No Debugger at All
Use BlueScreenView from NirSoft (61KB portable):
```
Download: https://www.nirsoft.net/utils/bluescreenview.zip
Usage: BlueScreenView.exe /LoadFrom <dump-folder> /stext report.txt
```
If download fails, use the event log data from Stage 2.0.

### Stage 3 Output
Write a card with:
```
DUMP ANALYSIS:
  BugCheck: 0x??? = NAME
  What it means: [one sentence]
  Module in bucket: xxx.sys
  This module is: CULPRIT / VICTIM / UNKNOWN
  Reason: [why you classified it this way]
  Pool tag (if applicable): XXXX -> known/unknown -> source
  Suspicious unloaded modules: [...]
  Blackbox flags: [...]
```

---

## Stage 4: AUDIT -- System Scan

### 4.0 Generate Search Terms
DO NOT use a hardcoded list. Generate from:
1. Any driver names found in the dump analysis
2. Any known-bad software names from the BugCheck code lookup
3. Default fallback list ONLY if dump yielded nothing:
```
mumu, gameviewer, vigem, gvinput, xunlei, netease, quark, wintun, proxifier, flclash
```
**Noise filter**: If searching for "nemu", exclude results containing "ZuneMusic" or "Microsoft.ZuneMusic".

### 4.1 Quick Audit (User-Level, Always Possible)
Run these in parallel. All read-only.

```
# Disk drivers (driver store + WFP subfolder)
Get-ChildItem C:\Windows\System32\drivers\*<term>* -Recurse -ErrorAction SilentlyContinue
Get-ChildItem C:\Windows\System32\drivers\wfp\*<term>* -Recurse -ErrorAction SilentlyContinue
Get-ChildItem C:\Windows\System32\drivers\UMDF\*<term>* -Recurse -ErrorAction SilentlyContinue

# Registry: services
reg query HKLM\SYSTEM\CurrentControlSet\Services /s /f "<term>"

# Registry: uninstall
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall /s /f "<term>"
reg query HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall /s /f "<term>"

# Registry: driver packages (Windows Update migration cache)
reg query HKLM\SYSTEM\Setup\Upgrade\DriverPackages /s /f "<term>"
reg query HKLM\SYSTEM\DriverPackages /s /f "<term>"

# Scheduled tasks
schtasks /query /fo LIST /v | findstr /i "<term>"

# AppData remnants (use PowerShell env vars, not CMD %VAR% -- this runs in .ps1)
dir $env:APPDATA\*<term>* -Directory
dir $env:LOCALAPPDATA\*<term>* -Directory  
dir $env:PROGRAMDATA\*<term>* -Directory
```

### 4.2 Deep Audit (Admin Required)
If not admin, skip. If admin:

**Search strategy: do NOT scan CLSID or HKEY_USERS hives by brute force.**
These contain tens of thousands of keys. Instead, use category-targeted queries:

```
--- CRASH-DIRECTED (search for what the dump told you) ---
# Driver inventory (exact names from dump's lm output)
driverquery /v 2>&1
Get-WmiObject Win32_PnPSignedDriver | Select DeviceName,DriverVersion,DriverDate,DriverProviderName
Get-WmiObject Win32_SystemDriver | Select Name,DisplayName,PathName,State,StartMode

# Storage / NTFS event providers
Get-WinEvent -LogName System -MaxEvents 500 | Where-Object {
  $_.ProviderName -match "disk|Ntfs|stornvme|storport|disk|volmgr|fvevol"
}

# Network adapter and filter drivers
Get-NetAdapter | Select Name,InterfaceDescription,DriverFileName,DriverVersion
Get-NetAdapterBinding | Where-Object { $_.Enabled }

# WER crash reports (Windows Error Reporting archive)
dir "$env:ProgramData\Microsoft\Windows\WER\ReportArchive\*" -Directory -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select -First 10

--- SECURITY / FILTER DRIVER INVENTORY ---
# File system filter drivers (antivirus, backup, encryption)
fltmc filters
# Network filter providers (WFP)
netsh wfp show state 2>&1 | Select-String "Provider|Filter"
# Active minifilters
fltmc instances

--- FIREWALL & STARTUP ---
netsh advfirewall firewall show rule name=all | findstr /i "<term>"
reg query HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run

--- Only if dump identified a specific DLL/COM component ---
reg query HKLM\SOFTWARE\Classes\CLSID /s /f "<specific-guid-from-dump>" 2>&1 | Select-String "HKEY"
# Use the GUID from dump analysis. Never /f without a specific term.
```

**CloudStore, DirectInput cache, and ghost driver checks remain the same as before.**
These are specific targeted queries, not full-hive scans.

### 4.3 Ghost Driver Detection
Compare the dump's loaded driver list (from `lm t n`) with what's on disk:
- If a driver was in the dump but the .sys file no longer exists -> **ghost driver**
- Its registry entries may still be active -> mark for cleanup with SYSTEM privileges
- This is especially important for filter drivers (network, file system, antivirus)

### Stage 4 Output
```
AUDIT FINDINGS:
  [P0] <item> | Location: <path> | Risk: <why> | Delete: <method> | Permission: <level>
  [P1] <item> | ...
  Total: N items across M categories
```

---

## Stage 5: CLEANUP PLAN (do NOT execute by default)

**Stage 5 produces a PLAN, not automatic actions.** Destructive operations
(deleting files, modifying registry, resetting network stack) require
explicit user confirmation before execution.

### 5.0 Generate Cleanup Plan
Based on Stage 4 findings, produce a plan with:
- What to remove, why, and what permission level is needed
- Risk level for each action
- Rollback method for each action
- Which actions can be done user-level, which need admin/SYSTEM

**Present the plan and ask: "Execute this cleanup plan?"**
Only proceed if the user says yes.

If the user confirms, then:

### 5.0b Safety
Before executing:
- If admin: check if a restore point already exists from the last 24 hours
  ```powershell
  $recent = Get-ComputerRestorePoint | Where-Object { $_.CreationTime -gt (Get-Date).AddHours(-24) -and $_.Description -match "BSOD" }
  if (-not $recent) { Checkpoint-Computer -Description "Before_BSOD_cleanup" -RestorePointType MODIFY_SETTINGS }
  ```
  -> Skip if one exists from today. Do not create duplicates.
- If not admin: back up registry keys with `reg export <key> $env:TEMP\bsod_backup_<keyname>.reg`
  -> Always use $env:TEMP so the file doesn't clutter the user's home directory
  -> Delete the .reg file after the cleanup operation succeeds

### 5.1 Permission Matrix

| Target | Permission | How |
|--------|-----------|-----|
| Files in %APPDATA%, %LOCALAPPDATA%, %PROGRAMDATA% | User | `Remove-Item -Force` |
| HKCU registry | User | `Remove-Item` |
| HKLM\SOFTWARE | Admin | `Start-Process -Verb RunAs` |
| HKLM\SYSTEM | Admin or SYSTEM | `schtasks` with SYSTEM |
| COM CLSID/AppID/TypeLib | **SYSTEM** | `schtasks /create /ru SYSTEM /sc once` |
| CloudStore | User | `reg delete <path> /f` |
| PnP devices | Admin | `pnputil /delete-driver` or `devcon remove` |
| Firewall rules | Admin | `Remove-NetFirewallRule` |
| Scheduled tasks | Admin | `Unregister-ScheduledTask` |

### 5.2 SYSTEM Cleanup Template
When deleting COM keys or protected registry entries:
```
0. FIRST: check for and delete any stale task from previous crashed run
   schtasks /delete /tn "BSODCleanup" /f 2>&1  (ignore errors -- means no stale task)

1. Write cleanup commands to $env:TEMP\cleanup.ps1
2. Create task: schtasks /create /tn "BSODCleanup" /ru SYSTEM /sc once /st 00:00 /sd 01/01/2000 /f /tr "powershell -File $env:TEMP\cleanup.ps1"
3. VERIFY creation: schtasks /query /tn "BSODCleanup" 2>&1
   If "ERROR" appears -> task creation failed. Do not proceed.
4. Run: schtasks /run /tn "BSODCleanup"
5. Wait 10 seconds
6. Verify the key is gone (reg query the path)
7. Delete: schtasks /delete /tn "BSODCleanup" /f
8. Delete cleanup script: Remove-Item $env:TEMP\cleanup.ps1 -Force
```

### 5.3 Network Stack Repair
If audit found network-related drivers (wintun, flclash, sing-box, proxifier, xlink, xlwfp):
```
netsh winsock reset
netsh int ip reset
netsh winhttp reset proxy
```
**These commands require a reboot to take effect.**

Note: running them twice without rebooting in between undoes the first reset.
If you're re-running the skill and the previous run already did this (and the system
has not rebooted since), skip this step.

### 5.4 Verification
After cleanup and reboot:
1. Re-run Stage 4 audit with the same search terms
2. Output: `Before: N items -> After: M items`
3. If M > 0 and items are low-risk -> report to user
4. If M > 0 and items are P0 -> escalate permission and retry once
5. If retry still fails -> stop and ask user

---

## Stage 6: PREVENTION

### 6.1 Crash Dump Configuration

**Default recommendation: kernel memory dump (type 2), not full dump (type 1).**
Full dumps are 16GB+ and need pagefile >= RAM, BitLocker off, and plenty of disk space.
Kernel dumps capture all kernel memory (drivers, stacks, pool) at ~1-3GB.

```
Recommended (kernel dump, works for most cases):
  CrashDumpEnabled = 2  (kernel memory dump)
  DumpFile = %SystemRoot%\MEMORY.DMP
  Overwrite = 1   (single file, auto-overwrites)
  AutoReboot = 0  (stay on BSOD screen)
  MinidumpsCount = 1

Only offer full dump (CrashDumpEnabled = 1) if:
  - RAM <= 16GB, pagefile on C: >= RAM + 256MB
  - C: has > 40GB free
  - BitLocker is OFF on C:
  - User explicitly agrees to the disk usage
```

Apply only what differs from current values. Requires admin.
If not admin, tell the user the exact commands to run.

### 6.1b Proactive Monitoring (Category-Targeted)

If the root cause involves a hardware device (GPU, storage, network), deploy monitoring
BEFORE the next crash. This captures the exact failure context that a dump alone may miss.

**Why this matters:** A GPU driver can corrupt random kernel memory for days before
being caught. The first 3 crashes show the victim (heap/MM/pool manager), not the
perpetrator. Proactive monitoring catches the perpetrator in the act.

**Deploy based on crash category:**

```
GPU / Display crashes (0x116, 0x117, 0x119, 0x141, 0x1E with dxgmms2/dxgkrnl):
  - Log GPU driver version: Get-WmiObject Win32_PnPSignedDriver | Where-Object {$_.DeviceName -match "NVIDIA|AMD"}
  - Log GPU events: Get-WinEvent -LogName System -MaxEvents 100 | Where-Object {$_.ProviderName -match "Display|dxg"}
  - Recommended: GPU stress test (FurMark/OCCT) to verify stability under load

Storage crashes (0x7A, 0xF4, 0x133, 0x9F with stornvme/storport):
  - Log SSD firmware version: Get-PhysicalDisk | Select Model,FirmwareVersion
  - Log SMART data: Get-Disk | Get-StorageReliabilityCounter
  - Enable storport ETW: wevtutil epl System storage-events.evtx

Network crashes (0xD1, 0x126, 0x15E, 0xC2 with ndis/tcpip/wintun):
  - Log active network adapters: Get-NetAdapter | Select Name,InterfaceDescription,DriverVersion
  - Log active filter drivers: fltmc filters
  - Log WFP state: netsh wfp show state (admin)

Memory corruption (0x1A, 0x50, 0xC2, 0x13A, 0x139 with nt!ExFreePoolWithTag):
  - Log all non-Microsoft driver versions and dates
  - Enable Driver Verifier on non-Microsoft drivers (only after explaining risks - see 6.2)
```

**Output this for the user BEFORE the next crash:**
```
PROACTIVE MONITORING DEPLOYED:
  - [Category] events being logged
  - Driver versions captured: [list]
  - Next crash will produce: minidump + monitoring log
  - If next crash occurs, collect BOTH files
```

This turns the skill from reactive (analyze after crash) to adaptive (hunt between crashes).

### 6.1c Firmware & Platform Check

If crash codes are random but all kernel memory corruption:
```
1. Check BIOS version: Get-CimInstance Win32_BIOS | Select SMBIOSBIOSVersion, ReleaseDate
2. Compare BIOS date vs OS build date. If BIOS is OLDER -> firmware may be incompatible.
3. Check OEM website for newer BIOS for this OS version.
4. Check: did Win10 run stable on this EXACT hardware? If YES and Win11 crashes:
   The hardware is fine. The platform support (BIOS/chipset) for the new OS is broken.
   Recommend: BIOS update from OEM, or roll back to prior OS version.
```

### 6.1d Modification Tracker

Every time a fix is applied, record it with date + what was changed + observation result:
```
MODIFICATION LOG:
  [DATE] Changed HmbAllocationPolicy from 1 to 2 -> RESULT: [crashed again / stable / observing]
  [DATE] Replaced NVIDIA driver vXXX with OEM vXXX -> RESULT: [...]
  [DATE] Disabled Modern Standby -> RESULT: [...]
```
This prevents re-trying fixes that already failed. In the final report, include
a "MODIFICATIONS TRIED" section with each change's outcome.

### 6.1e Escape Hatch: When Nothing Works

After 3+ different fixes fail AND crash codes remain random kernel memory corruption:
```
DO NOT KEEP GUESSING. Do NOT enable Driver Verifier on random drivers.

Step back and ask:
1. Does Win10/older OS run stable on this hardware? -> If YES: firmware/platform gap.
2. Is BIOS from before the current OS build date? -> If YES: firmware update needed.
3. Has EVERY crash been kernel memory corruption with a DIFFERENT victim? -> If YES:
   the culprit is writing to arbitrary kernel addresses. Only HMB (NVMe) and DMA (GPU)
   can do this from hardware-level. Driver-level corruption usually has a pattern.

Output: "ROOT CAUSE IS PLATFORM-LEVEL. Cannot be fixed without BIOS/firmware update
or OS rollback. Individual driver changes will continue to fail."
```

### 6.2 Only If Root Cause is Still Unknown: Driver Verifier

*** WARNING: Driver Verifier CAN cause boot-loop BSODs. Read this entire section first. ***

Driver Verifier is NOT a first-line diagnostic tool. Only use it when ALL of these are true:
- Multiple BSODs have occurred with different BugCheck codes
- Full memory dump analysis could not identify the culprit
- All Stage 4 audit findings have been cleaned
- The system has been observed for at least 48 hours post-cleanup

If ANY of the above is false, do NOT enable Driver Verifier. Continue observation instead.

Before enabling, verify these safety conditions:
- A system restore point exists and was created within the last 24 hours
- You have confirmed Safe Mode is accessible (force-shutdown 3x during boot)
- The user understands their system WILL be slower and WILL BSOD more often
- The user knows how to disable it (verifier /reset in Safe Mode)

If conditions met:
```
0. FIRST: check if Verifier is already enabled
   verifier /query 2>&1
   If output says "verified" or "verifying" -> ALREADY ON, skip to analysis
   Do NOT re-enable while running -- you'll get duplicate BSODs and lose the original state

1. Create restore point (non-negotiable) -- skip if one exists from today:
   Get-ComputerRestorePoint | Where-Object { $_.CreationTime -gt (Get-Date).AddHours(-24) -and $_.Description -match "verifier|Verifier" }
   If not found: Checkpoint-Computer -Description "Before_Driver_Verifier" -RestorePointType MODIFY_SETTINGS
2. Run: verifier.exe
3. Select: Create custom settings -> Select individual settings
4. Check: Special Pool, Pool Tracking, Force IRQL Checking, Deadlock Detection
5. Select driver names from list -> Sort by Provider -> Check all NON-Microsoft drivers
6. Reboot
7. Let it BSOD 3+ times over 24-48 hours
8. Disable: verifier /reset
9. If unbootable: force shutdown 3 times -> Recovery -> Safe Mode -> verifier /reset + verifier /bootmode resetonbootfail
```
Warn user: system will be slower and will BSOD more often. This is expected -- it catches the driver in the act.

---

## Stage 7: REPORT

Format the diagnosis in LAYERS. Never mix facts with guesses.
This prevents users from misreading a "primary suspect" as "100% confirmed culprit."

```
=== CRASH DIAGNOSIS REPORT ===

MACHINE PROFILE: [model, CPU, GPU, RAM, storage, BIOS version, OS build]
  (Only include info that matters for THIS crash. Do not generalize.)

=== WHAT WAS ALREADY TRIED ===
  - CONFIRMED INEFFECTIVE: [actions that were tried and crash recurred]
  - INCONCLUSIVE: [actions taken but not enough observation time]
  - DO NOT REPEAT: [actions already proven ineffective]

=== KNOWLEDGE BASE MATCHES ===
  - BugcheckKB: [code] matched / NO entry found
  - KnownBadDrivers: [N] drivers checked, [N] in version range, [N] matched

=== LAYER 1: CONFIRMED FACTS ===
  (Only what is directly observed. No interpretation.)
  - BugCheck event: [date] [code] [params]
  - Minidump present: [filename] (size: X MB, type: minidump/full)
  - Loaded modules at crash: [count] non-Microsoft drivers
  - Event log pattern: [N BugCheck events, N Kernel-Power events]
  - Dump analysis: IMAGE_NAME=X, stack shows Y, pool tag Z
  - Unloaded modules: [list]
  - Audit findings: [N items found, N items removed, N remaining]
  - Dump environment: BitLocker=[on/off], Pagefile=[ok/small/off-C], HVCI=[on/off]

=== LAYER 2: HIGH-CONFIDENCE CONCLUSIONS ===
  (Evidence-backed interpretations. Confidence >= 70%.)
  - Primary suspect: [driver/module] -- because [evidence A, B, C]
  - [module X] is classified as VICTIM, not culprit -- because [reason]
  - Timeline correlation: crashes [started/stopped] after [event]
  - Modern Standby [is/is not] a contributing factor -- because [evidence]

=== LAYER 3: DOWNGRADED HYPOTHESES ===
  (Possible but unconfirmed. Confidence < 70%.)
  - [hypothesis] -- downgraded because [missing evidence or alt explanation]

=== LAYER 4: BLOCKED INVESTIGATIONS ===
  (What we wanted to check but couldn't, and why.)
  - [item]: blocked by [permission/tool/missing artifact]
  - Minimum command to unblock: [one-liner for user to run as admin]

=== MODIFICATIONS TRIED ===
  (Every change + date + result. Prevents repeating failed fixes.)
  - [DATE] [change] -> RESULT: [crashed again / stable / observing]

=== WHAT WE DID ===
  - Removed: [N items] -- [types]
  - Configured: [dump type, restore point, etc.]
  - Skipped: [stages skipped and why]

=== NEXT ACTION ===
  1. [one concrete thing user should do now]
  2. [observation window: how long to watch for recurrence]

=== IF CRASH RECURS ===
  - Capture: photo of BSOD screen + location of C:\Windows\MEMORY.DMP
  - Run: [specific command to collect artifacts]
  - Do NOT: [dangerous action to avoid]
```

**Rules for the report:**
- Layer 1 contains ONLY directly observed data. No "probably" or "likely."
- Layer 2 contains interpretations supported by multiple pieces of evidence.
- Layer 3 MUST state WHY each hypothesis was downgraded.
- Layer 4 MUST include the exact command that would unblock each item.
- Machine-specific details stay in MACHINE PROFILE, not in conclusions.
  Never write "this crash pattern means NVIDIA drivers are buggy."
  Write "on THIS machine, with THIS driver version, at THIS OS build, nvlddmkm.sys was loaded at crash time."

---

## Operation Rules

0. **This skill folder is READ-ONLY.** Never write temp scripts, dump copies, reports,
   or any runtime artifacts into the folder containing this skill file.
   All output goes to `$env:TEMP`. The skill folder travels as a clean package.

1. Every PowerShell command goes into a `.ps1` file, never inline in bash
2. Temp scripts go in `$env:TEMP`, not user's home directory, not skill folder
3. Before starting: check for and delete stale artifacts from a previous crashed run:
   - `schtasks /delete /tn "BSODCleanup" /f` (ignore errors)
   - `Remove-Item $env:TEMP\cleanup.ps1 -Force` (ignore errors)
   - `Remove-Item $env:TEMP\bsod_backup_*.reg -Force` (ignore errors)
4. Delete all temp scripts after completion
5. `reg query` beats `Get-ChildItem` for registry search speed (100x faster on large hives)
5. CloudStore MUST use `reg query HKEY_USERS /s`, PowerShell can't read those keys
6. If a stage has no data (e.g., no dumps), skip it and note why in the report
7. If previous conversation already has data for a stage, use it instead of re-running
8. Do not recommend system reinstall
9. After cleanup: REBOOT, then verify. Without reboot, ghost drivers and migration caches are invisible.
