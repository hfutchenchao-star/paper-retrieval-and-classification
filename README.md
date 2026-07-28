# Paper 检索和分类

这是一个 Codex skill：根据用户指定的研究领域和年份范围自动检索论文，判断每篇论文解决的具体问题，按“解决的问题”分类，并为每篇论文生成独立的 Markdown 总结。

## 它会做什么

1. 你先告诉它要研究的领域。
2. 如果没有提供年份，它会先追问：`你希望检索哪几年？例如 2020–2025。`
3. 从 OpenAlex、Crossref，以及适用时的 arXiv 或 PubMed 搜集论文。
4. 根据摘要或可访问全文分析论文解决的问题、方法、结果、结论和局限。
5. 按论文所解决的问题分类。
6. 生成“分类文件夹 → 论文文件夹 → summary.md”的文献库。

默认检索 30 篇论文；你也可以在请求中指定数量。

## 安装

### 方法一：在 Codex 中通过 GitHub 安装

把下面这句话发给 Codex，并将 `<你的GitHub用户名>` 替换成仓库所有者：

```text
$skill-installer 请从
https://github.com/<你的GitHub用户名>/paper-retrieval-and-classification/tree/main/.agents/skills/literature-evidence-synthesis
安装这个 skill
```

安装完成后，从下一轮对话开始可用。

### 方法二：克隆仓库后直接使用

```bash
git clone https://github.com/<你的GitHub用户名>/paper-retrieval-and-classification.git
cd paper-retrieval-and-classification
```

用 Codex 打开这个仓库。Codex 会自动发现 `.agents/skills/literature-evidence-synthesis/`。

## 使用示例

只提供领域：

```text
$literature-evidence-synthesis 帮我搜集并分类“多模态医学影像分析”领域的论文。
```

它会先询问年份。也可以一次提供完整条件：

```text
$literature-evidence-synthesis 搜集 2021–2025 年“多模态医学影像分析”领域的 40 篇论文，
按论文解决的问题分类，并生成中文 Markdown 总结。
```

## 输出结构

```text
多模态医学影像分析_2021-2025/
├── 00-检索与分类总览.md
├── 01-数据与标注不足/
│   └── 2024-作者-论文标题/
│       └── summary.md
├── 02-跨模态融合/
│   └── ...
└── _data/
    ├── papers.jsonl
    ├── search-log.jsonl
    └── taxonomy.json
```

`_data/` 保存去重、增量检索和重新生成结果所需的机器可读数据，不会存放 API 密钥。

## 运行要求

- Codex
- Python 3
- 能够访问所使用的论文检索接口
- 不需要额外安装 Python 第三方包

Skill 主文件位于：

```text
.agents/skills/literature-evidence-synthesis/SKILL.md
```
