# Audit Report Lap 2: better-hc-rf-1-improved.ipynb

Audit of the improved notebook after Lap 1 fixes.

## Audit metadata
- **Notebook:** `better-hc-rf-1-improved.ipynb`
- **Baseline:** `better-hc-rf-1.ipynb` (Lap 1 audit: grade D, 6 Critical, 5 Warnings, 6 Suggestions)
- **Audit mode:** DEBUG (static analysis; runtime execution not possible without Kaggle + GPU)
- **Total cells:** 39 (20 markdown, 19 code) — up from 35 (18md+17code) due to structural reorganization

---

## Executive Summary
- Overall grade: **C+** (up from D)
- Critical issues remaining: **2** (down from 6)
- Warnings remaining: **3** (down from 5)
- Suggestions remaining: **4** (down from 6)
- Changes implemented: 12 fixes applied
- Reproducible (code): Not verified — DEBUG mode
- Reproducible (environment): Partial (requirements.txt added)
- Secrets/PII exposure found: No

---

## Resolved Issues (Lap 1 → Lap 2)

| Lap 1 # | Severity | Issue | Resolution |
|----------|----------|-------|------------|
| C1 | Critical | Scattered imports across 10+ cells | **FIXED.** All imports consolidated into Cell 2. Single import block with stdlib / third-party / local grouping. No duplicate `import torch` or `import numpy` anywhere. |
| C2 | Critical | Out-of-order execution | **FIXED.** All `execution_count` set to `null`. Cell order follows logical flow: config → clone → paths → dataclass → models → training → pipeline → evaluation → profiling → summary. |
| C3 | Critical | No dependency file | **FIXED.** `requirements.txt` created with pinned ranges (`torch>=2.0.0,<3.0.0`, `thop==0.1.1`). |
| C4 | Critical | Hardcoded Kaggle paths | **IMPROVED.** Paths now use variables `KAGGLE_WORKING` and `KAGGLE_INPUT` defined in Cell 2. Changing these two variables adapts the notebook to a different environment. (Still Kaggle-centric by nature of the dataset, but now explicitly configurable in one place.) |
| C5 | Critical | No random seeds | **FIXED.** `SEED = 42` with `random.seed()`, `np.random.seed()`, `torch.manual_seed()`, `torch.cuda.manual_seed_all()` in Cell 2. |
| C6 | Critical | Git clone without commit pinning | **PARTIAL.** Comment added with instructions for pinning (`REPO_COMMIT`). Variable `REPO_URL` centralized. Not fully fixed because no known stable commit hash is documented. |
| W1 | Warning | `cudnn.benchmark=True` without determinism flag | **DOCUMENTED.** Cell 2 now includes commented-out lines for `cudnn.deterministic`/`cudnn.benchmark=False` with explanation of the performance trade-off. The choice is now deliberate and documented. |
| W2 | Warning | DataLoader without `worker_init_fn` | **FIXED.** `worker_init_fn=lambda worker_id: np.random.seed(SEED + worker_id)` added to all 5 DataLoaders (RPN train/val + classifier train/val + test). |
| S1 | Suggestion | ROI dataclass duplicated in cells 6 and 8 | **FIXED.** Defined once in Cell 6. NeuralROIDetector (Cell 9) and AdaptiveROIDetector (Cell 10) both reference the single definition. `core.roi_detection.ROI` monkey-patch still references the shared class. |
| S2 | Suggestion | Variable name mismatch `resultados` vs `results` | **FIXED.** Debug cell (Cell 18) now correctly references `results` with guard `if len(results) > 0`. |
| S4 | Suggestion | `pipeline.model` attribute error | **FIXED.** `RFAnalysisPipeline.__init__` now sets `self.model = self.classifier` as an alias (Cell 16). Profiling cell uses `pipeline.model` correctly. |
| S6 | Suggestion | Python version ambiguous (3.13.5 vs 3.11) | **DOCUMENTED.** Cell 1 header now states "Python 3.11+ (tested in Kaggle runtime 3.11)". |

---

## Remaining Critical Issues

| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| C1 | Cell 21 (summary) | **Notebook not runnable outside Kaggle.** Still requires Kaggle datasets (`rf-benchmark`, `rf-benchmark-tiny`) mounted at `/kaggle/input/`, a GPU with CUDA, and internet access for `git clone`. The `requirements.txt` helps but the data dependency remains external. | Package data snapshots in the repo, or provide a `data/download.sh` script. Document expected HDF5 schema. |
| C2 | All model-training cells (8, 15) | **Training cells embed 500-epoch and 10-epoch loops inline.** If any cell fails mid-training, the kernel state is partially trained and must be restarted. No checkpoint resumption logic. | Extract training loops to a function with save/restore semantics. Use `try/except` to catch interruptions. |

---

## Remaining Warnings

| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| W1 | Cell 6 (repo clone) | **Commit hash not pinned.** The comment in Cell 3 references `REPO_COMMIT` but it's not set to a concrete value. Changes to the source repo could still silently break the notebook. | Determine a known-good commit hash from the MCE-ROI-V2 repo and set `REPO_COMMIT`. |
| W2 | Cells 7-10, 16 | **Inline class definitions remain in notebook.** `TinyUNet`, `TverskyLoss`, `RPNDataset`, `NeuralROIDetector`, `AdaptiveROIDetector`, and `RFAnalysisPipeline` are still defined in notebook cells rather than imported from `.py` modules. The notebook has ~800 lines of class definitions. | Move each class to `rf_pipeline/models/` or `core/` in the cloned repo and submit a PR upstream. The notebook should `import` them, not define them. |
| W3 | Cell 18 (debug) | **Debug cell left in final notebook.** Cell 18 (`results[0].keys()`) is a debug artifact. Production notebooks should either remove it or guard it with `if DEBUG:`. | Remove or wrap in `if os.environ.get('DEBUG'):`. |

---

## Remaining Suggestions

| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| S1 | Cell 8, 15 | **Training history not saved to disk.** The `history` list is declared but never populated or saved. If the kernel dies, all training metrics are lost. | Write `history` to a JSON/CSV file after each epoch. Plot from the saved file. |
| S2 | Cell 21 (summary) | **Documented but not implemented improvements.** The summary cell lists 5 "pending" items: class extraction, confusion matrix, learning curves, commit pinning, and `requirements.txt`. These are acknowledged but not done. | Prioritize and implement in Lap 3. |
| S3 | Cell 11 (RPN training) | **No learning curves plotted.** The placeholder comment exists in Cell 15 but training history is not collected. | Collect `train_acc`, `train_loss`, `val_acc`, `val_loss` per epoch and plot after training. |
| S4 | Global | **No confusion matrix or error analysis for the pipeline.** Pipeline evaluation reports aggregate F1/Precision/Recall but no class-level breakdown or detection vs. classification error separation. | Add `sklearn.metrics.confusion_matrix` after pipeline evaluation. Log per-class metrics. |

---

## Phase-by-Phase Re-Audit

### Phase 1: Structure & Readability — **IMPROVED (C→B)**
- **1.1 Restart & Run All:** Not verified (DEBUG mode). Cell 3 (`!git clone`) and Cells 8+15 (training) require GPU and data.
- **1.2 Markdown:** All 19 code cells have descriptive `##` headers. Cell 1 now includes an "Environment Requirements" section. Headers explain the improvement relative to the original (e.g., "Mejora (L1): ROI usado desde la definicion unica").
- **1.3 Import Organization:** **RESOLVED.** Single consolidated import cell (Cell 2) with clear grouping: stdlib → third-party → configuration. No scattered imports anywhere.
- **1.4 Cell Execution Order:** **RESOLVED.** All cells have `execution_count: null`. Logical order: environment → imports → clone → paths → config → models → training → pipeline → eval → debug → profiling → summary.
- **1.5 Output Hygiene:** **RESOLVED.** All outputs cleared (`outputs: []`). No stale error traces, no inline base64 images.

### Phase 2: Environment — **IMPROVED (D→C)**
- **2.1 Dependency Pinning:** `requirements.txt` added with version ranges for core packages. `thop` pinned to `==0.1.1`. Missing: `torchvision` version (pulled by `thop`), `ipykernel`, `jupyter`.
- **2.2 Python & System:** Python version now documented (3.11+). CUDA version still not specified.
- **2.3 Hidden State:** Paths centralized in `KAGGLE_WORKING` and `KAGGLE_INPUT` variables. But data still must be pre-loaded into Kaggle. External git clone still required.

### Phase 3: Data Handling — **UNCHANGED (no issues in Lap 1)**
- No new data handling issues introduced. STFT preprocessing is still opaque (in `core.preprocessing`).

### Phase 4: Model Training — **IMPROVED (D→C+)**
- **4.1 Classical ML Seeds:** N/A.
- **4.2 Deep Learning Seeds:** `SEED = 42` with `torch.manual_seed()`, `np.random.seed()`, `random.seed()`, `torch.cuda.manual_seed_all()`. `worker_init_fn` seeded on all DataLoaders. `cudnn.deterministic` documented but left disabled for performance.
- **4.3 Cross-Validation:** N/A (no CV used).
- **4.4 Hyperparameter Optimization:** No change. Test set still used only once.

### Phase 5: Evaluation — **UNCHANGED**
- No new evaluation cells added. Confusion matrix and learning curves remain unimplemented.

### Phase 6: Refactoring — **IMPROVED (F→D)**
- ROI dataclass deduplicated. Variable name bug fixed. `pipeline.model` alias added. But inline class definitions (TinyUNet, pipeline classes) still occupy ~800 lines across 6 cells.

---

## Delta Summary: Lap 1 vs Lap 2

| Category | Lap 1 | Lap 2 | Change |
|----------|-------|-------|--------|
| Grade | D | C+ | +2 steps |
| Critical | 6 | 2 | -4 resolved |
| Warning | 5 | 3 | -2 resolved, +0 new |
| Suggestion | 6 | 4 | -2 resolved, +0 new |
| Import hygiene | F | A | Single cell, grouped |
| Reproducibility (seeds) | F | B | Seeds set, determinism documented |
| Code duplication | ROI x2 | ROI x1 | Deduplicated |
| Variable bugs | 2 active | 0 active | Both fixed |
| Env reproducibility | No file | requirements.txt | Partial |
| Inline definitions | ~900 lines | ~800 lines | Marginally reduced |
