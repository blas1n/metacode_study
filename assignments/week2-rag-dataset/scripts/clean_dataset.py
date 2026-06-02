#!/usr/bin/env python3
"""Clean the source-derived BSVibe memory dataset for a future RAG database import."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
SECRET_RE = re.compile(r"\b(?:(?:sk|pk|ghp|github_pat)-[A-Za-z0-9_-]{10,}|demo-secret-token-[A-Za-z0-9_-]+)\b")
LOCAL_PATH_RE = re.compile(r"/Users/[A-Za-z0-9._-]+/[^\s,.)]+")
WHITESPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"[^a-z0-9가-힣]+")

REQUIRED_FIELDS = ("id", "created_at", "source_type", "product", "title", "content", "tags")
SOURCE_FIELDS = (
    "source_repo",
    "source_commit",
    "source_path",
    "source_line_start",
    "source_line_end",
    "source_url",
    "secondary_source_url",
)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line_no, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def normalize_text(value: str) -> str:
    value = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    value = SECRET_RE.sub("[REDACTED_SECRET]", value)
    value = LOCAL_PATH_RE.sub("[REDACTED_LOCAL_PATH]", value)
    return WHITESPACE_RE.sub(" ", value).strip()


def normalize_tag(tag: str) -> str:
    normalized = TAG_RE.sub("-", tag.strip().lower()).strip("-")
    return normalized


def validate_record(record: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in record:
            issues.append(f"missing_{field}")
    if "created_at" in record:
        try:
            datetime.fromisoformat(str(record["created_at"]))
        except ValueError:
            issues.append("invalid_created_at")
    if not str(record.get("content", "")).strip():
        issues.append("empty_content")
    if not isinstance(record.get("tags", []), list):
        issues.append("tags_not_list")
    return issues


def infer_note_type(source_type: str) -> str:
    mapping = {
        "readme": "project_overview",
        "backend_code": "implementation_evidence",
        "runtime_code": "runtime_evidence",
        "frontend_code": "surface_evidence",
        "test_code": "verification_evidence",
        "ops_doc": "operational_evidence",
        "ops_yaml": "operational_evidence",
    }
    return mapping.get(source_type, "source_evidence")


def stable_hash(*parts: str) -> str:
    joined = "\n".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def split_into_chunks(text: str, max_chars: int, min_chars: int = 40) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n+|(?<=[.!?。])\s+", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current} {paragraph}".strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars])
            current = ""
    if current:
        chunks.append(current)

    # Absorb a trailing fragment that's too small to retrieve usefully on its own.
    if len(chunks) >= 2 and len(chunks[-1]) < min_chars:
        tail = chunks.pop()
        chunks[-1] = f"{chunks[-1]} {tail}".strip()
    return chunks


def clean_records(records: list[dict[str, Any]], max_chunk_chars: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    issue_counter: Counter[str] = Counter()
    redaction_counter: Counter[str] = Counter()

    for record in records:
        issues = validate_record(record)
        issue_counter.update(issues)

        raw_content = str(record.get("content", ""))
        raw_title = str(record.get("title", ""))
        redaction_counter["email"] += len(EMAIL_RE.findall(raw_content))
        redaction_counter["secret"] += len(SECRET_RE.findall(raw_content))
        redaction_counter["local_path"] += len(LOCAL_PATH_RE.findall(raw_content))

        tags = sorted({normalize_tag(str(tag)) for tag in record.get("tags", []) if normalize_tag(str(tag))})
        content = normalize_text(raw_content)
        title = normalize_text(raw_title)
        note_type = infer_note_type(str(record.get("source_type", "")))
        note_id = f"note-{stable_hash(str(record.get('id', '')), title, content)}"

        source_metadata = {
            field: record.get(field)
            for field in SOURCE_FIELDS
            if record.get(field) is not None
        }
        clean_note = {
            "note_id": note_id,
            "source_id": record.get("id"),
            "created_at": record.get("created_at"),
            "product": normalize_text(str(record.get("product", ""))),
            "source_type": record.get("source_type"),
            "note_type": note_type,
            "title": title,
            "content": content,
            "tags": tags,
            "verified": bool(record.get("verified", False)),
            "quality_flags": issues,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            **source_metadata,
        }
        cleaned.append(clean_note)

        for index, chunk_text in enumerate(split_into_chunks(content, max_chunk_chars), start=1):
            chunks.append(
                {
                    "chunk_id": f"{note_id}-chunk-{index:02d}",
                    "note_id": note_id,
                    "source_id": record.get("id"),
                    "chunk_index": index,
                    "text": chunk_text,
                    "char_count": len(chunk_text),
                    "metadata": {
                        "created_at": record.get("created_at"),
                        "product": clean_note["product"],
                        "source_type": clean_note["source_type"],
                        "note_type": note_type,
                        "title": title,
                        "tags": tags,
                        "verified": clean_note["verified"],
                        **source_metadata,
                    },
                }
            )

    report = {
        "input_records": len(records),
        "clean_notes": len(cleaned),
        "rag_chunks": len(chunks),
        "quality_issues": dict(sorted(issue_counter.items())),
        "redactions": dict(sorted(redaction_counter.items())),
        "max_chunk_chars": max_chunk_chars,
        "output_contract": {
            "clean_notes": "one JSON object per source note with normalized tags, redacted text, provenance, and quality flags",
            "rag_chunks": "one JSON object per retrievable chunk with embedding-ready text and metadata filters",
        },
        "source_fields": list(SOURCE_FIELDS),
    }
    return cleaned, chunks, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("assignments/week2-rag-dataset/data/raw/bsvibe_memory_seed.jsonl"))
    parser.add_argument("--notes-out", type=Path, default=Path("assignments/week2-rag-dataset/data/processed/clean_notes.jsonl"))
    parser.add_argument("--chunks-out", type=Path, default=Path("assignments/week2-rag-dataset/data/processed/rag_chunks.jsonl"))
    parser.add_argument("--report-out", type=Path, default=Path("assignments/week2-rag-dataset/data/processed/cleaning_report.json"))
    parser.add_argument("--max-chunk-chars", type=int, default=420)
    args = parser.parse_args()

    records = load_jsonl(args.input)
    notes, chunks, report = clean_records(records, args.max_chunk_chars)

    write_jsonl(args.notes_out, notes)
    write_jsonl(args.chunks_out, chunks)
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"clean_notes={len(notes)} rag_chunks={len(chunks)} report={args.report_out}")


if __name__ == "__main__":
    main()
