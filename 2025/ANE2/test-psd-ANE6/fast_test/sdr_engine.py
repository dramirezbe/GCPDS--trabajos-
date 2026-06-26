import struct
import subprocess
import threading
import time
import queue
import collections
import numpy as np

from scipy.signal import welch, resample_poly, butter, lfilter, lfilter_zi


class HackRFEngine:
    """
    HackRF One acquisition and processing engine.

    This engine replaces the old RTL-SDR rtl_tcp/socket acquisition path.
    It uses hackrf_transfer and reads raw signed 8-bit IQ samples from stdout.

    Main features:
        - Starts hackrf_transfer.
        - Reads HackRF IQ samples from stdout.
        - Computes real-time PSD.
        - Optionally demodulates WBFM audio when the sample rate supports exact decimation.
        - Captures hackrf_transfer stderr for debugging.
        - Stops cleanly when hackrf_transfer fails.
    """

    def __init__(
        self,
        center_freq_hz=98_000_000,
        sample_rate_hz=20_000_000,
        lna_gain_db=0,
        vga_gain_db=0,
        amp_enable=True,
        serial_number=None,
    ):
        self.center_freq_hz = int(center_freq_hz)
        self.sample_rate_hz = int(sample_rate_hz)

        # HackRF RX gain stages:
        # LNA gain: usually 0 to 40 dB in 8 dB steps.
        # VGA gain: usually 0 to 62 dB in 2 dB steps.
        self.lna_gain_db = int(lna_gain_db)
        self.vga_gain_db = int(vga_gain_db)

        # RF amplifier near the antenna input.
        # Be careful: it may saturate the receiver in strong-signal environments.
        self.amp_enable = bool(amp_enable)

        # Optional HackRF serial number.
        self.serial_number = serial_number

        # Audio path configuration.
        # PSD works with the selected sample rate.
        # WBFM audio only works when sample_rate_hz is an exact multiple of 240 kHz.
        self.audio_rate_hz = 48_000
        self.channel_rate_hz = 240_000

        self.audio_supported = self.sample_rate_hz % self.channel_rate_hz == 0

        if self.audio_supported:
            self.rf_decim = self.sample_rate_hz // self.channel_rate_hz
            self.audio_decim = self.channel_rate_hz // self.audio_rate_hz
        else:
            self.rf_decim = None
            self.audio_decim = None
            print(
                "Warning: audio demodulation disabled because sample_rate_hz "
                "is not an integer multiple of 240 kHz."
            )

        # PSD/acquisition parameters.
        self.fft_size = 4096
        self.iq_samples_per_block = 64 * 1024

        # HackRF raw RX format:
        # signed 8-bit interleaved IQ:
        # I0, Q0, I1, Q1, ...
        self.bytes_per_iq_sample = 2
        self.bytes_per_block = self.iq_samples_per_block * self.bytes_per_iq_sample

        self.hackrf_process = None

        self.running = False
        self.audio_enabled = False

        self.reader_thread = None
        self.stderr_thread = None

        self.lock = threading.RLock()

        self.latest_psd_freq_mhz = None
        self.latest_psd_db = None

        self.audio_queue = queue.Queue(maxsize=50)

        # Keep recent stderr lines from hackrf_transfer.
        self.stderr_lines = collections.deque(maxlen=100)

        # Audio filter states.
        self.audio_lpf_b = None
        self.audio_lpf_a = None
        self.audio_lpf_zi = None

        self.deemph_b = None
        self.deemph_a = None
        self.deemph_zi = None

        self.prev_channel_sample = None

        self._design_audio_filters()

    # ============================================================
    # HackRF process control
    # ============================================================

    def _build_hackrf_command(self):
        """
        Build hackrf_transfer command.

        -r - means:
            receive samples and write raw IQ to stdout.
        """

        cmd = [
            "hackrf_transfer",
            "-r", "-",
            "-f", str(self.center_freq_hz),
            "-s", str(self.sample_rate_hz),
            "-l", str(self.lna_gain_db),
            "-g", str(self.vga_gain_db),
            "-a", "1" if self.amp_enable else "0",
        ]

        if self.serial_number is not None:
            cmd.extend(["-d", str(self.serial_number)])

        return cmd

    @staticmethod
    def _kill_old_hackrf_transfer():
        """
        Kill stale hackrf_transfer processes.
        """

        subprocess.run(
            ["pkill", "-f", "hackrf_transfer"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _stderr_reader_loop(self):
        """
        Continuously read hackrf_transfer stderr.

        This avoids blocking if stderr fills up and preserves diagnostic messages.
        """

        if self.hackrf_process is None or self.hackrf_process.stderr is None:
            return

        try:
            while True:
                line = self.hackrf_process.stderr.readline()

                if not line:
                    break

                try:
                    text = line.decode(errors="replace").rstrip()
                except Exception:
                    text = str(line).rstrip()

                if text:
                    self.stderr_lines.append(text)
                    print(f"[hackrf_transfer] {text}")

        except Exception as exc:
            print(f"stderr reader error: {exc}")

    def _get_recent_stderr(self):
        """
        Return recent hackrf_transfer stderr as a string.
        """

        if not self.stderr_lines:
            return ""

        return "\n".join(self.stderr_lines)

    def _start_hackrf_process(self):
        """
        Start hackrf_transfer and stream IQ samples through stdout.
        """

        self._kill_old_hackrf_transfer()
        self.stderr_lines.clear()

        cmd = self._build_hackrf_command()

        print("Starting hackrf_transfer:")
        print(" ".join(cmd))

        self.hackrf_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        self.stderr_thread = threading.Thread(
            target=self._stderr_reader_loop,
            daemon=True,
        )
        self.stderr_thread.start()

        time.sleep(0.7)

        if self.hackrf_process.poll() is not None:
            error_text = self._get_recent_stderr()

            raise RuntimeError(
                "hackrf_transfer failed to start.\n"
                "Check that HackRF is connected, detected by hackrf_info, "
                "and that HackRF tools are installed.\n\n"
                f"Recent hackrf_transfer stderr:\n{error_text}"
            )

    def start(self):
        """
        Start HackRF acquisition and launch the reader thread.
        """

        with self.lock:
            if self.running:
                return

            self._start_hackrf_process()

            self.running = True

            self.reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
            )
            self.reader_thread.start()

            print("HackRF configured:")
            print(f"  Center frequency: {self.center_freq_hz / 1e6:.3f} MHz")
            print(f"  Sample rate:      {self.sample_rate_hz / 1e6:.3f} MS/s")
            print(f"  LNA gain:         {self.lna_gain_db} dB")
            print(f"  VGA gain:         {self.vga_gain_db} dB")
            print(f"  RF amp enabled:   {self.amp_enable}")
            print(f"  Audio supported:  {self.audio_supported}")

    def stop(self):
        """
        Stop acquisition and close hackrf_transfer.
        """

        self.running = False
        self.audio_enabled = False

        time.sleep(0.2)

        try:
            if self.hackrf_process is not None:
                self.hackrf_process.terminate()
                self.hackrf_process.wait(timeout=2)
        except Exception:
            try:
                if self.hackrf_process is not None:
                    self.hackrf_process.kill()
            except Exception:
                pass

        self._kill_old_hackrf_transfer()

        print("HackRF engine stopped.")

    def tune(
        self,
        center_freq_hz,
        lna_gain_db=None,
        vga_gain_db=None,
        amp_enable=None,
        sample_rate_hz=None,
    ):
        """
        Retune HackRF.

        hackrf_transfer does not behave like rtl_tcp.
        To retune or change gains/sample rate, this engine restarts hackrf_transfer.
        """

        with self.lock:
            was_running = self.running

            self.center_freq_hz = int(center_freq_hz)

            if sample_rate_hz is not None:
                self.sample_rate_hz = int(sample_rate_hz)

            if lna_gain_db is not None:
                self.lna_gain_db = int(lna_gain_db)

            if vga_gain_db is not None:
                self.vga_gain_db = int(vga_gain_db)

            if amp_enable is not None:
                self.amp_enable = bool(amp_enable)

            # Recompute audio support after possible sample-rate change.
            self.audio_supported = self.sample_rate_hz % self.channel_rate_hz == 0

            if self.audio_supported:
                self.rf_decim = self.sample_rate_hz // self.channel_rate_hz
                self.audio_decim = self.channel_rate_hz // self.audio_rate_hz
            else:
                self.rf_decim = None
                self.audio_decim = None
                self.audio_enabled = False
                print(
                    "Warning: audio demodulation disabled because sample_rate_hz "
                    "is not an integer multiple of 240 kHz."
                )

            self.bytes_per_block = self.iq_samples_per_block * self.bytes_per_iq_sample

            print(f"Tuning HackRF to {self.center_freq_hz / 1e6:.3f} MHz")
            print(f"  Sample rate:      {self.sample_rate_hz / 1e6:.3f} MS/s")
            print(f"  LNA gain:         {self.lna_gain_db} dB")
            print(f"  VGA gain:         {self.vga_gain_db} dB")
            print(f"  RF amp enabled:   {self.amp_enable}")

            self._clear_audio_queue()
            self._reset_audio_states()

            if was_running:
                self.running = False
                time.sleep(0.2)

                try:
                    if self.hackrf_process is not None:
                        self.hackrf_process.terminate()
                        self.hackrf_process.wait(timeout=2)
                except Exception:
                    try:
                        if self.hackrf_process is not None:
                            self.hackrf_process.kill()
                    except Exception:
                        pass

                self._start_hackrf_process()

                self.running = True

                self.reader_thread = threading.Thread(
                    target=self._reader_loop,
                    daemon=True,
                )
                self.reader_thread.start()

    # ============================================================
    # Acquisition
    # ============================================================

    def _recv_exactly(self, n_bytes):
        """
        Receive exactly n_bytes from hackrf_transfer stdout.
        """

        if self.hackrf_process is None or self.hackrf_process.stdout is None:
            raise RuntimeError("hackrf_transfer is not running.")

        chunks = []
        bytes_received = 0

        # If no bytes arrive for this long, consider the stream broken.
        no_data_timeout_s = 1.5
        last_data_time = time.time()

        while bytes_received < n_bytes and self.running:
            if self.hackrf_process.poll() is not None:
                error_text = self._get_recent_stderr()
                raise RuntimeError(
                    "hackrf_transfer stopped unexpectedly.\n"
                    f"Recent hackrf_transfer stderr:\n{error_text}"
                )

            remaining = n_bytes - bytes_received

            try:
                chunk = self.hackrf_process.stdout.read(remaining)
            except Exception as exc:
                error_text = self._get_recent_stderr()
                raise RuntimeError(
                    f"Could not read from hackrf_transfer stdout: {exc}\n"
                    f"Recent hackrf_transfer stderr:\n{error_text}"
                )

            if chunk:
                chunks.append(chunk)
                bytes_received += len(chunk)
                last_data_time = time.time()
                continue

            if time.time() - last_data_time > no_data_timeout_s:
                error_text = self._get_recent_stderr()
                raise RuntimeError(
                    "No IQ bytes received from hackrf_transfer.\n"
                    "This usually means the HackRF stream is not delivering samples.\n"
                    "The same problem appeared in your manual command as:\n"
                    "'Couldn't transfer any bytes for one second.'\n\n"
                    f"Recent hackrf_transfer stderr:\n{error_text}"
                )

            time.sleep(0.01)

        return b"".join(chunks)

    @staticmethod
    def hackrf_bytes_to_iq(raw_bytes):
        """
        Convert signed 8-bit interleaved HackRF IQ samples to complex64.

        HackRF byte format:
            I0, Q0, I1, Q1, ...

        Each I/Q value is signed int8:
            range: -128 to +127
        """

        data = np.frombuffer(raw_bytes, dtype=np.int8)

        if len(data) % 2 != 0:
            data = data[:-1]

        i_data = data[0::2].astype(np.float32)
        q_data = data[1::2].astype(np.float32)

        # Normalize approximately to [-1, +1].
        i_data = i_data / 128.0
        q_data = q_data / 128.0

        return (i_data + 1j * q_data).astype(np.complex64)

    def _reader_loop(self):
        """
        Main acquisition loop.
        """

        print("Starting HackRF reader loop...")

        while self.running:
            try:
                raw = self._recv_exactly(self.bytes_per_block)

                if not raw:
                    continue

                iq = self.hackrf_bytes_to_iq(raw)

                if iq.size == 0:
                    continue

                # Remove DC offset for PSD and demodulation.
                iq = iq - np.mean(iq)

                self._update_psd(iq)

                if self.audio_enabled and self.audio_supported:
                    audio_bytes = self._demodulate_fm_chunk(iq)

                    if audio_bytes is not None and len(audio_bytes) > 0:
                        try:
                            self.audio_queue.put_nowait(audio_bytes)
                        except queue.Full:
                            # Drop old audio if the browser is not consuming fast enough.
                            try:
                                _ = self.audio_queue.get_nowait()
                            except queue.Empty:
                                pass

                            try:
                                self.audio_queue.put_nowait(audio_bytes)
                            except queue.Full:
                                pass

            except Exception as exc:
                if self.running:
                    print(f"Reader loop error:\n{exc}")

                # Stop instead of printing the same error forever.
                self.running = False
                self.audio_enabled = False
                break

        print("HackRF reader loop stopped.")

    # ============================================================
    # PSD
    # ============================================================

    def _update_psd(self, iq):
        """
        Compute and store the latest PSD.
        """

        freqs, psd = welch(
            iq,
            fs=self.sample_rate_hz,
            window="hann",
            nperseg=self.fft_size,
            noverlap=self.fft_size // 2,
            return_onesided=False,
            scaling="density",
        )

        freqs_shifted = np.fft.fftshift(freqs)
        psd_shifted = np.fft.fftshift(psd)

        rf_freq_mhz = (self.center_freq_hz + freqs_shifted) / 1e6
        psd_db = 10.0 * np.log10(psd_shifted + 1e-20)

        # Downsample points sent to browser to reduce JSON size.
        max_points = 1024

        if len(psd_db) > max_points:
            step = max(1, len(psd_db) // max_points)
            rf_freq_mhz = rf_freq_mhz[::step]
            psd_db = psd_db[::step]

        with self.lock:
            self.latest_psd_freq_mhz = rf_freq_mhz.astype(float)
            self.latest_psd_db = psd_db.astype(float)

    def get_latest_psd(self):
        """
        Return latest PSD as plain Python lists for JSON serialization.
        """

        with self.lock:
            if self.latest_psd_freq_mhz is None or self.latest_psd_db is None:
                return None

            return {
                "center_freq_mhz": self.center_freq_hz / 1e6,
                "sample_rate_mhz": self.sample_rate_hz / 1e6,
                "freq_mhz": self.latest_psd_freq_mhz.tolist(),
                "psd_db": self.latest_psd_db.tolist(),
                "lna_gain_db": self.lna_gain_db,
                "vga_gain_db": self.vga_gain_db,
                "amp_enable": self.amp_enable,
                "audio_supported": self.audio_supported,
                "engine_running": self.running,
                "hackrf_stderr": self._get_recent_stderr(),
            }

    # ============================================================
    # FM demodulation
    # ============================================================

    def _design_audio_filters(self):
        """
        Design streaming filters for WBFM mono audio.
        """

        # Audio low-pass filter at 15 kHz.
        audio_cutoff_hz = 15_000
        nyquist = self.channel_rate_hz / 2

        self.audio_lpf_b, self.audio_lpf_a = butter(
            N=5,
            Wn=audio_cutoff_hz / nyquist,
            btype="low",
        )

        # FM de-emphasis.
        # Colombia/Americas FM broadcast usually uses 75 us.
        tau = 75e-6
        dt = 1.0 / self.channel_rate_hz
        alpha = dt / (tau + dt)

        self.deemph_b = np.array([alpha], dtype=np.float64)
        self.deemph_a = np.array([1.0, -(1.0 - alpha)], dtype=np.float64)

        self._reset_audio_states()

    def _reset_audio_states(self):
        """
        Reset demodulator and filter memories.
        """

        self.prev_channel_sample = None

        if self.audio_lpf_b is not None and self.audio_lpf_a is not None:
            self.audio_lpf_zi = lfilter_zi(self.audio_lpf_b, self.audio_lpf_a) * 0.0

        if self.deemph_b is not None and self.deemph_a is not None:
            self.deemph_zi = lfilter_zi(self.deemph_b, self.deemph_a) * 0.0

    def _demodulate_fm_chunk(self, iq):
        """
        Demodulate one IQ block into PCM16 WAV audio bytes.

        This only works when audio_supported is True.
        Example:
            sample_rate_hz = 2_400_000 works.
            sample_rate_hz = 20_000_000 does not work with this simple path.
        """

        if not self.audio_supported:
            return None

        if self.rf_decim is None or self.audio_decim is None:
            return None

        # Decimate RF IQ to 240 kS/s channel rate.
        iq_channel = resample_poly(
            iq,
            up=1,
            down=self.rf_decim,
        )

        if len(iq_channel) < 2:
            return None

        # Preserve phase continuity between chunks.
        if self.prev_channel_sample is not None:
            iq_for_demod = np.concatenate(
                [
                    np.array([self.prev_channel_sample], dtype=np.complex64),
                    iq_channel,
                ]
            )
        else:
            iq_for_demod = iq_channel

        self.prev_channel_sample = iq_channel[-1]

        # FM phase discriminator.
        fm_demod = np.angle(iq_for_demod[1:] * np.conj(iq_for_demod[:-1]))
        fm_demod = fm_demod - np.mean(fm_demod)

        # Audio low-pass.
        audio, self.audio_lpf_zi = lfilter(
            self.audio_lpf_b,
            self.audio_lpf_a,
            fm_demod,
            zi=self.audio_lpf_zi,
        )

        # De-emphasis.
        audio, self.deemph_zi = lfilter(
            self.deemph_b,
            self.deemph_a,
            audio,
            zi=self.deemph_zi,
        )

        # Resample 240 kS/s audio to 48 kS/s.
        audio_48k = resample_poly(
            audio,
            up=1,
            down=self.audio_decim,
        )

        # Remove DC.
        audio_48k = audio_48k - np.mean(audio_48k)

        # Simple chunk normalization.
        max_abs = np.max(np.abs(audio_48k))

        if max_abs > 1e-6:
            audio_48k = audio_48k / max_abs

        audio_48k = 0.8 * audio_48k

        audio_int16 = np.int16(np.clip(audio_48k, -1.0, 1.0) * 32767)

        return audio_int16.tobytes()

    def enable_audio(self):
        """
        Enable FM audio demodulation.
        """

        if not self.audio_supported:
            print(
                "Audio is not supported with the current sample rate. "
                "Use a sample rate that is an integer multiple of 240 kHz, "
                "for example 2_400_000."
            )
            self.audio_enabled = False
            self._clear_audio_queue()
            return

        self._clear_audio_queue()
        self._reset_audio_states()
        self.audio_enabled = True

    def disable_audio(self):
        """
        Disable FM audio demodulation.
        """

        self.audio_enabled = False
        self._clear_audio_queue()

    def _clear_audio_queue(self):
        """
        Empty pending audio chunks.
        """

        while True:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def audio_generator(self):
        """
        Yield PCM16 audio bytes for Flask streaming.
        """

        self.enable_audio()

        try:
            while self.running and self.audio_enabled and self.audio_supported:
                try:
                    chunk = self.audio_queue.get(timeout=1.0)
                    yield chunk
                except queue.Empty:
                    continue
        finally:
            self.disable_audio()


def wav_stream_header(sample_rate_hz=48_000, channels=1, bits_per_sample=16):
    """
    Generate a WAV header for streaming.

    The data size is set to a large value because the stream length is not known.
    """

    byte_rate = sample_rate_hz * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8

    data_size = 0x7FFFFFFF
    riff_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate_hz,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    return header


# Compatibility alias.
# This lets old server.py files still import RTLSDREngine,
# but internally it uses the HackRF engine.
RTLSDREngine = HackRFEngine