---
name: literature-evidence-synthesis
description: Search academic papers for a user-specified field and year range, determine the concrete problem each paper addresses, classify papers by the problem they solve, and create a browsable folder tree where every category is a folder and every paper has its own folder containing a Markdown summary. Use for requests to find, collect, organize, classify, or summarize literature by domain, including 文献搜集、论文分类、找某领域论文、分析论文解决的问题、按类别生成 Markdown or literature organization.
---

# Literature Field Organizer

Create a simple, browsable literature library organized by the concrete problem each paper addresses.

## Enforce the conversation contract

Treat the field and numeric year range as required inputs.

- If the user gives a field but no explicit year or year range, ask only: `你希望检索哪几年？例如 2020–2025。`
- Do not search, analyze papers, or create output files before receiving the year range.
- If the user says only “最近几年”, ask for explicit start and end years.
- If the user supplies the field and years together, proceed without asking again.
- Use 30 papers by default. Honor a user-specified count.
- Use the user's requested language. Otherwise write summaries in Chinese and preserve original paper titles.

Do not ask about classification unless the user volunteers a taxonomy. By default, classify papers by the problem they solve.

## Resolve resources

Resolve the directory containing this `SKILL.md` as `<skill-root>`.

Read:

- [references/paper-analysis-schema.md](references/paper-analysis-schema.md) before analyzing papers.
- [references/classification-rules.md](references/classification-rules.md) before assigning categories.
- [references/output-contract.md](references/output-contract.md) before rendering files.

## Run the workflow

### 1. Search the requested field and years

Expand the field into 2–4 complementary English queries and add Chinese queries when useful. Search:

- OpenAlex and Crossref by default;
- arXiv for computer science, AI, mathematics, physics, and related fields;
- PubMed for medicine, biology, and health fields;
- Semantic Scholar only when available and useful.

Run the collector once per query or pass repeated `--query` arguments:

```bash
python3 <skill-root>/scripts/collect_literature.py \
  --query "query one" \
  --query "query two" \
  --from-year 2020 \
  --to-year 2025 \
  --limit-per-source 40 \
  --sources openalex,crossref \
  --output "<output-root>/_data/papers.jsonl"
```

Use `--sources openalex,crossref,arxiv` for computing-related fields and `--sources openalex,crossref,pubmed` for biomedical fields. Record all searches in `_data/search-log.jsonl`.

### 2. Deduplicate and select papers

Deduplicate by normalized DOI, then normalized title and year. Keep the most complete metadata and abstract when multiple sources match.

Filter to the requested years before analysis. Rank candidates using relevance first, then abstract availability, publication status, citation signal, and recency. Select the requested number.

Do not create a paper summary from title-only metadata. Search for an abstract or accessible full text; if neither is available, leave the record in `_data/papers.jsonl` with `analysis_status: "insufficient_text"` and omit it from category folders.

### 3. Determine what each paper solves

Read the abstract at minimum. Prefer accessible full text for important or ambiguous papers.

For every selected paper, fill:

- `problem`: the concrete limitation, unmet need, failure, cost, uncertainty, or research gap addressed;
- `method`: what the authors did;
- `results`: the main reported findings;
- `conclusion`: the authors' main conclusion;
- `limitations`: stated or clearly evidenced limits;
- `one_sentence_summary`: problem + method + main result in one sentence;
- `reading_scope`: `full_text` or `abstract`;
- `category` and `category_reason`.

Do not infer results from the title. Do not turn association into causation. When using only an abstract, write `阅读范围：摘要` in the summary without adding a review queue or approval workflow.

### 4. Classify by solved problem

Create a small set of distinct categories based on recurring paper problems. Examples include data scarcity, multimodal fusion, interpretability, generalization, efficiency, safety, or deployment, but derive actual categories from the corpus.

Assign exactly one primary category to each paper. Use `其他与待分类` only when no stable category fits. Save the category definitions and paper mapping to `_data/taxonomy.json`.

### 5. Render the folder library

After enriching `_data/papers.jsonl`, run:

```bash
python3 <skill-root>/scripts/render_library.py \
  --input "<output-root>/_data/papers.jsonl" \
  --taxonomy "<output-root>/_data/taxonomy.json" \
  --output "<output-root>" \
  --field "领域名称" \
  --from-year 2020 \
  --to-year 2025
```

Create:

```text
<field>_<from-year>-<to-year>/
├── 00-检索与分类总览.md
├── 01-<category>/
│   └── <year>-<first-author>-<paper-title>/
│       └── summary.md
└── _data/
    ├── papers.jsonl
    ├── search-log.jsonl
    └── taxonomy.json
```

Sanitize unsafe filename characters and add a short paper ID when two folder names collide. Do not download PDFs unless the user explicitly requests them.

### 6. Validate and report

Run:

```bash
python3 <skill-root>/scripts/validate_library.py \
  --root "<output-root>"
```

Resolve errors before delivery. Report:

- field and year range;
- sources and query count;
- records found and deduplicated;
- papers summarized;
- full-text versus abstract summaries;
- category names and counts;
- records omitted because no abstract or full text was available.

Do not generate an industry-core-problem report, evidence matrix, approval state, or human-review queue unless the user separately requests one.
