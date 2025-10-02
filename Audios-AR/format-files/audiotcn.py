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
DEVICE = torch.device("cpu")
DTYPE = torch.float32           # << más rápido en CPU que float64
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
class ARNN(torch.nn.Module):
    """A flexible AR-NN: linear AR, or a deep MLP with dropout and activations."""
    def __init__(
        self, lags: int, hidden_size: int = 32, num_hidden_layers: int = 1,
        dropout_rate: float = 0.1, activation_fn: str = "relu",
        bias: bool = False
    ):
        super().__init__()
        if hidden_size <= 0:
            # Pure linear AR with configurable bias
            self.net = torch.nn.Linear(lags, 1, bias=bias)
            return

        activations = {"relu": torch.nn.ReLU(), "gelu": torch.nn.GELU(), "silu": torch.nn.SiLU()}
        act_fn = activations.get(activation_fn.lower())
        if act_fn is None:
            raise ValueError(f"Unsupported activation_fn: '{activation_fn}'")

        layers = []
        # Use the provided bias flag consistently across all Linear layers
        layers.extend([torch.nn.Linear(lags, hidden_size, bias=bias), act_fn])
        if dropout_rate > 0:
            layers.append(torch.nn.Dropout(dropout_rate))
        for _ in range(num_hidden_layers - 1):
            layers.extend([torch.nn.Linear(hidden_size, hidden_size, bias=bias), act_fn])
            if dropout_rate > 0:
                layers.append(torch.nn.Dropout(dropout_rate))
        layers.append(torch.nn.Linear(hidden_size, 1, bias=bias))
        self.net = torch.nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


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
    flip_input: Optional[bool] = None,
) -> np.ndarray:
    """
    Roll forecasts forward for `steps`.
    If flip_input is True, reverse the input context along time (ARNN convention).
    If flip_input is False, feed context as-is (TCN).
    If None, try to infer via isinstance(model, ARNN).
    """
    model.eval()
    # make sure we own the memory and it's contiguous (prevents view/alias surprises)
    ctx = last_context.to(dtype=DTYPE, device=DEVICE).contiguous().clone()  # (lags,)
    preds = np.empty(steps, dtype=np.float32)

    if flip_input is None:
        flip_input = isinstance(model, ARNN)

    for t in range(steps):
        inp = ctx.unsqueeze(0)  # (1, lags)
        if flip_input:
            inp = torch.flip(inp, dims=[1])
        y_hat = float(model(inp).item())
        preds[t] = y_hat

        # SAFE shift: avoid overlapping copy
        # Option A (fast & clean): use roll (allocates a tiny new tensor)
        ctx = torch.roll(ctx, shifts=-1)
        ctx[-1] = y_hat

        # Option B (if you prefer explicit copy):
        # tmp = ctx[1:].clone()
        # ctx[:-1].copy_(tmp)
        # ctx[-1] = y_hat

    return preds


# def fit_sequence_model(
#     waveform: torch.Tensor,
#     model_type: str = 'arnn',
#     lags: int = 10,
#     samples_to_predict: int = 100,
#     nn_params: Dict[str, Any] = {},
#     epochs: int = 5,
#     batch_size: int = 8192,
#     lr: float = 1e-2,
#     weight_decay: float = 0.0,
#     grad_clip: float = 1.0,
#     verbose: bool = True,
#     shuffle: bool = True,
#     train_dtype: torch.dtype = DTYPE,
# ) -> Tuple[Optional[dict], Optional[np.ndarray]]:
#     """Trains a sequence model (ARNN or TCN) on overlapping windows.
#        For ARNN with hidden_size <= 0, uses a closed-form OLS/ridge fit (no training loop)."""
#     if waveform.ndim != 2:
#         raise ValueError(f"Expected (C, N), got {tuple(waveform.shape)}")
#     x = waveform[0]
#     if x.numel() <= lags + 1:
#         if verbose: print("Not enough samples for the requested lags.")
#         return None, None

#     # ---- Build model
#     model: torch.nn.Module
#     if model_type.lower() == 'tcn':
#         if verbose: print("Initializing TCNModel...")
#         t_build = time.perf_counter()
#         model = TCNModel(
#             num_channels=nn_params.get("channels", [16, 32]),
#             kernel_size=nn_params.get("kernel_size", 3),
#             dropout=nn_params.get("dropout_rate", 0.2),
#         )
#         if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")
#     elif model_type.lower() == 'arnn':
#         if verbose: print("Initializing ARNN...")
#         t_build = time.perf_counter()
#         # normalize bias flag name
#         bias_flag = nn_params.get("bias", nn_params.get("include_bias", True))
#         model = ARNN(
#             lags=lags,
#             hidden_size=nn_params.get("hidden_size", 32),
#             num_hidden_layers=nn_params.get("num_hidden_layers", 1),
#             activation_fn=nn_params.get("activation_fn", "relu"),
#             dropout_rate=nn_params.get("dropout_rate", 0.1),
#             bias=bias_flag,
#         )
#         if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")
#     else:
#         raise ValueError(f"Unknown model_type: '{model_type}'")
    
#     # ---- Move once to device/dtype
#     t_to = time.perf_counter()
#     model.to(device=DEVICE, dtype=train_dtype)
#     if verbose: print(f"  moved to device/dtype in {time.perf_counter()-t_to:.3f}s")

#     # ---- Create windows
#     t_unfold = time.perf_counter()
#     windows = x.unfold(0, lags + 1, 1)   # (M, lags+1)
#     if verbose: print(f"  unfolded windows in {time.perf_counter()-t_unfold:.3f}s")
#     M = windows.shape[0]
#     if M == 0:
#         if verbose: print("No training windows available.")
#         return None, None

#     # ---- Fast path: ARNN linear case -> closed-form solve
#     if model_type.lower() == 'arnn' and nn_params.get("hidden_size", 32) <= 0:
#         if verbose: print("Using closed-form linear AR (OLS/Ridge).")
#         # Design matrix with ARNN convention (reverse lag order)
#         X_all = windows[:, :lags]
#         X_all = torch.flip(X_all, dims=[1]).to(dtype=train_dtype, device=DEVICE)  # (M, lags)
#         y_all = windows[:, -1].to(dtype=train_dtype, device=DEVICE)               # (M,)

#         # Append bias column if the linear layer has bias
#         linear = model.net  # nn.Linear(lags, 1, bias=bias_flag)
#         has_bias = (isinstance(linear, torch.nn.Linear) and linear.bias is not None)
#         if has_bias:
#             ones = torch.ones((M, 1), dtype=train_dtype, device=DEVICE)
#             X_design = torch.cat([X_all, ones], dim=1)   # (M, lags+1)
#         else:
#             X_design = X_all                              # (M, lags)

#         # Solve (X^T X + lambda I) w = X^T y
#         lam = float(nn_params.get("ridge_lambda", 1e-6))
#         Xt = X_design.transpose(0, 1)                     # (p, M)
#         XtX = Xt @ X_design                               # (p, p)
#         if lam > 0:
#             p = XtX.shape[0]
#             XtX = XtX + lam * torch.eye(p, dtype=train_dtype, device=DEVICE)
#         Xty = Xt @ y_all                                  # (p,)

#         try:
#             w = torch.linalg.solve(XtX, Xty)              # (p,)
#         except RuntimeError:
#             # Fallback to pinv if XtX is singular
#             w = torch.linalg.pinv(X_design) @ y_all       # (p,)

#         # Assign into the linear layer
#         if has_bias:
#             w_no_bias = w[:-1]
#             b = w[-1]
#             linear.weight.data.copy_(w_no_bias.view(1, -1))
#             linear.bias.data.copy_(b.view_as(linear.bias))
#         else:
#             linear.weight.data.copy_(w.view(1, -1))

#         # ---- Roll-out with the fitted linear AR
#         last_ctx = x[-lags:]
#         preds_future = _roll_predict_sequence(model, last_context=last_ctx, steps=samples_to_predict)
#         return model.state_dict(), preds_future

#     # ---- Otherwise: standard training loop (ARNN with hidden layers or TCN)
#     opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
#     loss_fn = torch.nn.MSELoss()

#     # Probe first forward
#     if verbose and M > 0:
#         Xprobe = windows[:min(64, M), :lags]
#         Xprobe_in = torch.flip(Xprobe, dims=[1]) if model_type.lower() == 'arnn' else Xprobe
#         t_fwd = time.perf_counter()
#         _ = model(Xprobe_in)
#         if verbose: print(f"  first forward in {time.perf_counter()-t_fwd:.3f}s")

#     # Precompute full tensors once to reduce per-batch work
#     X_all = windows[:, :lags]
#     if model_type.lower() == 'arnn':
#         X_all = torch.flip(X_all, dims=[1])
#     y_all = windows[:, -1]

#     for ep in range(1, epochs + 1):
#         epoch_loss, count = 0.0, 0
#         model.train()
#         indices = torch.randperm(M) if shuffle else torch.arange(M)
#         effective_bs = min(batch_size, M)
#         for i in range(0, M, effective_bs):
#             batch_indices = indices[i:i+effective_bs]
#             Xb = X_all[batch_indices]
#             yb = y_all[batch_indices]

#             opt.zero_grad(set_to_none=True)
#             yhat = model(Xb)
#             loss = loss_fn(yhat, yb)
#             loss.backward()
#             if grad_clip > 0:
#                 torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
#             opt.step()

#             epoch_loss += loss.item() * Xb.size(0)
#             count += Xb.size(0)
#         if verbose:
#             print(f"Epoch {ep}/{epochs}, Loss: {epoch_loss / max(count, 1):.6f}")

#     # ---- Roll-out
#     last_ctx = x[-lags:]
#     preds_future = _roll_predict_sequence(model, last_context=last_ctx, steps=samples_to_predict)
#     return model.state_dict(), preds_future


#----------------------------------------
 #Precompute X_all/y_all and do the AR flip once
def fit_sequence_model(
    waveform: torch.Tensor,
    model_type: str = 'arnn',
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
) -> Tuple[Optional[dict], Optional[np.ndarray]]:
    """Train ARNN/TCN on overlapping windows.
       Uses closed-form fit when ARNN is linear (hidden_size <= 0)."""
    if nn_params is None:
        nn_params = {}

    if waveform.ndim != 2:
        raise ValueError(f"Expected (C, N), got {tuple(waveform.shape)}")
    x = waveform[0]
    if x.numel() <= lags + 1:
        if verbose: print("Not enough samples for the requested lags.")
        return None, None

    mtype = model_type.lower()

    # ---- Build model
    if mtype == 'tcn':
        if verbose: print("Initializing TCNModel...")
        t_build = time.perf_counter()
        model = TCNModel(
            num_channels=nn_params.get("channels", [16, 32]),
            kernel_size=nn_params.get("kernel_size", 3),
            dropout=nn_params.get("dropout_rate", 0.2),
        )
        if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")
    elif mtype == 'arnn':
        if verbose: print("Initializing ARNN...")
        t_build = time.perf_counter()
        bias_flag = nn_params.get("bias", nn_params.get("include_bias", True))
        model = ARNN(
            lags=lags,
            hidden_size=nn_params.get("hidden_size", 32),
            num_hidden_layers=nn_params.get("num_hidden_layers", 1),
            activation_fn=nn_params.get("activation_fn", "relu"),
            dropout_rate=nn_params.get("dropout_rate", 0.1),
            bias=bias_flag,
        )
        if verbose: print(f"  built in {time.perf_counter()-t_build:.3f}s")
    else:
        raise ValueError(f"Unknown model_type: '{model_type}'")

    # ---- Safe optional compile (no Windows inductor crash)
    model = _maybe_compile(model)

    # ---- Move once to device/dtype
    t_to = time.perf_counter()
    model.to(device=DEVICE, dtype=train_dtype)
    if verbose: print(f"  moved to device/dtype in {time.perf_counter()-t_to:.3f}s")

    # ---- Create windows
    t_unfold = time.perf_counter()
    windows = x.unfold(0, lags + 1, 1)   # (M, lags+1)
    if verbose: print(f"  unfolded windows in {time.perf_counter()-t_unfold:.3f}s")
    M = windows.shape[0]
    if M == 0:
        if verbose: print("No training windows available.")
        return None, None

    # ---- Precompute once: base features/targets, then AR flip once if needed
    X_base = windows[:, :lags]                                              # (M, lags)
    y_all  = windows[:, -1].to(dtype=train_dtype, device=DEVICE)            # (M,)
    if mtype == 'arnn':
        X_all = torch.flip(X_base, dims=[1]).to(dtype=train_dtype, device=DEVICE)
    else:
        X_all = X_base.to(dtype=train_dtype, device=DEVICE)

    # ---- Fast path: ARNN linear case -> closed-form solve (uses precomputed X_all/y_all)
    if mtype == 'arnn' and nn_params.get("hidden_size", 32) <= 0:
        if verbose: print("Using closed-form linear AR (OLS/Ridge).")
        linear = model.net  # nn.Linear(lags, 1, bias=bias_flag)
        has_bias = (isinstance(linear, torch.nn.Linear) and linear.bias is not None)

        X_design = X_all if not has_bias else torch.cat(
            [X_all, torch.ones((M, 1), dtype=train_dtype, device=DEVICE)], dim=1
        )

        lam = float(nn_params.get("ridge_lambda", 1e-6))
        Xt = X_design.transpose(0, 1)
        XtX = Xt @ X_design
        if lam > 0:
            p = XtX.shape[0]
            XtX = XtX + lam * torch.eye(p, dtype=train_dtype, device=DEVICE)
        Xty = Xt @ y_all

        try:
            w = torch.linalg.solve(XtX, Xty)
        except RuntimeError:
            w = torch.linalg.pinv(X_design) @ y_all

        if has_bias:
            linear.weight.data.copy_(w[:-1].view(1, -1))
            linear.bias.data.copy_(w[-1].view_as(linear.bias))
        else:
            linear.weight.data.copy_(w.view(1, -1))

        last_ctx = x[-lags:]
        preds_future = _roll_predict_sequence(
            model, last_context=last_ctx, steps=samples_to_predict, flip_input=(mtype == 'arnn')
        )
        return model.state_dict(), preds_future

    # ---- Otherwise: standard training loop (ARNN deep / TCN)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.MSELoss()

    # Probe first forward (no grad) using precomputed X_all
    if verbose and M > 0:
        t_fwd = time.perf_counter()
        with torch.no_grad():
            _ = model(X_all[:min(64, M)])
        if verbose: print(f"  first forward in {time.perf_counter()-t_fwd:.3f}s")

    # Train with larger batches & fewer loops
    effective_bs = min(batch_size, M)
    for ep in range(1, epochs + 1):
        epoch_loss, count = 0.0, 0
        model.train()
        indices = torch.randperm(M, device=X_all.device) if shuffle \
                  else torch.arange(M, device=X_all.device)
        for i in range(0, M, effective_bs):
            batch_indices = indices[i:i+effective_bs]
            Xb = X_all[batch_indices]
            yb = y_all[batch_indices]

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
            print(f"Epoch {ep}/{epochs}, Loss: {epoch_loss / max(count, 1):.6f}")

    # ---- Roll-out
    last_ctx = x[-lags:]
    preds_future = _roll_predict_sequence(
        model, last_context=last_ctx, steps=samples_to_predict, flip_input=(mtype == 'arnn')
    )

    return model.state_dict(), preds_future




# ===== Orchestrator =====
# def process_audio_files(
#     audio_files: list,
#     base_path: Union[str, Path],
#     model_type: str = 'arnn',
#     max_lags: int = 10,
#     samples_to_predict: int = 100,
#     target_sr: Optional[int] = None,
#     mono_mode: str = "first",
#     max_duration_s: Optional[float] = None,
#     verbose: bool = True,
#     nn_params: Dict[str, Any] = {},
#     nn_epochs: int = 5,
#     nn_batch_size: int = 8192,
#     nn_lr: float = 1e-2,
#     nn_weight_decay: float = 0.0,
#     nn_grad_clip: float = 1.0,
#     do_prewhitening_check: bool = True,
# ) -> Dict[str, Any]:
#     """Processes audio files using a configurable sequence model ('arnn' or 'tcn')."""
#     base_path = Path(base_path)
#     results: Dict[str, Any] = {}

#     if verbose:
#         print(f"\nProcessing {len(audio_files)} audio files with model_type='{model_type}'...")

#     for i, file_name in enumerate(audio_files, 1):
#         file_path = base_path / file_name
#         if verbose:
#             print(f"\n[{i}/{len(audio_files)}] {file_name}")

#         if not file_path.is_file():
#             if verbose: print(f"↪️  Skipping missing file: {file_path}")
#             results[file_name] = {"success": False, "error": f"File not found: {file_path}"}
#             continue

#         t0 = time.perf_counter()
#         try:
#             waveform, sr = read_wav(file_path, target_sr=target_sr, max_duration_s=max_duration_s, mono_mode=mono_mode)
#             item: Dict[str, Any] = {"success": True, "sample_rate": sr, "duration": waveform.shape[1] / sr}
            
#             if do_prewhitening_check:
#                 item["prewhitening"] = prewhitening_check(waveform[0], sr, verbose=verbose)

#             nn_state, nn_preds = fit_sequence_model(
#                 waveform, model_type=model_type, lags=max_lags,
#                 samples_to_predict=samples_to_predict, nn_params=nn_params,
#                 epochs=nn_epochs, batch_size=nn_batch_size, lr=nn_lr,
#                 weight_decay=nn_weight_decay, grad_clip=nn_grad_clip, verbose=verbose
#             )

#             if nn_state is not None:
#                 flat_params = np.concatenate([v.detach().cpu().numpy().ravel() for v in nn_state.values()])
#                 item["nn_model"] = {
#                     "model_type": model_type,
#                     "lags": max_lags,
#                     "predictions": nn_preds,
#                     "hyperparams": nn_params,
#                     "flat_params": flat_params,
#                 }
#             else:
#                 item["success"] = False
#                 item["error"] = f"{model_type.upper()} training failed"

#             item["time_sec"] = time.perf_counter() - t0
#             results[file_name] = item
#             if verbose: print(f"✓ Done: {file_name} | time={item['time_sec']:.2f}s")

#         except Exception as e:
#             results[file_name] = {"success": False, "error": str(e), "time_sec": time.perf_counter() - t0}
#             if verbose: print(f"✗ Failed: {file_name}: {e}")
#         finally:
#             gc.collect()

#     successful = sum(1 for r in results.values() if r.get("success", False))
#     if verbose: print(f"\n📊 Summary: {successful}/{len(audio_files)} files processed successfully.")
#     return results
def process_audio_files(
    audio_files: list,
    base_path: Union[str, Path],
    model_type: str = 'arnn',
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
    """Process audio files using an ARNN/TCN sequence model."""
    if nn_params is None:
        nn_params = {}

    base_path = Path(base_path)
    results: Dict[str, Any] = {}

    if verbose:
        print(f"\nProcessing {len(audio_files)} audio files with model_type='{model_type}'...")

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

            nn_state, nn_preds = fit_sequence_model(
                waveform, model_type=model_type, lags=max_lags,
                samples_to_predict=samples_to_predict, nn_params=nn_params,
                epochs=nn_epochs, batch_size=nn_batch_size, lr=nn_lr,
                weight_decay=nn_weight_decay, grad_clip=nn_grad_clip, verbose=verbose
            )

            if nn_state is not None:
                flat_params = np.concatenate([v.detach().cpu().numpy().ravel() for v in nn_state.values()])
                item["nn_model"] = {
                    "model_type": model_type,
                    "lags": max_lags,
                    "predictions": nn_preds,
                    "hyperparams": nn_params,
                    "flat_params": flat_params,
                }
            else:
                item["success"] = False
                item["error"] = f"{model_type.upper()} training failed"

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
    Construye la matriz de características X (n_files x d) a partir de 'results'.
    Por defecto usa 'predictions' (longitud fija). Si usas 'flat_params', puedes
    fijar target_dim para zero-pad/recortar y así uniformar dimensiones.
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
        raise RuntimeError("No se construyó ninguna característica. Revisa 'results'.")
    X = np.vstack(feats)  # (n_files, d)
    return names, X


def _pca_svd(X: np.ndarray, k: int = 2) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    PCA mediante SVD (centrado). Devuelve (Z, comps, var_exp):
      - Z: proyección en k dimensiones (n_files, k)
      - comps: vectores propios (k, d)
      - var_exp: varianza explicada por componente (k,)
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
    Guarda un CSV con columnas: file_name, pc1, pc2[, pc3], más varianza explicada en encabezado.
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
    print(f"📁 PCA guardado en: {out_csv} | Var. explicada: {', '.join([f'{v*100:.2f}% ' for v in var_exp])}")


def plot_pca_scatter(names: List[str], Z: np.ndarray, var_exp: np.ndarray, out_png: Union[str, Path]) -> None:
    """
    Dibuja y guarda un scatter 2D/3D de la PCA si Matplotlib está disponible.
    No define colores explícitos.
    """
    if not MATPLOTLIB_AVAILABLE:
        print("ℹ️ Matplotlib no disponible: se omite el gráfico.")
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
        print(f"🖼️ Scatter 3D PCA guardado en: {out_png}")
    else:
        print("Z debe tener 2 o 3 columnas para graficar.")

# ===== Clustering utilities (KMeans on PCA coords) =====
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
        print(f"📁 Clusters guardados en: {out_csv}")

    # --- Plot with centroids (if matplotlib available) ---
    if out_png and MATPLOTLIB_AVAILABLE:
        import matplotlib.pyplot as plt
        if Z.shape[1] == 2:
            plt.figure()
            plt.scatter(Z[:, 0], Z[:, 1], c=labels, cmap="tab10", alpha=0.7)
            plt.scatter(centroids[:, 0], centroids[:, 1], marker="*", c="black", s=200, label="Centroides")
            for i, name in enumerate(names):
                plt.annotate(name, (Z[i, 0], Z[i, 1]), fontsize=8)
            plt.xlabel("PC1"); plt.ylabel("PC2")
            plt.title(f"KMeans (k={k}), inertia={inertia:.2f}")
            plt.legend(); plt.tight_layout()
            plt.savefig(out_png, dpi=150); plt.close()
            print(f"🖼️ Scatter clusters guardado en: {out_png}")
        elif Z.shape[1] == 3:
            from mpl_toolkits.mplot3d import Axes3D  # noqa
            fig = plt.figure(); ax = fig.add_subplot(111, projection='3d')
            ax.scatter(Z[:, 0], Z[:, 1], Z[:, 2], c=labels, cmap="tab10", alpha=0.7)
            ax.scatter(centroids[:, 0], centroids[:, 1], centroids[:, 2], marker="*", c="black", s=300, label="Centroides")
            for i, name in enumerate(names):
                ax.text(Z[i, 0], Z[i, 1], Z[i, 2], name, fontsize=8)
            ax.set_xlabel("PC1"); ax.set_ylabel("PC2"); ax.set_zlabel("PC3")
            ax.set_title(f"KMeans (k={k}), inertia={inertia:.2f}")
            ax.legend(); plt.tight_layout()
            fig.savefig(out_png, dpi=150); plt.close(fig)
            print(f"🖼️ Scatter 3D clusters guardado en: {out_png}")

    return {"labels": labels, "inertia": inertia, "centroids": centroids}


# ===== Main Execution Block =====
if __name__ == "__main__":
    start_time = time.time()
    base_path = Path("CommRad_Dataset/COBRAMR-678")  # carpeta con .wav
    
    # --- Elegir modelo: 'tcn' o 'arnn' ---
    model_to_run = 'tcn'
    
    if not base_path.exists():
        print(f"❌ Base path does not exist: {base_path}")
        print("Please create the directory and add some .wav files.")
    else:
        # Toma hasta 5 audios para una corrida rápida (ajusta si deseas)
        audio_files = [p.name for p in base_path.glob("*.wav")][:5]
        
        if not audio_files:
            print(f"❌ No .wav files found in {base_path}")
        else:
            # --- Configuración según modelo ---
            if model_to_run == 'tcn':
                print("--- Configuring TCN Model (light) ---")
                nn_config = {
                    "model_type": 'tcn',
                    "max_lags": 128,   # baja a 64 si quieres aún más rápido
                    "nn_params": {
                        "channels": [16, 32],
                        "kernel_size": 3,
                        "dropout_rate": 0.1,
                    },
                    "nn_epochs": 5,
                    "nn_batch_size": 512,
                    "nn_lr": 1e-3
                }
            elif model_to_run == 'arnn':
                print("--- Configuring Deep ARNN Model ---")
                nn_config = {
                    "model_type": 'arnn',
                    "max_lags": 40,
                    "nn_params": {
                        "hidden_size": 128,
                        "num_hidden_layers": 3,
                        "activation_fn": 'gelu',
                        "dropout_rate": 0.15,
                    },
                    "nn_epochs": 10,
                    "nn_batch_size": 4096,
                    "nn_lr": 1e-3
                }
            else:
                raise ValueError("model_to_run debe ser 'tcn' o 'arnn'")
            
            # --- Ejecutar pipeline principal ---
            results = process_audio_files(
                audio_files,
                base_path=base_path,
                max_duration_s=10.0,   # recorta a 10s por archivo
                **nn_config
            )

            # --- Directorio de salida ---
            out_dir = base_path / "model_outputs"
            out_dir.mkdir(parents=True, exist_ok=True)

            # --- Guardar traza de parámetros del modelo ---
            params_csv = out_dir / f"{model_to_run}_params_trace.csv"
            save_ar_params_csv(results, params_csv)
            

            # --- PCA usando predicciones como embedding ---
            try:
                # Construir matriz de características (n_archivos x samples_to_predict)
                names, X = _feature_matrix_from_results(results, feature="predictions")

                # PCA 2D
                Z2, comps2, var_exp2 = _pca_svd(X, k=2)
                pca_csv2 = out_dir / f"{model_to_run}_pca_predictions_2d.csv"
                save_pca_csv(names, Z2, var_exp2, pca_csv2)
                plot_pca_scatter(names, Z2, var_exp2, out_dir / f"{model_to_run}_pca_predictions_2d.png")

                # PCA 3D (opcional)
                Z3, comps3, var_exp3 = _pca_svd(X, k=3)
                pca_csv3 = out_dir / f"{model_to_run}_pca_predictions_3d.csv"
                save_pca_csv(names, Z3, var_exp3, pca_csv3)
                plot_pca_scatter(names, Z3, var_exp3, out_dir / f"{model_to_run}_pca_predictions_3d.png")

                # --- Clustering KMeans sobre la proyección 2D (k seguro) ---
                try:
                    n_samples = Z2.shape[0]
                    if n_samples < 2:
                        print("⚠️ No hay suficientes muestras para clustering (se requieren ≥ 2).")
                    else:
                        # límite superior por muestras y por puntos distintos
                        n_distinct = np.unique(Z2, axis=0).shape[0]
                        if n_distinct < 2:
                            print("⚠️ Menos de 2 puntos distintos en Z2: no es posible clusterizar.")
                        else:
                            max_k = min(4, n_samples, n_distinct)
                            for k in range(2, max_k + 1):
                                out_csv_k = out_dir / f"{model_to_run}_clusters_k{k}.csv"
                                out_png_k = out_dir / f"{model_to_run}_clusters_k{k}.png"
                                if not SKLEARN_AVAILABLE:
                                    raise RuntimeError("scikit-learn not available; install scikit-learn to run KMeans.")
                                run_kmeans(Z2, names, n_clusters=k, out_csv=out_csv_k, out_png=out_png_k)
                except Exception as e:
                    print(f"⚠️ Clustering falló: {e}")


            except Exception as e:
                print(f"⚠️ PCA falló: {e}")

    elapsed_time = time.time() - start_time
    print(f"\n⏳ Total execution time: {elapsed_time:.2f} seconds")

