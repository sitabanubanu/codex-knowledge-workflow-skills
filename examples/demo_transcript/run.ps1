$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
$InputFile = Join-Path $ScriptDir 'input.txt'
$ProjectRoot = Join-Path $RepoRoot 'outputs\knowledge-workflow\demo-transcript'

python (Join-Path $RepoRoot 'kw.py') run `
  --input $InputFile `
  --project-root $ProjectRoot `
  --mode audit `
  --language en `
  --final-language en `
  --document-goal 'Write an auditable knowledge report from the demo transcript.'
