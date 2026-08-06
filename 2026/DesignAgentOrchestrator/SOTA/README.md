# SOTA for DesignAgentOrchestrator

This folder collects a compact, curated map of research relevant to an agent orchestrator that must support three things at once:

- audit and evaluation of LLM outputs,
- notebook-centric creation and transformation workflows, and
- skill-based orchestration through tools, plugins, and MCP servers.

## Scope and selection criteria

- Priority is given to 2025–2026 work, with a few foundational pre-2025 papers retained for context.
- Each item should be directly useful for a system like DesignAgentOrchestrator: audit pipelines, notebook lifecycle management, skill registry design, or orchestration architecture.
- The collection favors arXiv papers and official references with direct links, not PDFs stored locally.

## Reading order

1. Start with the judge foundations to understand the evaluation substrate.
2. Continue with audit-focused work for reliability and failure modes.
3. Then review notebook agents and skill-based orchestration patterns.
4. Finish with MCP ecosystem work for tool integration and execution boundaries.

## Index

- [Judge foundations](01-judge-foundations.md)
- [Audit SOTA 2025–2026](02-audit-sota-2025-2026.md)
- [Notebook agents](03-notebook-agents.md)
- [Agent skills](04-agent-skills.md)
- [MCP ecosystem](05-mcp-ecosystem.md)

## Recommended thesis for this repository

The strongest conceptual bridge for this project is the combination of three ideas:

- use judge-like evaluation pipelines to audit outputs,
- use notebook agents to turn exploratory work into production-ready artifacts,
- use skills and MCP interfaces to keep orchestration modular, auditable, and extensible.
