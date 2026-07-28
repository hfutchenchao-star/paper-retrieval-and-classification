#!/usr/bin/env python3
"""Validate the generated literature folder tree and its internal data."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS = (
    "problem_evidence",
    "problem",
    "method",
    "results",
    "conclusion",
    "limitations",
    "one_sentence_summary",
    "category",
    "category_reason",
)
REQUIRED_HEADINGS = (
    "## 论文解决了什么问题",
    "## 问题证据",
    "## 使用了什么方法",
    "## 得到了什么结果",
    "## 主要结论",
    "## 局限性",
    "## 一句话总结",
    "## 分类说明",
)
PAPER_ID_MARKER = re.compile(r"<!--\s*paper_id:\s*([A-Za-z0-9_-]+)\s*-->")
REQUIRED_OVERVIEW_HEADINGS = (
    "## 领域核心问题",
)
FORBIDDEN_OVERVIEW_HEADINGS = ("## 分类", "## 论文索引")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    return parser.parse_args()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records, errors = [], []
    if not path.exists():
        return records, [f"Missing file: {path}"]
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.name}:{line_number}: record must be an object")
            continue
        records.append(value)
    return records, errors


def normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def main() -> int:
    args = parse_args()
    root = args.root
    data_dir = root / "_data"
    papers_path = data_dir / "papers.jsonl"
    search_log_path = data_dir / "search-log.jsonl"
    taxonomy_path = data_dir / "taxonomy.json"
    overview_path = root / "00-检索与分类总览.md"
    errors: list[str] = []
    warnings: list[str] = []

    records, record_errors = read_jsonl(papers_path)
    errors.extend(record_errors)
    _, search_errors = read_jsonl(search_log_path)
    errors.extend(search_errors)

    taxonomy: dict[str, Any] = {}
    if not taxonomy_path.exists():
        errors.append(f"Missing file: {taxonomy_path}")
    else:
        try:
            taxonomy = json.loads(taxonomy_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid taxonomy JSON: {exc}")
    if not overview_path.exists():
        errors.append(f"Missing file: {overview_path}")
    else:
        overview_content = overview_path.read_text(encoding="utf-8")
        for heading in REQUIRED_OVERVIEW_HEADINGS:
            if heading not in overview_content:
                errors.append(f"Overview missing heading '{heading}'")
        for heading in FORBIDDEN_OVERVIEW_HEADINGS:
            if re.search(rf"^{re.escape(heading)}\s*$", overview_content, re.MULTILINE):
                errors.append(f"Overview must not contain heading '{heading}'")
        if re.search(r"^- 代表论文：", overview_content, re.MULTILINE):
            errors.append("Overview core problems must not include representative papers")
        if "因未识别到明确论文问题而跳过：" not in overview_content:
            errors.append("Overview missing no-identifiable-problem skip count")
        if "具有可核验问题证据：" not in overview_content:
            errors.append("Overview missing verifiable-problem-evidence count")

    ids = [record.get("paper_id") for record in records if record.get("paper_id")]
    duplicate_ids = [value for value, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        errors.append("Duplicate paper IDs: " + ", ".join(duplicate_ids))

    taxonomy_categories = taxonomy.get("categories", []) if isinstance(taxonomy, dict) else []
    if not isinstance(taxonomy_categories, list):
        errors.append("taxonomy.categories must be a list")
        taxonomy_categories = []
    category_names = [item.get("name") for item in taxonomy_categories if isinstance(item, dict)]
    if len(category_names) != len(set(category_names)):
        errors.append("Duplicate taxonomy category names")
    taxonomy_by_paper: dict[str, str] = {}
    for item in taxonomy_categories:
        if not isinstance(item, dict):
            errors.append("Each taxonomy category must be an object")
            continue
        name = item.get("name")
        if not name or not item.get("definition") or not item.get("synthesis"):
            errors.append("Taxonomy category missing name, definition, or synthesis")
        if not isinstance(item.get("is_core"), bool):
            errors.append(f"{name or '<unnamed>'}: taxonomy is_core must be boolean")
        paper_ids = item.get("paper_ids", [])
        if not isinstance(paper_ids, list):
            errors.append(f"{name or '<unnamed>'}: paper_ids must be a list")
            paper_ids = []
        representatives = item.get("representative_paper_ids", [])
        if not isinstance(representatives, list):
            errors.append(f"{name or '<unnamed>'}: representative_paper_ids must be a list")
            representatives = []
        unknown_representatives = sorted(set(representatives) - set(paper_ids))
        if unknown_representatives:
            errors.append(
                f"{name or '<unnamed>'}: representative papers absent from paper_ids: "
                + ", ".join(unknown_representatives)
            )
        if item.get("is_core") is True and len(paper_ids) < 2:
            errors.append(f"{name or '<unnamed>'}: core problem needs at least two papers")
        for paper_id in paper_ids:
            if paper_id in taxonomy_by_paper:
                errors.append(f"{paper_id}: assigned to multiple taxonomy categories")
            taxonomy_by_paper[paper_id] = name

    eligible_ids: set[str] = set()
    abstract_count = 0
    full_text_count = 0
    completed_problems: dict[str, list[str]] = {}
    completed_category_reasons: dict[str, list[str]] = {}
    for record in records:
        paper_id = record.get("paper_id") or "<missing-id>"
        for field in ("paper_id", "title", "sources", "analysis_status"):
            if record.get(field) in (None, "", []):
                errors.append(f"{paper_id}: missing {field}")
        for field in ("authors", "year", "url"):
            if record.get(field) in (None, "", []):
                warnings.append(f"{paper_id}: missing bibliographic field {field}")
        status = record.get("analysis_status")
        if status not in {
            "pending",
            "complete",
            "insufficient_text",
            "no_identifiable_problem",
            "excluded",
        }:
            errors.append(f"{paper_id}: invalid analysis_status={status}")
        if status == "complete" and record.get("selected") is True:
            eligible_ids.add(paper_id)
            for field in ("year", "url"):
                if record.get(field) in (None, ""):
                    errors.append(f"{paper_id}: selected paper missing {field}")
            if record.get("reading_scope") not in {"abstract", "full_text"}:
                errors.append(f"{paper_id}: invalid or missing reading_scope")
            if record.get("reading_scope") == "abstract":
                abstract_count += 1
            if record.get("reading_scope") == "full_text":
                full_text_count += 1
            for field in REQUIRED_ANALYSIS:
                if record.get(field) in (None, ""):
                    errors.append(f"{paper_id}: missing {field}")
            evidence = record.get("problem_evidence")
            if not isinstance(evidence, dict):
                errors.append(f"{paper_id}: problem_evidence must be an object")
            else:
                for field in ("quote", "source", "location"):
                    if evidence.get(field) in (None, ""):
                        errors.append(f"{paper_id}: problem_evidence missing {field}")
                source = evidence.get("source")
                if source not in {"abstract", "full_text"}:
                    errors.append(f"{paper_id}: invalid problem_evidence source={source}")
                if record.get("reading_scope") == "abstract" and source != "abstract":
                    errors.append(
                        f"{paper_id}: abstract-only analysis must use abstract problem evidence"
                    )
                quote = normalized_text(evidence.get("quote"))
                if len(quote) < 15:
                    errors.append(f"{paper_id}: problem_evidence quote is too short")
                if len(quote) > 500:
                    errors.append(f"{paper_id}: problem_evidence quote is not concise")
                if source == "abstract" and quote not in normalized_text(record.get("abstract")):
                    errors.append(
                        f"{paper_id}: problem_evidence quote is not an exact abstract excerpt"
                    )
                if quote and quote == normalized_text(record.get("problem")):
                    errors.append(
                        f"{paper_id}: problem must paraphrase rather than copy problem_evidence"
                    )
            normalized_problem = normalized_text(record.get("problem"))
            if normalized_problem:
                completed_problems.setdefault(normalized_problem, []).append(paper_id)
            normalized_reason = normalized_text(record.get("category_reason"))
            if normalized_reason:
                completed_category_reasons.setdefault(normalized_reason, []).append(paper_id)
            if record.get("category") not in category_names:
                errors.append(f"{paper_id}: category absent from taxonomy")
            if taxonomy_by_paper.get(paper_id) != record.get("category"):
                errors.append(f"{paper_id}: taxonomy mapping disagrees with paper category")
        elif status == "insufficient_text" and record.get("abstract"):
            warnings.append(f"{paper_id}: marked insufficient_text despite having an abstract")
        elif status == "no_identifiable_problem":
            if record.get("skip_reason") in (None, ""):
                errors.append(f"{paper_id}: no_identifiable_problem missing skip_reason")
            if record.get("selected") is not True:
                errors.append(f"{paper_id}: analyzed skipped paper must keep selected=true")
            for field in (
                "problem_evidence",
                "problem",
                "category",
                "category_reason",
                "one_sentence_summary",
            ):
                if record.get(field) not in (None, ""):
                    errors.append(f"{paper_id}: skipped paper must not contain {field}")

    for problem, paper_ids in completed_problems.items():
        if len(paper_ids) >= 3:
            errors.append(
                "Identical templated problem reused across papers: " + ", ".join(paper_ids)
            )
        elif len(paper_ids) == 2:
            warnings.append(
                "Identical problem statement reused twice; verify individualization: "
                + ", ".join(paper_ids)
            )
    for reason, paper_ids in completed_category_reasons.items():
        if len(paper_ids) >= 3:
            errors.append(
                "Identical templated category_reason reused across papers: "
                + ", ".join(paper_ids)
            )

    summary_by_id: dict[str, Path] = {}
    for summary_path in root.glob("[0-9][0-9]-*/*/summary.md"):
        content = summary_path.read_text(encoding="utf-8")
        match = PAPER_ID_MARKER.search(content)
        if not match:
            errors.append(f"{summary_path}: missing paper_id marker")
            continue
        paper_id = match.group(1)
        if paper_id in summary_by_id:
            errors.append(f"{paper_id}: more than one summary.md")
        summary_by_id[paper_id] = summary_path
        for heading in REQUIRED_HEADINGS:
            if heading not in content:
                errors.append(f"{paper_id}: summary missing heading '{heading}'")

    missing_summaries = sorted(eligible_ids - set(summary_by_id))
    if missing_summaries:
        errors.append("Eligible papers missing summary.md: " + ", ".join(missing_summaries))
    extra_summaries = sorted(set(summary_by_id) - eligible_ids)
    if extra_summaries:
        errors.append("Summary files for ineligible/unknown papers: " + ", ".join(extra_summaries))

    known_ids = set(ids)
    unknown_taxonomy_ids = sorted(set(taxonomy_by_paper) - known_ids)
    if unknown_taxonomy_ids:
        errors.append("Taxonomy references unknown paper IDs: " + ", ".join(unknown_taxonomy_ids))
    ineligible_taxonomy_ids = sorted(set(taxonomy_by_paper) - eligible_ids)
    if ineligible_taxonomy_ids:
        errors.append(
            "Taxonomy references ineligible papers: " + ", ".join(ineligible_taxonomy_ids)
        )

    print(f"Validated {len(records)} paper records")
    print(
        f"Summaries: {len(summary_by_id)} "
        f"({full_text_count} full text, {abstract_count} abstract)"
    )
    print(f"Errors: {len(errors)}; warnings: {len(warnings)}")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARNING: {message}")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
