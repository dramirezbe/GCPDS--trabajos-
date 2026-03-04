import { useState, useRef, useEffect } from 'react';

const API_BASE = window.location.origin;

export default function Controls({ mac, setStatus, setChartData }) {
    const [c, setC] = useState({
        method_psd: 'pfb', center_freq_mhz: '', sample_rate_mhz: '', rbw_khz: '',
        window: 'hann', overlap: 0.5, antenna_port: 1, lna_gain: 0, vga_gain: 0, 
        antenna_amp: false, filter_start_mhz: '', filter_end_mhz: ''
    });
    const [msg, setMsg] = useState({ text: '', color: '' });
    const [isRunning, setIsRunning] = useState(false);
    const intervalRef = useRef(null);

    const handleChange = (e) => {
        const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        setC({ ...c, [e.target.name]: value });
    };

    const showMsg = (text, color) => {
        setMsg({ text, color });
        setTimeout(() => setMsg({ text: '', color: '' }), 4000);
    };

    const loadConfig = async () => {
        try {
            const res = await fetch(`${API_BASE}/${mac}/realtime`);
            if (!res.ok) throw new Error();
            const d = await res.json();
            setC({
                method_psd: d.method_psd || 'pfb',
                center_freq_mhz: d.center_freq_hz ? (d.center_freq_hz / 1e6).toFixed(3) : '',
                sample_rate_mhz: d.sample_rate_hz ? (d.sample_rate_hz / 1e6).toFixed(3) : '',
                rbw_khz: d.rbw_hz ? (d.rbw_hz / 1e3).toFixed(1) : '',
                window: d.window || 'hann', 
                overlap: d.overlap || 0.5, 
                antenna_port: d.antenna_port || 1,
                lna_gain: d.lna_gain || 0, 
                vga_gain: d.vga_gain || 0, 
                antenna_amp: d.antenna_amp || false,
                filter_start_mhz: d.filter?.start_freq_hz ? (d.filter.start_freq_hz / 1e6).toFixed(3) : '',
                filter_end_mhz: d.filter?.end_freq_hz ? (d.filter.end_freq_hz / 1e6).toFixed(3) : ''
            });
            showMsg('Sincronizado', '#0d6efd');
        } catch { showMsg('Error de conexión API', '#dc3545'); }
    };

    useEffect(() => { loadConfig(); }, [mac]);

    const getPayload = () => ({
        method_psd: c.method_psd,
        center_freq_hz: Math.round((parseFloat(c.center_freq_mhz) || 0) * 1e6),
        sample_rate_hz: Math.round((parseFloat(c.sample_rate_mhz) || 0) * 1e6),
        rbw_hz: Math.round((parseFloat(c.rbw_khz) || 0) * 1e3),
        window: c.window, 
        overlap: parseFloat(c.overlap), 
        lna_gain: parseInt(c.lna_gain),
        vga_gain: parseInt(c.vga_gain), 
        antenna_port: parseInt(c.antenna_port), 
        antenna_amp: c.antenna_amp,
        filter: (c.filter_start_mhz && c.filter_end_mhz) ? { 
            start_freq_hz: Math.round(parseFloat(c.filter_start_mhz) * 1e6), 
            end_freq_hz: Math.round(parseFloat(c.filter_end_mhz) * 1e6) 
        } : null
    });

    const sendConfig = async (payload) => fetch(`${API_BASE}/${mac}/realtime`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });

    const fetchData = async () => {
        try {
            const res = await fetch(`${API_BASE}/${mac}/data`);
            if (!res.ok) return;
            const d = await res.json();
            if (d.Pxx?.length > 0) {
                const step = (d.end_freq_hz - d.start_freq_hz) / d.Pxx.length;
                setChartData({
                    labels: d.Pxx.map((_, i) => ((d.start_freq_hz + (i * step)) / 1e6).toFixed(3)),
                    data: d.Pxx
                });
            } else setChartData({ labels: [], data: [] });
        } catch { showMsg('Error obteniendo datos', '#dc3545'); }
    };

    const startAcq = async () => {
        const p = getPayload();
        if (p.center_freq_hz < 1e6) return showMsg('Center Freq > 1 MHz', '#dc3545');
        try {
            await sendConfig(p);
            showMsg('ADQUISICIÓN ACTIVA', '#198754');
            setIsRunning(true);
            setStatus('ACTIVE');
            fetchData();
            intervalRef.current = setInterval(fetchData, 250);
        } catch { showMsg('Fallo hardware', '#dc3545'); }
    };

    const stopAcq = async () => {
        try {
            await sendConfig({ ...getPayload(), center_freq_hz: 0 });
            showMsg('HARDWARE STANDBY', '#dc3545');
            setIsRunning(false);
            setStatus('STANDBY');
            clearInterval(intervalRef.current);
        } catch { showMsg('Fallo hardware', '#dc3545'); }
    };

    return (
        <div className="col-xl-4 col-lg-5 mb-4">
            <div className="card h-100">
                <div className="card-header d-flex justify-content-between align-items-center py-3">
                    <span className="fs-6">⎈ Parámetros de RF</span>
                    <button className="btn btn-sm btn-light text-primary fw-bold" onClick={loadConfig}>SYNC ⟳</button>
                </div>
                <div className="card-body">
                    <div className="row g-3">
                        <div className="col-12">
                            <label className="form-label">Método PSD</label>
                            <select className="form-select" name="method_psd" value={c.method_psd} onChange={handleChange}>
                                <option value="pfb">PFB</option>
                                <option value="welch">Welch</option>
                            </select>
                        </div>
                        <div className="col-md-6">
                            <label className="form-label">Center Freq</label>
                            <input type="number" className="form-control" name="center_freq_mhz" value={c.center_freq_mhz} onChange={handleChange} step="0.001" />
                        </div>
                        <div className="col-md-6">
                            <label className="form-label">Sample Rate</label>
                            <input type="number" className="form-control" name="sample_rate_mhz" value={c.sample_rate_mhz} onChange={handleChange} step="0.1" />
                        </div>
                        <div className="col-md-12">
                            <label className="form-label">RBW (kHz)</label>
                            <input type="number" className="form-control" name="rbw_khz" value={c.rbw_khz} onChange={handleChange} step="1" />
                        </div>

                        <hr className="border-secondary-subtle my-3" />

                        <div className="col-md-6">
                            <label className="form-label">Window Function</label>
                            <select className="form-select form-select-sm" name="window" value={c.window} onChange={handleChange}>
                                <option value="hann">Hann</option>
                                <option value="rectangular">Rectangular</option>
                                <option value="blackman">Blackman</option>
                                <option value="hamming">Hamming</option>
                                <option value="flattop">Flat-Top</option>
                                <option value="kaiser">Kaiser</option>
                                <option value="tukey">Tukey</option>
                                <option value="bartlett">Bartlett</option>
                            </select>
                        </div>
                        <div className="col-md-6">
                            <label className="form-label">Overlap</label>
                            <select className="form-select form-select-sm" name="overlap" value={c.overlap} onChange={handleChange}>
                                <option value="0.25">25%</option>
                                <option value="0.5">50%</option>
                                <option value="0.75">75%</option>
                            </select>
                        </div>

                        <hr className="border-secondary-subtle my-3" />

                        <div className="col-md-4">
                            <label className="form-label">Antenna Port</label>
                            <select className="form-select form-select-sm" name="antenna_port" value={c.antenna_port} onChange={handleChange}>
                                <option value="1">Port 1</option>
                                <option value="2">Port 2</option>
                                <option value="3">Port 3</option>
                                <option value="4">Port 4</option>
                            </select>
                        </div>
                        
                        <div className="col-md-12 mt-3">
                            <label className="form-label w-100">LNA Gain <span className="value-display">{c.lna_gain} dB</span></label>
                            <input type="range" className="form-range" name="lna_gain" min="0" max="40" step="8" value={c.lna_gain} onChange={handleChange} />
                        </div>
                        <div className="col-md-12 mt-2">
                            <label className="form-label w-100">VGA Gain <span className="value-display">{c.vga_gain} dB</span></label>
                            <input type="range" className="form-range" name="vga_gain" min="0" max="62" step="2" value={c.vga_gain} onChange={handleChange} />
                        </div>

                        <div className="col-12 mt-3">
                            <div className="form-check form-switch">
                                <input className="form-check-input" type="checkbox" name="antenna_amp" checked={c.antenna_amp} onChange={handleChange} />
                                <label className="form-check-label text-dark fw-bold">Activar Amplificador (Bias-T)</label>
                            </div>
                        </div>

                        <hr className="border-secondary-subtle my-3" />
                        <h6 className="text-secondary mb-2" style={{ fontSize: '0.8rem', textTransform: 'uppercase', fontWeight: 'bold' }}>Filtro Lógico (Opcional)</h6>
                        <div className="col-md-6">
                            <label className="form-label">Start (MHz)</label>
                            <input type="number" className="form-control form-control-sm" name="filter_start_mhz" value={c.filter_start_mhz} onChange={handleChange} step="0.001" />
                        </div>
                        <div className="col-md-6">
                            <label className="form-label">End (MHz)</label>
                            <input type="number" className="form-control form-control-sm" name="filter_end_mhz" value={c.filter_end_mhz} onChange={handleChange} step="0.001" />
                        </div>
                    </div>
                    
                    <div className="d-grid gap-2 mt-4">
                        {!isRunning ? (
                            <button className="btn btn-action-green" onClick={startAcq}>▶ INICIAR ADQUISICIÓN</button>
                        ) : (
                            <button className="btn btn-action-red" onClick={stopAcq}>⏹ DETENER HARDWARE</button>
                        )}
                    </div>
                    <div className="mt-2 text-center fw-bold" style={{ minHeight: '24px', color: msg.color }}>{msg.text}</div>
                </div>
            </div>
        </div>
    );
}