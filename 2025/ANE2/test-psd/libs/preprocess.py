# preprocess.py
"""
Preprocessing and shape-focused metrics for signal comparison.
- preprocessSignalsForShape: Standardizes and resamples signals for shape analysis.
- computeSignalMetrics: Computes MSE, MAE, Pearson Correlation, and a custom Spectral Distance.
"""
import numpy as np
from scipy import signal
from scipy.stats import pearsonr
from sklearn.preprocessing import StandardScaler

def preprocessSignalsForShape(nominalSignal, recordedSignal):
    """
    Standardizes two signals to have Mean=0 and StdDev=1 to analyze shape.
    Resamples the longer signal to match the shorter one.
    """
    # Ensure inputs are 1D arrays
    nominalArray = np.asarray(nominalSignal).flatten()
    recordedArray = np.asarray(recordedSignal).flatten()

    # Clean data: Replace NaNs/Infs with the median to avoid math errors
    nominalArray = np.nan_to_num(nominalArray, nan=np.nanmedian(nominalArray))
    recordedArray = np.nan_to_num(recordedArray, nan=np.nanmedian(recordedArray))

    # Determine common length
    targetLength = min(nominalArray.size, recordedArray.size)

    # Resample signals to the same length (Fourier method)
    nominalResampled = signal.resample(nominalArray, targetLength)
    recordedResampled = signal.resample(recordedArray, targetLength)

    # Erase Offset (Bias) and Power (Gain) using Z-Score Standardization
    nominalScaler = StandardScaler()
    recordedScaler = StandardScaler()

    # Fit_transform expects 2D, so we reshape then ravel back to 1D
    nominalStandardized = nominalScaler.fit_transform(nominalResampled.reshape(-1, 1)).ravel()
    recordedStandardized = recordedScaler.fit_transform(recordedResampled.reshape(-1, 1)).ravel()

    # Package metadata for transparency
    transformationMetadata = {
        "nominalMean": nominalScaler.mean_[0],
        "nominalStd": nominalScaler.scale_[0],
        "recordedMean": recordedScaler.mean_[0],
        "recordedStd": recordedScaler.scale_[0],
        "sampleCount": targetLength
    }

    return nominalStandardized, recordedStandardized, transformationMetadata

def computeSignalMetrics(nominalScaled, recordedScaled):
    """
    Computes MSE, MAE, Pearson Correlation, and a custom Spectral Distance.
    Expects standardized signals for accurate shape comparison.
    """
    # Ensure working with floats
    arrayA = np.asarray(nominalScaled).astype(float)
    arrayB = np.asarray(recordedScaled).astype(float)

    if arrayA.size != arrayB.size:
        raise ValueError("Signals must be the same length. Run preprocessSignalsForShape first.")

    # 1. Basic Error Metrics
    signalDifference = arrayA - arrayB
    meanSquaredError = np.mean(signalDifference ** 2)
    meanAbsoluteError = np.mean(np.abs(signalDifference))

    # 2. Pearson Correlation (The primary 'Shape' metric)
    # Result is a tuple (correlationCoefficient, pValue)
    pearsonCorrelation, _ = pearsonr(arrayA, arrayB)

    # 3. Stable Spectral Distance (Log-ratio of errors)
    epsilon = 1e-12
    if meanAbsoluteError <= epsilon:
        spectralDistanceDb = 0.0 if meanSquaredError <= epsilon else float('inf')
    else:
        # Measures outlier significance relative to average error
        spectralDistanceDb = 10.0 * np.log10((meanSquaredError + epsilon) / (meanAbsoluteError + epsilon))

    return {
        "meanSquaredError": meanSquaredError,
        "meanAbsoluteError": meanAbsoluteError,
        "pearsonCorrelation": pearsonCorrelation,
        "spectralDistanceDb": spectralDistanceDb
    }