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
    from skopt.space import Real, Integer
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
class Autoencoder(torch.nn.Module):
    """A simple autoencoder with a 2D latent space for visualization."""
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden_dim, 2)  # 2D Latent Space
        )
        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(2, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Linear(hidden_dim, input_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Full autoencoding pass."""
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Encodes the input into the latent space."""
        return self.encoder(x)


# ===== Training and Feature Extraction =====
def fit_autoencoder(
    waveform: torch.Tensor,
    window_size: int = 256,
    nn_params: Optional[Dict[str, Any]] = None,
    epochs: int = 10,
    batch_size: int = 2048,
    lr: float = 1e-3,
    weight_decay: float = 1e-5,
    grad_clip: float = 1.0,
    verbose: bool = True,
    shuffle: bool = True,
    train_dtype: torch.dtype = DTYPE,
    validation_split: float = 0.1,
) -> Tuple[Optional[dict], Optional[float]]:
    """
    Train an Autoencoder on overlapping windows of a waveform.
    Returns (state_dict, validation_loss).
    """
    if nn_params is None:
        nn_params = {}

    if waveform.ndim != 2:
        raise ValueError(f"Expected (C, N), got {tuple(waveform.shape)}")
    x = waveform[0]
    if x.numel() <= window_size:
        if verbose: print("Not enough samples for the requested window size.")
        return None, None

    # ---- Build model
    if verbose: print("Initializing Autoencoder...")
    t_build = time.perf_counter()
    model = Autoencoder(
        input_dim=window_size,
        hidden_dim=nn_params.get("hidden_dim", 64)
    )
    if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")

    model = _maybe_compile(model)
    model.to(device=DEVICE, dtype=train_dtype)

    # ---- Create windows
    windows = x.unfold(0, window_size, 1).clone()
    M = windows.shape[0]
    if M == 0:
        if verbose: print("No training windows available.")
        return None, None

    # For an autoencoder, input is the target
    X_all = windows.to(dtype=train_dtype, device=DEVICE)
    y_all = windows.to(dtype=train_dtype, device=DEVICE)


    # ---- Data Splitting for Validation ----
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


    return model.state_dict(), val_loss


def process_audio_files(
    audio_files: list,
    base_path: Union[str, Path],
    window_size: int = 256,
    target_sr: Optional[int] = None,
    mono_mode: str = "first",
    max_duration_s: Optional[float] = None,
    verbose: bool = True,
    nn_params: Optional[Dict[str, Any]] = None,
    nn_epochs: int = 10,
    nn_batch_size: int = 2048,
    nn_lr: float = 1e-3,
    nn_weight_decay: float = 1e-5,
    nn_grad_clip: float = 1.0,
    do_prewhitening_check: bool = True,
) -> Dict[str, Any]:
    """Process audio files using an Autoencoder to extract latent features."""
    if nn_params is None:
        nn_params = {}

    base_path = Path(base_path)
    results: Dict[str, Any] = {}

    if verbose:
        print(f"\nProcessing {len(audio_files)} audio files with model_type='autoencoder'...")

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

            # Train the autoencoder for this specific file
            nn_state, _ = fit_autoencoder(
                waveform, window_size=window_size,
                nn_params=nn_params,
                epochs=nn_epochs, batch_size=nn_batch_size, lr=nn_lr,
                weight_decay=nn_weight_decay, grad_clip=nn_grad_clip, verbose=verbose,
                validation_split=0.1
            )

            # If training was successful, extract the mean latent representation
            if nn_state is not None:
                model = Autoencoder(input_dim=window_size, hidden_dim=nn_params.get("hidden_dim", 64))

                # Clean the state_dict keys to remove the '_orig_mod.' prefix added by torch.compile
                clean_state_dict = {
                    (k[10:] if k.startswith('_orig_mod.') else k): v
                    for k, v in nn_state.items()
                }
                model.load_state_dict(clean_state_dict)

                model.to(DEVICE)
                model.eval()

                with torch.no_grad():
                    all_windows = waveform[0].unfold(0, window_size, 1).clone()
                    latent_vectors = model.encode(all_windows.to(DEVICE))
                    # Get a single representative vector for the file by averaging
                    mean_latent_vector = latent_vectors.mean(dim=0).cpu().numpy()

                item["nn_model"] = {
                    "model_type": 'autoencoder',
                    "window_size": window_size,
                    "latent_representation": mean_latent_vector,
                    "hyperparams": nn_params,
                }
            else:
                item["success"] = False
                item["error"] = "Autoencoder training failed"

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
def create_hpo_objective(waveform: torch.Tensor, window_size: int, epochs: int, search_space: List) -> callable:
    """
    Creates the objective function for skopt to minimize for the Autoencoder.
    This function takes a set of hyperparameters, trains a model, and returns the validation loss.
    """
    @use_named_args(search_space)
    def objective(**params):
        print(f"\n HPO Trial with params: {params}")
        nn_params_trial = {
            "hidden_dim": params.get("hidden_dim"),
        }
        nn_params_trial = {k: v for k, v in nn_params_trial.items() if v is not None}

        # Train the model with a validation split to get a score
        _, val_loss = fit_autoencoder(
            waveform=waveform,
            window_size=window_size,
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
        latent_rep = model_info.get("latent_representation", np.array([np.nan, np.nan]))
        row = {
            "file_name": fname,
            "model_type": model_info.get("model_type"),
            "window_size": model_info.get("window_size"),
            "sample_rate": item.get("sample_rate"),
            "duration_sec": item.get("duration"),
            "time_sec": item.get("time_sec"),
            "latent_dim_1": float(latent_rep[0]),
            "latent_dim_2": float(latent_rep[1]),
            "hyperparams_json": json.dumps(model_info.get("hyperparams")),
        }
        rows.append(row)
    return rows

def save_latent_space_csv(results: Dict[str, Any], out_csv_path: Union[str, Path]) -> int:
    """Writes model parameter trace to CSV for downstream analysis."""
    rows = _rows_from_results(results)
    if not rows:
        print("⚠️  No model parameters to save.")
        return 0

    out_csv_path = Path(out_csv_path)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["file_name", "model_type", "window_size", "sample_rate", "duration_sec",
                  "time_sec", "latent_dim_1", "latent_dim_2", "hyperparams_json"]
    with out_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"📁 Saved latent space coordinates to: {out_csv_path} ({len(rows)} rows)")
    return len(rows)

def _feature_matrix_from_results(
    results: Dict[str, Any],
) -> Tuple[List[str], np.ndarray]:
    """
    Build the feature matrix X (n_files x 2) from the autoencoder's latent space.
    """
    names, feats = [], []
    for fname, item in results.items():
        if not item.get("success"):
            continue
        nnm = item.get("nn_model", {})
        vec = np.asarray(nnm.get("latent_representation"), dtype=np.float32)
        if vec.shape != (2,):
            continue
        names.append(fname)
        feats.append(vec)

    if not feats:
        raise RuntimeError("No features were built. Check 'results'.")
    X = np.vstack(feats)  # (n_files, 2)
    return names, X


def plot_latent_space_scatter(names: List[str], Z: np.ndarray, out_png: Union[str, Path]) -> None:
    """
    Draw and save a 2D scatter plot of the latent space if Matplotlib is available.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("ℹ️ Matplotlib not available: the graph is omitted.")
        return
    import matplotlib.pyplot as plt

    if Z.shape[1] != 2:
        print("Z must have 2 columns to plot.")
        return

    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    plt.figure()
    plt.scatter(Z[:, 0], Z[:, 1])
    for i, name in enumerate(names):
        plt.annotate(name, (Z[i, 0], Z[i, 1]), fontsize=8)
    plt.xlabel("Latent Dimension 1")
    plt.ylabel("Latent Dimension 2")
    plt.title("Audio Latent Space Representation (Autoencoder)")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    print(f"🖼️ Scatter plot saved to: {out_png}")


# ===== Clustering utilities (KMeans on latent coords with centroids) =====
def run_kmeans(
    Z: np.ndarray, names: List[str], n_clusters: int = 2,
    out_csv: Optional[Union[str, Path]] = None,
    out_png: Optional[Union[str, Path]] = None
) -> Dict[str, Any]:
    """
    Applies KMeans on latent space coords Z (n x d). Writes CSV and optional scatter with centroids.
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
    if out_png and MATPLOTLIB_AVAILABLE and Z.shape[1] == 2:
        import matplotlib.pyplot as plt
        plt.figure()
        plt.scatter(Z[:, 0], Z[:, 1], c=labels, cmap="tab10", alpha=0.7)
        plt.scatter(centroids[:, 0], centroids[:, 1], marker="*", c="black", s=200, label="Centroids")
        for i, name in enumerate(names):
            plt.annotate(name, (Z[i, 0], Z[i, 1]), fontsize=8)
        plt.xlabel("Latent Dimension 1"); plt.ylabel("Latent Dimension 2")
        plt.title(f"KMeans (k={k}), inertia={inertia:.2f}")
        plt.legend(); plt.tight_layout()
        plt.savefig(out_png, dpi=150); plt.close()
        print(f"🖼️ Cluster scatter plot saved to: {out_png}")

    return {"labels": labels, "inertia": inertia, "centroids": centroids}


# ===== Main Execution Block =====
if __name__ == "__main__":
    start_time = time.time()
    base_path = Path("/home/javastral/GIT/GCPDS--trabajos-/Audios-AR/PresenceANEAudios")  # folder with .wav

    model_to_run = 'autoencoder'

    if not base_path.exists():
        print(f"❌ Base path does not exist: {base_path}")
        print("Please create the directory and add some .wav files.")
    else:
        audio_files = [p.name for p in base_path.glob("*.wav")]

        if not audio_files:
            print(f"❌ No .wav files found in {base_path}")
        else:
            # --- 1. Hyperparameter Optimization (HPO) ---
            if not SKOPT_AVAILABLE:
                raise ImportError("scikit-optimize is required for HPO. Please install it: pip install scikit-optimize")

            print("--- 1. Starting Hyperparameter Optimization (HPO) for Autoencoder ---")
            # Use the first audio file as a representative sample for HPO
            hpo_audio_file = base_path / audio_files[0]
            print(f"Using '{audio_files[0]}' for HPO.")
            hpo_waveform, _ = read_wav(hpo_audio_file, max_duration_s=10.0)

            base_config = {"window_size": 256, "nn_epochs_hpo": 10}
            search_space = [
                Real(1e-4, 5e-3, "log-uniform", name='lr'),
                Real(1e-6, 1e-3, "log-uniform", name='weight_decay'),
                Integer(1024, 8192, name='batch_size'),
                Integer(32, 128, name='hidden_dim'),
            ]

            # Create the objective function
            objective_fn = create_hpo_objective(
                waveform=hpo_waveform,
                window_size=base_config["window_size"],
                epochs=base_config["nn_epochs_hpo"],
                search_space=search_space
            )

            # Run Bayesian Optimization
            n_hpo_calls = 20 # Number of HPO trials to run
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
                    best_params[key] = value.item() # Use .item() to convert
                else:
                    best_params[key] = value

            print("Best parameters found:")
            print(json.dumps(best_params, indent=2))


            # --- 2. Build Final Configuration from HPO Results ---
            print("\n--- 2. Configuring Final Model with Best Hyperparameters ---")
            final_nn_config = {
                "window_size": base_config["window_size"],
                "nn_params": {
                    "hidden_dim": best_params.get("hidden_dim"),
                },
                "nn_epochs": 10, # Use more epochs for the final run
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

            # --- 4. Post-processing (Clustering, Visualization) ---
            print("\n--- 4. Running Post-processing ---")
            out_dir = base_path / "model_outputs"
            out_dir.mkdir(parents=True, exist_ok=True)

            params_csv = out_dir / f"{model_to_run}_latent_space.csv"
            save_latent_space_csv(results, params_csv)

            try:
                names, Z = _feature_matrix_from_results(results)

                # Visualize the 2D latent space directly
                plot_latent_space_scatter(names, Z, out_dir / f"{model_to_run}_latent_space_2d.png")

                # KMeans clustering on the 2D latent space
                try:
                    if Z.shape[0] >= 2:
                         # Automatically determine max number of clusters
                         max_k = min(4, Z.shape[0], np.unique(Z, axis=0).shape[0])
                         if max_k >= 2:
                             for k in range(2, max_k + 1):
                                 run_kmeans(Z, names, n_clusters=k,
                                            out_csv=out_dir / f"{model_to_run}_clusters_k{k}.csv",
                                            out_png=out_dir / f"{model_to_run}_clusters_k{k}.png")
                         else:
                            print("⚠️ Less than 2 distinct points for clustering.")
                    else:
                        print("⚠️ Not enough samples for clustering (requires ≥ 2).")

                except Exception as e:
                    print(f"⚠️ Clustering failed: {e}")

            except Exception as e:
                print(f"⚠️ Feature extraction or visualization failed: {e}")

    elapsed_time = time.time() - start_time
    print(f"\n⏳ Total execution time: {elapsed_time:.2f} seconds")