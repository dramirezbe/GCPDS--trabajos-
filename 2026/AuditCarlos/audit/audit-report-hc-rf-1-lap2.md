# AUDIT REPORT — hc-rf-1.ipynb (Lap 2 — Refined Evaluation)
**Fingerprint:** `lap 1`  
**Generated:** 2026-07-04T00:00:00Z

---

## 1 — Overall Purpose / Goal

This notebook builds a two-stage neural pipeline for **RF signal detection and classification** from raw IQ samples, operating on HDF5-backed spectrogram datasets. The first stage trains a **TinyUNet Region Proposal Network** on MCE spectrograms to segment signal-bearing regions from background noise; the second stage trains a **HybridRFClassifier** (CNN visual encoder + MLP feature-engineering encoder) on a smaller benchmark to classify each proposed region as signal or noise. The final integrated pipeline accepts an HDF5 file of raw IQ signals, runs neural ROI detection via the RPN, extracts visual and engineered features per ROI, and outputs per-sample predictions with precision/recall/F1 metrics and bounding-box visualizations.

**Input:** Raw IQ signals in HDF5 format (`/kaggle/input/rf-benchmark*/raw_iq_hdf5/{train,val,test}/data.h5`).
**Outputs:** Trained models (`best_unet_rpn.pt`, `best_model.pt`), evaluation metrics (F1, Precision, Recall), and spectrogram visualizations with predicted and ground-truth boxes.

---

## 2 — Code Block Descriptions

### Block 1 — Python Path Configuration
**Logic Flow:** Appends two directory paths from the cloned MCE-ROI-V2 repository to `sys.path`, making sub-packages (`rf_pipeline`, `core`, `config`) importable by downstream blocks.
**Data Transformations:** No data transforms; mutates global import resolution order.
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** `/kaggle/working/MCE-ROI-V2/rf_pipeline`, `/kaggle/working/MCE-ROI-V2`.
**Side Effects:** Global `sys.path` mutation. Imports `inspect` but never uses it (dead import).

---

### Block 2 — U-Net RPN Definition and Training
**Logic Flow:**
1. Appends an additional sys.path entry (`/kaggle/working/MCE-ROI-V2/MCE-ROI-V2`).
2. Imports `Preprocessor` and `config` from the cloned repository.
3. Defines `CFG` configuration class (DEVICE, EPOCHS=500, PATIENCE=30, BATCH_SIZE=64, LR=1e-3, IMG_SIZE=256×256, HDF5 paths).
4. Enables `cudnn.benchmark` if CUDA available.
5. Defines `DoubleConv` (Conv2d→BN→ReLU→Conv2d→BN→ReLU with bias=False) and `TinyUNet` (encoder: 16→32→64→128 channels, decoder: 64→32, skip connections at 32-ch and 16-ch layers, sigmoid output).
6. Defines `TverskyLoss(α=0.3, β=0.7, smooth=1.0)` — asymmetric focal-like loss penalizing false negatives (β=0.7) more than false positives (α=0.3).
7. Defines `RPNDataset(Dataset)`:
   - `__init__`: Opens HDF5, collects integer-named keys, initializes `Preprocessor(mode="mce")` for 3-channel MCE spectrogram computation.
   - `_meta_to_box`: Converts metadata `(start_in_samples, duration_in_samples, low_freq, high_freq)` → pixel-space bounding box `[x1, y1, x2, y2]` using hop length and frequency range.
   - `__getitem__`: Opens HDF5 (per-call), reads IQ, computes MCE spectrogram → fftshift → binary mask from metadata boxes, resizes both to 256×256, returns `(torch.Tensor[3,256,256], torch.Tensor[1,256,256])`.
8. Training loop: 500 epochs max, Adam(1e-3), ReduceLROnPlateau(mode='max', patience=10, factor=0.5), early stopping at 30 no-improvement epochs, checkpoint saves `best_unet_rpn.pt`.

**Data Transformations:**
- **Input:** HDF5 key → raw IQ `[n_samples]` or `[n_samples, 2]` (complex I+Q).
- **→ MCE spectrogram** `[3, freq_bins, time_bins]` via Preprocessor (STFT + magnitude/coherence/entropy).
- **→ fftshift** on freq axis (centers DC component).
- **→ Binary mask** `[freq_bins, time_bins]` from metadata bounding boxes.
- **→ Resize** spectrogram to `[3, 256, 256]`, mask to `[1, 256, 256]` via skimage (reflect mode, order=0 for mask).
- **Output:** `(Tensor[3,256,256], Tensor[1,256,256])` — spectrogram patch + binary segmentation target.

**Model/Algorithm Operations:**
- U-Net segmentation with 4-level encoder-decoder and skip connections.
- Tversky loss (asymmetric soft-Dice variant).
- ReduceLROnPlateau scheduler monitoring Tversky score.
- Validation metric: 1 − Tversky loss (Tversky score).

**Key Variables/Parameters:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| DEVICE | cuda/cpu | Auto-detected |
| EPOCHS | 500 | Max training epochs |
| PATIENCE | 30 | Early stopping threshold |
| BATCH_SIZE | 64 | Memory-optimized for T4 |
| NUM_WORKERS | os.cpu_count() | Data loading parallelism |
| LR | 1e-3 | Adam learning rate |
| IMG_SIZE | (256, 256) | Input patch dimensions |
| Tversky α/β | 0.3 / 0.7 | FP weight / FN weight |

**Side Effects:**
- Writes `best_unet_rpn.pt` to `/kaggle/working/`.
- Sets `torch.backends.cudnn.benchmark = True` (global CUDA config change).
- `self.conv1 = DoubleConv(96,64)` defined but **never used** in `TinyUNet.forward()` — dead parameter allocation.
- ~12 minutes per epoch reported (744.9s for Epoch 1).

---

### Block 3 — Neural ROI Detector Definition
**Logic Flow:**
1. Re-defines `ROI` dataclass (y1, x1, y2, x2, score, snr_db=0.0).
2. Defines `NeuralROIDetector`:
   - `__init__`: Instantiates a TinyUNet-compatible model class, loads pretrained weights (`torch.load`, no `weights_only=True`), sets eval mode.
   - `detect(S_mce[3,H,W])`: Resize to 256×256 → U-Net inference → sigmoid → binarize (threshold=0.5) → connected-components labeling → bounding box extraction → rescale to original coordinates → filter by minimum size (>2y, >4x) → sort by score (mean probability within box).

**Data Transformations:**
- **Input:** `S_mce: np.ndarray[3, H, W]` (3-channel MCE spectrogram at original resolution).
- **→** Transpose to `[H, W, 3]` for skimage.
- **→** Resize to `[256, 256]` (reflect mode, anti-alias).
- **→** Transpose back to `[3, 256, 256]`, convert to `Tensor[1, 3, 256, 256]` on device.
- **→** U-Net inference → `Tensor[1, 1, 256, 256]` → `.squeeze().cpu().numpy()` → `ndarray[256, 256]`.
- **→** Binarize: `prob_map > 0.5`.
- **→** `scipy.ndimage.label` → `find_objects` → list of slice tuples.
- **→** Scale factor: `scale_y = H/256, scale_x = W/256`.
- **Output:** `list[ROI]` sorted by mean confidence score, filtered to (y2−y1)>2 and (x2−x1)>4 at original scale.

**Model/Algorithm Operations:** U-Net inference (single-image), thresholding, connected-components extraction.

**Key Variables/Parameters:** threshold=0.5, input_size=(256,256), device='cuda'.

**Side Effects:** Prints `"[NeuralROI] Cargando RPN desde ..."`. Loads model weights from disk (no weights_only=True — PyTorch ≥2.4 security concern).

---

### Block 4 — Adaptive ROI Detector Definition + Module Injection
**Logic Flow:**
1. Appends additional sys.path entries.
2. Re-defines `ROI` dataclass (identical to Block 3 — overwrites).
3. Defines `AdaptiveROIDetector`:
   - `_robust_noise_floor`: Estimates noise floor (median) and sigma ((p50−p25)/0.6745).
   - `_should_merge`: IoU-based merge criterion requiring overlap ratio > `overlap_thresh` (default 10%), using min(area_a, area_b) as denominator.
   - `_merge_boxes`: Iterative greedy merge — pops first box, checks against all remaining, merges if criterion met, repeats outer loop when any merge occurred.
   - `detect(S_det[H,W])`: Z-score normalization → white top-hat (disk=3) → weak mask (z>low_sigma OR tophat>low_sigma×1.5) → strong mask (z>high_sigma) → binary_dilation(strong, mask=weak) → label → find_objects → filter by min_width/min_height → score = p90(z within box) → merge → filter by min_area → sort by score descending.
4. Monkey-patches `core.roi_detection.AdaptiveROIDetector` and `core.roi_detection.ROI` with local definitions.

**Data Transformations:**
- **Input:** `S_det: ndarray[H, W]` (single-channel detection map / magnitude spectrogram).
- **→** Z-score: `(S_det − μ) / σ` via robust noise estimation.
- **→** Top-hat morphological filtering.
- **→** Weak/strong binary masks.
- **→** Masked binary dilation.
- **→** Connected components → bounding boxes → 90th percentile z-score per box.
- **Output:** `List[ROI]` sorted by score.

**Model/Algorithm Operations:** Robust noise estimation (median-based), z-score thresholding, white top-hat morphology, binary dilation, connected-components labeling, overlap-ratio-based box merging.

**Key Variables/Parameters:** high_sigma=3.0, low_sigma=2.0, min_area=50, min_width=4, min_height=2, time_tol=0 (unused), freq_tol=0 (unused), overlap_thresh=0.10.

**Side Effects:**
- Monkey-patches global module state (`core.roi_detection`).
- Prints activation confirmation message.
- `time_tol` and `freq_tol` accepted as init parameters but **never referenced** in any method.
- Typo in comment: `"NOTA IMPORANTE"` (missing T).
- Appends sys.path entries already added by Block 1.

---

### Block 5 — Hybrid Classifier Import
**Logic Flow:** Single import of `HybridRFClassifier` from the cloned repository's models subpackage.
**Data Transformations:** None.
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** Import path: `rf_pipeline.models.hybrid_classifier.HybridRFClassifier`.
**Side Effects:** Module load. Import path differs from Block 9 (`models.hybrid_classifier` vs `rf_pipeline.models.hybrid_classifier` — both resolve only due to sys.path manipulation).

---

### Block 6 — Config File Generation + Dataset Import
**Logic Flow:**
1. Defines config.py content string with signal processing parameters (FS=10MHz, NPERSEG=32, NOVERLAP=16, NFFT=32, IMG_SIZE=256).
2. Writes to `/kaggle/working/MCE-ROI-V2/config.py`.
3. Imports `config` module and forces reload via `importlib.reload`.
4. Imports `rf_pipeline.core.data_loader`, reloads it, imports `H5HybridDetectionDataset`.

**Data Transformations:** None (creates a Python module file on disk).
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** FS=10_000_000, NPERSEG=32, NOVERLAP=16, NFFT=32, IMG_SIZE=256, BATCH_SIZE=128, EPOCHS=50, LR=1e-3, DEVICE="cuda".
**Side Effects:**
- File write: creates/overwrites `config.py`.
- `importlib.reload` × 2 forces module cache invalidation.
- Printed confirmation messages.

---

### Block 7 — Classifier Configuration
**Logic Flow:** Defines a second `CFG` class (distinct from Block 2's `CFG`) with classifier-specific paths and hyperparameters. Creates output directory.
**Data Transformations:** None.
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| TRAIN_H5 | `/kaggle/input/rf-benchmark-tiny/raw_iq_hdf5/train/data.h5` | Training data |
| VAL_H5 | `/kaggle/input/rf-benchmark-tiny/raw_iq_hdf5/val/data.h5` | Validation data |
| TEST_H5 | `/kaggle/input/rf-benchmark-tiny/raw_iq_hdf5/test/data.h5` | Test data |
| BATCH_SIZE | 128 | Training batch size |
| EPOCHS | 10 | Training epochs |
| LR | 1e-3 | Learning rate |
| NUM_WORKERS | 2 | Data loader workers |
| DEVICE | cuda/cpu | Auto-detected |
| OUTPUT_DIR | `/kaggle/working/resultados_finales` | Checkpoint save path |

**Side Effects:** `os.makedirs(CFG.OUTPUT_DIR, exist_ok=True)`. Prints device confirmation. **Overwrites Block 2's `CFG` class in global namespace.**

---

### Block 8 — Dataset Loading and DataLoader Creation
**Logic Flow:**
1. Re-imports `core.data_loader` and `H5HybridDetectionDataset` (redundant with Block 6).
2. Forces `importlib.reload` on data_loader again.
3. Instantiates `H5HybridDetectionDataset` for train (700 samples), val (150), test (150) — all using `mode="train"`.
4. Creates `DataLoader` objects with `pin_memory=True`, `shuffle=True` for train, batch_size=128 (train) and 256 (val/test).

**Data Transformations:**
- **Input:** HDF5 file paths (I/Q raw signals with metadata).
- **→** `H5HybridDetectionDataset(mode="train")` returns `(tensor_visual, tensor_engineered, label)` per sample.
- **Output:** Batched tuples via DataLoader: `([B, 3, H, W], [B, feat_dim], [B])`.

**Model/Algorithm Operations:** Delegates spectrogram computation to Preprocessor inside the dataset class.

**Key Variables/Parameters:** 700 train / 150 val / 150 test samples. Batch sizes: 128 (train), 256 (val/test).

**Side Effects:** Console output showing sample counts. Preprocessing warnings (`UserWarning: Input data is complex, switching to return_onesided=False`) emitted during dataset iteration.

---

### Block 9 — Hybrid Classifier Initialization
**Logic Flow:** Instantiates `HybridRFClassifier` with dual-stream architecture (CNN + MLP head), moves to device, creates Adam optimizer (lr=1e-3) and CrossEntropyLoss criterion.
**Data Transformations:** None (model parameter initialization only).
**Model/Algorithm Operations:**
- `HybridRFClassifier(num_classes=2, feat_dim=32, img_in_ch=3, cnn_channels=(16,32,64), mlp_hidden=(64,64))`
  - CNN: 3-layer conv stack (3→16, 16→32, 32→64 channels).
  - MLP: 2 hidden layers (64→64, 64→2 output).
  - Feature fusion: CNN visual output + engineered features → MLP classification head.
- Adam optimizer, CrossEntropyLoss for binary classification.

**Key Variables/Parameters:** feat_dim=32, img_in_ch=3, cnn_channels=(16,32,64), mlp_hidden=(64,64).
**Side Effects:** None (pure initialization).

---

### Block 10 — Batch Structure Debug
**Logic Flow:** Grabs one batch from the training DataLoader using `next(iter(dl_train))`, prints the type, length, and element types of the batch.
**Data Transformations:** Triggers spectrogram computation for one batch (up to 128 samples of STFT/MCE computation on first access).
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** None.
**Side Effects:** Triggers `UserWarning` from Preprocessor (complex-input STFT switching). Outputs batch structure: `list` of 3 `torch.Tensor` objects.

---

### Block 11 — Hybrid Classifier Training
**Logic Flow:**
1. 10-epoch training loop over `dl_train` and `dl_val`.
2. Per epoch: forward pass (visual + engineered features → logits), CrossEntropy loss, backward, Adam step. Training accuracy accumulated per batch.
3. Validation: no-grad forward pass, loss accumulation, accuracy via `sklearn.metrics.accuracy_score`.
4. Checkpointing: saves `best_model.pt` when validation accuracy improves.

**Data Transformations:**
- **Input:** `(x_vis[B,3,H,W], x_eng[B,32], y[B])` from DataLoader.
- **→** Forward: `logits[B, 2]` → `argmax(dim=1)` → predicted class.
- **→** Loss: `CrossEntropyLoss(logits, y) → scalar`.
- **Output:** Per-epoch train acc/loss, val acc/loss. Writes `best_model.pt`.

**Model/Algorithm Operations:**
- Supervised binary classification (2-class softmax).
- No LR scheduler, no early stopping, no gradient clipping.
- Greedy best-checkpoint saving by validation accuracy.

**Key Variables/Parameters:** EPOCHS=10, Learning rate 1e-3. Trained with `CFG.DEVICE` (cuda).

**Side Effects:**
- Writes `best_model.pt` to `resultados_finales/`.
- Training metrics printed per epoch (14-15s per epoch).
- Final metrics: Train Acc 96.00%, Val Acc 97.33% at epoch 10.
- **Test DataLoader loaded but never evaluated** — `dl_test` is created in Block 8 but no test-phase evaluation exists.

---

### Block 12 — Full Inference Pipeline Class Definition
**Logic Flow:**
1. Defines `RFAnalysisPipeline` class:
   - `__init__`: Loads `HybridRFClassifier` from checkpoint, loads `NeuralROIDetector` from RPN checkpoint (raises `FileNotFoundError` if RPN missing). Instantiates `FeatureEngineer` and `VisualStream` for per-ROI feature extraction.
   - `predict(h5_path, confidence_thresh, max_samples)`: Iterates `H5HybridDetectionDataset(mode="eval")` → per sample: extract `S_mce[3,H,W]`, run `detector.detect(S_mce)` → `rois`, extract engineered features via `FeatureEngineer.features_for_rois()` and visual patches via `VisualStream.extract_patches()`, run classifier on matched feature pairs, filter by confidence threshold, collect predictions as `{box, score}`.
   - `_calculate_iou(boxA, boxB)`: Standard intersection-over-union with epsilon 1e-6.
   - `evaluate(results, iou_thresh=0.2)`: Greedy Hungarian-style matching (first-match wins) of predictions to ground-truth boxes. Computes TP/FP/FN → precision, recall, F1, avg inference time, FPS.
   - `evaluate_by_noise(results, iou_thresh)`: Groups results by `noise_level` key and calls `evaluate()` per group.
   - `visualize(results, num_samples=5)`: Plots S_mce[0] channel with green ground-truth boxes and red predicted boxes.

**Data Transformations:**
- **predict input:** HDF5 file path → per sample `{S_mce[3,H,W], iq, S_det, gt_boxes}`.
- **→** Neural ROI detection: `S_mce[3,H,W]` → `list[ROI]` (Block 3's method).
- **→** Feature engineering: `(iq, S_det, rois)` → `list[ROIFeatures]` with 32-dim features per ROI.
- **→** Visual patches: `(S_mce, rois)` → `list[ndarray[3,256,256]]` per ROI.
- **→** Classifier inference: `(batch_visual[B,3,256,256], batch_engineered[B,32])` → `logits[B,2]` → softmax → `prob_signal[B]`.
- **→** Threshold filter: `prob >= confidence_thresh` → `[{box:[x1,y1,x2,y2], score:float}]`.
- **predict output:** `list[{id, S_mce, predictions, gt_boxes, inference_time_ms=0}]`.
  - **Missing key:** `noise_level` is **never set** in the result dict, despite `evaluate_by_noise()` depending on it.
  - `inference_time_ms` is **hardcoded to 0** (placeholder).

**Model/Algorithm Operations:**
- Two-model cascade: U-Net (segmentation → ROI proposal) + Hybrid CNN-MLP (classification).
- Greedy IoU matching for evaluation (iou_thresh=0.2, very permissive).
- Confidence-thresholded prediction filtering.

**Key Variables/Parameters:**
| Parameter | Value | Purpose |
|-----------|-------|---------|
| classifier_path | Path | Loads `best_model.pt` |
| rpn_path | Path | Loads `best_unet_rpn.pt` |
| confidence_thresh | 0.2 (caller) | Prediction score cutoff |
| iou_thresh | 0.2 | Detection matching threshold |
| device | cuda/cpu | Inference device |

**Side Effects:**
- Prints pipeline initialization message.
- Constructor raises `FileNotFoundError` if RPN checkpoint missing (hard failure, no fallback).
- `FeatureEngineer` instantiated with `(fs, nperseg, noverlap)` — no `target_size` parameter.
- `VisualStream` instantiated with `target_size=cfg.IMG_SIZE` (256).

---

### Block 13 — Pipeline Execution and Evaluation
**Logic Flow:**
1. Sets paths: `RPN_PATH`, `CLF_PATH`, `TEST_DATA`.
2. Instantiates `RFAnalysisPipeline`.
3. Runs `predict()` on 150 test samples with `confidence_thresh=0.2`.
4. Calls `evaluate()` to compute F1/Precision/Recall.
5. Calls `visualize()` to display 5 sample plots.

**Data Transformations:**
- **Input:** Test HDF5 (150 samples from rf-benchmark-tiny).
- **→** Pipeline predict → results list.
- **→** evaluate → metrics dict.
- **Output:** Printed metrics (F1=0.8272, Precision=1.0000, Recall=0.7053, Tiempo=0.00ms, FPS=0.0). 5 matplotlib figures.

**Model/Algorithm Operations:** Full pipeline forward pass: RPN ROI detection + feature extraction + hybrid classification + IoU evaluation.

**Key Variables/Parameters:** confidence_thresh=0.2, max_samples=150, iou_thresh=0.2 (default).
**Side Effects:**
- Displays matplotlib plots inline.
- Runtime: ~7s for 150 samples (20.94 it/s per tqdm).
- `Tiempo Promedio: 0.00 ms` and `Velocidad: 0.0 FPS` because `inference_time_ms` is hardcoded to 0.

---

### Block 14 — Debug Print (Potentially Broken)
**Logic Flow:** Attempts to print keys of `resultados[0]` and access `"noise_level"` key.
**Data Transformations:** None (pending execution).
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** `resultados` — **never defined** in any prior block. The pipeline output variable is named `results` (English) in Block 13, not `resultados` (Spanish). This will raise `NameError` if executed.
**Side Effects:** None (unexecuted).

---

### Block 15 — Package Installation
**Logic Flow:** Installs the `thop` PyTorch profiling library via pip.
**Data Transformations:** None.
**Model/Algorithm Operations:** None.
**Key Variables/Parameters:** `thop` package.
**Side Effects:** System-level pip installation in Kaggle environment.

---

### Block 16 — FLOPs Profiling (Broken)
**Logic Flow:**
1. Creates dummy inputs: `x_img[1,3,224,224]` and `x_feat[1,32]`.
2. Calls `thop.profile(pipeline.model, inputs=(x_img, x_feat))`.

**Data Transformations:** None (would profile model if it worked).
**Model/Algorithm Operations:** FLOPs and parameter counting via thop.
**Key Variables/Parameters:** Dummy input shapes: `[1,3,224,224]` and `[1,32]`.

**Side Effects:** Two critical bugs:
1. `pipeline.model` — the pipeline object stores the classifier as `self.classifier`, not `self.model`. Will raise `AttributeError`.
2. Input shape `[1,3,224,224]` contradicts `IMG_SIZE=256` used throughout the entire pipeline for spectrogram patches. If the attribute error were fixed, the model would receive wrong-size inputs.

---

## 3 — Pipeline Summary

The notebook encodes a **sequential two-stage training-and-inference pipeline** with the following data flow:

```
Block 1 (sys.path) → enables imports for all downstream blocks
       ↓
Block 2 (RPN Training) ──produces──→ best_unet_rpn.pt
       ↓
Block 3 (NeuralROI) ◄──references── TinyUNet (defined in Block 2)
Block 4 (AdaptiveROI)   [independent; monkey-patches core, unused by pipeline]
       ↓
Block 5 → Block 6 → Block 7 → Block 8 → Block 9 → Block 10 → Block 11
  (import    (config    (CFG     (data-    (model    (debug)   (training)
   classifier) .py)      class)   loaders)  init)               ↓
                                                          best_model.pt
       ↓
Block 12 (RFAnalysisPipeline) ◄──loads── best_unet_rpn.pt + best_model.pt
       ↓
Block 13 (Execution) ──→ F1/Precision/Recall + visualization plots
       ↓
Block 14 (Debug print) … broken (undefined variable)
Block 15 (pip install) … auxiliary (thop)
Block 16 (FLOPs profiling) … broken (wrong attribute, wrong input size)
```

**Branching/Dependencies:**
- Blocks 2, 3, 4, 5–11 are two independent training tracks (RPN vs Classifier) that converge in Block 12.
- Block 4 has zero effect on the pipeline — it monkey-patches `core.roi_detection` but the pipeline instantiates `NeuralROIDetector` directly, not via `core.roi_detection`.
- Block 11 loads test data in Block 8 but **never evaluates on it** — no test-phase inference is run before the pipeline in Block 13.
- Blocks 14–16 are terminal/auxiliary and do not feed back into any earlier block.

---

## 4 — Cross-Block Code Quality Audit

### Coherence and Consistency
- **CFG class shadowing:** Block 2 defines `CFG` with attributes `H5_TRAIN`, `H5_VAL`, `BATCH_SIZE=64`. Block 7 defines a second `CFG` with `TRAIN_H5`, `VAL_H5`, `TEST_H5`, `BATCH_SIZE=128`. Blocks 8–11 reference `CFG.TRAIN_H5` expecting the second definition. If execution order reverses, all downstream blocks break silently.
- **Import path inconsistency:** Block 5 imports `from rf_pipeline.models.hybrid_classifier import HybridRFClassifier`; Block 9 imports `from models.hybrid_classifier import HybridRFClassifier`. Both resolve only because Block 1 appended both `/rf_pipeline` and `/` to sys.path. Brittle.
- **Variable name mismatch (resultados vs results):** Block 14 references `resultados` but Block 13 defines `results`. This is a guaranteed `NameError` on execution.
- **Attribute mismatch (pipeline.model vs pipeline.classifier):** Block 16 accesses `pipeline.model`, but `RFAnalysisPipeline` stores the classifier as `self.classifier` (line 1249). Guaranteed `AttributeError`.
- **Input dimension mismatch:** Block 16 creates dummy inputs of size `[1,3,224,224]` but the entire pipeline uses `IMG_SIZE=256`. The classifier's CNN parameters assume 256×256 patches.
- **Missing data key (noise_level):** Block 12's `evaluate_by_noise()` reads `res["noise_level"]` from each result dict, but `predict()` never populates this key. The method will always iterate an empty `noise_groups` dict.
- **Timing data absent:** `inference_time_ms` is hardcoded to `0` in Block 12's `predict()`. All downstream timing reports (Block 13) display 0.00 ms / 0.0 FPS regardless of actual runtime.
- **Duplicate ROI dataclass:** Blocks 3 and 4 both define identical `@dataclass ROI`. The second overwrites the first in global scope.
- **Monkey-patched class never used:** Block 4 injects `AdaptiveROIDetector` into `core.roi_detection`, but Block 12's pipeline never imports from `core.roi_detection` for detection — it directly instantiates `NeuralROIDetector`.

### Redundancy and Waste
- **Per-sample HDF5 file open:** `RPNDataset.__getitem__` (Block 2, line 278) opens the entire HDF5 file on every single item retrieval. With `persistent_workers=True` and multi-worker DataLoaders, each worker opens the file ~5250× per epoch (21000/4 workers). This is an extreme I/O bottleneck. The file should be opened once per worker via `worker_init_fn` or in `__init__`.
- **Repeated module import and reload:** Block 8 re-imports `core.data_loader`, reloads it via `importlib.reload`, and re-imports `H5HybridDetectionDataset` — all of which was already done in Block 6. Redundant.
- **Repeated sys.path append:** Blocks 1, 2, and 4 all append paths to sys.path. Entries accumulate redundantly.
- **Unused model parameter:** `TinyUNet.conv1 = DoubleConv(96,64)` (Block 2, line 165) allocates parameters but is never referenced in `forward()`. Wastes approximately 128K parameters.
- **Unused constructor parameters:** `AdaptiveROIDetector` accepts `time_tol` and `freq_tol` but never uses them (Block 4, lines 527-528).
- **Unused DataLoader:** `dl_test` is created in Block 8 (line 907) but never consumed — no test-set evaluation occurs.
- **Unused import:** `inspect` is imported in Block 1 but never used.
- **Spectrogram recomputation:** `H5HybridDetectionDataset` (Blocks 8, 11, 12) computes STFT/MCE spectrograms on-the-fly per `__getitem__` call. With 700 training samples × 10 epochs = 7000 redundant spectrogram computations. No caching mechanism.

### Contradictory Logic
- **Dual detection strategy:** Block 4 defines `AdaptiveROIDetector` (classical vision, z-score + morphology) and monkey-patches it. Block 3 defines `NeuralROIDetector` (deep learning, U-Net). Block 12's pipeline uses `NeuralROIDetector` exclusively. The classical detector exists but is never wired into the pipeline — creating confusion about which detection strategy is operational.
- **Two CFG classes contradict:** Block 2's CFG targets a different dataset (`rf-benchmark`) with 21000 train samples. Block 7's CFG targets `rf-benchmark-tiny` with 700 train samples. Only one `CFG` class exists in global scope at a time. The pipeline (Block 12) imports `config as cfg` from the config.py file (Block 6), not from either CFG class directly.
- **Model checkpoint dependency hidden:** Block 12's constructor requires `rpn_path` and raises `FileNotFoundError` if missing. But the RPN training cell (Block 2) has `execution_count: null` — it may not have completed successfully. The pipeline would fail without a clear error indicating the training step was skipped.
- **Bare `except:` in dataset code:** `RPNDataset._meta_to_box` (Block 2, line 245) uses a bare `except:` clause that silently returns `None` for ANY exception type, hiding KeyError, TypeError, and ValueError bugs.

---

## LEVEL 1 — CONCEPTUAL (Structural + Reproducibility)

### Structural Overview
The notebook is structured as two independent training routines (U-Net RPN, Hybrid Classifier) followed by an integration pipeline. The layering is conceptually clean: segmentation → detection → classification. However, the dual-detector approach (neural + classical) with monkey-patching introduces ambiguity about which code path is active.

### Reproducibility Assessment
| Factor | Status | Detail |
|--------|--------|--------|
| Git clone | FAIL | Cell 0 errored (missing ipykernel). MCE-ROI-V2 repo not cloned in this session. |
| Hardcoded paths | YES | All HDF5/data paths are Kaggle-absolute. Not portable. |
| Config file | DYNAMIC | config.py is generated at runtime (Block 6). Good for adaptation, bad for versioning. |
| Model checkpoints | PARTIAL | `best_unet_rpn.pt` and `best_model.pt` saved. No seed setting — random initialization varies per run. |
| Execution order | FRAGILE | Multiple cells with `execution_count: null`. Cells 14, 15, 16 never executed. |
| Environment | LIMITED | Requires specific Kaggle dataset mounts, GPU (T4 assumed), pip packages not listed. No `requirements.txt`. |
| **Verdict** | **NOT REPRODUCIBLE** | The git clone fails, RPN training never ran in current kernel, and multiple cells are broken. Even with fixed environment, results vary due to no random seed. |

---

## LEVEL 2 — METHODOLOGICAL (Data Integrity + ML Correctness)

### Data Integrity Review
- **Train/Val/Test split:** Clean 700/150/150 split for classifier. RPN uses different dataset with 21000/4500 split. No cross-contamination observed.
- **Label derivation:** RPN masks are derived from metadata bounding boxes in HDF5 via `_meta_to_box()`. The mapping from `(start_in_samples, duration, low_freq, high_freq)` to pixel coordinates uses `hop = NPERSEG - NOVERLAP` and frequency range `[-FS/2, FS/2]`. This is correct if metadata values are accurate.
- **Bare except clause:** `_meta_to_box` has a blanket `except:` (line 245) that silently returns `None`, meaning corrupt or missing metadata silently produces empty masks rather than raising errors.
- **Key filtering:** `RPNDataset` filters HDF5 keys by `str.isdigit()` — assumes all integer-named keys are valid dataset entries. This is fragile if the HDF5 has non-dataset integer-named groups.
- **Complex IQ handling:** `RPNDataset.__getitem__` handles 2-channel IQ `[..., 2]` by forming complex arrays and single-channel by passing through. This is reasonable but the `ndim > 1 and shape[-1] == 2` check could miss edge cases (e.g., `[2, N]`).

### ML Correctness Audit
- **Tversky loss asymmetry:** α=0.3, β=0.7 correctly penalizes false negatives more heavily — appropriate for signal detection where missing a signal is worse than a false alarm.
- **Validation metric mismatch:** RPN training (Block 2) monitors Tversky score (IoU-like). Classifier training (Block 11) monitors accuracy. These are different metric families — the RPN's scheduler optimizes overlap quality, the classifier optimizes per-sample correctness. Both are valid for their respective tasks.
- **No early stopping on classifier:** Block 11 trains for exactly 10 epochs with no early stopping, no LR schedule, no gradient clipping. For a small dataset (700 samples), this is acceptable but lacks robustness against overfitting.
- **IoU threshold for evaluation:** `iou_thresh=0.2` in `evaluate()` is very permissive — boxes need only 20% overlap to count as a match. At this threshold, precision=1.0 (no false positives) but recall=0.7053 (30% of ground-truth signals missed).
- **No test evaluation:** Despite loading `dl_test` (Block 8), the training loop never runs evaluation on it. The pipeline (Block 13) does test evaluation, but this conflates the classifier's standalone performance with the full pipeline's end-to-end performance.
- **Confidence threshold:** `confidence_thresh=0.2` (Block 13) is extremely low for a binary classifier — nearly any signal-like output passes. This explains the perfect precision (only real signals produce any activation) but low recall (RPN misses some signals entirely).
- **No seed initialization:** Neither `torch.manual_seed`, `np.random.seed`, nor `random.seed` is set anywhere. Training results are not reproducible across runs.

---

## LEVEL 3 — IMPLEMENTATION (Code Quality + Deployment Readiness)

### Code Quality Issues
- **Bare `except:` (Block 2, line 245):** Swallows all exception types. Must be replaced with specific exceptions or at minimum log the error type and value.
- **`torch.load` without `weights_only=True` (Block 3, line 422):** PyTorch ≥2.4 issues a `FutureWarning` and this is a known security vulnerability for untrusted checkpoints.
- **HDF5 opened per `__getitem__` (Block 2, line 278):** Antipattern for multi-worker DataLoaders. Should use `worker_init_fn` to open one file handle per worker, or pre-load IQ data into memory if it fits.
- **Monkey-patching `core.roi_detection` (Block 4, line 684):** Global state mutation that is invisible to static analysis. The patched class is never actually used by the pipeline — dead injection.
- **`os.cpu_count()` for workers (Block 2, line 122):** Returns total system CPU count, not the count available to the Kaggle kernel. If the kernel is restricted to 2 CPUs but the host has 64, creates 64 workers that contend.
- **Duplicate definitions (ROI, CFG):** Two `ROI` dataclasses and two `CFG` classes create ambiguity and risk of attribute mismatch.
- **Placeholder comments in production code:** `"# (Calcula tu tiempo real)"` and `"El resto... permanece IGUAL"` are development notes left in deployable code.
- **Typo:** `"NOTA IMPORANTE"` (line 622).
- **Misleading comment:** `"Usa todos los núcleos disponibles (4 en Kaggle)"` — hardcoded assumption contradicted by using `os.cpu_count()`.

### Deployment Readiness
| Criterion | Status | Detail |
|-----------|--------|--------|
| Portable paths | NO | All paths are Kaggle-absolute (`/kaggle/input/...`, `/kaggle/working/...`) |
| Model artifact management | PARTIAL | Checkpoints saved with fixed names (no versioning, no metadata) |
| Error handling | WEAK | Bare excepts, no retry logic, no graceful degradation |
| Config management | CONFLICTED | Hardcoded CFG + runtime-generated config.py, two CFG classes |
| Logging | MINIMAL | Only `print()` statements, no structured logging |
| Test coverage | NONE | No unit tests, no integration tests |
| Dependency listing | NONE | No `requirements.txt`, `environment.yml`, or `!pip list` export |
| GPU fallback | YES | `DEVICE = "cuda" if torch.cuda.is_available() else "cpu"` in both CFG classes |
| **Verdict** | **NOT DEPLOYABLE** | Fix at minimum: paths, error handling, checkpoint versioning, and dead code before considering deployment. |

---

**Fingerprint:** `lap 1`
**Timestamp:** 2026-07-04T00:00:00Z
