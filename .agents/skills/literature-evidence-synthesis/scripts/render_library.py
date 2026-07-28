#!/usr/bin/env python3
"""Render category folders and one summary.md file per analyzed paper."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ANALYSIS_FIELDS = (
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Enriched papers.jsonl")
    parser.add_argument("--taxonomy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--field", required=True)
    parser.add_argument("--from-year", type=int, required=True)
    parser.add_argument("--to-year", type=int, required=True)
    parser.add_argument(
        "--requested-count",
        type=int,
        default=50,
        help="Requested number of final evidence-grounded paper summaries.",
    )
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise SystemExit(f"{path}:{line_number}: record must be an object")
        records.append(value)
    return records


def clean(value: Any, fallback: str = "未提供") -> str:
    if value in (None, "", []):
        return fallback
    if isinstance(value, list):
        value = "、".join(str(item) for item in value)
    return re.sub(r"\s+", " ", str(value)).strip()


def safe_component(value: Any, limit: int = 120) -> str:
    text = unicodedata.normalize("NFKC", clean(value, "未命名"))
    text = re.sub(r'[\/\\:*?"<>|\x00-\x1f]', "-", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip(" .-_")
    return (text or "未命名")[:limit].rstrip(" .-_")


def paper_folder_base(record: dict[str, Any]) -> str:
    authors = record.get("authors") or []
    first_author = authors[0] if authors else "未知作者"
    prefix = f"{record.get('year') or '未知年份'}-{safe_component(first_author, 28)}"
    available = max(24, 120 - len(prefix) - 1)
    return f"{prefix}-{safe_component(record.get('title'), available)}"


def eligible(record: dict[str, Any]) -> bool:
    evidence = record.get("problem_evidence")
    return (
        record.get("selected") is True
        and record.get("analysis_status") == "complete"
        and record.get("reading_scope") in {"abstract", "full_text"}
        and all(record.get(field) not in (None, "") for field in ANALYSIS_FIELDS)
        and isinstance(evidence, dict)
        and all(evidence.get(field) not in (None, "") for field in ("quote", "source", "location"))
    )


def summary_markdown(record: dict[str, Any]) -> str:
    doi = clean(record.get("doi"))
    url = clean(record.get("url"))
    scope = "全文" if record.get("reading_scope") == "full_text" else "摘要"
    evidence = record.get("problem_evidence") or {}
    evidence_scope = "全文" if evidence.get("source") == "full_text" else "摘要"
    return f"""<!-- paper_id: {clean(record.get("paper_id"))} -->
# {clean(record.get("title"))}

- 作者：{clean(record.get("authors"))}
- 年份：{clean(record.get("year"))}
- 期刊/会议：{clean(record.get("venue"))}
- DOI：{doi}
- 论文链接：{url}
- 阅读范围：{scope}

## 论文解决了什么问题

{clean(record.get("problem"))}

## 问题证据

- 原文摘录：{clean(evidence.get("quote"))}
- 证据来源：{evidence_scope}
- 位置：{clean(evidence.get("location"))}

## 使用了什么方法

{clean(record.get("method"))}

## 得到了什么结果

{clean(record.get("results"))}

## 主要结论

{clean(record.get("conclusion"))}

## 局限性

{clean(record.get("limitations"), "摘要未说明")}

## 一句话总结

{clean(record.get("one_sentence_summary"))}

## 分类说明

- 所属分类：{clean(record.get("category"))}
- 分类原因：{clean(record.get("category_reason"))}
"""


def search_details(search_log_path: Path) -> tuple[list[str], list[str], int]:
    if not search_log_path.exists():
        return [], [], 0
    rows = read_jsonl(search_log_path)
    sources = sorted({clean(row.get("source")) for row in rows if row.get("source")})
    queries = []
    seen = set()
    for row in rows:
        query = clean(row.get("query"), "")
        if query and query not in seen:
            seen.add(query)
            queries.append(query)
    returned = sum(int(row.get("returned_count") or 0) for row in rows)
    return sources, queries, returned


def main() -> int:
    args = parse_args()
    if args.from_year > args.to_year:
        raise SystemExit("--from-year cannot be greater than --to-year")
    if args.requested_count < 1:
        raise SystemExit("--requested-count must be at least 1")
    if not args.input.exists():
        raise SystemExit(f"Missing input: {args.input}")
    if not args.taxonomy.exists():
        raise SystemExit(f"Missing taxonomy: {args.taxonomy}")

    records = read_jsonl(args.input)
    taxonomy = json.loads(args.taxonomy.read_text(encoding="utf-8"))
    categories = taxonomy.get("categories", [])
    if not isinstance(categories, list):
        raise SystemExit("taxonomy.categories must be a list")

    category_order: dict[str, int] = {}
    category_definitions: dict[str, str] = {}
    category_syntheses: dict[str, str] = {}
    category_core_flags: dict[str, bool] = {}
    for fallback_order, item in enumerate(categories, 1):
        if not isinstance(item, dict):
            continue
        name = clean(item.get("name"), "")
        if not name:
            continue
        category_order[name] = int(item.get("order") or fallback_order)
        category_definitions[name] = clean(item.get("definition"), "未提供分类定义")
        category_syntheses[name] = clean(
            item.get("synthesis"), category_definitions[name]
        )
        paper_ids = item.get("paper_ids") if isinstance(item.get("paper_ids"), list) else []
        category_core_flags[name] = bool(
            item.get("is_core", len(paper_ids) >= 2)
        )

    rendered_records = [record for record in records if eligible(record)]
    unlisted = sorted(
        {clean(record.get("category")) for record in rendered_records} - set(category_order),
        key=str.casefold,
    )
    next_order = max(category_order.values(), default=0) + 1
    for name in unlisted:
        category_order[name] = next_order
        category_definitions[name] = "该分类存在于论文记录中，但尚未写入 taxonomy.json。"
        category_syntheses[name] = category_definitions[name]
        category_core_flags[name] = False
        next_order += 1

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in rendered_records:
        by_category[clean(record.get("category"))].append(record)

    args.output.mkdir(parents=True, exist_ok=True)
    used_paths: set[Path] = set()
    ordered_names = sorted(by_category, key=lambda name: (category_order.get(name, 9999), name.casefold()))
    for category_name in ordered_names:
        order = category_order.get(category_name, 9999)
        category_dir = args.output / f"{order:02d}-{safe_component(category_name, 80)}"
        category_dir.mkdir(parents=True, exist_ok=True)
        category_records = sorted(
            by_category[category_name],
            key=lambda item: (-(item.get("year") or 0), clean(item.get("title")).casefold()),
        )
        for record in category_records:
            base = paper_folder_base(record)
            paper_dir = category_dir / base
            if paper_dir in used_paths:
                paper_dir = category_dir / f"{base}-{safe_component(record.get('paper_id'), 16)}"
            used_paths.add(paper_dir)
            paper_dir.mkdir(parents=True, exist_ok=True)
            summary_path = paper_dir / "summary.md"
            summary_path.write_text(summary_markdown(record), encoding="utf-8")

    sources, queries, raw_returned = search_details(args.input.parent / "search-log.jsonl")
    counts = Counter(clean(record.get("category")) for record in rendered_records)
    full_text_count = sum(record.get("reading_scope") == "full_text" for record in rendered_records)
    abstract_count = sum(record.get("reading_scope") == "abstract" for record in rendered_records)
    insufficient_text_count = sum(
        record.get("analysis_status") == "insufficient_text" for record in records
    )
    no_problem_count = sum(
        record.get("analysis_status") == "no_identifiable_problem" for record in records
    )
    selected_count = sum(record.get("selected") is True for record in records)
    retrieval_shortfall = max(0, args.requested_count - len(rendered_records))
    generated_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    lines = [
        f"# {args.field}：检索与分类总览",
        "",
        f"- 检索年份：{args.from_year}–{args.to_year}",
        f"- 生成时间：{generated_at}",
        f"- 数据来源：{'、'.join(sources) or '未记录'}",
        f"- 查询式数量：{len(queries)}",
        f"- 目标检索数量：{args.requested_count}",
        f"- 各来源累计返回：{raw_returned}",
        f"- 去重后记录：{len(records)}",
        f"- 被选中：{selected_count}",
        f"- 检索数量缺口：{retrieval_shortfall}",
        f"- 已生成总结：{len(rendered_records)}",
        f"- 具有可核验问题证据：{len(rendered_records)}",
        f"- 全文总结：{full_text_count}",
        f"- 摘要总结：{abstract_count}",
        f"- 因缺少摘要或全文而跳过：{insufficient_text_count}",
        f"- 因未识别到明确论文问题而跳过：{no_problem_count}",
        "",
        "## 检索词",
        "",
    ]
    lines.extend(f"- {query}" for query in queries)
    if not queries:
        lines.append("- 未记录")
    lines.extend(["", "## 领域核心问题", ""])
    core_names = [name for name in ordered_names if category_core_flags.get(name)]
    if not core_names:
        lines.append("当前有效论文样本中没有形成由至少两篇论文共同支持的稳定核心问题。")
        lines.append("")
    for name in core_names:
        lines.extend(
            [
                f"### {category_order[name]:02d} — {name}",
                "",
                f"- 问题定义：{category_definitions[name]}",
                f"- 跨论文归纳：{category_syntheses[name]}",
                f"- 支持论文数：{counts[name]}",
                "",
            ]
        )
    (args.output / "00-检索与分类总览.md").write_text("\n".join(lines), encoding="utf-8")

    print(
        f"Rendered {len(rendered_records)} papers into {len(ordered_names)} category folders at {args.output}"
    )
    print(
        f"Reading scope: {full_text_count} full text, {abstract_count} abstract; "
        f"skipped for insufficient text: {insufficient_text_count}; "
        f"skipped for no identifiable problem: {no_problem_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
