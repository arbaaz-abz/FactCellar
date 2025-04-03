# FactCellar: An Evidence-Based Dataset for Automated Fact-Checking

**FactCellar** is a comprehensive, real-world fact-checking dataset designed to address limitations in existing resources, such as lack of source credibility metadata and insufficient or outdated evidence. It pairs claims with web-retrieved evidence and enriches them with crucial metadata for robust automated fact-checking research.

This repository contains the dataset described in the paper: *FactCellar: Evidence based automated fact-checking*.

**Authors:** Arbaaz Dharmavaram, Farrukh Bin Rashid, Saqib Hakak (University of New Brunswick)

---

## Overview

The proliferation of misinformation necessitates scalable and reliable automated fact-checking systems. While benchmark datasets like FEVER have advanced the field, they often rely on synthetic claims or lack the nuanced metadata needed to assess real-world evidence credibility.

FactCellar aims to bridge this gap by providing:

1.  **Real-world Claims:** Sourced from reputable fact-checking organizations.
2.  **Web-Retrieved Evidence:** Corresponding evidence scraped from the web for each claim.
3.  **Source Credibility Metrics:** Detailed annotations quantifying the trustworthiness of evidence sources.
4.  **Claim Impact Analysis:** An assessment of the potential societal impact of each claim.
5.  **Decomposed Claims:** Claims broken down into verifiable sub-statements to aid retrieval.

---

## Motivation

Existing fact-checking datasets often:
*   Lack sufficient evidence or context.
*   Do not provide metadata about the credibility of evidence sources (e.g., domain authority, bias).
*   Are based on synthetic claims or older data, not reflecting current information landscapes.
*   Treat all evidence sources equally, regardless of reliability.

FactCellar addresses these issues by providing a rich dataset grounded in recent, real-world claims and incorporating explicit source credibility indicators.

---

## ✨ Key Features & Contributions

*   **Dataset:** 5,145 real-world claims from PolitiFact (2,557) and Snopes (2,588).
*   **Timeliness:** Claims published between January 3rd, 2021, and September 10th, 2024.
*   **Evidence Store:** Includes up to 40 relevant evidence URLs per claim, retrieved via search queries based on the original claim and its decomposed sub-statements. Crawled content stored.
*   **Source Credibility Annotation:** Each evidence URL is annotated with:
    *   Domain Age (from WHOIS)
    *   Top-Level Domain (TLD) Score (custom mapping, e.g., .gov higher)
    *   PageRank (from OpenPageRank API)
    *   Bias Rating, Factual Rating, Credibility Rating (from Media Bias/Fact Check - MBFC)
*   **Claim Impact Analysis:** Each claim includes:
    *   An LLM-generated societal impact score (1-10).
    *   A textual justification for the assigned impact score.
*   **Claim Decomposition:** Each claim is broken down into fine-grained, individually verifiable statements using an LLM (Gemini 2.0 Flash exp) to facilitate precise evidence retrieval.
*   **Baseline Pipeline:** The paper includes a baseline automated fact-checking pipeline using this dataset, demonstrating its utility.

---

## 📊 Dataset Statistics

*   **Total Claims:** 5,145
*   **Language:** English
*   **Time Range:** January 3rd, 2021 - September 10th, 2024
*   **Sources:** PolitiFact, Snopes

### Label Distribution (Original & Remapped for Experiments)

**Politifact (2,557 Claims)**
| Original Label | Count | Remapped Label (for experiments) |
|----------------|-------|----------------------------------|
| True           | 117   | True                             |
| Mostly True    | 203   | True                             |
| Half True      | 295   | Mixed                            |
| Mostly False   | 415   | Mixed                            |
| False          | 1,214 | False                            |
| Pants on Fire  | 313   | False                            |
*Final Politifact Labels:* True (320), Mixed (710), False (1,527)

**Snopes (2,588 Claims)**
| Original Label | Count | Remapped Label (for experiments) |
|----------------|-------|----------------------------------|
| True           | 847   | True                             |
| Mostly True    | 53    | True                             |
| Mostly False   | 31    | False                            |
| False          | 1,657 | False                            |
*Final Snopes Labels:* True (900), False (1,688)

*(Note: Remapping was done to address class imbalance and simplify the task, as described in the paper's Experiments section.)*

### Topics Covered (Examples)

Includes a wide range of topics such as:
`coronavirus`, `economy`, `crime`, `health-care`, `education`, `politics`, `environment`, `military`, `technology`, `history`, `science`, `abortion`, `climate-change`, `border-security`, `lgbtq`, `guns`, and many more.

---

## 🏗️ Dataset Construction Pipeline

The dataset was created through the following steps:
1.  **Data Collection:** Claims scraped from PolitiFact and Snopes (post-2021). Metadata standardized using LLM where needed (Snopes).
2.  **Claim Decomposition:** Claims broken into sub-queries using Gemini 2.0 Flash exp.
3.  **Knowledge Store Construction:**
    *   Evidence URLs retrieved using Serper based on original and decomposed queries (Top 10 results per query, up to 40 unique URLs total).
    *   URLs filtered (removing social media, primary fact-checking sites).
    *   Content crawled using Trafilatura (with Selenium fallback).
4.  **Domain Credibility Annotation:** Metrics (Domain Age, TLD Score, PageRank, MBFC scores) gathered for evidence URLs. An average credibility score per claim is computed.
5.  **Impact Analysis:** Potential societal impact score (1-10) and justification generated per claim using Gemini 2.0 Flash exp.

---

## 💾 Data Format

The dataset is provided in JSON format. Each entry corresponds to a single claim and includes fields such as:

*   `claim_text`: The text of the claim.
*   `claim_source_site`: Original site (Politifact/Snopes).
*   `claim_author`: Author of the claim (if available).
*   `claim_source_context`: Source context of the claim (if available).
*   `claim_date`: Date the claim was made/published.
*   `fact_check_date`: Date the fact-check was published.
*   `original_label`: The label assigned by the source site (e.g., "True", "Mostly False", "Pants on Fire").
*   `remapped_label`: The simplified label used for experiments (e.g., "True", "Mixed", "False").
*   `issue`: Topic/category assigned by the source site.
*   `fact_checking_sources_urls`: URLs cited by the original fact-checker.
*   `justification`: Textual explanation from the original fact-checker.
*   `decomposed_statements`: List of sub-statements generated via LLM.
*   `evidence_urls`: List of URLs retrieved as evidence.
*   `evidence_content`: JSON object mapping evidence URLs to their crawled text content.
*   `domain_credibility_metrics`: JSON object with aggregated and per-URL credibility scores (Domain Age, TLD, PageRank, Bias, Factual, Credibility).
*   `impact_score`: Numerical score (1-10) indicating potential societal impact.
*   `impact_justification`: Textual explanation for the impact score.

*(Please refer to the dataset files and the paper for the exact schema details)*

---

## 🚀 Baseline Pipeline & Usage

The accompanying paper proposes and evaluates an evidence-based fact-checking pipeline using this dataset. The pipeline involves:

1.  **Refined Query Generation (HyDE):** Generating diverse question-document pairs using an LLM (Qwen2.5-7B-Instruct) based on an initial predicted label.
2.  **Semantic Chunking & Retrieval:** Splitting crawled evidence into semantic chunks, embedding chunks and queries (using models like `bilingual-embedding-small` and `snowflake-arctic-embed-m-v2.0`), and retrieving top-N relevant evidence chunks based on semantic similarity.
3.  **Veracity Prediction:** Using an LLM (Qwen2.5-7B-Instruct) with a Chain-of-Thought, few-shot prompt that incorporates the claim, metadata, and retrieved evidence chunks to predict the final veracity label (True/False/Mixed).

This demonstrates one way the FactCellar dataset can be leveraged for building and evaluating advanced fact-checking systems that consider evidence and source credibility.

---

## 📁 How to Access

*   The dataset files can be found here: `https://drive.google.com/drive/folders/1DNiGI8gp_O1xGCoI4s_6sskAWkpLVxDT?usp=sharing` <!-- Add link here -->
---

## 📜 Citation
If you use the FactCellar dataset or methodology in your research, please cite our dataset!