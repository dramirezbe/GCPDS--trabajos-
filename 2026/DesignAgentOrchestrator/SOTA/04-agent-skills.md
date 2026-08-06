# Agent skills

This file covers the emerging literature on skill representations, skill evaluation, and the use of reusable capabilities in agent systems.

## 1. SkillCorpus
- arXiv: [2607.15557](https://arxiv.org/abs/2607.15557)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.15557)
- Summary: SkillCorpus focuses on building and curating a corpus of reusable skills that can support agent behavior in a more structured and compositional way.
- Why it matters here: It is strongly relevant to a skill registry architecture for DesignAgentOrchestrator.

## 2. AEVAL
- arXiv: [2607.16345](https://arxiv.org/abs/2607.16345)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.16345)
- Summary: AEVAL studies evaluation methods for agentic skill execution, which is highly relevant when skills are reused across workflows.
- Why it matters here: It supports the idea that skills should be benchmarked, not just stored.

## 3. SkillSec-Eval
- arXiv: [2607.13987](https://arxiv.org/abs/2607.13987)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.13987)
- Summary: This work highlights security-oriented evaluation for skill-based agents, which is important when skills have side effects or external tool access.
- Why it matters here: It reinforces the need for safety checks and permission-aware orchestration.

## 4. SLBench
- arXiv: [2607.09016](https://arxiv.org/abs/2607.09016)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.09016)
- Summary: SLBench targets benchmark-style evaluation for skill learning and skill execution quality.
- Why it matters here: It provides a useful benchmark framing for the skill registry and selection logic.

## 5. PL-HCL
- arXiv: [2607.10534](https://arxiv.org/abs/2607.10534)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.10534)
- Summary: This work looks at cross-layer misalignment when skills are loaded and composed in agent systems.
- Why it matters here: It is directly relevant to orchestration failures caused by incompatible or poorly scoped skills.

## 6. Skill Self-Play
- arXiv: [2607.22529](https://arxiv.org/abs/2607.22529)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.22529)
- Summary: Skill Self-Play explores how competitive co-evolution of skills can improve capability boundaries over time.
- Why it matters here: It is useful for future extensions where the orchestrator learns or refines skills dynamically.

## 7. SkillReranker
- arXiv: [2607.06283](https://arxiv.org/abs/2607.06283)
- PDF: [arXiv PDF](https://arxiv.org/pdf/2607.06283)
- Summary: This line of work focuses on ranking or selecting the best skill for a given task.
- Why it matters here: It maps directly to the routing and selection logic in an orchestrator.

## Official reference

- Anthropic Agent Skills: https://agentskills.io

This is a useful design reference for understanding how skill descriptions, invocation patterns, and tool boundaries can be formalized.
