#!/usr/bin/env sh
set -eu

DRY_RUN=0
VERIFY_ONLY=0
CODEX_SKILLS_ROOT="${CODEX_SKILLS_ROOT:-$HOME/.codex/skills}"

usage() {
  cat <<'USAGE'
Usage: ./sync_to_codex_skills.sh [--dry-run] [--verify-only] [--codex-skills-root PATH]

Sync the Knowledge Workflow skills into the Codex skills directory.

Options:
  --dry-run                 Show what would change without writing files.
  --verify-only             Compare installed skills with the repository copy.
  --codex-skills-root PATH  Override the target skills root.
  -h, --help                Show this help.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      ;;
    --verify-only)
      VERIFY_ONLY=1
      ;;
    --codex-skills-root)
      if [ "$#" -lt 2 ]; then
        echo "Missing value for --codex-skills-root" >&2
        exit 2
      fi
      CODEX_SKILLS_ROOT=$2
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$DRY_RUN" -eq 1 ] && [ "$VERIFY_ONLY" -eq 1 ]; then
  echo "Use only one of --dry-run or --verify-only." >&2
  exit 2
fi

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
REPO_ROOT=$SCRIPT_DIR
SOURCE_ROOT=$REPO_ROOT/skills
SKILLS="knowledge-workflow-console acquire-source-material web-intent-scout source-gated-evidence-layer knowledge-learning-article knowledge-document-composer"
OBSOLETE_SKILLS="agent-reach-console"

if [ ! -d "$SOURCE_ROOT" ]; then
  echo "Missing source skills directory: $SOURCE_ROOT" >&2
  exit 1
fi

mkdir -p "$CODEX_SKILLS_ROOT"
CODEX_ROOT_FULL=$(CDPATH= cd -- "$CODEX_SKILLS_ROOT" && pwd -P)

hash_file() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Missing sha256sum or shasum." >&2
    exit 1
  fi
}

count_skill_files() {
  path=$1
  if [ ! -d "$path" ]; then
    echo 0
    return
  fi
  find "$path" \
    -type f \
    ! -path '*/__pycache__/*' \
    ! -name '*.pyc' \
    | wc -l | tr -d ' '
}

write_manifest() {
  path=$1
  output=$2
  : > "$output"
  if [ ! -d "$path" ]; then
    return
  fi
  root=$(CDPATH= cd -- "$path" && pwd -P)
  find "$root" \
    -type f \
    ! -path '*/__pycache__/*' \
    ! -name '*.pyc' \
    | sort \
    | while IFS= read -r file; do
        rel=${file#$root/}
        printf '%s  %s\n' "$(hash_file "$file")" "$rel"
      done > "$output"
}

verify_skill_equal() {
  src=$1
  dst=$2
  src_manifest=$(mktemp)
  dst_manifest=$(mktemp)
  write_manifest "$src" "$src_manifest"
  write_manifest "$dst" "$dst_manifest"
  if diff -u "$src_manifest" "$dst_manifest"; then
    rm -f "$src_manifest" "$dst_manifest"
    return 0
  fi
  rm -f "$src_manifest" "$dst_manifest"
  return 1
}

assert_contained_path() {
  child=$1
  case "$child/" in
    "$CODEX_ROOT_FULL"/*)
      ;;
    *)
      echo "Refusing to operate outside Codex skills root: $child" >&2
      exit 1
      ;;
  esac
}

changes=0

for skill in $OBSOLETE_SKILLS; do
  dst=$CODEX_ROOT_FULL/$skill
  assert_contained_path "$dst"
  if [ ! -d "$dst" ]; then
    continue
  fi
  if [ "$VERIFY_ONLY" -eq 1 ]; then
    echo "[verify] obsolete installed skill: $skill"
    changes=$((changes + 1))
  elif [ "$DRY_RUN" -eq 1 ]; then
    echo "[verify] would remove obsolete installed skill: $skill"
    changes=$((changes + 1))
  else
    echo "[remove] obsolete installed skill: $skill"
    rm -rf -- "$dst"
  fi
done

for skill in $SKILLS; do
  src=$SOURCE_ROOT/$skill
  dst=$CODEX_ROOT_FULL/$skill

  if [ ! -d "$src" ]; then
    echo "Missing required skill source: $src" >&2
    exit 1
  fi

  assert_contained_path "$dst"

  if [ "$DRY_RUN" -eq 1 ] || [ "$VERIFY_ONLY" -eq 1 ]; then
    mode=verify
  else
    mode=sync
  fi

  echo "[$mode] $skill"
  echo "  source: $src"
  echo "  target: $dst"

  if [ "$VERIFY_ONLY" -eq 1 ]; then
    if verify_skill_equal "$src" "$dst"; then
      :
    else
      changes=$((changes + 1))
    fi
    echo "  files: source=$(count_skill_files "$src") target=$(count_skill_files "$dst")"
    continue
  fi

  if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is required for sync and dry-run modes." >&2
    exit 1
  fi

  mkdir -p "$dst"
  if [ "$DRY_RUN" -eq 1 ]; then
    rsync -a --delete \
      --exclude '__pycache__/' \
      --exclude '*.pyc' \
      --dry-run \
      --itemize-changes \
      "$src/" "$dst/"
  else
    rsync -a --delete \
      --exclude '__pycache__/' \
      --exclude '*.pyc' \
      "$src/" "$dst/"
  fi

  if verify_skill_equal "$src" "$dst"; then
    :
  else
    changes=$((changes + 1))
  fi

  echo "  files: source=$(count_skill_files "$src") target=$(count_skill_files "$dst")"
done

if [ "$VERIFY_ONLY" -eq 1 ]; then
  if [ "$changes" -eq 0 ]; then
    echo "VERIFY OK: installed skills match the repository copy."
    exit 0
  fi
  echo "VERIFY DIFFERENCE: run ./sync_to_codex_skills.sh to update installed skills."
  exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "DRY RUN complete. No files were changed."
else
  echo "SYNC complete. Knowledge Workflow skills were updated."
fi
