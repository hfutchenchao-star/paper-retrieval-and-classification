# Core-problem synthesis and classification rules

Synthesize the field's recurring core problems, then classify papers by the primary problem they solve.

## Procedure

1. Use only records with `analysis_status: complete` and a non-empty, source-supported `problem`.
2. Group semantically equivalent problems.
3. Name each group with a short problem-oriented phrase understandable without domain jargon.
4. Write a one-sentence definition and a cross-paper synthesis.
5. Mark a recurring group supported by at least two papers as `is_core: true`.
6. Keep singleton or unstable groups as `is_core: false`; do not present them as stable field-wide core problems.
7. Assign each valid paper to exactly one category.
8. Keep the taxonomy small enough to browse; prefer 5–12 categories for a 50-paper set.
9. Create `其他问题` or `其他与待分类` only for genuine outliers.

## Choose the primary category

When a paper addresses several problems, select the problem that motivates its central contribution. Use the title, abstract objective, introduction problem statement, and main evaluation target as evidence.

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
