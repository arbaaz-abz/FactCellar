# FactCellar - Summary and Overview

FactCellar is a fact-checking dataset made of claims crawled from politifact. The task is to predict the veracity label using evidence, domain authority metrics, and impact assessment.

## Dataset Statistics
- **Number of claims**: 2,557
- **Language**: English
- **Time Range**: Jan 3rd 2021 - Nov 10th 2024

### Label Distribution
| Label | Count |
|-------|--------|
| True | 117 |
| Mostly True | 203 |
| Half True | 295 |
| Mostly False | 415 |
| False | 1,214 |
| Pants on Fire | 313 |

### Topics Covered
`abortion` `health-care` `education` `economy` `children` `crime` `military` `food` `religion` `science` `animals` `environment` `energy` `climate-change` `taxes` `technology` `weather` `coronavirus` `drugs` `border-security` `natural-disasters` `housing` `human-rights` `corporations` `history` `sports` `welfare` `lgbtq` `guns` `ethics`

## Key Components

### Query Generation
We break down each claim into verifiable facts, using each as a web search query to retrieve up to 10 relevant results.

### Impact Assessment
We analyze claim content to:
- Predict a societal impact score on a scale of 1-10
- Provide detailed justification for impact scores

### Domain Authority Metrics
For each evidence link, we evaluate domain authority using:

| Metric | Scale |
|--------|--------|
| Domain Age | 0-∞ |
| TLD Score | 1-10 |
| Page Rank | 1-10 |
| Bias Rating | 1-5 |
| Factual Rating | 1-6 |
| Credibility Rating | 1-4 |

These metrics are aggregated per claim, sourced from:
- WHOIS
- Open PageRank
- SSL
- mediabiasfactcheck.com

### Knowledge Store
- Uses trafilatura for evidence link scraping
- Stores scraped text in JSON format
- Creates individual JSON files per claim containing all evidence
