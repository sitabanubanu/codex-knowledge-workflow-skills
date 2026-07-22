param(
  [switch]$DryRun,
  [switch]$VerifyOnly,
  [string]$CodexSkillsRoot = "$env:USERPROFILE\.codex\skills"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Join-Path $repoRoot "skills"
$skills = @(
  "knowledge-workflow-console",
  "acquire-source-material",
  "web-intent-scout",
  "source-gated-evidence-layer",
  "knowledge-learning-article",
  "knowledge-document-composer"
)
$obsoleteSkills = @("agent-reach-console")

function Assert-ContainedPath {
  param(
    [Parameter(Mandatory=$true)][string]$Parent,
    [Parameter(Mandatory=$true)][string]$Child
  )
  $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
  $childFull = [System.IO.Path]::GetFullPath($Child).TrimEnd('\') + '\'
  if (-not $childFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to operate outside Codex skills root: $childFull"
  }
}

function Count-SkillFiles {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return 0
  }
  return @(
    Get-ChildItem -LiteralPath $Path -Recurse -File -Force |
      Where-Object {
        $_.FullName -notmatch '\\__pycache__\\' -and
        $_.Extension -ne ".pyc"
      }
  ).Count
}

function Get-SkillManifest {
  param([Parameter(Mandatory=$true)][string]$Path)
  $manifest = @{}
  if (-not (Test-Path -LiteralPath $Path)) {
    return $manifest
  }
  $root = [System.IO.Path]::GetFullPath($Path).TrimEnd('\') + '\'
  Get-ChildItem -LiteralPath $Path -Recurse -File -Force |
    Where-Object {
      $_.FullName -notmatch '\\__pycache__\\' -and
      $_.Extension -ne ".pyc"
    } |
    ForEach-Object {
      $relative = $_.FullName.Substring($root.Length).Replace('\', '/')
      $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
      $manifest[$relative] = $hash
    }
  return $manifest
}

function Test-SkillEqual {
  param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$Target
  )
  $sourceManifest = Get-SkillManifest -Path $Source
  $targetManifest = Get-SkillManifest -Path $Target
  $allKeys = @($sourceManifest.Keys + $targetManifest.Keys | Sort-Object -Unique)
  $diffs = @()
  foreach ($key in $allKeys) {
    if (-not $sourceManifest.ContainsKey($key)) {
      $diffs += "extra target file: $key"
    } elseif (-not $targetManifest.ContainsKey($key)) {
      $diffs += "missing target file: $key"
    } elseif ($sourceManifest[$key] -ne $targetManifest[$key]) {
      $diffs += "content differs: $key"
    }
  }
  return $diffs
}

if (-not (Test-Path -LiteralPath $sourceRoot)) {
  throw "Missing source skills directory: $sourceRoot"
}

if ($DryRun -and $VerifyOnly) {
  throw "Use only one of -DryRun or -VerifyOnly."
}

New-Item -ItemType Directory -Force -Path $CodexSkillsRoot | Out-Null
$codexRootFull = [System.IO.Path]::GetFullPath($CodexSkillsRoot)

$changes = 0
foreach ($skill in $obsoleteSkills) {
  $dst = Join-Path $codexRootFull $skill
  Assert-ContainedPath -Parent $codexRootFull -Child $dst
  if (-not (Test-Path -LiteralPath $dst)) {
    continue
  }
  if ($VerifyOnly) {
    Write-Host "[verify] obsolete installed skill: $skill"
    $changes += 1
  } elseif ($DryRun) {
    Write-Host "[verify] would remove obsolete installed skill: $skill"
    $changes += 1
  } else {
    Write-Host "[remove] obsolete installed skill: $skill"
    Remove-Item -LiteralPath $dst -Recurse -Force
  }
}

foreach ($skill in $skills) {
  $src = Join-Path $sourceRoot $skill
  $dst = Join-Path $codexRootFull $skill
  if (-not (Test-Path -LiteralPath $src)) {
    throw "Missing required skill source: $src"
  }
  Assert-ContainedPath -Parent $codexRootFull -Child $dst

  $mode = if ($DryRun -or $VerifyOnly) { "verify" } else { "sync" }
  Write-Host "[$mode] $skill"
  Write-Host "  source: $src"
  Write-Host "  target: $dst"

  if ($VerifyOnly) {
    $diffs = Test-SkillEqual -Source $src -Target $dst
    foreach ($diff in $diffs) {
      Write-Host "  $diff"
    }
    if ($diffs.Count -gt 0) {
      $changes += 1
    }
    $srcCount = Count-SkillFiles -Path $src
    $dstCount = Count-SkillFiles -Path $dst
    Write-Host "  files: source=$srcCount target=$dstCount"
    continue
  }

  $args = @(
    $src,
    $dst,
    "/MIR",
    "/XD", "__pycache__",
    "/XF", "*.pyc",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/NP"
  )
  if ($DryRun) {
    $args += "/L"
  }

  $output = & robocopy @args
  $exitCode = $LASTEXITCODE
  if ($output) {
    $output | ForEach-Object { Write-Host "  $_" }
  }
  if ($exitCode -ge 8) {
    throw "robocopy failed for $skill with exit code $exitCode"
  }
  if ($exitCode -ne 0) {
    $changes += 1
  }

  $srcCount = Count-SkillFiles -Path $src
  $dstCount = Count-SkillFiles -Path $dst
  Write-Host "  files: source=$srcCount target=$dstCount"
}

if ($VerifyOnly) {
  if ($changes -eq 0) {
    Write-Host "VERIFY OK: installed skills match the repository copy."
    exit 0
  }
  Write-Host "VERIFY DIFFERENCE: run .\sync_to_codex_skills.ps1 to update installed skills."
  exit 1
}

if ($DryRun) {
  Write-Host "DRY RUN complete. No files were changed."
} else {
  Write-Host "SYNC complete. Knowledge Workflow skills were updated."
}
