# GitHub Search Syntax Reference

Use this reference when the task needs precise GitHub repository, code, skill, or plugin discovery.

## Repository Search Qualifiers

Common GitHub repository qualifiers:

- `in:name`, `in:description`, `in:readme`, `in:topics`: restrict where text must match.
- `repo:owner/name`: target one repository.
- `user:USERNAME`, `org:ORGNAME`: target an owner or organization.
- `stars:>=100`, `stars:10..100`: filter by stars.
- `forks:>=10`: filter by forks.
- `language:TypeScript`, `language:Python`, `language:Rust`: filter primary language.
- `topic:agent`, `topic:claude-code`, `topic:codex`: filter by topic.
- `license:mit`, `license:apache-2.0`: filter by license.
- `pushed:>=2026-01-01`, `created:>=2025-01-01`: filter by recent activity.
- `archived:false`: exclude archived repositories.
- `fork:true` or `fork:only`: include or isolate forks.
- `template:false`, `mirror:false`: exclude templates/mirrors when needed.

Use quotes around multi-word phrases:

```text
"Claude Code" "Codex CLI" worktree
"coding agent" "git worktree" orchestrator
```

Use negative terms after evidence of drift:

```text
"multi-agent" "Claude Code" Codex -CrewAI -AutoGen
```

## GitHub CLI Patterns

Repo search:

```powershell
gh search repos '"Claude Code" "Codex" worktree' --sort stars --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos '"coding agent" orchestrator' --sort updated --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos 'agent skills' --topic=claude-code --sort updated --limit 20 --json fullName,description,stargazersCount,updatedAt,url
```

Code search for structural evidence:

```powershell
gh search code '"CLAUDE.md" ".codex/skills"' --language markdown --limit 20 --json repository,path
gh search code '"spawn_agent" "assign_task"' --language markdown --limit 20 --json repository,path
gh search code '"git worktree" "Claude Code"' --language markdown --limit 20 --json repository,path
```

Inspect candidates:

```powershell
gh repo view OWNER/REPO --json nameWithOwner,description,stargazerCount,updatedAt,licenseInfo,url
gh repo view OWNER/REPO --web
gh api repos/OWNER/REPO/contents/README.md
gh api repos/OWNER/REPO/contents/.claude
gh api repos/OWNER/REPO/contents/.codex
```

## Search Rotation Pattern

Borrow the Scout idea: do not run one query forever. Rotate:

1. Broad vocabulary query.
2. Mechanism query.
3. Tool-name query.
4. File/config evidence query.
5. Recent-updated query.
6. Code-search structural query.

Track what worked and what did not. If all results are wrong-category, change vocabulary instead of adding more words to the same category.

## Candidate Evidence Checklist

For each likely repository, look for:

- Supported tools listed by name.
- Concrete commands or launch scripts.
- Worktree/workspace/session isolation details.
- Task lifecycle: plan, execute, inspect, review, merge.
- Artifacts: diff, logs, review report, state database, dashboard.
- Windows/macOS/Linux support.
- License and activity.
- Whether it uses existing CLI agent auth or requires model API keys.
