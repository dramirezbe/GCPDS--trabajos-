# Notebook Audit Report: better-hc-rf-1.ipynb

## Executive Summary
- Overall grade: **D**
- Audit mode: **DEBUG** (notebook cannot be executed locally — requires Kaggle environment, GPU, and external data)
- Critical issues: **6**
- Warnings: **5**
- Suggestions: **6**
- Reproducible (code): **Not verified — DEBUG mode**
- Reproducible (environment): **No**
- Secrets/PII exposure found: **No**

---

## Critical Issues
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | Cells 2, 4, 6, 8, 10, 12, 14, 16, 18, 22, 24 | **Scattered imports.** `import` statements are spread across 10+ code cells instead of consolidated at the top. Imports of `torch`, `numpy`, `sys`, `os` appear in multiple cells each with their own import blocks. | Consolidate ALL imports into the first code cell. Group: stdlib (`os`, `sys`, `importlib`, `time`), third-party (`torch`, `numpy`, `h5py`, `skimage`, `scipy`, `matplotlib`, `sklearn`), local (`core.*`, `models.*`, `rf_pipeline.*`). |
| 2 | All code cells | **Out-of-order execution.** Execution counts: `null, 3, null, 68, 54, 5, 6, 7, 8, 9, 10, 11, 71, 73, null, null, null`. Cells were run in a non-sequential order, meaning the notebook relies on hidden state from prior sessions. | Restart kernel and Run All to reset execution counts. Fix any cell dependency ordering. |
| 3 | Notebook-wide | **No dependency file.** No `requirements.txt`, `pyproject.toml`, `environment.yml`, or lockfile. The notebook silently depends on packages available in the Kaggle runtime (`torch`, `h5py`, `scikit-image`, `scipy`, `matplotlib`, `thop`, `tqdm`). | Create `requirements.txt` with pinned versions: `torch==2.x`, `h5py==3.x`, `scikit-image==0.2x`, `thop==0.1.x`, etc. Include it in the repo. |
| 4 | Cells 1, 4, 6, 7, 8, 14, 16 | **Hardcoded Kaggle paths.** All file paths are absolute Kaggle paths (`/kaggle/working/`, `/kaggle/input/rf-benchmark/`, `/kaggle/input/rf-benchmark-tiny/`). Notebook requires a Kaggle environment + mounted datasets. | Replace hardcoded paths with configurable variables (e.g., `os.environ` entries or a `.env` file). Document the expected data layout in a README. |
| 5 | Cells 4, 12 (U-Net and classifier training) | **No random seed initialization.** Neither `torch.manual_seed()`, `np.random.seed()`, nor `random.seed()` is called anywhere. Training results are not reproducible across runs. | Add at the top: `SEED = 42; torch.manual_seed(SEED); np.random.seed(SEED); random.seed(SEED)`. |
| 6 | Cell 1 (git clone) | **Unpinned external dependency.** `!git clone https://github.com/caltamiranda/MCE-ROI-V2.git` clones master HEAD with no commit hash or tag. Future changes to the repo can silently break the notebook. | Pin to a specific commit: `!git clone ... && cd MCE-ROI-V2 && git checkout <commit-hash>`. Document the expected commit in the README. |

---

## Warnings
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | Cell 4 (U-Net training) | **GPU determinism flags incomplete.** `torch.backends.cudnn.benchmark = True` enables performance optimization but disables determinism. No explicit `torch.backends.cudnn.deterministic = True` call. | Decide deliberately: either set `cudnn.deterministic=True; cudnn.benchmark=False` for reproducibility, or document that performance was prioritized over determinism. |
| 2 | Cells 4, 9, 16 (`DataLoader` usage) | **Multi-worker DataLoaders lack `worker_init_fn`.** `dl_train`, `dl_val`, `dl_test` all use `num_workers > 0` but no seeded `worker_init_fn`. Each worker process has its own RNG state, adding nondeterministic variation. | Add `worker_init_fn=lambda id: np.random.seed(SEED + id)` to each DataLoader. |
| 3 | Cell 14 (pipeline evaluate) | **No confusion matrix or error analysis.** The pipeline reports F1/Precision/Recall but does not show a confusion matrix or analyze false positives vs. false negatives. | Add a confusion matrix plot and discuss the business impact of FP vs FN for RF signal detection. |
| 4 | Cells 1, 4 (first 2 code cells) | **Stale/error outputs in saved notebook.** Cell 1 (git clone) has an `output_type: "error"` for ipykernel not installed. Cell 4 (U-Net training) has incomplete output — only 3 epochs shown with no completion status, suggesting the cell crashed or was interrupted mid-execution. | Clear all outputs with `nbstripout` or `nbconvert --clear-output`. Re-run from scratch, fix the errors, and save only clean outputs. |
| 5 | Cells 14 (visualize output) | **Large inline base64 image blobs.** Five `image/png` outputs with embedded base64 strings bloat the `.ipynb` file (~800KB+). This makes the notebook slow to open, hard to diff, and unfriendly to version control. | Run `nbstripout` before commits. Consider exporting plots to PNG files in a `reports/figures/` directory instead of inlining them. |

---

## Suggestions
| # | Cell(s) | Issue | Fix |
|---|---------|-------|-----|
| 1 | Cells 6, 8 | **ROI dataclass defined twice.** `@dataclass class ROI` is defined identically in cell 6 (NeuralROIDetector) and cell 8 (AdaptiveROIDetector). | Define `ROI` once in a separate cell or import it from a shared module. |
| 2 | Cell 15 (debug cell) | **Variable name mismatch.** The debug cell references `resultados[0]` but the pipeline cell defines `results`. This cell will fail with `NameError`. | Fix to `results[0].keys()` or remove the debug cell. |
| 3 | Cells 4, 6, 8 | **Inline model and class definitions.** `TinyUNet`, `DoubleConv`, `TverskyLoss`, `RPNDataset`, `NeuralROIDetector`, `AdaptiveROIDetector`, and `RFAnalysisPipeline` are all defined inline in notebook cells. | Move these to `.py` modules in the source library (e.g., `rf_pipeline/models/`, `rf_pipeline/detection/`). The notebook should import them, not define them. |
| 4 | Cell 17 (profiling) | **Wrong attribute reference.** `pipeline.model` is called in the `profile()` call, but `RFAnalysisPipeline.__init__` stores the classifier as `self.classifier`. This will raise `AttributeError`. | Fix to `pipeline.classifier` or add `self.model = self.classifier` in `__init__`. |
| 5 | Cell 12 (training loop) | **No learning curves plotted.** Training/validation metrics are printed per epoch but not plotted. Visual curves help diagnose convergence and overfitting. | Add a matplotlib subplot showing train and val loss + accuracy over epochs after training finishes. |
| 6 | Metadata | **Python version mismatch.** The kernel metadata declares Python 3.13.5, but stderr outputs reference `/usr/local/lib/python3.11/dist-packages/` (Python 3.11). The actual runtime environment is ambiguous. | Document the actual Python version used in a header markdown cell. Align kernel metadata with the real runtime. |

---

## Phase Details

### Phase 1: Structure & Readability
- **1.1 Restart & Run All:** Skipped (DEBUG mode). Notebook contains hardcoded Kaggle paths, requires GPU, and depends on external data not available locally. Runtime reproducibility remains an untested risk.
- **1.2 Markdown:** Adequate. 17 of 18 code cells have descriptive markdown headings explaining intent. Content is in Spanish; this is acceptable as long as the target audience is Spanish-speaking. Headers use `##` consistently.
- **1.3 Import Organization:** **FAIL.** Import statements are scattered across 10+ cells (see Critical #1). `torch` is imported independently at least 4 times. `numpy` at least 5 times. `sys` is appended to `sys.path` in 3 separate cells with different paths.
- **1.4 Cell Execution Order:** **FAIL.** Execution counts: 3, 68, 54, 5, 6, 7, 8, 9, 10, 11, 71, 73, with three `null` entries. The sequence 68→54→5 indicates cells were re-run out of order (likely after edits). This means the notebook's saved state does not reflect a clean top-to-bottom execution.
- **1.5 Output Hygiene:** **POOR.** Cell 1 contains an error output (`ipykernel` not installed). Cell 4 has a truncated training log (3 epochs). Five inline base64-encoded plot images bloat the file. Stale warnings from `preprocessing.py` are repeated ~40 times in stderr.

### Phase 2: Environment & Dependency Reproducibility
- **2.1 Dependency Pinning:** **FAIL.** No `requirements.txt`, lockfile, or environment spec. Libraries are assumed present in the Kaggle runtime. `thop` is installed via `!pip install thop` without a version pin. Unpinned dependencies on `torch`, `sklearn`, `h5py`, `scipy` are a risk given their frequent breaking changes.
- **2.2 Python & System Version:** **AMBIGUOUS.** Kernel metadata says Python 3.13.5, but runtime stderr paths show Python 3.11 (`/usr/local/lib/python3.11/`). CUDA version is undocumented. The Kaggle metadata says `"isGpuEnabled": false` despite the notebook using CUDA extensively.
- **2.3 Hidden External State:** **FAIL.** All paths are Kaggle-specific. The git clone fetches a live repo with no commit hash. Data files (`data.h5`) must be pre-loaded into Kaggle datasets. A second person cannot run this notebook without significant manual setup. GPU is required (15+ second epoch times on CUDA suggest training on CPU would be impractical).

### Phase 3: Data Handling & EDA
- **3.1 Data Leakage:** No issues detected. Target labels come from HDF5 metadata and are not used in preprocessing. The STFT/preprocessing transforms are applied per-sample, not across samples.
- **3.2 Train/Test/Validation Splits:** Split is done at the file level using separate HDF5 files (`train/data.h5`, `val/data.h5`, `test/data.h5`). The split was performed before this notebook. Dataset sizes are reasonable (700/150/150). No stratification check possible from static analysis.
- **3.3 Scaling/Encoding:** Preprocessing is handled by the `core.preprocessing.Preprocessor` class from the cloned repo. No `fit_transform`/`transform` leaks visible at the notebook level. However, the internals of `Preprocessor`, `FeatureEngineer`, and `VisualStream` are opaque and unauditable from this notebook alone.
- **3.4 Secrets/PII:** **Clean.** No credentials, API keys, or PII found in code cells or outputs.

### Phase 4: Model Training & Reproducibility
- **4.1 Classical ML Seeds:** N/A. The classifier is a PyTorch neural network, not classical ML. `accuracy_score` from sklearn is used only for evaluation and does not need a seed.
- **4.2 Deep Learning Seeds:** **FAIL.** No seed calls anywhere. See Critical #5 and Warnings #1-#2. `cudnn.benchmark=True` trades determinism for speed. Multi-worker dataloaders lack worker seeding. Weight initialization is left to PyTorch defaults (which are nondeterministic without a global seed).
- **4.3 Cross-Validation:** N/A. No cross-validation used. A single train/val/test split via file-level partitioning.
- **4.4 Hyperparameter Optimization:** N/A. Fixed hyperparameters throughout. Learning rate is scheduled via `ReduceLROnPlateau` for U-Net training (appropriate). No hyperparameter search touches the test set. The test set is used only in the final pipeline evaluation cell (correct).

### Phase 5: Evaluation & Metrics
- **5.1 Business Metric Alignment:** **ADEQUATE.** The classifier training uses accuracy (reasonable for roughly balanced 700-sample binary task) and `CrossEntropyLoss`. The pipeline evaluation uses Precision/Recall/F1 with IoU-based matching, which is the correct metric for object detection in spectrograms. However, the pipeline `evaluate()` method uses `iou_thresh=0.2` — a very low threshold that should be justified.
- **5.2 Overfitting/Underfitting:** **No overfitting observed.** Training accuracy plateaus at ~96%, validation at ~97% by epoch 10. The small gap suggests good generalization on this dataset. No learning curves are plotted (see Suggestion #5).
- **5.3 Confusion Matrix:** **MISSING.** The pipeline reports aggregate Precision/Recall/F1 but provides no breakdown of true positives, false positives, false negatives per signal type or per SNR level despite having an `evaluate_by_noise()` method. No discussion of the business cost of missed detections (FN) vs. false alarms (FP).

### Phase 6: Refactoring Potential
- **6.1 Rule of Three:** The `ROI` dataclass is duplicated in cells 6 and 8. The `resize(np.transpose(...), ...)` pattern appears 3+ times across the U-Net dataset and NeuralROIDetector. The training loop structure (train loop + val loop + metric accumulation) is duplicated between U-Net (cell 4) and classifier (cell 12).
- **6.2 Code Extraction Candidates:** `TinyUNet`, `DoubleConv`, `TverskyLoss`, `RPNDataset` all belong in `rf_pipeline/models/` or `rf_pipeline/data/`. `NeuralROIDetector` and `AdaptiveROIDetector` should be in `core/roi_detection.py` (the adaptive one is monkey-patched in, which is fragile). `RFAnalysisPipeline` should be a first-class library module. The notebook should be a thin orchestration layer.
- **6.3 Testability:** **NEAR-ZERO.** All logic runs in notebook cells making unit-testing impossible. The training loop, metric computation, and IoU matching logic must be extracted to `.py` files to enable `pytest` coverage. The monkey-patching pattern (`core.roi_detection.AdaptiveROIDetector = AdaptiveROIDetector`) is especially fragile and untestable.
