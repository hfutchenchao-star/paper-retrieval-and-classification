# Core-problem synthesis and classification rules

Synthesize the field's recurring core problems, then classify papers by the primary problem they solve.

## Procedure

1. Finish every paper's `problem_evidence` and individualized `problem` before drafting categories.
2. Use only records with `analysis_status: complete`, valid evidence, and a non-empty source-supported `problem`.
3. Compare the meanings of the complete problem statements and group semantically equivalent problems.
4. Name each group with a short problem-oriented phrase understandable without domain jargon.
5. Write a one-sentence definition and a cross-paper synthesis.
6. Mark a recurring group supported by at least two papers as `is_core: true`.
7. Keep singleton or unstable groups as `is_core: false`; do not present them as stable field-wide core problems.
8. Assign each valid paper to exactly one category.
9. Keep the taxonomy small enough to browse; prefer 5–12 categories for a 50-paper set.
10. Create `其他问题` or `其他与待分类` only for genuine outliers.

## Prohibited shortcuts

Do not:

- establish a fixed taxonomy before reading the papers;
- assign categories with keyword matching, regexes, embeddings-only clustering, or title rules;
- classify by the method used instead of the problem motivating the contribution;
- reuse an identical generic `problem` statement across multiple papers;
- write a generic `category_reason` such as “the paper contains this category's keywords”;
- use a script or batch template to generate paper-level analysis fields.

Computational tools may surface candidate similarities after the evidence-grounded problems have been written, but the final grouping and primary-category decision must be based on semantic comparison of those problems.

## Choose the primary category

When a paper addresses several problems, select the problem that motivates its central contribution. Use the title, abstract objective, introduction problem statement, and main evaluation target as evidence.

Write `category_reason` as a paper-specific explanation that connects its individualized `problem` to the category definition. The reason must remain valid if the paper title and keywords are hidden.

Do not classify primarily by:

- publication year;
- venue;
- model brand;
- dataset name;
- generic study type;
- keywords that do not express the addressed problem.

## Taxonomy format

Save `_data/taxonomy.json`:

```json
{
  "classification_axis": "该领域的核心问题",
  "synthesis_basis": "仅基于本次检索中有明确问题陈述的论文",
  "categories": [
    {
      "order": 1,
      "name": "数据与标注不足",
      "definition": "解决训练数据有限、标注昂贵、类别稀缺或监督信号不足的问题。",
      "synthesis": "多篇论文共同指出高质量标注成本高、稀有类别样本少，导致模型训练和评估受限。",
      "is_core": true,
      "paper_ids": ["P1A2B3C4D", "P5E6F7G8H"],
      "representative_paper_ids": ["P1A2B3C4D"]
    }
  ]
}
```

The `paper_ids` list and each paper's `category` must agree.
Every `representative_paper_ids` entry must also appear in that category's `paper_ids`.
