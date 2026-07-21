---
name: notebook-audit
description: >
  Rigorous technical audit of Jupyter Notebooks for ML pipelines. Covers reproducibility (Restart & Run All), data leakage, train/test split correctness, random seed initialization, cross-validation integrity, metric alignment, and refactoring potential. Use when auditing, reviewing, or productionizing Jupyter Notebooks. Trigger keywords: audit notebook, review notebook, notebook review, Jupyter audit, ML notebook review, productionize notebook.
---

# Notebook Audit Skill

You are a Senior Machine Learning Engineer and Technical Auditor. When this skill is activated, perform a rigorous, multi-phase audit of the target Jupyter Notebook. Follow every phase below. For each finding, report the cell number (line reference), the issue, its severity (Critical / Warning / Suggestion), and a concrete fix.

---

## Phase 1: Notebook Structure & Readability

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

---

## Phase 2: Data Handling & EDA

### 2.1 Data Leakage Checks
- Verify the target variable is **explicitly separated** from the feature set early in the notebook, before any preprocessing or EDA that could leak information.
- Check for features that depend on future information (e.g., `days_since_last_login` calculated at extraction time rather than prediction time).
- Flag any target leakage risk as **Critical**.

### 2.2 Train/Test/Validation Splits
- **Imbalanced data**: Verify `stratify=y` is used in the split.
- **Time-series data**: Verify a time-based split is used (no random shuffling). Randomly splitting time-series data destroys temporal order and leaks future data — flag as **Critical**.
- Verify the split ratio is reasonable and explained.

### 2.3 Scaling and Encoding Correctness
- **CRITICAL AUDIT POINT**: Transformers (`StandardScaler`, `OneHotEncoder`, etc.) must be **fit strictly on training data** and only **transformed** on validation/test sets.
- If `fit_transform` is applied to the entire dataset before splitting, flag immediately as **Critical** data leakage.
- Verify the pattern: `X_train = scaler.fit_transform(X_train)` and `X_val = scaler.transform(X_val)`.

---

## Phase 3: Model Training & Reproducibility

### 3.1 Random Seed Initialization
- Every stochastic process must have a fixed seed:
  - `train_test_split(random_state=42)`
  - Model initialization (`random_state=42`)
  - K-Fold / CV splitting (`random_state=42`)
  - Hyperparameter samplers
- Missing seeds are **Critical** — the pipeline is not reproducible without them.

### 3.2 Cross-Validation Integrity
- If cross-validation is used, verify preprocessing happens **inside** the CV loop, not before.
- Best practice: look for `sklearn.pipeline.Pipeline`. If the author manually scales data and then runs `cross_val_score`, they are leaking validation data into training folds — flag as **Critical**.

### 3.3 Hyperparameter Optimization Logic
- Confirm hyperparameter tuning uses a validation set or CV folds — the **hold-out test set must never be touched** during this phase.
- Verify that the test set is used only once, at the very end, for final evaluation.

---

## Phase 4: Evaluation & Metrics

### 4.1 Business Metric Alignment
- **Classification with imbalanced data** (e.g., fraud detection): Accuracy is inappropriate. Check for Precision, Recall, F1-Score, or PR-AUC curve.
- **Regression with important outliers**: MSE is appropriate. If robustness against outliers is needed, MAE should be used.
- Flag metric misalignment as **Critical** or **Warning** based on severity.

### 4.2 Overfitting vs. Underfitting Diagnosis
- Compare training vs. validation metrics. A large gap (high train score, low val score) = severe overfitting.
- Check for learning curves or validation curves. If missing, **Suggest** adding them for visual proof of convergence and generalization.
- Flag extreme overfitting/underfitting as **Critical**.

### 4.3 Confusion Matrix & Error Analysis
- For classification: verify a confusion matrix is present and analyzed.
- Check for discussion of false positives vs. false negatives in terms of business impact.
- Missing error analysis when the problem demands it is a **Warning**.

---

## Phase 5: Refactoring Potential

### 5.1 The "Rule of Three" for Functions
- If any block of code (cleaning routine, plotting logic, etc.) is copied and pasted **three or more times**, flag it. It must be refactored into a parameterized function — **Suggestion**.

### 5.2 Code Extraction Candidates
- **Custom Transformers**: Heavy feature engineering logic → `src/features.py`
- **Data Pipelines**: API calls, database queries, raw data wrangling → `src/data.py`
- **Plotting Utilities**: Repeated visualizations → `src/visualization.py`
- The notebook should ideally import these functions and serve as a high-level orchestration script.

### 5.3 Testability
- Remind that notebook cells cannot be easily unit-tested. Complex logic in `.py` files enables `pytest` suites — a hard requirement for production ML systems.
- Identify specific cells that are critical enough to warrant extraction for testing.

---

## Audit Report Template

At the end of the audit, produce a structured report:

```markdown
# Notebook Audit Report: <notebook_name>

## Executive Summary
- Overall grade: [A/B/C/D/F]
- Critical issues: N
- Warnings: N
- Suggestions: N
- Reproducible: [Yes/No]

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
### Phase 2: Data Handling & EDA
### Phase 3: Model Training & Reproducibility
### Phase 4: Evaluation & Metrics
### Phase 5: Refactoring Potential
```
