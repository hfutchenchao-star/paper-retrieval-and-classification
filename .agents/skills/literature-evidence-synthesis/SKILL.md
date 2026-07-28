---
name: literature-evidence-synthesis
description: Search a requested number of academic papers for a user-specified field and year range, identify each paper's concrete problem from abstract or full-text evidence, skip papers without identifiable source evidence, synthesize recurring core problems, classify papers by those problems, and create a browsable Markdown library. Use for requests to find, collect, organize, classify, or summarize literature by domain, including 文献搜集、论文分类、找某领域论文、分析论文解决的问题、提炼领域核心问题、按类别生成 Markdown or literature organization.
---

# Literature Field Organizer

Create a simple, browsable literature library organized by the concrete problem each paper addresses.

## Enforce the conversation contract

Treat the field and numeric year range as required inputs.

- If the user gives a field but no explicit year or year range, ask only: `你希望检索哪几年？例如 2020–2025。`
- Do not search, analyze papers, or create output files before receiving the year range.
- If the user says only “最近几年”, ask for explicit start and end years.
- If the user supplies the field and years together, proceed without asking again.
- Use 50 papers by default. If the user specifies a count, use that count instead.
- Use the user's requested language. Otherwise write summaries in Chinese and preserve original paper titles.

Do not ask about classification unless the user volunteers a taxonomy. By default, classify papers by the problem they solve.

## Enforce evidence-first classification

Treat these rules as non-negotiable:

- Read the abstract at minimum for every summarized paper.
- Record a short exact `problem_evidence` excerpt from the abstract or full text before writing `problem`.
- Write an individualized `problem` as a paraphrase of that evidence.
- Complete paper-level problem analysis before creating or assigning taxonomy categories.
- Derive categories by semantically grouping the completed `problem` statements.
- Do not classify from titles, keywords, model names, method names, venues, or generic study types.
- Do not use keyword matching, regexes, fixed category lists, or templated problem statements to assign categories.
- Do not use a script to populate `problem`, `problem_evidence`, `category`, or `category_reason`. Scripts may collect metadata, render completed analysis, and validate structural or evidence consistency only.
- If the source does not state a concrete problem, mark the paper `no_identifiable_problem`; never create a plausible problem to preserve the requested count.

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

Filter to the requested years before analysis. Rank candidates using relevance first, then abstract availability, publication status, citation signal, and recency. Continue down the ranked candidate pool until exactly the requested number have `analysis_status: "complete"` when enough valid records are available. Replace candidates skipped for insufficient text or no identifiable problem. If the pool is exhausted, use all valid records and report the final-summary shortfall.

Do not create a paper summary from title-only metadata. Search for an abstract or accessible full text; if neither is available, leave the record in `_data/papers.jsonl` with `analysis_status: "insufficient_text"` and omit it from category folders.

### 3. Determine what each paper solves

Read the abstract at minimum. Prefer accessible full text for important or ambiguous papers.

For every selected paper, fill:

- `problem_evidence`: a short exact excerpt and its source location supporting the problem;
- `problem`: the concrete limitation, unmet need, failure, cost, uncertainty, or research gap addressed;
- `method`: what the authors did;
- `results`: the main reported findings;
- `conclusion`: the authors' main conclusion;
- `limitations`: stated or clearly evidenced limits;
- `one_sentence_summary`: problem + method + main result in one sentence;
- `reading_scope`: `full_text` or `abstract`;
- `category` and `category_reason`.

Fill `problem_evidence` first. Only fill `problem` when that excerpt identifies a concrete limitation, unmet need, failure, cost, uncertainty, or research gap. A topic, keyword, task name, method name, or title-based inference is not a problem. Keep the evidence excerpt short and exact; paraphrase rather than copy it into `problem`.

If the source text does not provide enough evidence to identify a concrete problem, keep `selected: true`, set `analysis_status: "no_identifiable_problem"`, add a short `skip_reason`, and omit the paper from synthesis, category folders, and Markdown summaries. Do not invent a problem to keep a paper.

Do not infer results from the title. Do not turn association into causation. When using only an abstract, write `阅读范围：摘要` in the summary without adding a review queue or approval workflow.

### 4. Synthesize core field problems and classify papers

Use only papers with `analysis_status: "complete"`, a valid `problem_evidence`, and a source-supported individualized `problem`.

After all paper-level analyses are complete, normalize the individual problem statements, group semantically equivalent problems, and synthesize the recurring groups into the field's core problems. Do not create a category list first and fit papers into it. Each core problem must include:

- a short problem-oriented name;
- a concrete definition;
- a cross-paper synthesis explaining the shared unmet need or limitation;
- supporting paper IDs;
- 1–3 representative paper IDs.

Treat recurring problem groups as core problems. Keep genuine one-off problems as non-core categories or place them in `其他问题`; do not present a singleton as a stable field-wide core problem.

Possible outcomes include data scarcity, multimodal fusion, interpretability, generalization, efficiency, safety, or deployment, but never use this list as a preset taxonomy. Derive the actual categories from the collected problem statements.

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
  --to-year 2025 \
  --requested-count 50
```

Render into a fresh output root. When regenerating an existing library, archive the previous generated category folders first so stale summaries cannot survive a changed taxonomy.

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
- requested paper count and any shortfall;
- papers summarized;
- full-text versus abstract summaries;
- synthesized core problems and supporting-paper counts;
- category names and counts;
- records omitted because no abstract or full text was available.
- records skipped because no concrete paper problem could be identified.

Keep core-problem claims scoped to the collected paper set. Do not turn them into unsupported industry-wide claims, an approval state, or a human-review queue unless the user separately requests that.
