# AGENTS.md

## Repo structure

- **Monorepo of independent projects** organized as `YEAR/PROJECT-NAME/`. Each subproject is self-contained with its own dependencies and conventions. No shared build, test, or lint pipeline exists at the root.
- Technology stacks vary per project: Python/ML (Jupyter + PyTorch + scikit-learn), Kivy mobile, Expo/React Native, and LaTeX for formal reports.

## Project types and common patterns

- **ML/RF pipelines** (`*AuditCarlos*`, `*ANE*`, `*Curso-SDR*`): Deliverables are typically Jupyter Notebooks (`.ipynb`) with hardcoded Kaggle-style absolute paths. These notebooks are not runnable locally without adapting data paths. Training code, model definitions, and evaluation are often monolithic (single large cells).
- **Mobile apps** (`*Mamitas*`, `*MonRaF*`): Kivy (Python → APK via Buildozer) or Expo (React Native).
- **Reports**: LaTeX sources live in `report/` or `Latex_and_Diagrams/` directories. Compile with `pdflatex` (no Makefile).

## AuditCarlos notebook conventions

- `.ipynb` files are Kaggle-targeted; paths reference `/kaggle/input/` and `/kaggle/working/`.
- A notebook audit skill exists at `.agents/skills/notebook-audit/SKILL.md`. When auditing notebooks, load this skill first — it defines a 5-phase audit process (structure, data, training, evaluation, refactoring).
- Audit outputs go to `audit/`.

## Working with this repo

- Before modifying a project directory, inspect its immediate neighbors for tech stack clues (`.py` imports, `package.json`, `buildozer.spec`) rather than assuming a shared toolchain.
- Each project's entrypoint is typically the `.ipynb`, `main.py`, or `App.js` file at its root. There is no cross-project coupling.
- Git workflow is conventional; no branch rules, PR templates, or CI enforcement.
