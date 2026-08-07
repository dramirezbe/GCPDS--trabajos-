# AGENTS.md — JupyterPrompting

## Project overview

This project is a collection of Jupyter notebooks for prompt engineering experiments and tutorials. It contains a curated set of skills for notebook creation, editing, and quality auditing. All work lives under `/home/javastral/GIT/UNAL/GCPDS-trabajos/2026/JupyterPrompting/`.

## Available skills

### `final-nb-skill` — Raw notebook generator

Generates a complete `.ipynb` file as raw JSON. Use when you need a ready-to-run notebook from a description.

- **Output**: Raw JSON only — no markdown fences, no explanations.
- **Required fields**: `nbformat`, `nbformat_minor`, `metadata` (with `kernelspec` and `language_info`), `cells`.
- **Code cells**: must have `execution_count: null`, `outputs: []`, unique `id`.
- **Source**: array of strings, each line ends with `\n` except the last.

### `jupyter-notebook` — Scaffold from templates

Creates notebooks from bundled templates using `new_notebook.py`. Supports two modes:

| Kind | When to use |
|------|-------------|
| `experiment` | Exploratory, hypothesis-driven, analytical work |
| `tutorial` | Instructional, step-by-step, audience-facing |

```bash
# Scaffold experiment
python skills/jupyter-notebook/scripts/new_notebook.py \
  --kind experiment \
  --title "Compare prompt variants" \
  --out nb-outputs/compare-prompt-variants.ipynb

# Scaffold tutorial
python skills/jupyter-notebook/scripts/new_notebook.py \
  --kind tutorial \
  --title "Intro to embeddings" \
  --out nb-outputs/intro-to-embeddings.ipynb
```

### `jupyter-notebook-writing` — Markdown-first workflow

Write notebook content as Markdown, then convert with `uvx jupyter-switch`. The `.md` file is the source of truth.

```bash
# Markdown → Notebook
uvx jupyter-switch example.md

# Notebook → Markdown
uvx jupyter-switch example.ipynb
```

### `notebook` — Edit cells with jq

Modify existing `.ipynb` cells programmatically: list, replace, insert, delete. Uses `jq` for safe JSON manipulation. Always back up before complex edits.

## Running notebooks

Use the local venv at `./venv/`:

```bash
./venv/bin/jupyter execute NOTEBOOK.ipynb
# or
./venv/bin/jupyter run NOTEBOOK.ipynb
```

## Auditing notebooks

### Form audit (structure)

Check these on every `.ipynb`:

1. **Metadata**: `nbformat: 4`, `nbformat_minor: 5`, valid `kernelspec` and `language_info`.
2. **Cell IDs**: every cell has a unique `id` string.
3. **Code cells**: `execution_count: null`, `outputs: []` if not yet executed.
4. **Source format**: array of strings, lines end with `\n` except the last.
5. **Markdown cells**: `cell_type: "markdown"`, `metadata: {}`.
6. **JSON validity**: parseable by `json.loads()` — no trailing commas, no missing braces.

```bash
# Quick structure check
jq 'keys' NOTEBOOK.ipynb
jq '.cells | length' NOTEBOOK.ipynb
jq '.cells[] | {type: .cell_type, id: .id}' NOTEBOOK.ipynb
```

### Code quality audit

Run after every notebook modification:

```bash
./venv/bin/jupyter execute NOTEBOOK.ipynb 2>&1
```

Check for:

1. **Top-to-bottom execution**: no hidden state, no skipped cells.
2. **Clean outputs**: no giant tables or noisy output — prefer summaries.
3. **Narrative flow**: headings, short bullets, no long paragraphs.
4. **Imports at top**: all dependencies in early cells.
5. **No hardcoded secrets**: API keys use placeholders or env vars.
6. **TODOs labeled**: only when necessary, clearly marked.
7. **Dependencies external**: `pip install` cells should not run inside the notebook — install in the venv beforehand.

### Quality checklist (pre-delivery)

- [ ] Notebook runs top-to-bottom without errors
- [ ] Early cells set all required state
- [ ] Outputs are tidy (small tables, key metrics, short printouts)
- [ ] Narrative is skimmable with headings and bullets
- [ ] No hidden state from prior runs
- [ ] If execution fails, risk is documented with local validation steps

## Directory conventions

| Directory | Purpose |
|-----------|---------|
| `skills/` | Notebook-related skills |
| `nb-outputs/` | Final generated notebooks |
| `prompts/` | Prompt templates |
| `error-nb/` | Notebooks with intentional errors (for testing) |
| `venv/` | Local Python environment with jupyter |

## Style rules for notebooks

- **Experiment notebooks**: Title → Objective → Setup → Plan → Baseline → Results → Next Steps.
- **Tutorial notebooks**: Title → Audience/Prerequisites → Outline → Steps → Exercises → Pitfalls.
- Keep each code cell focused on one step.
- Add short markdown explanations before code cells.
- Set random seeds early for reproducibility.
- Prefer `uv` for dependency management.
