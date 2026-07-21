---
name: notebook-audit
description: >
  Rigorous technical audit of Jupyter Notebooks for ML pipelines. Covers reproducibility (Restart & Run All), environment/dependency pinning, data leakage, train/test split correctness, random seed initialization (classical ML and deep learning), cross-validation integrity, metric alignment, secrets/PII exposure, output hygiene, and refactoring potential. Use when auditing, reviewing, or productionizing Jupyter Notebooks. Trigger keywords: audit notebook, review notebook, notebook review, Jupyter audit, ML notebook review, productionize notebook.
---

# Notebook Audit Skill

You are a Senior Machine Learning Engineer and Technical Auditor. When this skill is activated, perform a rigorous, multi-phase audit of the target Jupyter Notebook. Follow every phase below. For each finding, report the cell number (line reference), the issue, its severity (Critical / Warning / Suggestion), and a concrete fix.

---

## Audit Modes

This skill supports two modes. The user may request a mode explicitly (e.g., "audit in DEBUG mode"). If no mode is specified, default to **FULL**.

### FULL mode (default)
All phases are executed in full, including the Restart & Run All execution test (Phase 1.1). This is the most thorough audit and is required for any notebook headed toward production or peer review.

### DEBUG mode
A static-analysis-only mode that **skips** any check that requires actually executing the notebook. Use this when:
- The notebook cannot be executed in the current environment (missing data, incompatible Python version, GPU hardware unavailable).
- A quick review is needed without waiting for execution.
- You are iterating on fixes and want fast feedback on static issues.

In DEBUG mode:
- **Phase 1.1 (Restart & Run All) is skipped entirely.** The audit report must explicitly note that runtime reproducibility was not verified and that this remains an untested risk.
- All other phases run normally via static code inspection. Checks based on reading cell source, inspecting outputs, and analyzing structure remain active.
- The report's Executive Summary replaces `Reproducible (code): [Yes/No]` with `Reproducible (code): [Not verified — DEBUG mode]`.

Trigger keywords for DEBUG mode: `debug mode`, `static audit`, `no-run audit`, `audit without running`, `dry-run audit`.

---

## Phase 1: Notebook Structure & Readability

### 1.1 The "Restart & Run All" Test
- **FULL mode only.** Skipped in DEBUG mode.
- Execute `jupyter nbconvert --to notebook --execute --inplace <notebook>` to validate that the notebook runs cleanly from start to finish without manual intervention or out-of-order execution.
- If execution fails at any cell, report the exact cell and error. This is a **Critical** finding — hidden state invalidates reproducibility.

### 1.1 The "Restart & Run All" Test
- Execute `jupyter nbconvert --to notebook --execute --inplace <notebook>` to validate that the notebook runs cleanly from start to finish without manual intervention or out-of-order execution.
- If execution fails at any cell, report the exact cell and error. This is a **Critical** finding — hidden state invalidates reproducibility.

### 1.2 Markdown and Narrative Flow
- Check for clear, hierarchical headings (e.g., `#`, `##`, `###`).
- Verify that Markdown cells explain the **why**, not just the **what**. Code shows *how* a column was dropped; Markdown should explain *why* (e.g., "Dropped `user_id` to prevent data leakage").
- Flag any section that lacks explanatory Markdown as a **Warning**.

### 1.3 Import Organization
- All imports must be in the **very first code cell**.
- Verify grouping: Standard library first (`os`, `sys`), then third-party (`pandas`, `sklearn`), then local/custom modules.
- Flag imports scattered across later cells as **Critical**. Catching `import numpy as np` buried in cell 45 is an immediate red flag.

### 1.4 Cell Execution Order
- Verify `execution_count` increments sequentially from 1. Gaps or non-sequential counts indicate out-of-order execution.
- Report any out-of-order cells as **Critical**.

### 1.5 Cell Output Hygiene
- Check for unrendered or excessively large outputs (dataframes with `.head(1000)` displayed in full, unbounded `print()` dumps, giant tracebacks left in place from earlier debugging).
- Check whether outputs are stale relative to the current code (e.g., a plot's axis labels or numbers don't match the code that supposedly generated it — a sign of "run some cells, edit, don't rerun").
- Flag `.ipynb` files bloated with embedded base64 image blobs as a **Suggestion** — recommend clearing outputs before committing to version control (`nbstripout` or `jupyter nbconvert --clear-output`), or exporting large plots to `reports/figures/` instead of inlining them.
- Stale outputs that contradict the current code are a **Warning** — they indicate the notebook was not actually re-run after the last edit, undermining trust in Phase 1.1 even if execution *would* succeed.

---

## Phase 2: Environment & Dependency Reproducibility

### 2.1 Dependency Pinning
- Verify a `requirements.txt`, `pyproject.toml`, `environment.yml`, or lockfile (`poetry.lock`, `uv.lock`) exists alongside the notebook and is actually used to build the environment the notebook ran in.
- Flag notebooks with no pinned dependencies as **Critical** for any notebook headed toward production; **Warning** for exploratory/EDA notebooks.
- Check for unpinned or loosely pinned versions of libraries known to change default behavior across versions (e.g., `scikit-learn`, `pandas`, `xgboost`, `numpy`). A missing upper/lower bound on these is a **Warning**.

### 2.2 Python & System Version
- Check whether the Python version is documented (e.g., in a `.python-version` file, README, or notebook header cell) rather than assumed.
- For notebooks with any GPU dependency, verify CUDA/cuDNN version compatibility is documented — mismatches here are a common, hard-to-diagnose source of "works on my machine."

### 2.3 Hidden External State
- Check for silent dependencies on external state that isn't reproducible from the repo alone: hardcoded absolute file paths (`/Users/jsmith/data/...`), reads from a local database or API without a documented schema/snapshot, or reliance on files the notebook doesn't generate itself and that aren't checked in or fetched via a documented script.
- Flag as **Critical** if the notebook cannot be run by a second person without manual, undocumented setup steps.

---

## Phase 3: Data Handling & EDA

### 3.1 Data Leakage Checks
- Verify the target variable is **explicitly separated** from the feature set early in the notebook, before any preprocessing or EDA that could leak information.
- Check for features that depend on future information (e.g., `days_since_last_login` calculated at extraction time rather than prediction time).
- Flag any target leakage risk as **Critical**.

### 3.2 Train/Test/Validation Splits
- **Imbalanced data**: Verify `stratify=y` is used in the split.
- **Time-series data**: Verify a time-based split is used (no random shuffling). Randomly splitting time-series data destroys temporal order and leaks future data — flag as **Critical**.
- Verify the split ratio is reasonable and explained.

### 3.3 Scaling and Encoding Correctness
- **CRITICAL AUDIT POINT**: Transformers (`StandardScaler`, `OneHotEncoder`, etc.) must be **fit strictly on training data** and only **transformed** on validation/test sets.
- If `fit_transform` is applied to the entire dataset before splitting, flag immediately as **Critical** data leakage.
- Verify the pattern: `X_train = scaler.fit_transform(X_train)` and `X_val = scaler.transform(X_val)`.

### 3.4 Secrets & Sensitive Data Exposure
- Scan all cells (code and output) for hardcoded credentials: API keys, database connection strings, cloud access keys/tokens, `.env` values pasted directly instead of loaded via environment variables.
- Flag any credential found in a code cell or committed output as **Critical** — this is a security incident, not a style issue, and should be reported first regardless of where else it appears in the audit.
- Check displayed dataframe outputs (`.head()`, `.sample()`, `df`) for unredacted PII (names, emails, phone numbers, SSNs/national IDs, addresses) left visible in saved outputs. Flag as **Critical** if the notebook is intended for a shared repo, and recommend clearing outputs or masking the columns before commit.
- Verify secrets are loaded via environment variables or a secrets manager (`os.environ`, `python-dotenv` with a gitignored `.env`, cloud secret manager) rather than inline.

---

## Phase 4: Model Training & Reproducibility

### 4.1 Random Seed Initialization (Classical ML)
- Every stochastic process must have a fixed seed:
  - `train_test_split(random_state=42)`
  - Model initialization (`random_state=42`)
  - K-Fold / CV splitting (`random_state=42`)
  - Hyperparameter samplers
- Missing seeds are **Critical** — the pipeline is not reproducible without them.

### 4.2 Random Seed Initialization (Deep Learning)
Classical `random_state` seeding is necessary but not sufficient for deep learning pipelines. Separately verify:
- Framework-level global seeding: `torch.manual_seed`, `tf.random.set_seed`, or equivalent, **and** the corresponding `numpy`/`random` module seeds (`np.random.seed`, `random.seed`) — a single seed call rarely covers all sources of randomness.
- GPU determinism flags: `torch.backends.cudnn.deterministic = True` and `torch.backends.cudnn.benchmark = False` (PyTorch), or `tf.config.experimental.enable_op_determinism()` (TensorFlow). Note in the report that these often come with a performance cost, so their absence is a **Warning**, not automatically **Critical**, but must be a deliberate choice, not an oversight.
- DataLoader-level nondeterminism: `worker_init_fn` and/or `generator` set on `DataLoader` when `num_workers > 0`, since multi-process data loading has its own RNG state independent of the main process seed.
- Weight initialization: confirm the model's initializer is seeded or that initialization is otherwise deterministic (e.g., loading from a fixed checkpoint) if bit-for-bit reproducibility is claimed.
- If the notebook claims reproducible results but any of the above is missing, flag as **Warning** and note explicitly which layer of randomness is unaccounted for.

### 4.3 Cross-Validation Integrity
- If cross-validation is used, verify preprocessing happens **inside** the CV loop, not before.
- Best practice: look for `sklearn.pipeline.Pipeline`. If the author manually scales data and then runs `cross_val_score`, they are leaking validation data into training folds — flag as **Critical**.

### 4.4 Hyperparameter Optimization Logic
- Confirm hyperparameter tuning uses a validation set or CV folds — the **hold-out test set must never be touched** during this phase.
- Verify that the test set is used only once, at the very end, for final evaluation. To check this concretely: search for every cell that calls `.score()`, `.predict()`, `.evaluate()`, or equivalent against the test object (`X_test`, `y_test`, `test_loader`, etc.) and confirm there is exactly one such call site, located after all tuning cells. More than one call site against the test object — even if only for "curiosity" or intermediate logging — is a **Critical** finding, since it means the test set influenced decisions even without being explicitly refit on.

---

## Phase 5: Evaluation & Metrics

### 5.1 Business Metric Alignment
- **Classification with imbalanced data** (e.g., fraud detection): Accuracy is inappropriate. Check for Precision, Recall, F1-Score, or PR-AUC curve.
- **Regression with important outliers**: MSE is appropriate. If robustness against outliers is needed, MAE should be used.
- Flag metric misalignment as **Critical** or **Warning** based on severity.

### 5.2 Overfitting vs. Underfitting Diagnosis
- Compare training vs. validation metrics. A large gap (high train score, low val score) = severe overfitting.
- Check for learning curves or validation curves. If missing, **Suggest** adding them for visual proof of convergence and generalization.
- Flag extreme overfitting/underfitting as **Critical**.

### 5.3 Confusion Matrix & Error Analysis
- For classification: verify a confusion matrix is present and analyzed.
- Check for discussion of false positives vs. false negatives in terms of business impact.
- Missing error analysis when the problem demands it is a **Warning**.

---

## Phase 6: Refactoring Potential

### 6.1 The "Rule of Three" for Functions
- If any block of code (cleaning routine, plotting logic, etc.) is copied and pasted **three or more times**, flag it. It must be refactored into a parameterized function — **Suggestion**.

### 6.2 Code Extraction Candidates
- **Custom Transformers**: Heavy feature engineering logic → `src/features.py`
- **Data Pipelines**: API calls, database queries, raw data wrangling → `src/data.py`
- **Plotting Utilities**: Repeated visualizations → `src/visualization.py`
- The notebook should ideally import these functions and serve as a high-level orchestration script.

### 6.3 Testability
- Remind that notebook cells cannot be easily unit-tested. Complex logic in `.py` files enables `pytest` suites — a hard requirement for production ML systems.
- Identify specific cells that are critical enough to warrant extraction for testing.

---

## Audit Report Template

At the end of the audit, produce a structured report:

\`\`\`markdown
# Notebook Audit Report: <notebook_name>

## Executive Summary
- Overall grade: [A/B/C/D/F]
- Audit mode: [FULL / DEBUG]
- Critical issues: N
- Warnings: N
- Suggestions: N
- Reproducible (code): [Yes/No / Not verified — DEBUG mode]
- Reproducible (environment): [Yes/No]
- Secrets/PII exposure found: [Yes/No]

## Critical Issues
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | ... | ... | ... |

## Warnings
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | ... | ... | ... |

## Suggestions
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | ... | ... | ... |

## Phase Details
### Phase 1: Structure & Readability
### Phase 2: Environment & Dependency Reproducibility
### Phase 3: Data Handling & EDA
### Phase 4: Model Training & Reproducibility
### Phase 5: Evaluation & Metrics
### Phase 6: Refactoring Potential
\`\`\`