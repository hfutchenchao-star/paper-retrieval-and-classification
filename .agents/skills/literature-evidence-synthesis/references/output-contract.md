# Output contract

## Directory layout

```text
<field>_<from-year>-<to-year>/
├── 00-检索与分类总览.md
├── 01-<category-name>/
│   ├── <year>-<first-author>-<paper-title>/
│   │   └── summary.md
│   └── ...
├── 02-<category-name>/
│   └── ...
└── _data/
    ├── papers.jsonl
    ├── search-log.jsonl
    └── taxonomy.json
```

`_data` is internal, machine-readable state. It enables deduplication, incremental runs, validation, and deterministic regeneration. Never store API keys in it.

## Overview file

`00-检索与分类总览.md` must contain:

- field and year range;
- generation date;
- sources and exact search queries;
- counts found, deduplicated, selected, summarized, and omitted;
- requested paper count and any retrieval shortfall;
- a `领域核心问题` section derived only from papers with an identifiable problem;
- for every core problem: definition, cross-paper synthesis, supporting-paper count, and representative papers;
- category descriptions and counts;
- an index linking to every paper's `summary.md`;
- full-text and abstract-only counts.

## Paper directory

Build a readable directory name from:

```text
<year>-<first-author-family-name>-<sanitized-original-title>
```

Preserve Chinese characters. Replace `/ \ : * ? " < > |` and control characters. Collapse whitespace and hyphens. Limit the directory component to 120 characters. Append `-<paper_id>` on collision.

## Paper summary

Every `summary.md` must contain:

```markdown
# Original paper title

- 作者：
- 年份：
- 期刊/会议：
- DOI：
- 论文链接：
- 阅读范围：全文 / 摘要

## 论文解决了什么问题

...

## 使用了什么方法

...

## 得到了什么结果

...

## 主要结论

...

## 局限性

...

## 一句话总结

...

## 分类说明

- 所属分类：
- 分类原因：
```

Use `未提供` for absent bibliographic fields. Use `摘要未说明` for limitations that cannot be determined from an abstract.

## Exclusions

Do not create category folders for:

- unselected records;
- excluded records;
- records with `analysis_status: insufficient_text`;
- records with `analysis_status: no_identifiable_problem`;
- records lacking a complete problem, method, results, conclusion, summary, category, or category reason.

Keep skipped records in `_data/papers.jsonl`. A record with `analysis_status: no_identifiable_problem` must include `skip_reason` and must not have a `summary.md`.
