# near the imports

from pathlib import Path
import warnings
from typing import Optional, Tuple, Union, Dict, Any, List
import gc
import math
import time
import json
import csv
import torch
import numpy as np

import os
IS_WINDOWS = (os.name == "nt")
try:
    import torch._dynamo as torchdynamo
except Exception:
    torchdynamo = None

def _maybe_compile(m: torch.nn.Module) -> torch.nn.Module:
    """Safe torch.compile wrapper. Skips inductor on Windows; falls back to eager."""
    if not hasattr(torch, "compile"):
        return m
    # Optional: avoid hard failures
    if torchdynamo is not None:
        torchdynamo.config.suppress_errors = True

    if IS_WINDOWS:
        # safest: don't use inductor on Windows
        try:
            return torch.compile(m, backend="eager")
        except Exception:
            return m
    # non-Windows: try inductor, then fall back to eager
    try:
        return torch.compile(m, mode="reduce-overhead", backend="inductor")
    except Exception:
        try:
            return torch.compile(m, backend="eager")
        except Exception:
            return m


# ===== Global numerical policy (single source of truth) =====
DEVICE = torch.device("cuda")
DTYPE = torch.float32           # << more fast in CPU than float64
CDTYPE = torch.complex64

# ===== Optional Dependencies =====
try:
    import torchaudio
except ImportError:
    torchaudio = None
try:
    import soundfile as sf
except ImportError:
    sf = None
try:
    from scipy.io import wavfile as scipy_wav
except ImportError:
    scipy_wav = None
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
try:
    from scipy import signal as sps
except Exception:
    sps = None

# ===== HPO Dependencies =====
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False


warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")


# ===== Global Setup =====
def _set_global_threads():
    """Set conservative global thread counts for PyTorch to avoid oversubscription."""
    try:
        torch.set_num_threads(max(1, (os.cpu_count() or 8) // 2))
        torch.set_num_interop_threads(1)
    except Exception:
        pass
_set_global_threads()

@torch.no_grad()
def _warmup_numerics():
    a = torch.randn(8192, dtype=DTYPE, device=DEVICE)
    _ = torch.fft.rfft(a)
    M = torch.randn(8, 8, dtype=DTYPE, device=DEVICE)
    G = M.T @ M + 1e-6 * torch.eye(8, dtype=DTYPE, device=DEVICE)
    b = torch.randn(8, 1, dtype=DTYPE, device=DEVICE)
    _ = torch.linalg.solve(G, b)

def _resample_waveform(waveform: torch.Tensor, sr: int, target_sr: int) -> Tuple[torch.Tensor, int, str]:
    """
    Resample (C, T) waveform sr -> target_sr using torchaudio if available,
    otherwise SciPy polyphase. Returns (waveform_resampled, new_sr, method_used).
    """
    if sr == target_sr:
        return waveform, sr, "none"

    # Preferred: torchaudio, keeps tensor on device
    if torchaudio is not None:
        wf = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=target_sr)
        return wf, target_sr, "torchaudio"

    # Fallback: SciPy polyphase (CPU NumPy → back to torch)
    if sps is not None:
        g = math.gcd(sr, target_sr)
        up, down = target_sr // g, sr // g
        wf_np = waveform.detach().to("cpu").numpy()        # (C, T)
        res_np = sps.resample_poly(wf_np, up, down, axis=1)  # vectorized over channels
        wf = torch.from_numpy(res_np).to(dtype=waveform.dtype, device=waveform.device)
        return wf, target_sr, "scipy"


    warnings.warn(
        f"Requested resample {sr}→{target_sr} but neither torchaudio nor SciPy is available. "
        "Proceeding with original sample rate."
    )
    return waveform, sr, "unavailable"



# ===== File I/O and Preprocessing =====
def read_wav(
    file_path: Union[str, Path],
    target_sr: Optional[int] = None,
    mono_mode: str = "first",
    max_duration_s: Optional[float] = None,
) -> Tuple[torch.Tensor, int]:
    """High-level WAV reader that returns a waveform on the global (DEVICE, DTYPE)."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: '{p}'")

    if sf:
        data, sr = sf.read(str(p), dtype="float32", always_2d=True)  # np.float32
        waveform = torch.from_numpy(data.T)  # (C, N)
    else:
        raise ImportError("Soundfile is required. Please install it: pip install soundfile")

    if max_duration_s is not None:
        max_samples = int(sr * max_duration_s)
        waveform = waveform[..., :max_samples]

    # Convert to mono
    if waveform.size(0) > 1:
        if mono_mode == "first":
            waveform = waveform[:1, :]
        else:
            waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if target_sr and sr != target_sr:
        if torchaudio is not None:
            waveform = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=target_sr)
            sr = target_sr
        elif sps is not None:
            # polyphase resample (per channel)
            g = math.gcd(sr, target_sr)
            up, down = target_sr // g, sr // g
            wf_np = waveform.detach().cpu().numpy()  # (C, T)
            resampled = [sps.resample_poly(ch, up, down) for ch in wf_np]
            waveform = torch.from_numpy(np.stack(resampled, axis=0))
            sr = target_sr
        else:
            warnings.warn(
                f"Requested resample {sr}→{target_sr} but neither torchaudio nor SciPy is available. "
                "Proceeding with original sample rate."
            )

    return waveform.to(dtype=DTYPE, device=DEVICE), sr

def prewhitening_check(x: torch.Tensor, sr: int, verbose: bool = True) -> Dict[str, Any]:
    """Assess whether the signal is near-white and safe to decimate. (placeholder)"""
    if verbose:
        print("Performing pre-whitening check (placeholder)...")
    return {"sfm": 0.5, "ljung_box_Q": 100.0, "aliasing_fraction": {2: 0.05}, "suggestion": "Placeholder suggestion"}


# ===== Neural Network Models =====
class Chomp1d(torch.nn.Module):
    """A module that removes elements from the end of a temporal dimension."""
    def __init__(self, chomp_size):
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x):
        return x[:, :, :-self.chomp_size].contiguous() if self.chomp_size > 0 else x

class TemporalBlock(torch.nn.Module):
    """A residual block for a TCN, with causal, dilated convolutions."""
    def __init__(self, n_inputs, n_outputs, kernel_size, stride, dilation, padding, dropout=0.2):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride,
                            padding=padding, dilation=dilation),
            Chomp1d(padding),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride,
                            padding=padding, dilation=dilation),
            Chomp1d(padding),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout)
        )
        self.downsample = torch.nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = torch.nn.ReLU()

    def forward(self, x):
        res = x if self.downsample is None else self.downsample(x)
        out = self.net(x)
        return self.relu(out + res)

class TCNModel(torch.nn.Module):
    """A Temporal Convolutional Network for time-series forecasting."""
    def __init__(self, num_channels: List[int], kernel_size=2, dropout=0.2):
        super().__init__()
        layers = []
        for i in range(len(num_channels)):
            dilation_size = 2 ** i
            in_channels = 1 if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            layers.append(
                TemporalBlock(in_channels, out_channels, kernel_size, stride=1,
                              dilation=dilation_size,
                              padding=(kernel_size-1) * dilation_size,
                              dropout=dropout)
            )
        self.network = torch.nn.Sequential(*layers)
        self.final_fc = torch.nn.Linear(num_channels[-1], 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T)
        x = x.unsqueeze(1)               # (B, 1, T)
        out = self.network(x)            # (B, C, T)
        last_time_step_out = out[:, :, -1]   # (B, C)
        return self.final_fc(last_time_step_out).squeeze(-1)  # (B,)


# ===== Training and Prediction =====
@torch.no_grad()
def _roll_predict_sequence(
    model: torch.nn.Module,
    last_context: torch.Tensor,
    steps: int,
) -> np.ndarray:
    """
    Roll forecasts forward for `steps` for TCN-style models.
    """
    model.eval()
    # make sure we own the memory and it's contiguous (prevents view/alias surprises)
    ctx = last_context.to(dtype=DTYPE, device=DEVICE).contiguous().clone()  # (lags,)
    preds = np.empty(steps, dtype=np.float32)

    for t in range(steps):
        inp = ctx.unsqueeze(0)  # (1, lags)
        y_hat = float(model(inp).item())
        preds[t] = y_hat

        # SAFE shift: avoid overlapping copy
        ctx = torch.roll(ctx, shifts=-1)
        ctx[-1] = y_hat

    return preds

#----------------------------------------
 #Precompute X_all/y_all and do the AR flip once
def fit_sequence_model(
    waveform: torch.Tensor,
    lags: int = 10,
    samples_to_predict: int = 100,
    nn_params: Optional[Dict[str, Any]] = None,
    epochs: int = 5,
    batch_size: int = 8192,
    lr: float = 1e-2,
    weight_decay: float = 0.0,
    grad_clip: float = 1.0,
    verbose: bool = True,
    shuffle: bool = True,
    train_dtype: torch.dtype = DTYPE,
    validation_split: float = 0.0,
) -> Tuple[Optional[dict], Optional[np.ndarray], Optional[float]]:
    """
    Train TCN on overlapping windows.
    Returns (state_dict, predictions, validation_loss).
    """
    if nn_params is None:
        nn_params = {}

    if waveform.ndim != 2:
        raise ValueError(f"Expected (C, N), got {tuple(waveform.shape)}")
    x = waveform[0]
    if x.numel() <= lags + 1:
        if verbose: print("Not enough samples for the requested lags.")
        return None, None, None

    # ---- Build model
    if verbose: print("Initializing TCNModel...")
    t_build = time.perf_counter()
    # TCN needs specific params, extract them
    tcn_channels = nn_params.get("channels", [16, 32])
    if isinstance(tcn_channels, str): # Handle string representation from HPO
        tcn_channels = json.loads(tcn_channels)
    model = TCNModel(
        num_channels=tcn_channels,
        kernel_size=nn_params.get("kernel_size", 3),
        dropout=nn_params.get("dropout_rate", 0.2),
    )
    if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")

    model = _maybe_compile(model)
    model.to(device=DEVICE, dtype=train_dtype)

    # ---- Create windows
    windows = x.unfold(0, lags + 1, 1)
    M = windows.shape[0]
    if M == 0:
        if verbose: print("No training windows available.")
        return None, None, None

    X_all = windows[:, :lags].to(dtype=train_dtype, device=DEVICE)
    y_all  = windows[:, -1].to(dtype=train_dtype, device=DEVICE)


    # ---- Data Splitting for HPO/Validation ----
    if validation_split > 0:
        val_size = int(M * validation_split)
        train_size = M - val_size
        indices = torch.randperm(M, device=X_all.device) if shuffle else torch.arange(M, device=X_all.device)
        train_indices, val_indices = indices[:train_size], indices[train_size:]
        X_train, y_train = X_all[train_indices], y_all[train_indices]
        X_val, y_val = X_all[val_indices], y_all[val_indices]
    else:
        X_train, y_train = X_all, y_all
        X_val, y_val = None, None # No validation set

    # ---- Standard training loop ----
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.MSELoss()

    effective_bs = min(batch_size, X_train.shape[0])
    for ep in range(1, epochs + 1):
        epoch_loss, count = 0.0, 0
        model.train()
        
        # Use training data for training loop
        indices = torch.randperm(X_train.shape[0], device=X_train.device) if shuffle else torch.arange(X_train.shape[0], device=X_train.device)
        
        for i in range(0, X_train.shape[0], effective_bs):
            batch_indices = indices[i:i+effective_bs]
            Xb, yb = X_train[batch_indices], y_train[batch_indices]

            opt.zero_grad(set_to_none=True)
            yhat = model(Xb)
            loss = loss_fn(yhat, yb)
            loss.backward()
            if grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            opt.step()

            bs = Xb.size(0)
            epoch_loss += loss.item() * bs
            count += bs
        if verbose:
            print(f"Epoch {ep}/{epochs}, Train Loss: {epoch_loss / max(count, 1):.6f}")

    # ---- Validation Loss Calculation ----
    val_loss = None
    if X_val is not None and y_val is not None:
        model.eval()
        with torch.no_grad():
            y_val_hat = model(X_val)
            val_loss = loss_fn(y_val_hat, y_val).item()
        if verbose:
            print(f"Final Validation Loss: {val_loss:.6f}")

    # ---- Roll-out
    last_ctx = x[-lags:]
    preds_future = _roll_predict_sequence(
        model, last_context=last_ctx, steps=samples_to_predict
    )

    return model.state_dict(), preds_future, val_loss


def process_audio_files(
    audio_files: list,
    base_path: Union[str, Path],
    max_lags: int = 10,
    samples_to_predict: int = 100,
    target_sr: Optional[int] = None,
    mono_mode: str = "first",
    max_duration_s: Optional[float] = None,
    verbose: bool = True,
    nn_params: Optional[Dict[str, Any]] = None,
    nn_epochs: int = 5,
    nn_batch_size: int = 8192,
    nn_lr: float = 1e-2,
    nn_weight_decay: float = 0.0,
    nn_grad_clip: float = 1.0,
    do_prewhitening_check: bool = True,
) -> Dict[str, Any]:
    """Process audio files using a TCN sequence model."""
    if nn_params is None:
        nn_params = {}

    base_path = Path(base_path)
    results: Dict[str, Any] = {}

    if verbose:
        print(f"\nProcessing {len(audio_files)} audio files with model_type='tcn'...")

    for i, file_name in enumerate(audio_files, 1):
        file_path = base_path / file_name
        if verbose:
            print(f"\n[{i}/{len(audio_files)}] {file_name}")

        if not file_path.is_file():
            if verbose: print(f"↪️  Skipping missing file: {file_path}")
            results[file_name] = {"success": False, "error": f"File not found: {file_path}"}
            continue

        t0 = time.perf_counter()
        try:
            waveform, sr = read_wav(file_path, target_sr=target_sr, max_duration_s=max_duration_s, mono_mode=mono_mode)
            item: Dict[str, Any] = {"success": True, "sample_rate": sr, "duration": waveform.shape[1] / sr}

            if do_prewhitening_check:
                item["prewhitening"] = prewhitening_check(waveform[0], sr, verbose=verbose)

            nn_state, nn_preds, _ = fit_sequence_model(
                waveform, lags=max_lags,
                samples_to_predict=samples_to_predict, nn_params=nn_params,
                epochs=nn_epochs, batch_size=nn_batch_size, lr=nn_lr,
                weight_decay=nn_weight_decay, grad_clip=nn_grad_clip, verbose=verbose,
                validation_split=0.0 # No validation split during final processing
            )

            if nn_state is not None:
                flat_params = np.concatenate([v.detach().cpu().numpy().ravel() for v in nn_state.values()])
                item["nn_model"] = {
                    "model_type": 'tcn',
                    "lags": max_lags,
                    "predictions": nn_preds,
                    "hyperparams": nn_params,
                    "flat_params": flat_params,
                }
            else:
                item["success"] = False
                item["error"] = "TCN training failed"

            item["time_sec"] = time.perf_counter() - t0
            results[file_name] = item
            if verbose: print(f"✓ Done: {file_name} | time={item['time_sec']:.2f}s")

        except Exception as e:
            results[file_name] = {"success": False, "error": str(e), "time_sec": time.perf_counter() - t0}
            if verbose: print(f"✗ Failed: {file_name}: {e}")
        finally:
            gc.collect()

    successful = sum(1 for r in results.values() if r.get("success", False))
    if verbose: print(f"\n📊 Summary: {successful}/{len(audio_files)} files processed successfully.")
    return results

# ===== HPO Objective Function =====
def create_hpo_objective(waveform: torch.Tensor, lags: int, epochs: int, search_space: List) -> callable:
    """
    Creates the objective function for skopt to minimize.
    This function takes a set of hyperparameters, trains a model, and returns the validation loss.
    """
    @use_named_args(search_space)
    def objective(**params):
        print(f"\n HPO Trial with params: {params}")
        nn_params_trial = {
            "dropout_rate": params.get("dropout_rate"),
            "channels": params.get("channels"),
            "kernel_size": params.get("kernel_size")
        }
        
        # Filter out None values for model-specific params
        nn_params_trial = {k: v for k, v in nn_params_trial.items() if v is not None}

        # Train the model with a validation split to get a score
        _, _, val_loss = fit_sequence_model(
            waveform=waveform,
            lags=lags,
            samples_to_predict=1, # We don't need predictions here
            nn_params=nn_params_trial,
            epochs=epochs,
            batch_size=params["batch_size"],
            lr=params["lr"],
            weight_decay=params["weight_decay"],
            verbose=False, # Keep HPO loop clean
            validation_split=0.20 # Use 20% of data for validation
        )

        # Handle cases where training might fail
        if val_loss is None or not np.isfinite(val_loss):
            return 9999.0 # Return a large number for failed runs
        
        print(f"  -> Validation Loss: {val_loss:.6f}")
        gc.collect() # Clean up memory between trials
        return val_loss
        
    return objective

# ===== Post-processing =====
def _rows_from_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts rows for a CSV from the results dictionary."""
    rows = []
    for fname, item in results.items():
        if not item.get("success") or "nn_model" not in item:
            continue
        model_info = item["nn_model"]
        row = {
            "file_name": fname,
            "model_type": model_info.get("model_type"),
            "lags": model_info.get("lags"),
            "sample_rate": item.get("sample_rate"),
            "duration_sec": item.get("duration"),
            "time_sec": item.get("time_sec"),
            "hyperparams_json": json.dumps(model_info.get("hyperparams")),
            "flat_params_json": json.dumps(model_info.get("flat_params", []).tolist()),
        }
        rows.append(row)
    return rows

def save_ar_params_csv(results: Dict[str, Any], out_csv_path: Union[str, Path]) -> int:
    """Writes model parameter trace to CSV for downstream analysis."""
    rows = _rows_from_results(results)
    if not rows:
        print("⚠️  No model parameters to save.")
        return 0

    out_csv_path = Path(out_csv_path)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["file_name", "model_type", "lags", "sample_rate", "duration_sec", "time_sec",
                  "hyperparams_json", "flat_params_json"]
    with out_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"📁 Saved model parameter trace to: {out_csv_path} ({len(rows)} rows)")
    return len(rows)
# ===== PCA utilities (feature building, PCA via SVD, plotting) =====
def _feature_matrix_from_results(
    results: Dict[str, Any],
    feature: str = "predictions",  # "predictions" o "flat_params"
    target_dim: Optional[int] = None  # si usas flat_params y quieres recortar/zero-pad
) -> Tuple[List[str], np.ndarray]:
    """
    Build the feature matrix X (n_files x d) from 'results'.
    By default, it uses 'predictions' (fixed length). If you use 'flat_params', you can
    set target_dim to zero-pad/trim and thus standardize dimensions.
    """
    names, feats = [], []
    for fname, item in results.items():
        if not item.get("success"):
            continue
        nnm = item.get("nn_model", {})
        if feature == "predictions":
            vec = np.asarray(nnm.get("predictions"), dtype=np.float32)
            if vec.size == 0:
                continue
        elif feature == "flat_params":
            vec = np.asarray(nnm.get("flat_params"), dtype=np.float32)
            if vec.size == 0:
                continue
            if target_dim is not None:
                if vec.size >= target_dim:
                    vec = vec[:target_dim]
                else:
                    vec = np.pad(vec, (0, target_dim - vec.size))
        else:
            raise ValueError("feature must be 'predictions' or 'flat_params'")
        names.append(fname)
        feats.append(vec)
    if not feats:
        raise RuntimeError("No features were built. Check 'results'.")
    X = np.vstack(feats)  # (n_files, d)
    return names, X


def _pca_svd(X: np.ndarray, k: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    PCA by SVD (centered). Returns (Z, comps, var_exp):
      - Z: projection in k dimensions (n_files, k)
      - comps: eigenvectors (k, d)
      - var_exp: variance explained by component (k,)
    """
    X = np.asarray(X, dtype=np.float64)
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    # SVD: Xc = U S Vt
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:k, :]                  # (k, d)
    Z = (Xc @ comps.T).astype(np.float32)  # (n, k)
    # Varianza explicada:
    sing_vals_sq = (S ** 2)
    var_total = sing_vals_sq.sum()
    var_exp = sing_vals_sq[:k] / (var_total + 1e-12)
    return Z, comps, var_exp


def save_pca_csv(names: List[str], Z: np.ndarray, var_exp: np.ndarray, out_csv: Union[str, Path]) -> None:
    """
    Save a CSV with columns: file_name, pc1, pc2[, pc3], plus explained variance in header.
    """
    out_csv = Path(out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pcs = Z.shape[1]
    fieldnames = ["file_name"] + [f"pc{i+1}" for i in range(pcs)]
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for fname, row in zip(names, Z):
            writer.writerow({"file_name": fname, **{f"pc{i+1}": float(row[i]) for i in range(pcs)}})
    print(f"📁 PCA saved in: {out_csv} | Var. explained: {', '.join([f'{v*100:.2f}% ' for v in var_exp])}")


def plot_pca_scatter(names: List[str], Z: np.ndarray, var_exp: np.ndarray, out_png: Union[str, Path]) -> None:
    """
    Draw and save a 2D/3D scatter of the PCA if Matplotlib is available.
    Does not define explicit colors.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("ℹ️ Matplotlib not available: the graph is omitted.")
        return
    import matplotlib.pyplot as plt

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if Z.shape[1] == 2:
        plt.figure()
        plt.scatter(Z[:, 0], Z[:, 1])
        for i, name in enumerate(names):
            plt.annotate(name, (Z[i, 0], Z[i, 1]), fontsize=8)
        plt.xlabel(f"PC1 ({var_exp[0]*100:.1f}% var)")
        plt.ylabel(f"PC2 ({var_exp[1]*100:.1f}% var)")
        plt.title("PCA de audios (feature: predictions)")
        plt.tight_layout()
        plt.savefig(out_png, dpi=150)
        plt.close()
        print(f"🖼️ Scatter PCA guardado en: {out_png}")
    elif Z.shape[1] == 3:
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(Z[:, 0], Z[:, 1], Z[:, 2])
        for i, name in enumerate(names):
            ax.text(Z[i, 0], Z[i, 1], Z[i, 2], name, fontsize=8)
        ax.set_xlabel(f"PC1 ({var_exp[0]*100:.1f}%)")
        ax.set_ylabel(f"PC2 ({var_exp[1]*100:.1f}%)")
        ax.set_zlabel(f"PC3 ({var_exp[2]*100:.1f}%)")
        ax.set_title("PCA de audios (feature: predictions)")
        plt.tight_layout()
        fig.savefig(out_png, dpi=150)
        plt.close(fig)
        print(f"🖼️ Scatter 3D PCA saved in: {out_png}")
    else:
        print("Z must have 2 or 3 columns to plot.")

# ===== Clustering utilities (KMeans on PCA coords with centroids) =====

def run_kmeans(

    Z: np.ndarray, names: List[str], n_clusters: int = 2,
    out_csv: Optional[Union[str, Path]] = None,
    out_png: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Applies KMeans on PCA coords Z (n x d). Writes CSV and optional scatter with centroids.
    Robust to k > n_samples and duplicate points.
    """
    if Z.ndim != 2 or Z.shape[0] == 0:
        raise ValueError("Z must be (n_samples, n_dims) with n_samples > 0")

    n_samples = Z.shape[0]
    if n_samples < 2:
        raise ValueError(f"Need at least 2 samples for clustering, got {n_samples}")

    # Clamp k to available samples
    k = min(n_clusters, n_samples)
    if k < 2:
        raise ValueError(f"n_clusters must be >= 2 but only {n_samples} samples are available")

    # If there are fewer distinct points than k, reduce k
    n_distinct = np.unique(Z, axis=0).shape[0]
    if n_distinct < k:
        warnings.warn(f"Only {n_distinct} distinct points; reducing k from {k} to {n_distinct}")
        k = n_distinct
        if k < 2:
            raise ValueError("Fewer than 2 distinct points—cannot run KMeans.")

    # n_init portable across sklearn versions
    try:
        km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    except TypeError:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)

    labels = km.fit_predict(Z)
    inertia = km.inertia_
    centroids = km.cluster_centers_

    # --- CSV ---
    if out_csv:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file_name", "cluster"])
            for name, lab in zip(names, labels):
                writer.writerow([name, int(lab)])
        print(f"📁 Clusters saved in: {out_csv}")

    # --- Plot with centroids (if matplotlib available) ---
    if out_png and MATPLOTLIB_AVAILABLE:
        import matplotlib.pyplot as plt
        if Z.shape[1] == 2:
            plt.figure()
            plt.scatter(Z[:, 0], Z[:, 1], c=labels, cmap="tab10", alpha=0.7)
            plt.scatter(centroids[:, 0], centroids[:, 1], marker="*", c="black", s=200, label="Centroids")
            for i, name in enumerate(names):
                plt.annotate(name, (Z[i, 0], Z[i, 1]), fontsize=8)
            plt.xlabel("PC1"); plt.ylabel("PC2")
            plt.title(f"KMeans (k={k}), inertia={inertia:.2f}")
            plt.legend(); plt.tight_layout()
            plt.savefig(out_png, dpi=150); plt.close()
            print(f"🖼️ Scatter clusters saved in: {out_png}")
        elif Z.shape[1] == 3:
            from mpl_toolkits.mplot3d import Axes3D  # noqa
            fig = plt.figure(); ax = fig.add_subplot(111, projection='3d')
            ax.scatter(Z[:, 0], Z[:, 1], Z[:, 2], c=labels, cmap="tab10", alpha=0.7)
            ax.scatter(centroids[:, 0], centroids[:, 1], centroids[:, 2], marker="*", c="black", s=300, label="Centroids")
            for i, name in enumerate(names):
                ax.text(Z[i, 0], Z[i, 1], Z[i, 2], name, fontsize=8)
            ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.set_zlabel("PC3")
            ax.set_title(f"KMeans (k={k}), inertia={inertia:.2f}")
            ax.legend(); plt.tight_layout()
            fig.savefig(out_png, dpi=150); plt.close(fig)
            print(f"🖼️ Scatter 3D clusters saved in: {out_png}")

    return {"labels": labels, "inertia": inertia, "centroids": centroids}


# ===== Main Execution Block =====
if __name__ == "__main__":
    start_time = time.time()
    base_path = Path("/home/javastral/GIT/GCPDS--trabajos-/Audios-AR/PresenceANEAudios")  # folder with .wav

    model_to_run = 'tcn'

    if not base_path.exists():
        print(f"❌ Base path does not exist: {base_path}")
        print("Please create the directory and add some .wav files.")
    else:
        audio_files = [p.name for p in base_path.glob("*.wav")]

        if not audio_files:
            print(f"❌ No .wav files found in {base_path}")
        else:
            # --- HPO Configuration ---
            if not SKOPT_AVAILABLE:
                raise ImportError("scikit-optimize is required for HPO. Please install it: pip install scikit-optimize")

            print("--- 1. Starting Hyperparameter Optimization (HPO) ---")
            # Use the first audio file as a representative sample for HPO
            hpo_audio_file = base_path / audio_files[0]
            print(f"Using '{audio_files[0]}' for HPO.")
            hpo_waveform, _ = read_wav(hpo_audio_file, max_duration_s=10.0)

            print("--- Configuring HPO for TCN Model ---")
            base_config = {"max_lags": 128, "nn_epochs": 10}
            search_space = [
                Real(1e-4, 1e-2, "log-uniform", name='lr'),
                Real(1e-6, 1e-3, "log-uniform", name='weight_decay'),
                Integer(1024, 4096, name='batch_size'),
                Integer(2, 3, name='kernel_size'),
                Categorical(['[16,16]', '[16,32]'], name='channels')
            ]


            # Create the objective function for this specific audio file and config
            objective_fn = create_hpo_objective(
                waveform=hpo_waveform,
                lags=base_config["max_lags"],
                epochs=base_config["nn_epochs"],
                search_space=search_space
            )

            # Run Bayesian Optimization
            n_hpo_calls = 5 # Number of HPO trials to run
            hpo_result = gp_minimize(
                func=objective_fn,
                dimensions=search_space,
                n_calls=n_hpo_calls,
                random_state=42,
                n_initial_points=5
            )

            print("\n--- HPO Finished ---")
            print(f"Best validation loss: {hpo_result.fun:.6f}")
            
            # Create a dictionary with the best parameters found
            best_params_raw = {dim.name: val for dim, val in zip(search_space, hpo_result.x)}
            
            # Convert any numpy types to native Python types for JSON serialization
            best_params = {}
            for key, value in best_params_raw.items():
                if isinstance(value, np.generic):
                    best_params[key] = value.item() # Use .item() to convert numpy type to Python native
                else:
                    best_params[key] = value

            print("Best parameters found:")
            print(json.dumps(best_params, indent=2))

            # --- 2. Build Final Configuration from HPO Results ---
            print("\n--- 2. Configuring Final Model with Best Hyperparameters ---")
            final_nn_config = {
                "max_lags": base_config["max_lags"],
                "nn_params": {
                    "channels": best_params.get("channels"),
                    "kernel_size": best_params.get("kernel_size"),
                    "dropout_rate": best_params.get("dropout_rate"),
                },
                "nn_epochs": base_config["nn_epochs"],
                "nn_batch_size": best_params["batch_size"],
                "nn_lr": best_params["lr"],
                "nn_weight_decay": best_params["weight_decay"],
            }
            # Clean up None values from the params dict
            final_nn_config["nn_params"] = {k: v for k, v in final_nn_config["nn_params"].items() if v is not None}
            
            # --- 3. Execute main pipeline with optimized config ---
            print("\n--- 3. Processing All Audio Files with Optimized Configuration ---")
            results = process_audio_files(
                audio_files,
                base_path=base_path,
                max_duration_s=10.0,   # trim to 10s per file
                **final_nn_config
            )

            # --- 4. Post-processing (PCA, Clustering, etc.) ---
            print("\n--- 4. Running Post-processing ---")
            out_dir = base_path / "model_outputs"
            out_dir.mkdir(parents=True, exist_ok=True)

            params_csv = out_dir / f"{model_to_run}_params_trace.csv"
            save_ar_params_csv(results, params_csv)

            try:
                names, X = _feature_matrix_from_results(results, feature="predictions")

                # PCA 2D
                Z2, comps2, var_exp2 = _pca_svd(X, k=2)
                save_pca_csv(names, Z2, var_exp2, out_dir / f"{model_to_run}_pca_predictions_2d.csv")
                plot_pca_scatter(names, Z2, var_exp2, out_dir / f"{model_to_run}_pca_predictions_2d.png")

                # PCA 3D
                Z3, comps3, var_exp3 = _pca_svd(X, k=3)
                save_pca_csv(names, Z3, var_exp3, out_dir / f"{model_to_run}_pca_predictions_3d.csv")
                plot_pca_scatter(names, Z3, var_exp3, out_dir / f"{model_to_run}_pca_predictions_3d.png")

                # KMeans clustering
                try:
                    if Z2.shape[0] >= 2:
                         max_k = min(4, Z2.shape[0], np.unique(Z2, axis=0).shape[0])
                         if max_k >= 2:
                             for k in range(2, max_k + 1):
                                 run_kmeans(Z2, names, n_clusters=k,
                                            out_csv=out_dir / f"{model_to_run}_clusters_k{k}.csv",
                                            out_png=out_dir / f"{model_to_run}_clusters_k{k}.png")
                         else:
                            print("⚠️ Less than 2 distinct points for clustering.")
                    else:
                        print("⚠️ Not enough samples for clustering (requires ≥ 2).")

                except Exception as e:
                    print(f"⚠️ Clustering failed: {e}")

            except Exception as e:
                print(f"⚠️ PCA or Clustering failed: {e}")

    elapsed_time = time.time() - start_time
    print(f"\n⏳ Total execution time: {elapsed_time:.2f} seconds")