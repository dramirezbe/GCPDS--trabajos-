import os
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

# ===== Global numerical policy (single source of truth) =====
# Enforce CPU and high-precision numerics everywhere for consistency/reproducibility.
# Float64 improves stability of linear algebra (Cholesky, eigen-decompositions),
# and complex128 pairs naturally with float64 for eigendecomposition on companion matrices.
DEVICE = torch.device("cpu")
DTYPE = torch.float64
CDTYPE = torch.complex128  # complex dtype paired with DTYPE

# Optional dependencies (import softly so the pipeline remains usable with a subset)
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

# Plotting (optional)
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

# For clustering (optional, for PCA/KMeans visualization)
try:
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")


# -----------------------
# Simple global thread knobs (no per-thread env edits)
# -----------------------
def _set_global_threads():
    """Set conservative global thread counts for PyTorch to avoid oversubscription.

    We avoid touching process env vars or using per-thread mutation.
    - Use up to half of logical cores (>=1) for compute threads
    - Set interop threads to 1
    """
    try:
        # Conservative: cap to half logical cores (>=1), interop = 1
        torch.set_num_threads(max(1, (os.cpu_count() or 8) // 2))
        torch.set_num_interop_threads(1)
    except Exception:
        pass
_set_global_threads()


# -----------------------
# First-use numerics warm-up
# -----------------------
@torch.no_grad()
def _warmup_numerics():
    """Touch common linear-algebra and FFT kernels once to amortize JIT/allocator overhead.

    This makes the first real call later less bursty in latency-sensitive contexts.
    """
    a = torch.randn(8192, dtype=DTYPE, device=DEVICE)
    _ = torch.fft.rfft(a)
    M = torch.randn(8, 8, dtype=DTYPE, device=DEVICE)
    G = M.T @ M + 1e-6 * torch.eye(8, dtype=DTYPE, device=DEVICE)
    L = torch.linalg.cholesky(G)
    _ = torch.cholesky_solve(torch.randn(8, 1, dtype=DTYPE, device=DEVICE), L)
    C = torch.zeros((4, 4), dtype=CDTYPE, device=DEVICE)
    C[0, :] = torch.rand(4, dtype=DTYPE, device=DEVICE).to(CDTYPE)
    for i in range(1, 4):
        C[i, i - 1] = 1
    _ = torch.linalg.eig(C)


# -----------------------
# File presence guard
# -----------------------
def _filter_existing_files(audio_files: list, base_path: Union[str, Path]):
    """Split a list of file names into (existing, missing) under a base path."""
    base = Path(base_path)
    existing, missing = [], []
    for fn in audio_files:
        fp = base / fn
        if fp.is_file():
            existing.append(fn)
        else:
            missing.append(fn)
    return existing, missing


# -----------------------
# Memory-savvy utilities
# -----------------------
def _pick_channel_inplace(waveform: torch.Tensor, mode: str = "first") -> torch.Tensor:
    """Select mono channel view without extra allocation when possible.

    Args:
        waveform: Tensor of shape (channels, samples).
        mode: "first" (default) or "mean" across channels.
    Returns:
        (1, samples) tensor.
    """
    if waveform.ndim != 2:
        raise ValueError(f"Expected (channels, samples), got {tuple(waveform.shape)}")
    if waveform.size(0) == 1 or mode == "first":
        return waveform.narrow(0, 0, 1)
    return waveform.mean(dim=0, keepdim=True)


def _int_normalize_inplace(x: torch.Tensor) -> torch.Tensor:

    """Convert integer PCM → float64 in [-1, 1] (in-place where reasonable).

    Handles common integer formats; falls back to range derived from dtype limits.
    Keeps result on global DEVICE and DTYPE.
    """
    if x.dtype.is_floating_point:
        return x.to(dtype=DTYPE, device=DEVICE)

    if x.dtype == torch.int16:
        x = x.to(dtype=DTYPE, device=DEVICE).div_(32768.0)
    elif x.dtype == torch.int32:
        x = x.to(dtype=DTYPE, device=DEVICE).div_(2147483648.0)
    elif x.dtype == torch.uint8:
        x = x.to(dtype=DTYPE, device=DEVICE).sub_(128.0).div_(128.0)
    else:
        info = torch.iinfo(x.dtype)
        denom = float(max(abs(info.min), abs(info.max)))
        x = x.to(dtype=DTYPE, device=DEVICE).div_(denom)

    return x.clamp_(-1.0, 1.0)


def _cheap_decimate_if_integer_ratio(
    waveform: torch.Tensor, sr: int, target_sr: Optional[int]
) -> Tuple[torch.Tensor, int]:
    """Downsample by exact integer factor via stride if sr % target_sr == 0.

    Fast, alias-prone if high-frequency energy exists; upstream caller should
    check whiteness/aliasing risk before using aggressive decimation.
    """
    if target_sr is None or sr == target_sr:
        return waveform, sr
    if target_sr > sr:
        return waveform, sr
    if sr % target_sr != 0:
        return waveform, sr
    factor = sr // target_sr
    decimated = waveform[..., ::factor].contiguous()
    return decimated, target_sr


def _resample_if_needed(
    waveform: torch.Tensor,
    sr: int,
    target_sr: Optional[int],
    allow_integer_decimation: bool = True
) -> Tuple[torch.Tensor, int]:
    """Resample to target SR using torchaudio if available, else integer decimation.

    Returns original if target_sr is None, equals sr, or no backend is available.
    """
    if target_sr is None or sr == target_sr:
        return waveform, sr

    if allow_integer_decimation:
        wf2, sr2 = _cheap_decimate_if_integer_ratio(waveform, sr, target_sr)
        if sr2 == target_sr:
            return wf2, sr2

    if torchaudio is not None:
        try:
            return torchaudio.functional.resample(waveform, sr, target_sr), target_sr
        except Exception as e:
            warnings.warn(f"Resampling failed: {e}. Returning original audio at {sr} Hz.")
            return waveform, sr

    warnings.warn(f"Requested resample {sr}→{target_sr} Hz but no backend; keeping original.")
    return waveform, sr


def _load_audio_with_fallback(
    p: Path,
    target_sr: Optional[int],
    mono_mode: str,
    max_duration_s: Optional[float],
    verbose: bool,
) -> Tuple[torch.Tensor, int]:
    """Load audio via torchaudio → soundfile → scipy.io.wavfile fallback chain.

    Ensures return tensor is (channels, samples), float32 initially; resampling and
    mono selection are applied before returning.
    """
    # 1) torchaudio
    if torchaudio is not None:
        try:
            waveform, sr = torchaudio.load(str(p))  # float32 CPU
            if max_duration_s is not None:
                max_samples = int(sr * max_duration_s)
                waveform = waveform[..., :max_samples]
            waveform = _pick_channel_inplace(waveform, mode=mono_mode)
            waveform, sr = _resample_if_needed(waveform, sr, target_sr)
            return waveform.contiguous(), sr
        except Exception as e:
            if verbose:
                warnings.warn(f"torchaudio.load failed for '{p.name}': {e}")

    # 2) soundfile
    if sf is not None:
        try:
            if max_duration_s is None:
                data, sr = sf.read(str(p), dtype="float32", always_2d=True)
            else:
                with sf.SoundFile(str(p), "r") as f:
                    sr = f.samplerate
                    frames = min(int(sr * max_duration_s), len(f))
                    data = f.read(frames=frames, dtype="float32", always_2d=True)
            waveform = torch.from_numpy(np.ascontiguousarray(data.T))
            waveform = _pick_channel_inplace(waveform, mode=mono_mode)
            waveform, sr = _resample_if_needed(waveform, sr, target_sr)
            return waveform.contiguous(), sr
        except Exception as e:
            if verbose:
                warnings.warn(f"soundfile failed for '{p.name}': {e}")

    # 3) SciPy WAV (mmap)
    if scipy_wav is not None and p.suffix.lower() == ".wav":
        try:
            sr, data = scipy_wav.read(str(p), mmap=True)
            if max_duration_s is not None:
                max_samples = int(sr * max_duration_s)
                data = data[:max_samples, ...] if data.ndim == 2 else data[:max_samples]
            if data.ndim == 1:
                t = torch.from_numpy(np.asarray(data))
                t = _int_normalize_inplace(t).unsqueeze(0)
            else:
                t = torch.from_numpy(np.asarray(data))
                t = _int_normalize_inplace(t)
                t = t.t().contiguous()
            t = _pick_channel_inplace(t, mode=mono_mode)
            t, sr = _resample_if_needed(t, sr, target_sr)
            return t.contiguous(), sr
        except Exception as e:
            if verbose:
                warnings.warn(f"scipy.io.wavfile failed for '{p.name}': {e}")

    loaders = [
        f"torchaudio: {'✓' if torchaudio is not None else '✗'}",
        f"soundfile: {'✓' if sf is not None else '✗'}",
        f"scipy.io.wavfile: {'✓' if scipy_wav is not None else '✗'}",
    ]
    raise RuntimeError(
        f"Failed to load audio file: '{p}'\n"
        f"Available loaders:\n  • " + "\n  • ".join(loaders) +
        "\nInstall 'soundfile' for reliable loading: pip install soundfile"
    )


def read_wav(
    file_path: Union[str, Path],
    target_sr: Optional[int] = None,
    verbose: bool = True,
    mono_mode: str = "first",
    max_duration_s: Optional[float] = None,
) -> Tuple[torch.Tensor, int]:
    """High-level WAV reader that returns waveform on (DEVICE, DTYPE).

    Returns:
        waveform: Tensor (1, samples) float64 on CPU
        sample_rate: int
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: '{p}'")
    if not p.is_file():
        raise ValueError(f"Path is not a file: '{p}'")
    if not os.access(p, os.R_OK):
        raise PermissionError(f"File is not readable: '{p}'")

    waveform, sample_rate = _load_audio_with_fallback(
        p, target_sr=target_sr, mono_mode=mono_mode, max_duration_s=max_duration_s, verbose=verbose
    )

    # Normalize to global dtype/device for downstream consistency
    waveform = waveform.to(dtype=DTYPE, device=DEVICE).contiguous()

    if verbose:
        dur = waveform.shape[1] / sample_rate
        print(f"Sample rate: {sample_rate:,} Hz")
        print(f"Shape: {tuple(waveform.shape)} (channels, samples)")
        print(f"Duration: {dur:.3f} s")
        mn = float(waveform.min()); mx = float(waveform.max())
        print(f"Data range: [{mn:.3f}, {mx:.3f}]")

    return waveform, sample_rate

# ---------------------------------------------
# Spectral helpers & pre-whitening/aliasing check (low-mem)
# ---------------------------------------------
_WIN_CACHE: Dict[Tuple[int, str], torch.Tensor] = {}

@torch.no_grad()
def _get_window(M: int, kind: str = "hann") -> torch.Tensor:
    """Retrieve and cache window tensors on the global (DEVICE, DTYPE)."""
    key = (M, kind)
    w = _WIN_CACHE.get(key)
    if w is not None and w.dtype == DTYPE and w.device == DEVICE:
        return w
    if kind == "hann":
        w = torch.hann_window(M, dtype=DTYPE, periodic=True, device=DEVICE)
    elif kind == "hamming":
        w = torch.hamming_window(M, dtype=DTYPE, periodic=True, device=DEVICE)
    else:
        w = torch.ones(M, dtype=DTYPE, device=DEVICE)
    _WIN_CACHE[key] = w
    return w


@torch.no_grad()
def psd_torch(x: torch.Tensor, sr: int, n_fft: Optional[int] = None) -> Tuple[torch.Tensor, torch.Tensor]:
    """Single-shot periodogram (rFFT) power spectral density estimate.

    Returns (freqs, Pxx) with densities normalized by (n_fft * sr).
    """
    if x.ndim != 1:
        raise ValueError("psd_torch expects a 1-D tensor")
    x = x.to(dtype=DTYPE, device=DEVICE)
    if n_fft is None:
        n_fft = min(1 << (x.numel() - 1).bit_length(), 1 << 17)
    X = torch.fft.rfft(x, n=n_fft)
    Pxx = (X.abs() ** 2) / (n_fft * sr)
    try:
        freqs = torch.fft.rfftfreq(n_fft, d=1.0 / sr).to(dtype=DTYPE, device=DEVICE)
    except AttributeError:
        freqs = torch.linspace(0, sr / 2, steps=X.numel(), dtype=DTYPE, device=DEVICE)
    return freqs, Pxx.to(dtype=DTYPE)


@torch.no_grad()
def welch_psd_torch(
    x: torch.Tensor,
    sr: int,
    *,
    seglen: Optional[int] = None,
    noverlap: Optional[int] = None,
    n_fft: Optional[int] = None,
    window: str = "hann",
    detrend: bool = True,
    avg: str = "mean",          # "mean" or "median"
    block_windows: int = 32,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Welch PSD with block processing to keep memory bound small.

    - Detrends by mean subtraction if requested
    - Supports mean/median aggregation across segments
    - Uses cached window and explicit normalization U = sum(w^2)
    """
    x = x.to(dtype=DTYPE, device=DEVICE)
    N = x.numel()
    if N == 0:
        return torch.empty(0, dtype=DTYPE, device=DEVICE), torch.empty(0, dtype=DTYPE, device=DEVICE)
    if detrend:
        x = x - x.mean()

    if seglen is None:
        seglen = min(8192, N)
        seglen = 1 << (seglen - 1).bit_length()
        seglen = min(seglen, N)
    if seglen <= 1:
        return torch.empty(0, dtype=DTYPE, device=DEVICE), torch.empty(0, dtype=DTYPE, device=DEVICE)

    if noverlap is None:
        noverlap = seglen // 2
    step = max(1, seglen - noverlap)
    if n_fft is None:
        n_fft = seglen

    windows = x.unfold(0, seglen, step)  # (K, seglen)
    K = int(windows.shape[0])
    if K == 0:
        return psd_torch(x, sr, n_fft=n_fft)

    w = _get_window(seglen, kind=window)
    U = (w * w).sum()

    acc = None
    meds = []

    for start in range(0, K, block_windows):
        end = min(start + block_windows, K)
        Wb = windows[start:end].contiguous()
        Xb = torch.fft.rfft(Wb * w, n=n_fft, dim=1)
        Pxx_b = (Xb.abs() ** 2) / (U * sr)  # density per segment
        # Double energy of non-DC/non-Nyquist bins to convert to one-sided PSD
        if n_fft % 2 == 0:
            Pxx_b[:, 1:-1] *= 2.0
        else:
            Pxx_b[:, 1:] *= 2.0

        if avg == "median":
            meds.append(Pxx_b.median(dim=0).values)
        else:
            s = Pxx_b.sum(dim=0)
            acc = s if acc is None else (acc + s)

        del Wb, Xb, Pxx_b

    if avg == "median":
        Pxx = torch.stack(meds, dim=0).median(dim=0).values
    else:
        Pxx = acc / K

    freqs = torch.fft.rfftfreq(n_fft, d=1.0 / sr).to(dtype=DTYPE, device=DEVICE)
    return freqs, Pxx.to(dtype=DTYPE, device=DEVICE)


@torch.no_grad()
def spectral_flatness(Pxx: torch.Tensor, eps: float = 1e-18) -> float:
    """Geometric/Arithmetic mean ratio of spectrum; 1≈white, 0≈tonal."""
    gm = torch.exp(torch.mean(torch.log(Pxx.to(dtype=DTYPE, device=DEVICE) + eps)))
    am = torch.mean(Pxx.to(dtype=DTYPE, device=DEVICE) + eps)
    return float((gm / am).clamp_min(0.0).clamp_max(1.0).item())


@torch.no_grad()
def spectral_flatness_bandlimited(
    freqs: torch.Tensor,
    Pxx: torch.Tensor,
    f_lo_ratio: float = 0.02,
    f_hi_ratio: float = 0.98,
    trim: float = 0.0,
    eps: float = 1e-18
) -> float:
    """Band-limit SFM to avoid DC/Nyquist artifacts and optionally trim tails."""
    freqs = freqs.to(dtype=DTYPE, device=DEVICE)
    Pxx = Pxx.to(dtype=DTYPE, device=DEVICE)
    if freqs.numel() == 0:
        return 0.0
    fmax = float(freqs[-1].item())
    f_lo = f_lo_ratio * fmax
    f_hi = f_hi_ratio * fmax
    band = (freqs >= f_lo) & (freqs <= f_hi)
    p = Pxx[band]
    if p.numel() == 0:
        p = Pxx
    if trim > 0 and p.numel() > 10:
        k = int(trim * p.numel())
        p = torch.sort(p).values[k: p.numel() - k]
    gm = torch.exp(torch.mean(torch.log(p + eps)))
    am = torch.mean(p + eps)
    return float((gm / am).clamp(0.0, 1.0).item())


@torch.no_grad()
def acf_torch(x: torch.Tensor, max_lag: int) -> torch.Tensor:
    """Unbiased (by denominator) normalized autocorrelation up to max_lag."""
    x = x.to(dtype=DTYPE, device=DEVICE)
    x = x - x.mean()
    denom = torch.sum(x * x) + 1e-18
    ac = [torch.tensor(1.0, dtype=DTYPE, device=DEVICE)]
    for k in range(1, max_lag + 1):
        ac.append(torch.dot(x[:-k], x[k:]) / denom)
    return torch.stack(ac, dim=0)


@torch.no_grad()
def ljung_box_q(acf: torch.Tensor, n: int, m: int) -> float:
    """Compute Ljung–Box Q statistic from ACF(1..m) to test whiteness."""
    ks = torch.arange(1, m + 1, dtype=DTYPE, device=DEVICE)
    Q = n * (n + 2) * torch.sum((acf[1:m+1].to(dtype=DTYPE, device=DEVICE) ** 2) / (n - ks))
    return float(Q.item())


@torch.no_grad()
def alias_fraction_from_psd(freqs: torch.Tensor, Pxx: torch.Tensor, sr: int, factor: int) -> float:
    """Fraction of spectral energy above the new Nyquist if downsampling by `factor`."""
    if factor <= 1:
        return 0.0
    freqs = freqs.to(dtype=DTYPE, device=DEVICE)
    Pxx = Pxx.to(dtype=DTYPE, device=DEVICE)
    new_nyq = sr / (2.0 * factor)
    m = freqs > new_nyq
    num = float(Pxx[m].sum().item())
    den = float(Pxx.sum().item()) + 1e-24
    return num / den


@torch.no_grad()
def decimation_aliasing_risk(x: torch.Tensor, sr: int, factor: int, n_fft: Optional[int] = None) -> float:
    """Shortcut: compute aliasing fraction for a raw 1-D signal."""
    if factor <= 1:
        return 0.0
    freqs, Pxx = psd_torch(x, sr, n_fft=n_fft)
    return alias_fraction_from_psd(freqs, Pxx, sr, factor)


@torch.no_grad()
def prewhitening_check(x: torch.Tensor, sr: int, candidate_factors: List[int] = [2, 3, 4], verbose: bool = True) -> Dict[str, Any]:
    """Assess whether the signal is near-white and safe to decimate.

    Combines: Welch PSD, band-limited spectral flatness, Ljung–Box Q, and
    aliasing fraction for candidate integer downsampling factors.
    """
    x = x.detach().to(dtype=DTYPE, device=DEVICE)
    x_eval = x[-131072:] if x.numel() > 131072 else x

    freqs, Pxx = welch_psd_torch(
        x_eval, sr,
        seglen=min(8192, x_eval.numel()),
        noverlap=None,
        n_fft=None,
        window="hann",
        detrend=True,
        avg="mean",
        block_windows=32
    )

    sfm = spectral_flatness_bandlimited(freqs, Pxx, f_lo_ratio=0.02, f_hi_ratio=0.98, trim=0.0)

    n = x_eval.numel()
    max_lag = min(40, max(10, n // 50))
    ac = acf_torch(x_eval, max_lag=max_lag)
    Q = ljung_box_q(ac, n=n, m=min(20, max_lag))

    alias = {f: alias_fraction_from_psd(freqs, Pxx, sr, f) for f in candidate_factors}

    suggestion = "No decimation (insufficient whiteness)"
    safe = [f for f, frac in alias.items() if frac < 0.02]
    if sfm > 0.6 and len(safe) > 0:
        suggestion = f"Integer decimation by {max(safe)} OK (SFM={sfm:.2f})"

    if verbose:
        print(f"Spectral Flatness (band-limited Welch): {sfm:.3f} (≈1 is white)")
        print(f"Ljung-Box Q: {Q:.2f} (larger suggests non-white)")
        for f, frac in alias.items():
            print(f"Aliasing fraction at factor {f}: {100*frac:.3f}%")
        print(f"Suggestion: {suggestion}")

    return {
        "sfm": sfm,
        "ljung_box_Q": Q,
        "aliasing_fraction": {int(k): float(v) for k, v in alias.items()},
        "suggestion": suggestion,
    }


# -----------------------
# Reverse-index cache
# -----------------------
_REV_IDX: Dict[int, torch.Tensor] = {}
@torch.no_grad()
def _rev_idx(P: int) -> torch.Tensor:
    """Return cached reverse index [P-1,..,0] to avoid reallocations in folds."""
    t = _REV_IDX.get(P)
    if t is None:
        t = torch.arange(P - 1, -1, -1, dtype=torch.long, device=DEVICE)
        _REV_IDX[P] = t
    return t


# -----------------------
# Vectorized linear AR forecasting (companion eigen)
# -----------------------
@torch.no_grad()
def _build_companion(params64: torch.Tensor) -> torch.Tensor:
    """Construct the AR(P) companion matrix in complex128 for eigen methods."""
    P = int(params64.numel())
    C = torch.zeros((P, P), dtype=CDTYPE, device=DEVICE)
    C[0, :P] = params64.to(CDTYPE)
    for i in range(1, P):
        C[i, i-1] = 1.0
    return C


@torch.no_grad()
def eigen_forecast_ar(params: torch.Tensor, last_ctx: torch.Tensor, steps: int) -> torch.Tensor:
    """Closed-form AR forecast y_{t+h} using eigendecomposition of companion matrix.

    Args:
        params: AR coefficients (most-recent-first) length P; accepts NumPy or Tensor.
        last_ctx: last P samples (1-D); accepts NumPy or Tensor.
        steps: number of future steps to forecast (>=0).
    Returns:
        Tensor[steps] on (DEVICE, DTYPE).
    """
    if not isinstance(params, torch.Tensor):
        params = torch.as_tensor(params, dtype=DTYPE, device=DEVICE)
    else:
        params = params.to(dtype=DTYPE, device=DEVICE)

    if not isinstance(last_ctx, torch.Tensor):
        last_ctx = torch.as_tensor(last_ctx, dtype=DTYPE, device=DEVICE)
    else:
        last_ctx = last_ctx.to(dtype=DTYPE, device=DEVICE)

    P = int(params.numel())
    if steps <= 0:
        return torch.zeros((0,), dtype=DTYPE, device=DEVICE)

    ctx_mrf = torch.flip(last_ctx, dims=[0]).to(CDTYPE)
    C = _build_companion(params)
    eigvals, V = torch.linalg.eig(C)
    c = torch.linalg.solve(V, ctx_mrf)
    alpha = V[0, :]

    h = torch.arange(1, steps + 1, dtype=DTYPE, device=DEVICE)
    lam_h = eigvals.unsqueeze(0) ** h.unsqueeze(1)
    y_h = (alpha * (lam_h * c)).sum(dim=1).real
    return y_h.to(dtype=DTYPE, device=DEVICE)


# -----------------------
# Low-memory AR(P) (Gram accumulation + Cholesky)
# -----------------------
@torch.no_grad()
def _ar_blockwise_gram_b(x64: torch.Tensor, P: int, block: int = 200_000) -> Tuple[torch.Tensor, torch.Tensor, int]:
    """Accumulate normal equations G=X^T X and b=X^T y for AR(P) in blocks.

    Windows shape: (M, P+1) where last column is y and first P columns are lags.
    """
    N = x64.numel()
    M = N - P
    if M <= 0:
        return torch.zeros((P, P), dtype=DTYPE, device=DEVICE), torch.zeros(P, dtype=DTYPE, device=DEVICE), 0

    windows = x64.unfold(0, P + 1, 1)
    G = torch.zeros((P, P), dtype=DTYPE, device=DEVICE)
    b = torch.zeros(P, dtype=DTYPE, device=DEVICE)

    idx = _rev_idx(P)
    for start in range(0, M, block):
        end = min(start + block, M)
        Wb = windows[start:end]
        yb = Wb[:, -1]
        Xb = Wb[:, :-1].index_select(1, idx).contiguous()
        G += Xb.T @ Xb
        b += Xb.T @ yb
        del Wb, Xb, yb
        gc.collect()

    return G, b, M


@torch.no_grad()
def _ar_rss_from_params(x64: torch.Tensor, P: int, params64: torch.Tensor, block: int = 200_000, step: int = 1) -> Tuple[float, int]:
    """Compute residual sum of squares for given params with block evaluation."""
    N = x64.numel()
    N = x64.numel()
    M = N - P
    if M <= 0:
        return float("inf"), 0

    windows = x64.unfold(0, P + 1, 1)
    rss = 0.0
    idx = _rev_idx(P)
    for start in range(0, M, block * step):
        end = min(start + block * step, M)
        Wb = windows[start:end:step]
        yb = Wb[:, -1].contiguous()
        Xb = Wb[:, :-1].index_select(1, idx).contiguous()
        resid = yb - (Xb @ params64)
        rss += float((resid * resid).sum().item())
        del Wb, Xb, yb, resid
        gc.collect()

    return rss, (M + step - 1) // step


@torch.no_grad()
def fit_ar_closed_form_lowmem(
    waveform: torch.Tensor,
    P: int,
    samples_to_predict: int = 100,
    lambda_reg: float = 0.0,
    verbose: bool = True,
    block: Optional[int] = None,
    vectorized_forecast: bool = True,
) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor], Optional[float], Optional[float]]:
    """Estimate AR(P) coefficients by solving normal equations with Cholesky.

    Memory-frugal: builds Gram matrix and RHS in blocks, then solves once.
    Optionally performs vectorized multi-step forecasting via eigen method.
    Returns (params, preds, AICc, BIC) or (None, ... ) on failure.
    """
    try:
        x = waveform[0] if waveform.shape[0] == 1 else waveform.narrow(0, 0, 1)[0]
        x64 = x.detach().to(DEVICE, dtype=DTYPE)
        N = x64.numel()
        if N <= P + 1:
            if verbose:
                print("Not enough samples for the requested lags")
            return None, None, None, None

        if block is None:
            block = min(262_144, max(65_536, N // 10))

        G, b, M = _ar_blockwise_gram_b(x64, P, block=block)
        if M == 0:
            return None, None, None, None

        if lambda_reg and lambda_reg > 0.0:
            G = G + (lambda_reg * torch.eye(P, dtype=DTYPE, device=DEVICE))

        try:
            L = torch.linalg.cholesky(G)
            params = torch.cholesky_solve(b.unsqueeze(1), L).squeeze(1)
        except RuntimeError:
            jitter = (1e-8 * torch.trace(G) / max(P, 1)).item()
            G = G + jitter * torch.eye(P, dtype=DTYPE, device=DEVICE)
            try:
                L = torch.linalg.cholesky(G)
                params = torch.cholesky_solve(b.unsqueeze(1), L).squeeze(1)
            except RuntimeError:
                params = torch.linalg.solve(G, b)

        rss, n = _ar_rss_from_params(x64, P, params, block=block, step=1)

        k = P
        if rss <= 0.0:
            aicc = bic = float("inf")
        else:
            sigma2 = rss / n
            loglik = -0.5 * n * (np.log(2 * np.pi * sigma2) + 1.0)
            aic = -2.0 * loglik + 2.0 * k
            bic = -2.0 * loglik + np.log(n) * k
            aicc = aic + (2.0 * k * (k + 1.0)) / max(n - k - 1.0, 1.0)

        preds = None
        if samples_to_predict > 0:
            if vectorized_forecast:
                # Call the corrected function which now returns a tensor
                preds = eigen_forecast_ar(params, last_ctx=x64[-P:], steps=samples_to_predict)
            else:
                ctx_mrf = torch.flip(x64[-P:], dims=[0]).clone()
                preds_list = []
                for _ in range(samples_to_predict):
                    yhat = (ctx_mrf * params).sum().item()
                    preds_list.append(yhat)
                    ctx_mrf = torch.cat([torch.tensor([yhat], dtype=DTYPE, device=DEVICE), ctx_mrf[:-1]])
                # Return a PyTorch tensor
                preds = torch.tensor(preds_list, dtype=DTYPE, device=DEVICE)

        if verbose:
            np.set_printoptions(precision=9, suppress=False)
            print(f"[Low-mem AR] P={P} | N={N:,} | AICc={aicc:.3f} | BIC={bic:.3f}")
            if P <= 12:
                print("AR coeffs (most-recent-first):", params.detach().cpu().numpy())

        # Return PyTorch tensors
        return params, preds, float(aicc), float(bic)

    except Exception as e:
        if verbose:
            print(f"Error in low-mem AR fit: {e}")
        return None, None, None, None

# -----------------------
# Classical AR (statsmodels) — safe wrapper (small N)
# -----------------------
def fit_ar_model_statsmodels(
    waveform: torch.Tensor,
    P: int,
    samples_to_predict: int = 100,
    verbose: bool = True,
) -> Tuple[Optional[object], Optional[np.ndarray]]:
    """Reference AutoReg(P) using statsmodels (CPU, NumPy space).

    Limits: used only for smaller N (threshold controlled by caller).
    Returns fitted model and NumPy predictions (if requested).
    """
    if not STATSMODELS_AVAILABLE:
        return None, None
    try:
        x_np = (waveform[0] if waveform.shape[0] == 1 else waveform.narrow(0,0,1)[0]).detach().cpu().numpy()
        if verbose:
            print(f"[statsmodels] Fitting AR(P={P}) on {x_np.shape[0]:,} samples")
        model = AutoReg(x_np, lags=P, trend="n")
        model_fit = model.fit()
        start_idx = x_np.shape[0]
        end_idx = start_idx + samples_to_predict - 1
        preds = model_fit.predict(start=start_idx, end=end_idx)
        if verbose:
            print(f"AIC: {model_fit.aic:.3f}, BIC: {model_fit.bic:.3f}")
        return model_fit, preds
    except Exception as e:
        if verbose:
            print(f"statsmodels AR failed: {e}")
        return None, None


# -----------------------
# Yule–Walker + Levinson–Durbin (fast order sweep)
# -----------------------
@torch.no_grad()
def _acf_fft_1d(x64: torch.Tensor, Pmax: int) -> torch.Tensor:
    """Compute normalized autocorrelation via FFT convolution trick (O(n log n))."""
    n = int(x64.numel())
    m = 1 << (2 * n - 1).bit_length()
    X = torch.fft.rfft(x64, n=m)
    S = (X * X.conj()).real
    acf_full = torch.fft.irfft(S, n=m)[:n]
    r0 = acf_full[0].clamp_min(1e-18)
    acf_full = acf_full / r0
    return acf_full[: Pmax + 1].contiguous().to(dtype=DTYPE, device=DEVICE)


@torch.no_grad()
def _levinson_durbin_all_orders(r: torch.Tensor) -> List[Tuple[torch.Tensor, torch.Tensor]]:
    """Levinson–Durbin recursion returning (coeffs, error) for orders 1..Pmax."""
    Pmax = int(r.numel() - 1)
    a = torch.zeros(Pmax, dtype=DTYPE, device=DEVICE)
    E = r[0].clone()
    out = []
    for p in range(1, Pmax + 1):
        if p == 1:
            k = -r[1] / E
            a[0] = k
            E = E * (1 - k * k)
        else:
            k = -(r[p] + (a[:p-1] * r[1:p].flip(0)).sum()) / E
            a[:p-1] = a[:p-1] + k * a[:p-1].flip(0)
            a[p-1] = k
            E = E * (1 - k * k)
        out.append((a[:p].flip(0).clone(), E.clamp_min(1e-18)))
    return out


def select_ar_order_aicc_yw(
    waveform: torch.Tensor,
    P_min: int = 1,
    P_max: int = 20,
    verbose: bool = True,
    patience: int = 3,
) -> Dict[str, Any]:
    """Sweep AR order using Yule–Walker/Levinson–Durbin and choose by AICc.

    Early-stop once `patience` consecutive orders fail to improve best AICc past
    the current best order.
    """
    x = waveform[0] if waveform.shape[0] == 1 else waveform.narrow(0,0,1)[0]
    x64 = x.detach().to(DEVICE, dtype=DTYPE)
    N = int(x64.numel())
    if N <= P_min + 1:
        return {"records": [], "best": {"P": None, "AICc": float("inf"), "BIC": float("inf")}}

    r = _acf_fft_1d(x64 - x64.mean(), P_max)
    seq = _levinson_durbin_all_orders(r)

    records = []
    best = {"P": None, "AICc": float("inf"), "BIC": float("inf")}
    worse_in_a_row = 0
    for p in range(P_min, P_max + 1):
        a_p, E_p = seq[p - 1]
        n_eff = max(N - p, 1)
        sigma2 = float(E_p)
        loglik = -0.5 * n_eff * (np.log(2 * np.pi * sigma2) + 1.0)
        aic = -2.0 * loglik + 2.0 * p
        bic = -2.0 * loglik + np.log(n_eff) * p
        aicc = aic + (2.0 * p * (p + 1.0)) / max(n_eff - p - 1.0, 1.0)
        records.append((p, aicc, bic))
        if aicc < best["AICc"] - 1e-12:
            best = {"P": p, "AICc": aicc, "BIC": bic}
            worse_in_a_row = 0
        else:
            worse_in_a_row += 1
            if worse_in_a_row >= patience and (best["P"] is not None) and (p > best["P"]):
                if verbose:
                    print(f"[YW sweep] Early stop at P={p} (patience={patience})")
                break

    if verbose and records:
        print(f"[YW sweep] Evaluated P={records[0][0]}..{records[-1][0]} | Best by AICc: P={best['P']} (AICc={best['AICc']:.3f})")

    return {"records": records, "best": best}


# -----------------------
# Order selection via AICc (sequential; no per-thread env tweaks)
# -----------------------
def select_ar_order_aicc_lowmem(
    waveform: torch.Tensor,
    P_min: int = 1,
    P_max: int = 20,
    lambda_reg: float = 0.0,
    verbose: bool = True,
    block: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Alternate sweep using the low-memory closed-form fitter each order.
    Sequential sweep to avoid thread-related races. If you need parallelism,
    prefer process-level parallel outside this function.
    """
    x = waveform[0] if waveform.shape[0] == 1 else waveform.narrow(0,0,1)[0]
    N = int(x.numel())
    records = []
    best = {"P": None, "AICc": float("inf"), "BIC": float("inf")}

    Ps = [P for P in range(P_min, P_max + 1) if N > P + 1]
    for P in Ps:
        _, _, aicc, bic = fit_ar_closed_form_lowmem(
            waveform, P, samples_to_predict=0, lambda_reg=lambda_reg, verbose=False, block=block
        )
        if aicc is not None:
            records.append((P, aicc, bic))
            if aicc < best["AICc"]:
                best = {"P": P, "AICc": aicc, "BIC": bic}

    records.sort(key=lambda t: t[0])
    if verbose and records:
        print(f"[Order sweep] Evaluated P={records[0][0]}..{records[-1][0]} | Best by AICc: P={best['P']} (AICc={best['AICc']:.3f})")
    return {"records": records, "best": best}


# -----------------------
# AR Neural Network (PyTorch) — CPU-only, consistent dtype
# -----------------------
class ARNN(torch.nn.Module):
    """A tiny AR-NN: either exact linear AR or a 1-hidden-layer MLP.

    - If hidden_size == 0: exactly a Linear(lags, 1) layer (optionally initialized
      from the closed-form solution for faster convergence and traceability).
    - If hidden_size > 0: Linear → ReLU → Linear.
    """
    def __init__(self, lags: int, hidden_size: int = 0, bias: bool = False, dtype: torch.dtype = DTYPE):
        super().__init__()
        self.lags = lags
        self.hidden_size = hidden_size
        self.bias = bias
        if hidden_size > 0:
            self.net = torch.nn.Sequential(
                torch.nn.Linear(lags, hidden_size, bias=True, dtype=dtype, device=DEVICE),
                torch.nn.ReLU(),
                torch.nn.Linear(hidden_size, 1, bias=True, dtype=dtype, device=DEVICE),
            )
        else:
            self.net = torch.nn.Linear(lags, 1, bias=bias, dtype=dtype, device=DEVICE)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)
    
@torch.no_grad()
def _roll_predict(model: ARNN, last_context: torch.Tensor, steps: int) -> np.ndarray:
    """Iteratively roll forecasts forward using the model in the time domain."""
    model.eval()
    ctx = torch.flip(last_context.to(dtype=DTYPE, device=DEVICE), dims=[0]).clone()
    preds = []
    for _ in range(steps):
        with torch.no_grad():
            y_hat_t = model(ctx.unsqueeze(0))
        y_hat = float(y_hat_t.item())
        preds.append(y_hat)
        ctx = torch.cat([torch.tensor([y_hat], dtype=DTYPE, device=DEVICE), ctx[:-1]], dim=0)
    return np.asarray(preds, dtype=np.float64)


def fit_ar_nn(
    waveform: torch.Tensor,
    lags: int = 10,
    samples_to_predict: int = 100,
    hidden_size: int = 0,
    epochs: int = 5,
    batch_size: int = 8192,
    lr: float = 1e-2,
    weight_decay: float = 0.0,
    grad_clip: float = 1.0,
    device: Optional[str] = "cpu",   # kept for signature; enforced to CPU
    verbose: bool = True,
    *,
    include_bias: bool = False,
    use_exact_linear: bool = True,
    train_dtype: torch.dtype = DTYPE,  # <<< unified dtype
    max_windows_for_nn: Optional[int] = None,
    shuffle: bool = False,
) -> Tuple[Optional[dict], Optional[np.ndarray], Optional[np.ndarray]]:
    """Train ARNN on overlapping windows; return state_dict, preds, and linear weights.

    Uses unfold to create training windows lazily; supports downsampling of windows
    via `step` when there are too many. If `hidden_size==0` and `use_exact_linear`,
    we initialize from the closed-form AR solution for fast convergence and auditability.
    """
    if waveform.ndim != 2:
        raise ValueError(f"Expected waveform (C, N), got {tuple(waveform.shape)}")

    # Enforce global device
    device = DEVICE

    x = waveform[0] if waveform.shape[0] == 1 else waveform.narrow(0, 0, 1)[0]
    x64 = x.detach().to(device=device, dtype=DTYPE)
    N = x64.numel()
    if N <= lags + 1:
        if verbose:
            print("Not enough samples for the requested lags")
        return None, None, None

    windows = x64.unfold(0, lags + 1, 1)
    M = int(windows.shape[0])

    if max_windows_for_nn is None:
        max_windows_for_nn = min(2_000_000, max(1_000_000, M // 2))

    step = max(1, math.ceil(M / max_windows_for_nn)) if (max_windows_for_nn and M > max_windows_for_nn) else 1

    model = ARNN(lags=lags, hidden_size=hidden_size, bias=include_bias, dtype=train_dtype).to(device=device)

    linear_weights = None

    # Optional exact linear init for the pure linear case (no bias)
    if hidden_size == 0 and use_exact_linear and not include_bias:
        G, b, _ = _ar_blockwise_gram_b(x64, lags, block=200_000)
        try:
            L = torch.linalg.cholesky(G)
            sol = torch.cholesky_solve(b.unsqueeze(1), L).squeeze(1)
        except RuntimeError:
            jitter = (1e-8 * torch.trace(G) / max(lags, 1)).item()
            G = G + jitter * torch.eye(lags, dtype=DTYPE, device=DEVICE)
            try:
                L = torch.linalg.cholesky(G)
                sol = torch.cholesky_solve(b.unsqueeze(1), L).squeeze(1)
            except RuntimeError:
                sol = torch.linalg.solve(G, b)
        with torch.no_grad():
            model.net.weight.data.copy_(sol.to(dtype=train_dtype, device=device).unsqueeze(0))
            if model.net.bias is not None:
                model.net.bias.zero_()
        linear_weights = sol.detach().cpu().numpy().astype(np.float64)
        if epochs <= 0:
            last_ctx = x64[-lags:]
            preds_future = _roll_predict(model, last_context=last_ctx, steps=samples_to_predict)
            if verbose:
                np.set_printoptions(precision=9)
                print("AR-NN (linear) exact weights (DTYPE) initialized.")
            return model.state_dict(), preds_future, linear_weights

    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.MSELoss()

    # Training with explicit grad context
    idx_rev = _rev_idx(lags)
    for ep in range(1, epochs + 1):
        epoch_loss = 0.0
        count = 0
        model.train()
        # Optional tiny offset to get a simple form of shuffling across epochs
        offset = int(torch.randint(low=0, high=min(10_000, max(1, step)), size=(1,), device=DEVICE).item()) if shuffle else 0

        start = offset
        while start < M:
            end = min(start + batch_size * step, M)
            with torch.no_grad():
                Wb = windows[start:end:step]
                Xb = Wb[:, :lags].index_select(1, idx_rev).contiguous().to(device=device, dtype=train_dtype)
                yb = Wb[:, -1].contiguous().to(device=device, dtype=train_dtype)

            with torch.enable_grad():
                opt.zero_grad(set_to_none=True)
                yhat = model(Xb)
                loss = loss_fn(yhat, yb)
                loss.backward()
                if grad_clip and grad_clip > 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                opt.step()

            batch_n = int(Wb.shape[0])
            epoch_loss += float(loss.item()) * batch_n
            count += batch_n

            del Wb, Xb, yb, yhat, loss
            gc.collect()
            start = end

        epoch_loss = epoch_loss / max(count, 1)

    last_ctx = x64[-lags:]
    preds_future = _roll_predict(model, last_context=last_ctx, steps=samples_to_predict)

    if hidden_size == 0:
        # Return learned linear weights for traceability
        w = model.net.weight.detach().to('cpu', dtype=DTYPE).squeeze(0).numpy().astype(np.float64)
        if model.net.bias is not None:
            b = model.net.bias.detach().to('cpu', dtype=DTYPE).numpy().astype(np.float64)
            linear_weights = np.concatenate([w, b], axis=0)
        else:
            linear_weights = w

    return model.state_dict(), preds_future, linear_weights


# -----------------------
# Post-processing: save & cluster AR parameters
# -----------------------
def _rows_from_results(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrae filas para CSV desde 'results', soportando AR clásico y NN-AR."""
    rows = []
    for fname, item in results.items():
        if not item or not item.get("success"):
            continue

        method = "unknown"
        P_out = None
        params_for_csv = None

        # --- 1) Preferir AR clásico si existe ---
        ar = item.get("ar", {})
        params_full = ar.get("params_full", None)
        if params_full is not None:
            method = "statsmodels" if ("aic" in ar or "bic" in ar) else ("lowmem" if ("AICc" in ar or "BIC" in ar) else "ar")
            P_out = int(ar.get("P")) if ar.get("P") is not None else None
            params_for_csv = np.asarray(params_full, dtype=np.float64)

        # --- 2) Si no hay AR clásico, usar NN-AR ---
        if params_for_csv is None:
            nn = item.get("nn_ar", {})
            if nn:
                P_out = int(nn.get("P")) if nn.get("P") is not None else None
                hidden = int(nn.get("hidden_size")) if nn.get("hidden_size") is not None else 0
                # Preferir vector lineal (coeficientes AR) si hidden_size == 0
                nn_weights = nn.get("linear_weights_plus_bias", None)
                if nn_weights is not None:
                    params_for_csv = np.asarray(nn_weights, dtype=np.float64)
                    method = "nn_ar_linear"
                else:
                    # Si no hay pesos lineales, usar TODOS los parámetros del NN (aplanados)
                    flat_params = nn.get("flat_params", None)
                    if flat_params is not None:
                        params_for_csv = np.asarray(flat_params, dtype=np.float64)
                        method = "nn_ar_hidden" if hidden > 0 else "nn_ar_flat"
        
        # Si aún no hay nada que guardar, saltar
        if params_for_csv is None:
            continue

        # Construir la fila
        row = {
            "file_name": fname,
            "P": P_out,
            "method": method,
            "sample_rate": float(item.get("sample_rate", float("nan"))),
            "duration_sec": float(item.get("duration", float("nan"))),
            "time_sec": float(item.get("time_sec", float("nan"))),
            "AIC": float(ar.get("aic", float("nan"))) if ar else float("nan"),
            "BIC": float(ar.get("bic", float("nan"))) if ar else float("nan"),
            "AICc": float(ar.get("AICc", float("nan"))) if ar else float("nan"),
            "params_json": json.dumps([float(x) for x in params_for_csv.tolist()]),
        }

        # Estos campos de NN-AR son metadatos útiles (si existen)
        nn = item.get("nn_ar", {})
        row["nn_P"] = int(nn.get("P")) if nn.get("P") is not None else None
        row["nn_hidden_size"] = int(nn.get("hidden_size")) if nn.get("hidden_size") is not None else None
        nn_weights = nn.get("linear_weights_plus_bias", None)
        row["nn_params_json"] = json.dumps([float(x) for x in np.asarray(nn_weights, dtype=np.float64).tolist()]) if nn_weights is not None else None

        rows.append(row)

    return rows



def save_ar_params_csv(results: Dict[str, Any], out_csv_path: Union[str, Path]) -> int:
    """Write AR parameter trace to CSV for downstream analysis/visualization."""
    rows = _rows_from_results(results)
    if not rows:
        print("⚠️  No AR parameters to save.")
        return 0
    out_csv_path = Path(out_csv_path)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file_name","P","method","sample_rate","duration_sec","time_sec","AIC","BIC","AICc","params_json","nn_P","nn_hidden_size","nn_params_json"]
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"📁 Saved AR parameter trace to: {out_csv_path}  ({len(rows)} rows)")
    return len(rows)


def _read_ar_params_csv(csv_path: Union[str, Path]) -> Tuple[List[str], np.ndarray, np.ndarray]:
    """Load params CSV back into (file_names, param-matrix padded to maxP, Pvec)."""
    file_names = []
    params_list = []
    P_list = []
    with Path(csv_path).open("r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                fname = row["file_name"]
                P = int(row["P"])
                params = json.loads(row["params_json"])
                if not isinstance(params, list):
                    continue
                file_names.append(fname)
                P_list.append(P)
                params_list.append(np.asarray(params, dtype=np.float64))
            except Exception:
                continue
    if not params_list:
        return [], np.empty((0,0), dtype=np.float64), np.empty((0,), dtype=np.int64)
    maxP = max(len(p) for p in params_list)
    X = np.zeros((len(params_list), maxP), dtype=np.float64)
    for i, p in enumerate(params_list):
        L = min(len(p), maxP)
        X[i, :L] = p[:L]
    return file_names, X, np.asarray(P_list, dtype=np.int64)


def _pca_2d(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simple PCA: center, SVD, take first two components and project rows."""
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    X2d = U[:, :2] * S[:2]
    comps = Vt[:2, :]
    return X2d, comps, mu


def _kmeans2(X: np.ndarray, k: int = 2, n_init: int = 10, max_iter: int = 100, seed: int = 42) -> Tuple[np.ndarray, np.ndarray, float]:
    rng = np.random.default_rng(seed)
    best_inertia = np.inf
    best_labels = None
    best_centers = None
    for _ in range(n_init):
        idx = rng.choice(X.shape[0], size=k, replace=False)
        centers = X[idx].copy()
        for _it in range(max_iter):
            d2 = ((X[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
            labels = np.argmin(d2, axis=1)
            new_centers = np.vstack([X[labels == j].mean(axis=0) if np.any(labels == j) else centers[j] for j in range(k)])
            shift = np.linalg.norm(new_centers - centers)
            centers = new_centers
            if shift < 1e-8:
                break
        inertia = ((X - centers[labels]) ** 2).sum()
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
            best_centers = centers.copy()
    return best_labels, best_centers, float(best_inertia)


def cluster_and_visualize(params_csv: Union[str, Path], out_png: Union[str, Path]) -> Dict[str, Any]:
    files, X, Pvec = _read_ar_params_csv(params_csv)
    if X.size == 0 or X.shape[0] < 2:
        print("⚠️  Not enough data to cluster/plot.")
        return {"ok": False}
    X2d, comps, mu = _pca_2d(X)
    if SKLEARN_AVAILABLE:
        kmeans = KMeans(n_clusters=2, n_init=20, max_iter=200, random_state=123)
        labels = kmeans.fit_predict(X2d)
        centers = kmeans.cluster_centers_
        inertia = float(kmeans.inertia_)
    else:
        labels, centers, inertia = _kmeans2(X2d, k=2, n_init=20, max_iter=200, seed=123)
    if MATPLOTLIB_AVAILABLE:
        plt.figure(figsize=(6, 5))
        plt.scatter(X2d[:, 0], X2d[:, 1], s=18, alpha=0.85, label="files")
        plt.scatter(centers[:, 0], centers[:, 1], s=80, marker="X", label="centers")
        plt.xlabel("PCA 1")
        plt.ylabel("PCA 2")
        plt.title("AR Params: PCA (k=2 clusters)")
        plt.legend()
        plt.tight_layout()
        out_png = Path(out_png)
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png, dpi=160)
        plt.close()
        print(f"📈 Saved PCA scatter to: {out_png}")
    else:
        print("⚠️  matplotlib not available; skipping plot.")
    counts = {int(i): int((labels == i).sum()) for i in range(2)}
    return {"ok": True, "n": int(X.shape[0]), "cluster_counts": counts, "inertia": inertia}


# -----------------------
# Orchestrator
# -----------------------
def process_audio_files(
    audio_files: list,
    base_path: Union[str, Path] = "/content",
    max_lags: int = 10,
    samples_to_predict: int = 100,
    target_sr: Optional[int] = None,
    mono_mode: str = "first",
    max_duration_s: Optional[float] = None,
    keep_model: bool = False,         # sin efecto en NAR puro
    verbose: bool = True,
    # --- AR-NN options ---
    use_nn_ar: bool = True,
    nn_hidden_size: int = 0,
    nn_epochs: int = 5,
    nn_batch_size: int = 8192,
    nn_lr: float = 1e-2,
    nn_weight_decay: float = 0.0,
    nn_grad_clip: float = 1.0,
    nn_device: Optional[str] = "cpu",  # for API shape only; se fuerza CPU global
    # --- Order selection (IGNORADO en NAR puro) ---
    do_order_selection: bool = False,
    order_P_min: int = 1,
    order_P_max: int = 24,
    order_method: str = "yw",
    # --- Other ---
    do_prewhitening_check: bool = True,
    lambda_reg: float = 0.0,           # sin efecto aquí
    statsmodels_threshold_samples: int = 300_000,  # sin efecto
) -> Dict[str, Any]:
    """
    Procesa múltiples audios y entrena SOLO un modelo NAR (AR-NN).
    - No usa AR clásico ni selección de orden basada en AR.
    - P (número de retardos) = max_lags.
    """
    base_path = Path(base_path)
    results: Dict[str, Any] = {}

    if base_path.exists():
        if verbose:
            try:
                entries = os.listdir(base_path)
                print(f"Files in {base_path}: {sorted(entries)[:50]}{' ...' if len(entries) > 50 else ''}")
            except Exception:
                pass
    else:
        print(f"⚠️  Base path does not exist: {base_path}")
        return {}

    if verbose:
        print(f"\nProcessing {len(audio_files)} audio files...")

    _warmup_numerics()

    for i, file_name in enumerate(audio_files, 1):
        file_path = base_path / file_name
        if verbose:
            print(f"\n[{i}/{len(audio_files)}] {file_name}")

        if not file_path.is_file():
            if verbose:
                print(f"↪️  Skipping missing file: {file_path}")
            results[file_name] = {"success": False, "error": f"File not found: {str(file_path)}"}
            continue

        waveform = None
        nn_state = None
        nn_preds = None
        nn_weights = None
        t0 = time.perf_counter()

        try:
            waveform, sr = read_wav(
                file_path,
                target_sr=target_sr,
                verbose=verbose,
                mono_mode=mono_mode,
                max_duration_s=max_duration_s,
            )

            item: Dict[str, Any] = {
                "success": True,
                "sample_rate": sr,
                "duration": waveform.shape[1] / sr,
            }

            # Diagnóstico opcional
            if do_prewhitening_check:
                pw = prewhitening_check(waveform[0], sr, candidate_factors=[2, 3, 4], verbose=verbose)
                item["prewhitening"] = {
                    "sfm": pw["sfm"],
                    "ljung_box_Q": pw["ljung_box_Q"],
                    "aliasing_fraction": {int(k): float(v) for k, v in pw["aliasing_fraction"].items()},
                    "suggestion": pw["suggestion"],
                }

            # NAR puro: elegimos P = max_lags (se ignora cualquier selección de orden AR).
            chosen_P = int(max_lags)

            if use_nn_ar:
                nn_state, nn_preds, nn_weights = fit_ar_nn(
                    waveform,
                    lags=chosen_P,
                    samples_to_predict=samples_to_predict,
                    hidden_size=nn_hidden_size,
                    epochs=nn_epochs,
                    batch_size=nn_batch_size,
                    lr=nn_lr,
                    weight_decay=nn_weight_decay,
                    grad_clip=nn_grad_clip,
                    device=nn_device,  # ignorado; se usa DEVICE global
                    verbose=verbose,
                    include_bias=False,
                    use_exact_linear=True,
                    train_dtype=DTYPE,
                    max_windows_for_nn=None,
                    shuffle=False,
                )
                if nn_state is not None:
                      # Aplana TODOS los tensores del estado del modelo (sirve para hidden_size=0 o >0)
                    flat_list = []
                    for k, v in nn_state.items():
                        try:
                            flat_list.append(v.detach().cpu().numpy().ravel().astype(np.float64))
                        except Exception:
                            pass
                    flat_params = np.concatenate(flat_list) if flat_list else None
                    item["nn_ar"] = {
                        "P": chosen_P,
                        "predictions": nn_preds,  # np.ndarray (float64)
                        "linear_weights_plus_bias": nn_weights,  # pesos lineales (si hidden_size==0)
                        "hidden_size": nn_hidden_size,
                        "state_dict_keys": list(nn_state.keys()),
                    }
                else:
                    # fallo explícito si no se pudo entrenar el NAR
                    item["success"] = False
                    item["error"] = "NAR training failed"

            else:
                # Si alguien desactiva use_nn_ar, no hay nada que hacer en modo NAR puro.
                item["success"] = False
                item["error"] = "use_nn_ar=False in NAR-only pipeline"

            item["time_sec"] = time.perf_counter() - t0
            results[file_name] = item

            if verbose and results[file_name].get("success"):
                print(f"✓ Done: {file_name}  |  time={item['time_sec']:.2f}s")

        except Exception as e:
            results[file_name] = {"success": False, "error": str(e), "time_sec": time.perf_counter() - t0}
            if verbose:
                print(f"✗ Failed: {file_name}: {e}")
        finally:
            del waveform, nn_state, nn_preds, nn_weights
            gc.collect()

    successful = sum(1 for r in results.values() if r.get("success", False))
    if verbose:
        print(f"\n📊 Summary: {successful}/{len(audio_files)} files processed successfully")
    return results



# -----------------------
# CLI / Entrypoint
# -----------------------
if __name__ == "__main__":
    import glob
    import os
    import time
    from pathlib import Path
    start_time = time.time()
    base_path = "AUDIOS"  # o el que uses en Colab
    # Busca todos los .wav en esa carpeta
    audio_files = [os.path.basename(p) for p in glob.glob(os.path.join(base_path, "*.wav"))][:5]
    # Prefiltro: procesar SOLO los que existan
    existing_files, missing_files = _filter_existing_files(audio_files, base_path)
    if missing_files:
        head = ", ".join(missing_files[:10])
        more = "" if len(missing_files) <= 10 else f" (+{len(missing_files)-10} más)"
        print(f"⚠️  Omitiendo {len(missing_files)} archivos inexistentes: {head}{more}")

    if not existing_files:
        print("❌ No hay archivos válidos para procesar en base_path.")
    else:
        # ⏱️ Medición de tiempo
        

        # 🔹 ÚNICA llamada al pipeline
        results = process_audio_files(
            existing_files,
            base_path=base_path,
            max_lags=10,
            samples_to_predict=128,
            target_sr=None,
            mono_mode="first",
            max_duration_s=None,
            keep_model=False,
            verbose=True,
            use_nn_ar=True,
            nn_hidden_size=0,
            nn_epochs=8,
            nn_batch_size=8192,
            nn_lr=3e-3,
            nn_weight_decay=1e-4,
            nn_grad_clip=1.0,
            nn_device="cpu",
            do_order_selection=False,      # en NAR puro no hace falta
            do_prewhitening_check=True,
        )

        # Guardado + clustering (ya con NN-AR habilitado según lo que añadiste)
        out_dir = Path(base_path) / "ar_outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        params_csv = out_dir / "ar_params_trace.csv"
        n_rows = save_ar_params_csv(results, params_csv)

        if n_rows > 0:
            pca_png = out_dir / "ar_params_pca_k2.png"
            summary = cluster_and_visualize(params_csv, pca_png)
            if summary.get("ok"):
                print(f"Clusters: {summary['cluster_counts']}, inertia={summary['inertia']:.2f}")
        else:
            print("⏭️  Sin clustering — no se guardaron parámetros.")

        # ⏱️ Tiempo total
        elapsed_time = time.time() - start_time
        print(f"⏳ Tiempo total de ejecución: {elapsed_time:.2f} segundos")

