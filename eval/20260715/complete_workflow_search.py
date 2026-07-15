"""Finish the stalled Workflow search shard using the same Agent-Reach backend.

This is an evaluation-only helper. It searches only the six missing tasks,
checks candidate accessibility, and writes disjoint search result files. It
does not change kw.py or any product skill.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
EVAL = Path(__file__).resolve().parent
MC_PORTER = shutil.which("mcporter.cmd") or shutil.which("mcporter") or "mcporter"
YT_DLP = shutil.which("yt-dlp.exe") or shutil.which("yt-dlp") or "yt-dlp"

MISSING = {
    "S-04": {
        "batch": "batch-01",
        "routes": [
            ("official_primary", "Costco membership business model annual report membership fees gross margin official"),
            ("structured_case", "Costco business model case study membership warehouse low prices supply chain course"),
            ("long_form_video", "Costco business model case study long interview transcript membership economics"),
            ("comparison_exact", "Costco membership flywheel low margin renewal rate business model analysis evidence"),
        ],
        "keywords": ["costco", "membership", "business model", "warehouse", "annual report", "renewal"],
    },
    "S-05": {
        "batch": "batch-01",
        "routes": [
            ("official_primary", "AI researcher long interview full transcript original page"),
            ("structured_course", "AI researcher interview transcript full conversation long form"),
            ("long_form_video", "AI researcher long interview YouTube full subtitles transcript"),
            ("comparison_exact", "Dwarkesh Patel AI interview transcript researcher long conversation"),
        ],
        "keywords": ["interview", "transcript", "AI", "researcher", "full", "conversation", "subtitles"],
    },
    "S-07": {
        "batch": "batch-02",
        "routes": [
            ("official_primary", "RAG versus fine tuning official documentation paper retrieval augmented generation"),
            ("structured_course", "RAG fine tuning decision framework complete technical course tutorial experiments"),
            ("long_form_video", "RAG vs fine tuning long lecture transcript technical explanation"),
            ("comparison_exact", "when to use RAG vs fine tuning cost updates evaluation evidence"),
        ],
        "keywords": ["RAG", "retrieval", "fine-tuning", "fine tuning", "evaluation", "knowledge"],
    },
    "S-08": {
        "batch": "batch-02",
        "routes": [
            ("official_primary", "Stanford CS229 machine learning lecture notes full course official"),
            ("structured_course", "CS229 complete lecture course syllabus notes exercises"),
            ("long_form_video", "Stanford CS229 lecture full video subtitles transcript"),
            ("comparison_exact", "CS229 lecture notes transcript study guide machine learning"),
        ],
        "keywords": ["CS229", "Stanford", "machine learning", "lecture", "notes", "transcript"],
    },
    "S-09": {
        "batch": "batch-02",
        "routes": [
            ("official_primary", "LangGraph official documentation CrewAI official documentation multi agent"),
            ("structured_course", "LangGraph CrewAI complete tutorial comparison code workflow"),
            ("long_form_video", "LangGraph vs CrewAI comparison long video transcript"),
            ("comparison_exact", "LangGraph versus CrewAI tradeoffs controllability collaboration architecture"),
        ],
        "keywords": ["LangGraph", "CrewAI", "multi-agent", "workflow", "graph", "crew"],
    },
    "S-10": {
        "batch": "batch-02",
        "routes": [
            ("official_primary", "Toyota Production System official lean manufacturing case study"),
            ("structured_case", "Toyota Production System complete case study course lecture"),
            ("long_form_video", "Toyota Production System long lecture transcript lean manufacturing case"),
            ("comparison_exact", "TPS just in time jidoka kaizen limitations evidence case study"),
        ],
        "keywords": ["Toyota", "production system", "lean", "just in time", "jidoka", "kaizen"],
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def call_exa(query: str) -> str:
    command = [MC_PORTER, "call", "exa.web_search_exa", f"query={query}", "numResults=5", "--output", "json"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"EXA_ERROR: {exc}"
    if completed.returncode != 0:
        return f"EXA_ERROR: {completed.stderr.strip() or completed.stdout.strip()}"
    return completed.stdout


def parse_exa(raw: str, route: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(raw)
        text = "\n".join(item.get("text", "") for item in value.get("content", []) if isinstance(item, dict))
    except json.JSONDecodeError:
        text = raw
    blocks = re.split(r"\n\s*---\s*\n", text)
    items: list[dict[str, Any]] = []
    for block in blocks:
        title = re.search(r"Title:\s*(.+)", block)
        url = re.search(r"URL:\s*(https?://\S+)", block)
        highlights = re.search(r"Highlights:\s*(.*?)(?:\n\s*Published:|\Z)", block, flags=re.S)
        if not url:
            continue
        clean_url = url.group(1).rstrip(")].,\"")
        items.append({
            "title": title.group(1).strip() if title else clean_url,
            "url": clean_url,
            "source_type": "search_result",
            "query_or_route": route,
            "highlights": (highlights.group(1).strip() if highlights else block.strip())[:4000],
        })
    return items


def preliminary_score(candidate: dict[str, Any], keywords: list[str]) -> float:
    text = f"{candidate.get('title','')} {candidate.get('highlights','')}".casefold()
    hits = sum(1 for keyword in keywords if keyword.casefold() in text)
    return hits + min(len(str(candidate.get("highlights") or "")) / 1000, 2)


def check_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    url = str(candidate.get("url") or "")
    host = urlparse(url).netloc.casefold()
    started = time.perf_counter()
    if "youtube.com" in host or "youtu.be" in host:
        command = [YT_DLP, "--list-subs", "--skip-download", "--no-warnings", url]
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            lower = output.casefold()
            if result.returncode == 0 and any(token in lower for token in ("english", "en", "subtitles", "字幕")) and "no subtitles" not in lower:
                access = "full_transcript"
                evidence = f"yt-dlp --list-subs returned subtitle metadata ({len(output)} chars)."
            elif result.returncode != 0:
                access = "blocked"
                evidence = f"yt-dlp subtitle probe failed: {output[-500:]}"
            else:
                access = "metadata_only"
                evidence = "Video metadata was reachable but no usable subtitle listing was confirmed."
        except (OSError, subprocess.TimeoutExpired) as exc:
            access = "blocked"
            evidence = f"yt-dlp probe error: {exc}"
        return {**candidate, "material_access": access, "source_check": evidence, "check_elapsed_seconds": round(time.perf_counter() - started, 2)}

    jina_url = "https://r.jina.ai/http://" + url.removeprefix("https://").removeprefix("http://")
    command = ["curl.exe", "-L", "--max-time", "20", "-sS", jina_url]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
        body = result.stdout or ""
        if result.returncode == 0 and len(body) >= 1200 and not any(token in body.casefold() for token in ("access denied", "captcha", "log in to continue")):
            access = "full_text"
            evidence = f"Jina Reader returned {len(body)} characters of page text."
        elif result.returncode == 0 and body.strip():
            access = "partial"
            evidence = f"Jina Reader returned only {len(body)} characters; completeness is not established."
        else:
            access = "blocked"
            evidence = f"Jina Reader failed: {(result.stderr or body)[-500:]}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        access = "blocked"
        evidence = f"Jina Reader probe error: {exc}"
    return {**candidate, "material_access": access, "source_check": evidence, "check_elapsed_seconds": round(time.perf_counter() - started, 2)}


def reliability(host: str) -> int:
    if any(domain in host for domain in (".gov", ".edu", "openai.com", "anthropic.com", "stanford.edu", "mit.edu", "toyota.com", "costco.com", "developers.", "docs.")):
        return 2
    if any(domain in host for domain in ("github.com", "huggingface.co", "wikipedia.org")):
        return 1
    return 1 if host else 0


def enrich(candidate: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    text = f"{candidate.get('title','')} {candidate.get('highlights','')}".casefold()
    hits = sum(1 for keyword in keywords if keyword.casefold() in text)
    relevance = 3 if hits >= 3 else 2 if hits >= 1 else 1
    access = str(candidate.get("material_access") or "unknown")
    body_len = len(str(candidate.get("highlights") or ""))
    depth = 2 if body_len >= 500 or access in {"full_text", "full_transcript"} else 1 if body_len >= 180 or access == "partial" else 0
    complete = 2 if access in {"full_text", "full_transcript"} else 1 if access == "partial" else 0
    fit = 1 if access in {"full_text", "full_transcript", "partial"} and relevance >= 2 else 0
    return {
        **candidate,
        "relevance_0_3": relevance,
        "depth_0_2": depth,
        "reliability_0_2": reliability(urlparse(str(candidate.get("url") or "")).netloc.casefold()),
        "complete_material_0_2": complete,
        "study_fit_0_1": fit,
    }


def run_task(task_id: str, spec: dict[str, Any], output_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    started_at = now()
    raw_candidates: dict[str, dict[str, Any]] = {}
    queries = []
    for route, query in spec["routes"]:
        queries.append({"route": route, "query": query})
        for candidate in parse_exa(call_exa(query), route):
            raw_candidates.setdefault(candidate["url"], candidate)
    preliminary = sorted(raw_candidates.values(), key=lambda item: preliminary_score(item, spec["keywords"]), reverse=True)[:10]
    checked: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(check_candidate, item) for item in preliminary]
        for future in as_completed(futures):
            checked.append(future.result())
    candidates = [enrich(item, spec["keywords"]) for item in checked]
    candidates.sort(key=lambda item: (sum(int(item.get(key) or 0) for key in ("relevance_0_3", "depth_0_2", "reliability_0_2", "complete_material_0_2", "study_fit_0_1")), preliminary_score(item, spec["keywords"])), reverse=True)
    candidates = candidates[:5]
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
        candidate.pop("highlights", None)
        candidate.pop("check_elapsed_seconds", None)
    result = {
        "task_id": task_id,
        "queries": queries,
        "candidate_count": len(candidates),
        "started_at": started_at,
        "finished_at": now(),
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "notes": "Completed by the evaluation fallback using four Agent-Reach Exa routes, deduplication, and source checks. Unknown/blocked material was not upgraded to complete.",
        "candidates": candidates,
    }
    batch_dir = output_root / spec["batch"]
    batch_dir.mkdir(parents=True, exist_ok=True)
    (batch_dir / f"{task_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output_root = args.output_root.resolve()
    results = []
    for task_id, spec in MISSING.items():
        results.append(run_task(task_id, spec, output_root))
    for batch in {spec["batch"] for spec in MISSING.values()}:
        batch_dir = output_root / batch
        rows = []
        for path in sorted(batch_dir.glob("S-*.json")):
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass
        (batch_dir / "batch.json").write_text(json.dumps({"protocol": "workflow-fallback", "tasks": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"completed {len(results)} tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
