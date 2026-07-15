"""Normalize ordinary-arm batch records into valid per-task UTF-8 JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.output_root.exists():
        import shutil
        shutil.rmtree(args.output_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    count = 0
    for batch_path in sorted(args.input_root.glob("batch-*/batch.json")):
        value = json.loads(batch_path.read_text(encoding="utf-8"))
        tasks = value.get("tasks") if isinstance(value, dict) else []
        out_dir = args.output_root / batch_path.parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        clean_tasks = []
        for task in tasks if isinstance(tasks, list) else []:
            if not isinstance(task, dict) or not task.get("task_id"):
                continue
            clean_tasks.append(task)
            (out_dir / f"{task['task_id']}.json").write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            count += 1
        (out_dir / "batch.json").write_text(json.dumps({"protocol": "ordinary-blinded-v2-normalized", "tasks": clean_tasks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"normalized {count} task records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
