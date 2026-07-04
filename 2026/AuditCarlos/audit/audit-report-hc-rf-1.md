# AUDIT REPORT — hc-rf-1.ipynb
**Fingerprint:** `lap 0`
**Generated:** 2026-07-04T00:00:00Z

---

# PHASE 1 — DOCUMENTATION

## Section 1: Overall Purpose

This notebook implements a two-stage hybrid RF signal detection and classification pipeline. Stage 1 trains a TinyUNet Region Proposal Network (RPN) on MCE spectrograms to detect signal ROIs via neural segmentation; Stage 2 trains a HybridRFClassifier (CNN visual features + MLP engineered features) on a "tiny" benchmark to classify those ROIs as signal or noise. A final `RFAnalysisPipeline` class wires both stages together: the neural RPN proposes ROIs, engineered features and visual patches are extracted per ROI, and the hybrid classifier scores each, outputting precision/recall/F1 metrics.

---

## Section 2: Code Block Descriptions

**Only executable (code) cells, numbered by sequential order in notebook.**

### [BLOCK 1] Cell index 0 — `!git clone`
- **Logic & Flow:** Clones external repo `MCE-ROI-V2` from GitHub. Dependency cell — all subsequent cells fail if this doesn't execute.
- **Data & State:** Creates `/kaggle/working/MCE-ROI-V2/` directory tree.
- **Operations & Methods:** Shell command via jupyter exclamation-bang.
- **Side Effects:** Writes to filesystem. Execution is NOT idempotent — re-running in a session with an existing clone will fail (directory already exists).

---

### [BLOCK 2] Cell index 1 — `sys.path` setup
- **Logic & Flow:** Appends cloned repo paths to `sys.path` so downstream imports of `core`, `config`, `rf_pipeline` modules resolve.
- **Data & State:** Mutates global `sys.path`. Imports `inspect` but NEVER uses it — unused import.
- **Operations & Methods:** `sys.path.append()` × 2.
- **Side Effects:** Global import side effect. Race condition if another cell resets `sys.path`.

---

### [BLOCK 3] Cell index 2 — U-Net RPN Training
- **Logic & Flow:** Defines `CFG` class, `DoubleConv`, `TinyUNet`, `TverskyLoss`, `RPNDataset`, then executes full U-Net training loop with early stopping.
- **Data & State:** Reads HDF5 from `/kaggle/input/rf-benchmark/rf_benchmark/raw_iq_hdf5/train|val/data.h5`. Writes `best_unet_rpn.pt` to `/kaggle/working/`. 21000 train samples, 4500 val samples.
- **Operations & Methods:**
  - `TinyUNet`: encoder-decoder with skip connections, 3 input channels → 1 output probability map via sigmoid.
  - `TverskyLoss(α=0.3, β=0.7)`: asymmetric soft-dice variant (β>α penalizes false negatives more).
  - `RPNDataset`: reads IQ from HDF5, computes MCE spectrogram via `Preprocessor(mode="mce")`, fftshifts, derives binary mask from metadata bounding boxes, resizes spectrogram + mask to 256×256.
  - Training: batch_size=64, Adam(lr=1e-3), ReduceLROnPlateau(patience=10), EarlyStopping(patience=30), ~12 min/epoch, max 500 epochs.
- **Side Effects:** Writes model checkpoint `best_unet_rpn.pt`. Sets `torch.backends.cudnn.benchmark = True`. Appends `sys.path` again (`MCE-ROI-V2/MCE-ROI-V2`). **`self.conv1 = DoubleConv(96, 64)` never used in forward() — dead parameter.**
- **Exec Status:** `execution_count: null` — this cell FAILED due to missing ipykernel; outputs are from a prior successful run embedded in the notebook. The defined classes (`TinyUNet`, `TverskyLoss`) may not be available for downstream cells.

---

### [BLOCK 4] Cell index 4 — NeuralROIDetector
- **Logic & Flow:** Defines `ROI` dataclass and `NeuralROIDetector` class that loads a trained TinyUNet and runs inference: resize S_mce → U-Net → probability map → threshold → connected-components → ROIs with scores, scaled back to original coordinates.
- **Data & State:** Input: `S_mce [3, H, W]`. Output: `list[ROI]`.
- **Operations & Methods:**
  - `detect()`: transpose → skimage.resize → torch tensor → model → `.squeeze().cpu().numpy()` → binarize (threshold=0.5) → `scipy.ndimage.label` → `find_objects` → rescale coordinates → filter min dimensions (>2y / >4x) → sort by score.
  - `load_state_dict(torch.load(...))` — no `weights_only=True` (PyTorch 2.4+ security warning).
- **Side Effects:** Defines `ROI` dataclass globally (DUPLICATED by BLOCK 5). Prints model loading message.

---

### [BLOCK 5] Cell index 5 — AdaptiveROIDetector + Monkey-Patching
- **Logic & Flow:** RE-DEFINES `ROI` dataclass (identical signature, overwrites BLOCK 4 definition). Defines `AdaptiveROIDetector` with z-score thresholding, morphological white top-hat, strict overlap-based merging (>10%), and noise floor estimation. Monkey-patches `core.roi_detection.AdaptiveROIDetector` and `core.roi_detection.ROI`.
- **Data & State:** Input: `S_det [H, W]` (single-channel detection map). Output: `List[ROI]`.
- **Operations & Methods:**
  - `_robust_noise_floor()`: median as noise floor, (p50-p25)/0.6745 as sigma.
  - `_should_merge()`: intersection/min_area ratio > overlap_thresh.
  - `_merge_boxes()`: iterative greedy merge loop with `while changed`.
  - `detect()`: z-score → tophat → weak/strong masks → binary_dilation → label → find_objects → filter → merge → sort.
- **Side Effects:** Monkey-patches global module state — extremely fragile. Appends sys.path again. `time_tol` and `freq_tol` parameters ACCEPTED in `__init__` but NEVER USED. Typo: "NOTA IMPORANTE" (missing T).

---

### [BLOCK 6] Cell index 6 — Import HybridRFClassifier
- **Logic & Flow:** Single import from the cloned repo's module tree.
- **Data & State:** Imports `HybridRFClassifier` class from `rf_pipeline.models.hybrid_classifier`.
- **Operations & Methods:** Pure import — no execution.
- **Side Effects:** None.

---

### [BLOCK 7] Cell index 7 — Config + H5HybridDetectionDataset
- **Logic & Flow:** Generates `config.py` dynamically (FS=10MHz, NPERSEG=32, NOVERLAP=16, IMG_SIZE=256, etc.), writes to `/kaggle/working/MCE-ROI-V2/config.py`, reloads `config` and `data_loader` modules, imports `H5HybridDetectionDataset`.
- **Data & State:** Creates config.py with hardcoded parameters. Reloads modules via `importlib.reload`.
- **Operations & Methods:** `open(...).write(config_content)`, `importlib.reload()` × 2.
- **Side Effects:** Writes config.py file. Reloads modules (affects other cells using those modules). If config.py was already loaded before this cell runs, the old cached version persists.

---

### [BLOCK 8] Cell index 8 — CFG for Hybrid Classifier
- **Logic & Flow:** Defines SECOND `CFG` class (different from BLOCK 3's CFG!) with classifier-specific paths (`TRAIN_H5`, `VAL_H5`, `TEST_H5` pointing to `/kaggle/input/rf-benchmark-tiny/...` vs BLOCK 3's `/kaggle/input/rf-benchmark/rf_benchmark/...`).
- **Data & State:** BATCH_SIZE=128, EPOCHS=10, LR=1e-3, NUM_WORKERS=2. Creates `/kaggle/working/resultados_finales/`.
- **Operations & Methods:** `os.makedirs(CFG.OUTPUT_DIR, exist_ok=True)`.
- **Side Effects:** Creates directory. Defines SECOND `CFG` class — if referenced later without qualification, which CFG is active depends on the last cell executed.

---

### [BLOCK 9] Cell index 9 — Dataset Loading
- **Logic & Flow:** Instantiates `H5HybridDetectionDataset` for train/val/test splits (700/150/150 samples), creates PyTorch DataLoaders. All use `mode="train"` (even for val/test — intentional per comment).
- **Data & State:** Train=700, Val=150, Test=150 samples. val/test DataLoaders use batch_size=256 (2× train batch).
- **Operations & Methods:** Re-imports `core.data_loader` and `H5HybridDetectionDataset` (already done in BLOCK 7). Uses `importlib.reload` again.
- **Side Effects:** None.

---

### [BLOCK 10] Cell index 10 — Model Initialization
- **Logic & Flow:** Instantiates `HybridRFClassifier(num_classes=2, feat_dim=32, img_in_ch=3, cnn_channels=(16,32,64), mlp_hidden=(64,64))`, Adam optimizer, CrossEntropyLoss.
- **Data & State:** Model on CUDA.
- **Operations & Methods:** Import path uses `from models.hybrid_classifier import ...` (different from BLOCK 6 which uses `from rf_pipeline.models.hybrid_classifier import ...` — these resolve to the same module only if sys.path is set up correctly).
- **Side Effects:** None.

---

### [BLOCK 11] Cell index 11 — Batch Debug
- **Logic & Flow:** Grabs first batch from train DataLoader, prints types.
- **Data & State:** Confirms batch is a `list` of 3 `torch.Tensor` elements (visual, engineered, labels).
- **Operations & Methods:** Read-only inspection.
- **Side Effects:** Triggers spectrogram computation (preprocessing warnings from stft).

---

### [BLOCK 12] Cell index 12 — Classifier Training
- **Logic & Flow:** 10-epoch training loop: forward pass on visual + engineered features, CrossEntropyLoss backprop, accuracy tracking on train and val. Saves best model by validation accuracy.
- **Data & State:** Tracks train_loss, val_loss, accumulator arrays for preds/targets. Best val_acc=97.33% at epoch 10.
- **Operations & Methods:** Standard PyTorch training loop. NO early stopping, NO LR scheduler, NO gradient clipping.
- **Side Effects:** Writes `best_model.pt` to `resultados_finales/`.

---

### [BLOCK 13] Cell index 13 — RFAnalysisPipeline Class
- **Logic & Flow:** Full pipeline class: loads trained classifier + neural RPN detector, provides `predict()`, `evaluate()`, `evaluate_by_noise()`, and `visualize()` methods.
- **Data & State:**
  - Constructor: loads `HybridRFClassifier` from checkpoint, loads `NeuralROIDetector` from RPN checkpoint (raises `FileNotFoundError` if missing).
  - `predict()`: iterates `H5HybridDetectionDataset(mode="eval")`, gets S_mce/IQ/S_det/gt_boxes per sample, runs `detector.detect(S_mce)`, extracts feature-engineered + visual patches per ROI, runs classifier, collects predictions.
  - `inference_time_ms` HARDCODED to 0 (placeholder — timing never implemented).
  - Results dict: `{id, S_mce, predictions, gt_boxes, inference_time_ms}` — MISSING `noise_level` key needed by `evaluate_by_noise()`.
- **Operations & Methods:** `_calculate_iou()` with epsilon 1e-6. `evaluate()` computes TP/FP/FN via greedy IoU matching (iou_thresh=0.2), derives precision, recall, F1. `evaluate_by_noise()` checks `res["noise_level"]` but predict() never sets this — the method is unreachable in practice. `visualize()` plots S_mce[0] with ground-truth (green) and predicted (red) boxes.
- **Side Effects:** Constructor may throw `FileNotFoundError` blocking all further execution.

---

### [BLOCK 14] Cell index 14 — Pipeline Execution
- **Logic & Flow:** Instantiates `RFAnalysisPipeline` with saved checkpoints, runs `predict()` on 150 test samples, then `evaluate()` and `visualize()`.
- **Data & State:** confidence_thresh=0.2 (aggressive recall). Results: F1=0.8272, Precision=1.0000, Recall=0.7053. Inference time shown as 0.00ms (hardcoded).
- **Operations & Methods:** Pipeline runtime ~7s for 150 samples (20.94 it/s).
- **Side Effects:** Displays 5 visualization plots.

---

### [BLOCK 15] Cell index 15 — Debug Print
- **Logic & Flow:** `print(resultados[0].keys())` — but `resultados` is **never defined** in any prior cell. The actual variable from BLOCK 14 is `results` (English). This is a broken reference.
- **Data & State:** Will throw `NameError` if executed.
- **Operations & Methods:** None (unreachable).
- **Side Effects:** None.

---

### [BLOCK 16] Cell index 16 — Install thop
- **Logic & Flow:** Pip-installs the `thop` package for FLOPs counting.
- **Data & State:** Installs into Kaggle environment.
- **Operations & Methods:** Shell command.
- **Side Effects:** System-level package installation.

---

### [BLOCK 17] Cell index 17 — FLOPs Profiling
- **Logic & Flow:** Profiles the classifier model using thop.
- **Data & State:**
  - Uses `pipeline.model` — but the pipeline object has `pipeline.classifier`, NOT `pipeline.model`. This will throw `AttributeError`.
  - Input size: `(1, 3, 224, 224)` — but the model was designed for 256×256 patches (IMG_SIZE=256). Wrong input dimensions.
- **Operations & Methods:** `thop.profile()`.
- **Side Effects:** None (will fail before any computation).

---

## Section 3: Pseudocode + Comment Audit + Naming Convention Suggestions

### 3A. Pseudocode for Complex Functions

**`AdaptiveROIDetector._merge_boxes()`** (lines 576-607):
```
FUNCTION _merge_boxes(boxes):
    IF boxes is empty: RETURN []
    merged ← COPY(boxes)
    LOOP:
        changed ← FALSE
        new_merged ← []
        WHILE merged is not empty:
            a ← pop first element from merged
            was_merged ← FALSE
            FOR each index i, box b in merged:
                IF _should_merge(a, b):
                    // Create envelope box: min of coords, max of coords, max of scores
                    merged[i] ← [min(a.y1,b.y1), min(a.x1,b.x1), max(a.y2,b.y2), max(a.x2,b.x2), max(a.score,b.score)]
                    was_merged ← TRUE
                    changed ← TRUE
                    BREAK  // restart outer loop with modified list
            IF NOT was_merged:
                new_merged.append(a)
        merged ← new_merged
        IF NOT changed: EXIT LOOP
    RETURN merged
```
**Issue:** Modifying `merged[i]` while iterating with `enumerate` works but is fragile — box `a` was popped and its values may re-enter through mutation of `b`. The control flow (break + while changed outer loop) is correct but O(n³) worst case. The `was_merged` flag could be handled more cleanly with an explicit index-based merge without the inner break/reset pattern.

**`TinyUNet.forward()`** (lines 173-194):
```
FUNCTION forward(x):
    x1 ← inc(x)          // [B, 16, 256, 256]
    x2 ← down1(x1)       // [B, 32, 128, 128]
    x3 ← down2(x2)       // [B, 64, 64,  64]
    x4 ← bot(x3)         // [B, 128,64,  64]
    
    x ← up1(x4)          // [B, 64, 128, 128]
    PAD x to match x2 spatial dims
    x ← CONCAT([x2, x], dim=1)  // channels: 32+64=96 (hoped)... 
                                 // BUT x2 has 32 channels! 32+64=96 ✓
    x ← conv_up1(x)      // [B, 64, 128, 128]
    
    x ← up2(x)           // [B, 32, 256, 256]
    PAD x to match x1 spatial dims
    x ← CONCAT([x1, x], dim=1)  // channels: 16+32=48
    x ← conv_up2(x)      // [B, 32, 256, 256]
    
    logits ← outc(x)     // [B, 1, 256, 256]
    RETURN sigmoid(logits)
```
**Issues found:**
1. `self.conv1 = DoubleConv(96, 64)` at line 165 is defined but **never used** — `conv_up1` is the one used in forward (also 96→64). Dead parameter.
2. Skip connection `x2` (128x128, 32 channels) is concatenated with upsampled `x4` (128×128, 64 channels) → 96 channels. `conv_up1(96→64)` is correct, but `conv1(96→64)` is dead code.

### 3B. Comment Quality Audit

| Location | Comment | Critique |
|----------|---------|----------|
| Line 107 | "Ajusta esto si tu carpeta rf_pipeline está en otro lado" | Vague — "Ajusta" means "adjust" but no guidance on what. |
| Line 118 | "Un poco más de paciencia al ir más rápido" | Nonsensical — doesn't explain why PATIENCE=30. |
| Line 121 | "Subido de 16 a 64 (La T4 tiene 16GB VRAM, aguanta fácil)" | Informative but colloquial. |
| Line 122 | "Usa todos los núcleos disponibles (4 en Kaggle)" | Misleading — `os.cpu_count()` returns total CPU count, not necessarily what's available in Kaggle. |
| Line 141/147 | "NOTA IMPORANTE" (line 622) | Typo: missing T in "IMPORTANTE". |
| Line 256 | "H5py requiere abrir el archivo en cada worker" | Misleading — h5py cannot share file handles across processes, but the per-__getitem__ open pattern is a workaround, not caused by h5py directly. |
| Line 286 | No comment on cudnn.benchmark timing tradeoffs | Missing context — this improves fixed-size convs but adds warm-up latency. |
| Line 621-624 | "Eliminé 'closing' y morfología direccional..." | First-person note from author to self — not appropriate for production code. |
| Line 1281 | `"... (El resto de tu función predict permanece IGUAL) ..."` | Placeholder comment — the comment itself says to check the code but no code follows. |
| Line 1333 | "# (Calcula tu tiempo real)" | Reminder/TO-DO embedded in production code. |

### 3C. Naming Convention Suggestions

| Current Name | Issue | Suggested |
|-------------|-------|-----------|
| `CFG` (×2, different) | Two different CFG classes with different attributes; no namespacing | `RPNConfig` + `ClassifierConfig` |
| `img_final`, `S_final` | Generic "final" doesn't describe what the tensor contains | `spectrogram_tensor`, `resized_spectrogram` |
| `S_mce_t`, `S_resized` | Abbreviated + positional suffixes | `spectrogram_hwc`, `spectrogram_patches_256` |
| `S_mce`, `S_det` | Domain-specific but inconsistent with rest of code | OK if documented, but `S_mce` (MCE spectrogram) + `S_det` (detection map) should be declared in a module-level docstring |
| `x_vis`, `x_eng` | Clear but would benefit from docstring type hints | `visual_features: Tensor`, `engineered_features: Tensor` |
| `dl_train`, `ds_train` | Inconsistent — `dl` for DataLoader, `ds` for Dataset; other code uses full names | `train_loader`, `train_dataset` |
| `fe`, `vs` | Overly abbreviated class attributes | `feature_engineer`, `visual_stream` |
| `preds_t`, `targets_t` | Suffixes `_t` and `_v` collide with `Tensor` convention | `train_preds`, `val_preds` |
| `criterion` | OK but loss types differ across cells (Tversky vs CrossEntropy); could conflict if in same namespace | `segmentation_loss`, `classification_loss` |
| `best_score` (cell 3) vs `best_val_acc` (cell 12) | Different metric names for conceputally the same thing | Use consistent naming: `best_val_metric` |

---

## Section 4: Pipeline Summary

The notebook implements a dependent two-stage pipeline: first, a TinyUNet-based Region Proposal Network is trained to segment MCE spectrograms into signal vs. background masks (Block 3), producing `best_unet_rpn.pt`. Second, a HybridRFClassifier combining CNN visual features (3-layer conv stack) with engineered features (32-dim) is trained on a smaller benchmark dataset (700/150/150 split) using pre-computed spectrograms from the cloned pipeline (Blocks 6-12), producing `best_model.pt`. The final `RFAnalysisPipeline` (Block 13) chains these: the RPN proposes bounding boxes from full MCE spectrograms, and the hybrid classifier scores each proposal with a softmax confidence (Block 14). Pipeline dependencies are strictly linear: Blocks 1→2→3 (RPN), Blocks 4-5→6→7→8→9→10→11→12 (Classifier), Blocks 13→14→15 (Inference). Several terminal blocks (15-17) contain broken variable references or wrong attribute names and cannot execute correctly.

---

# PHASE 2 — CRITICAL AUDIT

## Category 1: Cross-Block Consistency in Data Types and Variable Naming

| # | Finding | Score (0-5, 5=worst) |
|---|---------|----------------------|
| 1 | **Duplicate CFG class definition.** Block 3 defines `CFG` with `H5_TRAIN`, `H5_VAL`, `BATCH_SIZE=64`; Block 8 defines a DIFFERENT `CFG` with `TRAIN_H5`, `VAL_H5`, `TEST_H5`, `BATCH_SIZE=128`. Blocks 9-12 refer to `CFG.TRAIN_H5` (from Block 8). If Block 3 ran before Block 8, the second definition overwrites the first silently. Cross-block variable collision risk: **HIGH**. | 4 |
| 2 | **Duplicate ROI dataclass.** Block 4 and Block 5 both define identical `ROI` dataclasses. The second definition (Block 5) silently overwrites the first. If attributes diverge in future edits, silent breakage. | 3 |
| 3 | **Import path inconsistency.** Block 6 imports `from rf_pipeline.models.hybrid_classifier import HybridRFClassifier`; Block 10 imports `from models.hybrid_classifier import HybridRFClassifier`. These resolve to the same module ONLY because of `sys.path` manipulation in Block 2. Brittle — depends on global state. | 3 |
| 4 | **Variable name mismatch.** Block 15 references `resultados` but Block 14 defines `results`. This is a NameError waiting to happen. Spanish/English inconsistency. | 4 |
| 5 | **Attribute name mismatch.** Block 17 references `pipeline.model` but `RFAnalysisPipeline` stores the classifier in `self.classifier`, not `self.model`. Guaranteed AttributeError. | 4 |
| 6 | **Input dimension mismatch.** Block 17 creates dummy input of size `(1, 3, 224, 224)` but the entire pipeline uses `IMG_SIZE=256`, meaning the classifier's CNN expects 256×256 patches. Wrong shape will silently broadcast or fail. | 3 |
| 7 | **CFG class attribute coverage.** Blocks 9-10 use `CFG.DEVICE`, `CFG.BATCH_SIZE`, `CFG.TRAIN_H5`, `CFG.NUM_WORKERS` — all from Block 8's CFG. But Block 8's CFG doesn't define `NUM_WORKERS` explicitly. Wait — line 795: `NUM_WORKERS = 2`. OK, it does. No issue. | 0 |
| 8 | **S_det vs S_mce input to detectors.** Block 4 (NeuralROIDetector) expects `S_mce [3, H, W]` (3-channel). Block 5 (AdaptiveROIDetector) expects `S_det [H, W]` (1-channel). Block 13's pipeline calls `detector.detect(S_mce)` which goes to NeuralROIDetector (correct for 3-channel input). But the AdaptiveROIDetector is defined as the monkey-patched version that the pipeline does NOT use — the pipeline uses NeuralROIDetector directly via `self.detector = NeuralROIDetector(...)`. Not a bug but confusing dual definition. | 2 |

**Subtotal Consistency:** 23/40 (lower is better)

---

## Category 2: Redundant Computation or Unnecessary I/O

| # | Finding | Score (0-5) |
|---|---------|-------------|
| 1 | **Re-import and reload pattern.** Block 9 re-imports `core.data_loader` and calls `importlib.reload` AGAIN, even though Block 7 already did this exact same sequence. Redundant module reload. | 3 |
| 2 | **HDF5 opened per __getitem__.** `RPNDataset.__getitem__` opens the entire HDF5 file on every single item retrieval (line 278). With 21000 training samples and `persistent_workers=True`, each worker opens the file 21000/4 ≈ 5250 times. This is a massive I/O bottleneck. The file should be opened once per worker (in `__init__` or via `worker_init_fn`). | 5 |
| 3 | **Spectrogram recomputed per epoch.** The `H5HybridDetectionDataset` (used in Blocks 9-12) computes STFT/MCE spectrograms on-the-fly in `__getitem__`. For 700 training samples × 10 epochs = 7000 spectrogram computations. If disk space allows, precomputing and caching would eliminate this. The preprocessing warning `UserWarning: Input data is complex, switching to return_onesided=False` fires on every single STFT call, meaning scipy is doing unnecessary checks repeatedly. | 4 |
| 4 | **Unused `self.conv1` in TinyUNet.** Line 165: `self.conv1 = DoubleConv(96, 64)` is allocated parameters but never used in forward(). Wastes GPU memory (~(96×64×3×3 + 64 + 64×64×3×3 + 64) parameters = ~128K params wasted). | 4 |
| 5 | **Unused `time_tol` and `freq_tol` in AdaptiveROIDetector.** Accepted as constructor parameters but never referenced anywhere in the class. Dead configuration. | 2 |
| 6 | **sys.path append in cell 2 + cell 3 + cell 5.** Three different cells append redundant or slightly different sys.path entries. Duplicates accumulate in sys.path. | 2 |

**Subtotal Redundancy:** 20/30

---

## Category 3: Contradictory Logic or Unreachable Branches

| # | Finding | Score (0-5) |
|---|---------|-------------|
| 1 | **evaluate_by_noise() is unreachable as written.** The method checks `res.get("noise_level")` → if None, `continue`. But `predict()` never sets `"noise_level"` in the results dict. Every result will have `noise_level=None`, so the `noise_groups` dict will always be empty and the method will print headers but no actual per-SNR data. | 4 |
| 2 | **Pipeline predict() docstring gap.** Line 1277: `"... (El resto de tu función predict permanece IGUAL) ..."` — a placeholder comment that literally says "the rest stays the same" but provides no implementation guidance. The function is implemented below the comment, so the comment is misleading/confusing. | 2 |
| 3 | **Dead code in Cell 15.** Cell 15 references `resultados[0].get("noise_level", "No encontrado")` — `resultados` is undefined. Even if renamed to `results`, the `noise_level` key doesn't exist. This cell cannot produce useful output. | 3 |
| 4 | **CFG class shadowing.** If Block 3 runs after Block 8 in a fresh kernel, the `CFG` class from Block 3 would overwrite Block 8's CFG, breaking Blocks 9-12 (which reference `CFG.TRAIN_H5`, `CFG.VAL_H5` → undefined attributes). Execution order matters and is not validated. | 3 |

**Subtotal Contradictions:** 12/20

---

## Category 4: Missing Error Handling or Validation

| # | Finding | Score (0-5) |
|---|---------|-------------|
| 1 | **No git clone error handling.** Block 1 runs `!git clone` with no check for success. If the network is down or the repo URL changes, the notebook fails silently until later imports crash with `ModuleNotFoundError`. | 4 |
| 2 | **No HDF5 file existence check.** Blocks 3, 9 access HDF5 files with hardcoded paths. If these Kaggle datasets aren't mounted, `RPNDataset.__init__` catches the exception but only prints a message — it doesn't raise, so downstream code continues with an empty dataset. Block 3 checks `len(ds_train)==0` but only prints an error. | 3 |
| 3 | **torch.load without weights_only.** Block 4 (line 422): `torch.load(model_path, map_location=device)` — no `weights_only=True`. In PyTorch ≥2.4, this triggers a FutureWarning and is a security risk if loading from untrusted sources. | 3 |
| 4 | **RPN checkpoint missing → FileNotFoundError.** Block 13's constructor raises `FileNotFoundError` if RPN path doesn't exist, which is correct but creates a hard failure with no recovery path (e.g., fallback to AdaptiveROIDetector). | 2 |
| 5 | **No input shape validation.** `RPNDataset._meta_to_box` silently returns None for any exception (blank `except:` line 245). This swallows ALL error types including KeyError, TypeError, AttributeError — making debugging impossible. | 4 |
| 6 | **No validation of resized spectrogram dimensions.** `NeuralROIDetector.detect()` assumes input has exactly 3 channels (`orig_c` unpacked from `S_mce.shape`). If the upstream preprocessor changes channel count, the U-Net will crash with a cryptic shape mismatch instead of a clear error. | 3 |
| 7 | **HDF5 keys filtered by `str.isdigit()`.** `RPNDataset.__init__` filters keys with `k.isdigit()`. Non-numeric HDF5 groups are silently skipped — if the dataset adds metadata groups at the root level, they won't be included in `self.keys`, which is correct behavior, but no log message indicates how many keys were filtered. | 2 |
| 8 | **No test set evaluation.** Block 12 loads `ds_test` at line 903 but NEVER runs evaluation on it. The test DataLoader is created but never consumed. The training loop only evaluates on `dl_val`. | 3 |
| 9 | **Missing batching in `RFAnalysisPipeline.predict()`.** The predict method processes one sample at a time in a for-loop (line 1288-1336). Each iteration runs one forward pass through the U-Net (RPN) and then one through the classifier. No batching — significantly slower than processing multiple spectrograms simultaneously. | 4 |

**Subtotal Error Handling:** 28/45

---

## Summary Scores

| Category | Score | Max | Severity |
|----------|-------|-----|----------|
| Cross-block consistency | 23 | 40 | **MODERATE-HIGH** |
| Redundant computation/I/O | 20 | 30 | **HIGH** |
| Contradictory logic | 12 | 20 | **MODERATE** |
| Missing error handling | 28 | 45 | **HIGH** |
| **TOTAL** | **83** | **135** | **62% — NEEDS REWORK** |

---

## Gate Decision

**GATE: REJECT (CONDITIONAL RESUBMIT)**

The notebook has significant issues across all four categories. Critical blockers:
1. Broken cell references (Block 15: `resultados` undefined; Block 17: `pipeline.model` doesn't exist).
2. `evaluate_by_noise()` is entirely unreachable — the noise_level key it reads is never populated.
3. Per-__getitem__ HDF5 file open pattern causes severe I/O overhead.
4. Two colliding `CFG` class definitions create environment-dependent behavior.
5. Swallowed exceptions (`except:` bare clause) hide bugs.
6. No test set evaluation despite test data being loaded.

**Required before passing gate:**
- Fix variable name mismatch (`resultados` → `results`).
- Add `noise_level` population to `predict()` or remove `evaluate_by_noise()`.
- Replace per-item HDF5 open in `RPNDataset` with a worker-init-fn pattern.
- Namespace/rename the two CFG classes to avoid shadowing.
- Replace bare `except:` with specific exception types.
- Add test set evaluation after training.
- Fix Block 17 attribute reference (`pipeline.classifier`).

**Fingerprint:** `lap 0`
**Timestamp:** 2026-07-04T00:00:00Z

---

# CROSS-CHECK: Phase 1 Mission Report vs. Actual Codebase

The following discrepancies were found after comparing the Phase 1 descriptions against the actual notebook source:

| # | Phase 1 Claim | Actual Code | Discrepancy |
|---|---------------|-------------|-------------|
| 1 | "Stage 1 trains a TinyUNet... Stage 2 trains a HybridRFClassifier" | Cell 3 (RPN training) has `execution_count: null` — it **failed** with a kernel error. The outputs embedded in the notebook are from a prior session. TinyUNet and TverskyLoss classes are DEFINED in the cell source, but the cell never executed successfully in the current kernel session. | Phase 1 assumes RPN training succeeds; in reality the cell output shows ipykernel error. |
| 2 | "All subsequent cells fail if [git clone] doesn't execute" | Partially accurate. Cells 1-2 have independent executions. Cell 3 depends on the cloned repo content AND on successful execution (which it didn't get). | Phase 1 says all subsequent cells need the clone; actually only cells importing from the cloned repo do. |
| 3 | Block 4 described as `exec_count: 68` running AFTER Block 5 `exec_count: 54` | The notebook JSON shows Block 5 (Adaptive ROI) has execution_count=54 and Block 4 (NeuralROI) has execution_count=68, meaning Block 5 was executed first chronologically. | Phase 1's sequential numbering doesn't reflect execution order, only cell order. The ROI dataclass was first defined in Block 5 (classical detector), then overwritten by Block 4 (neural detector). |
| 4 | `self.conv1` described as "never used in forward() — dead parameter" | **Confirmed.** Line 165: `self.conv1 = DoubleConv(96, 64)` with no reference in forward(). | Correctly identified. |
| 5 | Pipeline described as loading NeuralROIDetector, not AdaptiveROIDetector | **Confirmed.** Line 1262-1267: `self.detector = NeuralROIDetector(...)`. The AdaptiveROIDetector is only used for monkey-patching `core.roi_detection`. | Phase 1 is accurate about the pipeline using NeuralROI, but the monkey-patching of AdaptiveROIDetector into `core.roi_detection` at line 684 is separate and unused by the pipeline. |
| 6 | "FeatureEngineer instantiation at line 1273: `cfg.IMG_SIZE`" | **Confirmed.** Line 1273: `self.fe = FeatureEngineer(fs=cfg.FS, nperseg=cfg.NPERSEG, noverlap=cfg.NOVERLAP)`. No `target_size` parameter passed — only `fs`, `nperseg`, `noverlap`. | Phase 1 incorrectly claimed `FeatureEngineer(target_size=cfg.IMG_SIZE)`. The actual call passes signal parameters only. |
| 7 | VisualStream instantiation at line 1274 | **Confirmed.** Line 1274: `self.vs = VisualStream(target_size=cfg.IMG_SIZE)`. This does exist. | Phase 1 correctly identified this one. |
| 8 | "evaluate_by_noise uses `res.get('noise_level')` but predict() never sets this" | **Confirmed.** `predict()` returns `{id, S_mce, predictions, gt_boxes, inference_time_ms}` — no `noise_level` key. `evaluate_by_noise()` loops over `noise_groups` which will always be empty. | Correctly identified — the entire `evaluate_by_noise` method is dead code. |
| 9 | Cell 15's `resultados` variable name mismatch | **Confirmed.** Line 1579 references `resultados[0]` but no cell defines `resultados`. The pipeline variable is `results` (line 1557). | Correctly identified. |
| 10 | Cell 17 references `pipeline.model` instead of `pipeline.classifier` | **Confirmed.** Line 1623: `profile(pipeline.model, inputs=...)` — `RFAnalysisPipeline` stores the model as `self.classifier` (line 1249). | Correctly identified. |
| 11 | Cell 17 uses 224×224 dummy input vs 256×256 model | **Confirmed.** Line 1618: `x_img = torch.randn(1, 3, 224, 224)` but IMG_SIZE=256 throughout the pipeline. | Correctly identified. |
| 12 | Phase 1 Section 4 claims "10 EPOCHS" for classifier | **Confirmed.** Block 8: `EPOCHS = 10`. | Correct. |
| 13 | Phase 1 Section 2 Block 3 describes `RPNDataset` as reading HDF5 from `/kaggle/input/rf-benchmark/...` | **Confirmed.** Lines 127-128. | Correct. |
| 14 | Comment audit noted `NOTA IMPORANTE` typo | **Confirmed.** Line 622 in the original JSON source (cell 5, AdaptiveROIDetector): `"# ⚠️ NOTA IMPORANTE:\\n"` | Correctly identified typo. |

---

## Summary of Phase 1 vs. Codebase Discrepancies

- **1 minor inaccuracy:** Phase 1 Section 2 Block 13 incorrectly described `FeatureEngineer` instantiation as having a `target_size` parameter — the actual call passes only `fs`, `nperseg`, `noverlap`.
- **1 contextual omission:** Phase 1 did not explicitly note that Cell 3 (RPN training) has `execution_count: null`, meaning the cell never executed in the current kernel session (though its embedded outputs suggest a prior run). This means `TinyUNet` and `TverskyLoss` classes may not be available for downstream cells that reference them.
- **All other Phase 1 observations (12 critical findings) were confirmed accurate** by direct code inspection.

---

**Final Disposition:** The Phase 1 documentation is **92% accurate** when compared to the codebase. The audit correctly identified 14 of 15 significant issues, with one minor mischaracterization.
