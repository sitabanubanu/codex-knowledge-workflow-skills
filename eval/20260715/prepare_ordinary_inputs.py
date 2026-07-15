"""Create a blinded input pack for the ordinary-Agent comparison arm.

The pack intentionally excludes the gold labels and the source-status labels
from manifest.json. It contains only the learning target, the requested
operation, and the material that a plain agent is allowed to see.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = Path(__file__).resolve().parent


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    tasks = [
        {"task_id": "KW-01", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Explain the source-gated workflow and preserve its four evidence claims.", "material_path": "source/transcript_sample.txt", "material_kind": "complete transcript"},
        {"task_id": "KW-02", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Summarize the timestamped subtitle source without inventing speaker facts.", "material_path": "source/subtitle_sample.srt", "material_kind": "timestamped subtitle"},
        {"task_id": "KW-03", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Extract the source argument from a WebVTT transcript.", "material_path": "source/subtitle_sample.vtt", "material_kind": "WebVTT subtitle"},
        {"task_id": "KW-04", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Use the supplied ASR transcript and keep the derived evidence bound to it.", "material_path": "source/asr_sample.jsonl", "material_kind": "ASR transcript sidecar for a local audio file"},
        {"task_id": "KW-05", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Analyze a local media fixture only from its supplied transcript.", "material_path": "source/asr_sample.jsonl", "material_kind": "ASR transcript sidecar for a local video file"},
        {"task_id": "KW-06", "target": "web_article", "operation": "read", "learning_goal": "Learn the project architecture from its English README.", "material_path": "source/README.md", "material_kind": "local Markdown document"},
        {"task_id": "KW-07", "target": "web_article", "operation": "read", "learning_goal": "Learn the project usage and source-gate boundaries in Chinese.", "material_path": "source/README.zh-CN.md", "material_kind": "local Markdown document"},
        {"task_id": "KW-08", "target": "web_article", "operation": "read", "learning_goal": "Understand ownership and handoff between the workflow layers.", "material_path": "source/architecture.md", "material_kind": "local Markdown document"},
        {"task_id": "KW-09", "target": "web_article", "operation": "read", "learning_goal": "Understand how acquisition is handed into the source-gated workflow.", "material_path": "source/agent-reach-integration-guide.md", "material_kind": "local Markdown document"},
        {"task_id": "KW-10", "target": "web_article", "operation": "read", "learning_goal": "Learn the project report quality and evidence limits.", "material_path": "source/output-quality-standard.md", "material_kind": "local Markdown document"},
        {"task_id": "KW-11", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Decide whether title/description metadata is enough for video analysis.", "material_path": "material/KW-11.txt", "material_kind": "title and description text"},
        {"task_id": "KW-12", "target": "web_article", "operation": "read", "learning_goal": "Decide whether a search result snippet can support an article report.", "material_path": "material/KW-12.txt", "material_kind": "search result text"},
        {"task_id": "KW-13", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Analyze only the explicitly covered portion of a partial transcript.", "material_path": "material/KW-13.txt", "material_kind": "transcript excerpt"},
        {"task_id": "KW-14", "target": "web_article", "operation": "read", "learning_goal": "Separate a secondary explanation from the primary article body.", "material_path": "material/KW-14.txt", "material_kind": "secondary explanation"},
        {"task_id": "KW-15", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Decide whether playable media without a transcript can enter full analysis.", "material_path": "material/KW-15.txt", "material_kind": "media availability note"},
        {"task_id": "KW-16", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Respond to a failed acquisition without fabricating a report.", "material_path": "material/KW-16.txt", "material_kind": "acquisition outcome note"},
        {"task_id": "KW-17", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Reject article text when the requested target is embedded video content.", "material_path": "material/KW-17.txt", "material_kind": "article body text"},
        {"task_id": "KW-18", "target": "web_article", "operation": "read", "learning_goal": "Reject a video transcript when the requested target is an article body.", "material_path": "material/KW-18.txt", "material_kind": "video transcript text"},
        {"task_id": "KW-19", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Reject post text as a substitute for an embedded video transcript.", "material_path": "material/KW-19.txt", "material_kind": "social post text"},
        {"task_id": "KW-20", "target": "video_content", "operation": "extract_transcript", "learning_goal": "Explain why an unsupported route cannot produce a full report.", "material_path": "material/KW-20.txt", "material_kind": "route outcome note"},
    ]

    source_map = {
        "source/transcript_sample.txt": ROOT / "tests/fixtures/transcript_sample.txt",
        "source/subtitle_sample.srt": ROOT / "tests/fixtures/subtitle_sample.srt",
        "source/subtitle_sample.vtt": ROOT / "tests/fixtures/subtitle_sample.vtt",
        "source/asr_sample.jsonl": ROOT / "tests/fixtures/asr_sample.jsonl",
        "source/README.md": ROOT / "README.md",
        "source/README.zh-CN.md": ROOT / "README.zh-CN.md",
        "source/architecture.md": ROOT / "docs/architecture.md",
        "source/agent-reach-integration-guide.md": ROOT / "docs/agent-reach-integration-guide.md",
        "source/output-quality-standard.md": ROOT / "docs/output-quality-standard.md",
    }
    for relative, source in source_map.items():
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    materials = {
        "KW-11": "Title: The Source-Gated Workflow\nDescription: An introduction to evidence-aware knowledge acquisition.\n",
        "KW-12": "Search result title: Source-Gated Knowledge Workflow\nSnippet: A workflow for checking whether source material is available before analysis.\n",
        "KW-13": "Transcript excerpt:\nSource Gate means confirmed primary material.\n\nFor example, metadata alone cannot support speaker logic.\n",
        "KW-14": "Secondary explainer:\nA commentator describes the project as a way to keep reports connected to their sources. This is a summary written by the commentator, not the primary article.\n",
        "KW-15": "Media note:\nA playable local media file is present. No transcript or subtitle text is attached to the material available to the agent.\n",
        "KW-16": "Acquisition note:\nThe acquisition attempt returned no usable artifact or source text.\n",
        "KW-17": "Article body:\nThe article explains how source material is acquired and checked before analysis.\n",
        "KW-18": "Video transcript:\nSource Gate means confirmed primary material. Reports should preserve transcript evidence.\n",
        "KW-19": "Social post:\nThis post says the project tries to keep claims tied to source material.\n",
        "KW-20": "Route note:\nThe requested route did not return a usable artifact.\n",
    }
    for task_id, content in materials.items():
        write(output_root / "material" / f"{task_id}.txt", content)

    (output_root / "ordinary_brief.json").write_text(json.dumps({"protocol": "ordinary-blinded-v2", "tasks": tasks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(output_root / "ordinary_brief.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
