#!/usr/bin/env python3
"""
Extract unchecked markdown checklist items into issue draft JSON.

Usage:
  python scripts/extract_tasks.py path/to/file.md [more.md ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*\[\s\]\s+(.+?)\s*$")
PRIORITY_RE = re.compile(r"\[(P[0-4])\]", re.IGNORECASE)
LABEL_RE = re.compile(r"(?:^|\s)#([a-zA-Z][\w-]*)\b")
ASSIGNEE_RE = re.compile(r"(?:^|\s)@([a-zA-Z0-9._-]+)\b")


def normalize_spaces(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_title(raw: str) -> str:
    text = PRIORITY_RE.sub(" ", raw)
    text = LABEL_RE.sub(" ", text)
    text = ASSIGNEE_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or normalize_spaces(raw)


def strip_md_inline(value: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", value)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return normalize_spaces(text)


def stable_external_key(source_file: str, heading_path: List[str], title: str) -> str:
    payload = "|".join([source_file, " > ".join(heading_path), title.lower()])
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"mdtask:{digest}"


def build_body_markdown(
    source_file: str,
    source_line: int,
    heading_path: List[str],
    raw_task: str,
    external_key: str,
) -> str:
    heading = " > ".join(heading_path) if heading_path else "(root)"
    return (
        "Imported from markdown planning notes.\n\n"
        f"Source: `{source_file}:{source_line}`\n"
        f"Heading: `{heading}`\n"
        f"External-Key: {external_key}\n\n"
        f"Original task: {raw_task}"
    )


def parse_file(path: Path, project_root: Path) -> List[Dict[str, object]]:
    headings: Dict[int, str] = {}
    tasks: List[Dict[str, object]] = []

    rel_file = str(path.resolve().relative_to(project_root.resolve()))

    with path.open("r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.rstrip("\n")

            heading_match = HEADING_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                headings[level] = strip_md_inline(heading_match.group(2))
                # Drop deeper headings when moving up the hierarchy.
                for key in list(headings.keys()):
                    if key > level:
                        del headings[key]
                continue

            task_match = TASK_RE.match(line)
            if not task_match:
                continue

            raw_task = normalize_spaces(task_match.group(1))
            if not raw_task:
                continue

            heading_path = [headings[level] for level in sorted(headings.keys())]
            priority_match = PRIORITY_RE.search(raw_task)
            priority = priority_match.group(1).upper() if priority_match else None
            labels = sorted(set(match.group(1).lower() for match in LABEL_RE.finditer(raw_task)))
            assignee_match = ASSIGNEE_RE.search(raw_task)
            assignee = assignee_match.group(1) if assignee_match else None

            title = strip_md_inline(normalize_title(raw_task))
            external_key = stable_external_key(rel_file, heading_path, title)

            tasks.append(
                {
                    "title": title,
                    "source_file": rel_file,
                    "source_line": line_no,
                    "heading_path": heading_path,
                    "labels": labels,
                    "assignee": assignee,
                    "priority": priority,
                    "external_key": external_key,
                    "body_markdown": build_body_markdown(
                        source_file=rel_file,
                        source_line=line_no,
                        heading_path=heading_path,
                        raw_task=raw_task,
                        external_key=external_key,
                    ),
                }
            )

    return tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract markdown checklist tasks.")
    parser.add_argument("files", nargs="+", help="Markdown files to parse.")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Root used to compute relative source paths (default: current directory).",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve()
    all_tasks: List[Dict[str, object]] = []

    for input_file in args.files:
        path = Path(input_file).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {input_file}")
        all_tasks.extend(parse_file(path, project_root))

    if args.pretty:
        print(json.dumps(all_tasks, indent=2, ensure_ascii=True))
    else:
        print(json.dumps(all_tasks, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
