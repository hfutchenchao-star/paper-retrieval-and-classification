# Paper analysis schema

Use this schema for each object in `_data/papers.jsonl`.

## Discovery fields

```json
{
  "paper_id": "P1A2B3C4D",
  "title": "Original paper title",
  "authors": ["First Author", "Second Author"],
  "year": 2024,
  "venue": "Journal or conference",
  "doi": "10.xxxx/xxxx",
  "url": "https://doi.org/...",
  "abstract": "Abstract text",
  "publication_type": "journal-article",
  "sources": ["openalex", "crossref"],
  "matched_queries": ["query text"],
  "citation_count": 12,
  "open_access": true,
  "collected_at": "ISO-8601 timestamp"
}
```

## Analysis fields

```json
{
  "selected": true,
  "analysis_status": "complete",
  "skip_reason": null,
  "reading_scope": "abstract",
  "problem": "The concrete problem or gap addressed by the paper.",
  "method": "The data, model, experiment, or approach used.",
  "results": "The main reported findings, with numbers when available.",
  "conclusion": "The authors' main conclusion.",
  "limitations": "Stated or clearly supported limitations.",
  "one_sentence_summary": "To solve X, the paper uses Y and reports Z.",
  "category": "Problem-oriented category",
  "category_reason": "Why the paper belongs in this category."
}
```

Allowed values:

- `analysis_status`: `pending`, `complete`, `insufficient_text`, `no_identifiable_problem`, `excluded`
- `reading_scope`: `abstract`, `full_text`

## Analysis rules

1. State the paper's problem as a deficiency or unmet need, not as a topic.
2. Separate method, result, and conclusion.
3. Use reported numbers only when present in the source.
4. Do not invent a limitation. Write `摘要未说明` when only the abstract is available and it does not state limitations.
5. Keep the original title and bibliographic fields.
6. Do not summarize from metadata alone.
7. Use Chinese for analysis fields unless the user asks for another language.
8. Require source-text support for `problem`. Do not derive it from the title, keywords, task name, or method alone.
9. If the abstract or full text does not identify a concrete problem, keep `selected: true`, set `analysis_status` to `no_identifiable_problem`, write `skip_reason`, and leave `problem`, `category`, and summary fields empty.

## Example transformation

Weak:

> 本文研究医学影像分割。

Strong:

> 论文试图解决医学影像像素级标注成本高、标注样本不足的问题。

One-sentence summary:

> 为降低医学影像像素级标注需求，论文采用弱监督分割方法，并在两个公开数据集上报告了优于对照方法的性能。
