# Classification rules

Classify papers by the primary problem they solve.

## Procedure

1. Read every selected paper's `problem`.
2. Group semantically equivalent problems.
3. Name each group with a short noun phrase understandable without domain jargon.
4. Write a one-sentence definition and inclusion rule.
5. Assign each paper to exactly one category.
6. Keep the taxonomy small enough to browse; prefer 4–10 categories for a 30-paper set.
7. Create `其他与待分类` only for genuine outliers.

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
  "classification_axis": "论文解决的问题",
  "categories": [
    {
      "order": 1,
      "name": "数据与标注不足",
      "definition": "解决训练数据有限、标注昂贵、类别稀缺或监督信号不足的问题。",
      "paper_ids": ["P1A2B3C4D"]
    }
  ]
}
```

The `paper_ids` list and each paper's `category` must agree.
