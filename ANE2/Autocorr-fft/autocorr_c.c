#include <fftw3.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
/*
Versión "Original" en C: Emula scipy.signal.fftconvolve.
*/
void autocorr_original_c(float* x, int n, float* rxx_out) {
    int n_fft = 1 << (int)(ceil(log2(2 * n - 1)));
    int n_out = n / 2;
    fftwf_complex* in_x = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    fftwf_complex* out_x = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    fftwf_complex* in_rev = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    fftwf_complex* out_rev = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    // Prepare original and reversed signals with zero-padding
    for (int i = 0; i < n; i++) {
        in_x[i][0] = x[i];
        in_x[i][1] = 0.0;
        in_rev[i][0] = x[n - 1 - i];
        in_rev[i][1] = 0.0;
    }
    for (int i = n; i < n_fft; i++) {
        in_x[i][0] = in_x[i][1] = 0.0;
        in_rev[i][0] = in_rev[i][1] = 0.0;
    }
    // Create and execute FFT plans
    fftwf_plan plan_fwd_x = fftwf_plan_dft_1d(n_fft, in_x, out_x, FFTW_FORWARD, FFTW_ESTIMATE);
    fftwf_plan plan_fwd_rev = fftwf_plan_dft_1d(n_fft, in_rev, out_rev, FFTW_FORWARD, FFTW_ESTIMATE);
    fftwf_execute(plan_fwd_x);
    fftwf_execute(plan_fwd_rev);
    // Frequency-domain complex multiplication (cross-spectrum)
    for (int i = 0; i < n_fft; i++) {
        float re_x = out_x[i][0];
        float im_x = out_x[i][1];
        out_x[i][0] = re_x * out_rev[i][0] - im_x * out_rev[i][1];
        out_x[i][1] = re_x * out_rev[i][1] + im_x * out_rev[i][0];
    }
    // Inverse FFT to obtain convolution result
    fftwf_plan plan_bwd = fftwf_plan_dft_1d(n_fft, out_x, in_x, FFTW_BACKWARD, FFTW_ESTIMATE);
    fftwf_execute(plan_bwd);
    // Biased normalization and copy relevant part of the result
    for (int i = 0; i < n_out; i++) {
        rxx_out[i] = (in_x[n - 1 + i][0] / n_fft) / (float)(n - i);
    }
    // Cleanup
    fftwf_destroy_plan(plan_fwd_x);
    fftwf_destroy_plan(plan_fwd_rev);
    fftwf_destroy_plan(plan_bwd);
    fftwf_free(in_x);
    fftwf_free(out_x);
    fftwf_free(in_rev);
    fftwf_free(out_rev);
}


/*
Versión "Optimized" en C: Emula la lógica de NumPy (Wiener–Khinchin
theorem).
*/
void autocorr_optimized_c(float* x, int n, float* rxx_out) {
    int n_fft = 1 << (int)(ceil(log2(2 * n - 1)));
    int n_out = n / 2;
    fftwf_complex* in_fft = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    fftwf_complex* out_fft = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    for (int i = 0; i < n; i++) {
        in_fft[i][0] = x[i];
        in_fft[i][1] = 0.0;
    }
    for (int i = n; i < n_fft; i++) {
        in_fft[i][0] = 0.0;
        in_fft[i][1] = 0.0;
    }
    fftwf_plan plan_fwd = fftwf_plan_dft_1d(n_fft, in_fft, out_fft, FFTW_FORWARD, FFTW_ESTIMATE);
    fftwf_plan plan_bwd = fftwf_plan_dft_1d(n_fft, out_fft, in_fft, FFTW_BACKWARD, FFTW_ESTIMATE);
    fftwf_execute(plan_fwd);
    // Compute |X(k)|^2 in frequency domain
    for (int i = 0; i < n_fft; i++) {
        float re = out_fft[i][0];
        float im = out_fft[i][1];
        out_fft[i][0] = re * re + im * im;
        out_fft[i][1] = 0.0;
    }
    fftwf_execute(plan_bwd);
    for (int i = 0; i < n_out; i++) {
        rxx_out[i] = (in_fft[i][0] / n_fft) / (float)(n - i);
    }
    fftwf_destroy_plan(plan_fwd);
    fftwf_destroy_plan(plan_bwd);
    fftwf_free(in_fft);
    fftwf_free(out_fft);
}

/*
Versión "Superfast" en C (normalized by zero-lag).
*/
void autocorr_superfast_c(float* x, int n, float* rxx_out) {
    int n_fft = 1 << (int)(ceil(log2(2 * n - 1)));
    int n_out = n / 2;
    fftwf_complex* in_fft = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    fftwf_complex* out_fft = (fftwf_complex*)fftwf_malloc(sizeof(fftwf_complex) * n_fft);
    for (int i = 0; i < n; i++) {
        in_fft[i][0] = x[i];
        in_fft[i][1] = 0.0;
    }
    for (int i = n; i < n_fft; i++) {
        in_fft[i][0] = 0.0;
        in_fft[i][1] = 0.0;
    }
    fftwf_plan plan_fwd = fftwf_plan_dft_1d(n_fft, in_fft, out_fft, FFTW_FORWARD, FFTW_ESTIMATE);
    fftwf_plan plan_bwd = fftwf_plan_dft_1d(n_fft, out_fft, in_fft, FFTW_BACKWARD, FFTW_ESTIMATE);
    fftwf_execute(plan_fwd);
    for (int i = 0; i < n_fft; i++) {
        float re = out_fft[i][0];
        float im = out_fft[i][1];
        out_fft[i][0] = re * re + im * im;
        out_fft[i][1] = 0.0;
    }
    fftwf_execute(plan_bwd);
    float norm_factor = in_fft[0][0]; // Rxx[0] before normalization
    for (int i = 0; i < n_out; i++) {
        rxx_out[i] = in_fft[i][0] / norm_factor;
    }
    fftwf_destroy_plan(plan_fwd);
    fftwf_destroy_plan(plan_bwd);
    fftwf_free(in_fft);
    fftwf_free(out_fft);
}