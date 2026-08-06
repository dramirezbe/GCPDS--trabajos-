# Judge foundations

This file gathers the core papers that define the evaluation substrate for an audit-oriented orchestrator.

## 1. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
- arXiv: [2306.05685](https://arxiv.org/abs/2306.05685)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2306.05685)
- Summary: This work is one of the foundational references for using language models as evaluators, especially when compared against human preference signals and public benchmark-style settings.
- Why it matters here: It provides the baseline argument for using an LLM judge as part of an audit layer inside DesignAgentOrchestrator.

## 2. G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment
- arXiv: [2303.16634](https://arxiv.org/abs/2303.16634)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2303.16634)
- Summary: G-Eval shows how chain-of-thought prompting and rubric-based evaluation can improve alignment with human judgments for generation tasks.
- Why it matters here: It suggests a strong template for rubric-driven audits, especially for notebook outputs, generated code, and narrative summaries.

## 3. A Survey on LLM-as-a-Judge
- arXiv: [2411.15594](https://arxiv.org/abs/2411.15594)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2411.15594)
- Summary: This survey synthesizes the field of LLM-based judging, covering evaluation protocols, bias concerns, and the trade-offs between reliability and cost.
- Why it matters here: It is the best single entry point for designing an audit module that is both practical and defensible.

## 4. LLM-as-Judge on a Budget
- arXiv: [2602.15481](https://arxiv.org/abs/2602.15481)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2602.15481)
- Summary: The paper studies budget-aware judge allocation, showing that selective or bandit-style routing can reduce cost without giving up too much evaluation quality.
- Why it matters here: It is highly relevant for orchestration design because the audit path should be adaptive rather than uniformly expensive.

## 5. The Metanym Game: A Self-Contained, Self-Consistent LLM Peer-Community Benchmark for Structural Intelligence
- arXiv: [2606.21008](https://arxiv.org/abs/2606.21008)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2606.21008)
- Summary: This work proposes a peer-community benchmark for structural intelligence, emphasizing self-consistent evaluation through multiple model perspectives.
- Why it matters here: It expands the judge concept from single-model scoring to a richer, community-style audit process that could be useful in multi-agent settings.
