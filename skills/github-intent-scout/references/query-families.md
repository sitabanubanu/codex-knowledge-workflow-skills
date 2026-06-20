# Query Families

Use this reference when building GitHub and web searches. Search for mechanisms and evidence, not only the user's literal wording.

## Core Rule

Generate at least three query families. Use one query family to learn vocabulary, then pivot based on drift.

## Family Types

- Literal terms from the user.
- Mechanism terms describing how the thing works.
- Ecosystem terms naming likely tools, file formats, CLIs, manifests, protocols, or config files.
- Evidence terms that reveal real implementation.
- Negative or exclusion terms when common drift appears.

## Evidence Terms

Good evidence terms include:

- Skill and plugin artifacts: `SKILL.md`, `skill.md`, `.codex-plugin/plugin.json`, `.claude/skills`, `mcpServers`.
- Agent workflow artifacts: `prompts/`, `tools/`, `commands`, `hooks`, `memory`, `persona`, `planner`, `router`.
- Claim-verification artifacts: parser names, import names, CLI flags, supported formats, API route names, dependency package names.
- Runtime artifacts: `pyproject.toml`, `package.json`, `Dockerfile`, `examples`, `scripts`, `tests`.

## Repo Discovery Patterns

```text
<literal phrase> GitHub
<mechanism phrase> GitHub
<tool names> <mechanism> GitHub
site:github.com <tool names> <mechanism>
```

Use multiple sort orders:

- Default relevance: map likely matches.
- `--sort stars`: mature or high-signal projects.
- `--sort updated`: emerging projects and new terminology.

Do not pass `--sort best-match` to `gh search repos`; default relevance is already best match.

## GitHub CLI Examples

```powershell
gh search repos "<query>" --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos "<query>" --sort stars --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search repos "<query>" --sort updated --limit 20 --json fullName,description,stargazersCount,updatedAt,url
gh search code "<needle>" --limit 20 --json repository,path,url
```

For skill/plugin searches, run at least one code-search round unless GitHub code search is unavailable:

```powershell
gh search code "SKILL.md" "<mechanism term>" --limit 20 --json repository,path,url
gh search code "<command or trigger phrase>" --limit 20 --json repository,path,url
gh search code "<claimed format or adapter>" "<project family term>" --limit 20 --json repository,path,url
```

See `github-search-syntax.md` for qualifier and command syntax patterns.

## Code Search Low-Yield Fallback

If GitHub code search is empty, noisy, or unavailable:

1. Split combined queries into smaller evidence terms.
2. Run repo search with mechanism terms.
3. Inspect serious candidate file trees with repo contents or `gh api`.
4. Record `Code Search: attempted / low-yield / unavailable`.
5. Do not conclude no project exists from empty code search alone.

## Niche Scout / Repo Research Vocabulary

When searching for projects similar to GitHub scouting, repository research, codebase discovery, or codebase mapping tools, try combinations such as:

- `repo research agent`
- `GitHub repository analysis`
- `codebase discovery`
- `repository map` / `repo map`
- `codebase summarization`
- `repository ingestion`
- `code search agent`
- `GitHub repo scout`
- `software project discovery`
- `codebase knowledge graph`

Pair these with evidence terms such as `README`, `pyproject.toml`, `package.json`, `server`, `repomap`, `indexer`, `parser`, `embedding`, `search`, `agent`, `MCP`, or `CLI`.

## Literal Search Fallback

If literal repo searches are empty or noisy, pivot automatically:

1. Domain terms: `systematic review`, `literature review`, `scientific papers`, `contracts`, `chat export`, `knowledge base`.
2. Mechanism terms: `RAG`, `vector search`, `citation`, `evidence synthesis`, `parser`, `chunking`, `OCR`, `index`.
3. Entry-point terms: `SKILL.md`, `mcpServers`, `pyproject.toml`, `Dockerfile`, `CLI`, `examples`, `prompts`, `tools`.
4. Known upstream tools: e.g. `PaperQA`, `GROBID`, `MarkItDown`, `Zotero`, `DocsGPT`, `LlamaIndex`, `LangChain`.
5. Host terms: `Claude skill`, `Codex skill`, `OpenClaw skill`, `MCP server`, `Cursor`, `OpenCode`, `AGENTS.md`.

Record the pivot in Search Rounds: what failed, what vocabulary replaced it, and what new candidates surfaced.
