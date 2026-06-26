import os

from flask import Flask, render_template, jsonify, request, Response
from sdr_engine import HackRFEngine, wav_stream_header


app = Flask(__name__)

# Global SDR engine.
# HackRF One centered at 98 MHz with 20 MHz instantaneous bandwidth.
# This covers approximately 88 MHz to 108 MHz.
engine = HackRFEngine(
    center_freq_hz=98_000_000,
    sample_rate_hz=20_000_000,
    lna_gain_db=0,
    vga_gain_db=0,
    amp_enable=True,
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    """
    Start SDR acquisition.
    """
    try:
        engine.start()
        return jsonify({"ok": True, "message": "HackRF engine started."})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/stop", methods=["POST"])
def api_stop():
    """
    Stop SDR acquisition.
    """
    try:
        engine.stop()
        return jsonify({"ok": True, "message": "HackRF engine stopped."})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/tune", methods=["POST"])
def api_tune():
    """
    Tune center frequency and HackRF gains.

    Expected JSON:
        {
            "freq_mhz": 98.0,
            "lna_gain_db": 16,
            "vga_gain_db": 16,
            "amp_enable": false
        }
    """
    try:
        data = request.get_json(force=True)

        freq_mhz = float(data.get("freq_mhz", 98.0))
        lna_gain_db = int(data.get("lna_gain_db", 16))
        vga_gain_db = int(data.get("vga_gain_db", 16))
        amp_enable = bool(data.get("amp_enable", False))

        center_freq_hz = int(freq_mhz * 1e6)

        engine.tune(
            center_freq_hz=center_freq_hz,
            lna_gain_db=lna_gain_db,
            vga_gain_db=vga_gain_db,
            amp_enable=amp_enable,
        )

        return jsonify(
            {
                "ok": True,
                "center_freq_mhz": freq_mhz,
                "lna_gain_db": lna_gain_db,
                "vga_gain_db": vga_gain_db,
                "amp_enable": amp_enable,
            }
        )

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/psd", methods=["GET"])
def api_psd():
    """
    Return latest PSD data.
    """
    psd = engine.get_latest_psd()

    if psd is None:
        return jsonify({"ok": False, "error": "PSD not ready yet."}), 503

    psd["ok"] = True
    return jsonify(psd)


@app.route("/audio.wav")
def audio_wav():
    """
    Stream demodulated WBFM audio as WAV.

    Browser can play this using:
        <audio src="/audio.wav" controls autoplay>
    """

    def generate():
        yield wav_stream_header(
            sample_rate_hz=engine.audio_rate_hz,
            channels=1,
            bits_per_sample=16,
        )

        for audio_chunk in engine.audio_generator():
            yield audio_chunk

    return Response(
        generate(),
        mimetype="audio/wav",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    host = os.getenv("SDR_WEB_HOST", "0.0.0.0")
    port = int(os.getenv("SDR_WEB_PORT", "5000"))

    try:
        engine.start()

        # Do not use debug=True because Flask reloader creates two processes,
        # which can break direct SDR access.
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True,
            use_reloader=False,
        )

    finally:
        engine.stop()
