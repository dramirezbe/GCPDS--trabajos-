import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

export default function ChartDisplay({ status, chartData }) {
    const plotRef = useRef(null);
    const history = useRef(Array(10).fill([])); // Holds last 50 sweeps for waterfall

    useEffect(() => {
        if (!chartData.data || chartData.data.length === 0) return;

        // Reset history if the spectrum length changes
        if (history.current[0] && history.current[0].length !== chartData.data.length) {
            history.current = []; 
        }

        // Update waterfall history
        history.current.unshift(chartData.data);
        if (history.current.length > 50) history.current.pop();

        // Find min and max safely for large arrays
        let minY = chartData.data[0], maxY = chartData.data[0];
        for (let i = 1; i < chartData.data.length; i++) {
            if (chartData.data[i] < minY) minY = chartData.data[i];
            if (chartData.data[i] > maxY) maxY = chartData.data[i];
        }

        const bottomY = minY - 20;

        const traces = [
            // 1. Invisible baseline trace for the fill
            {
                x: chartData.labels,
                y: Array(chartData.data.length).fill(bottomY),
                type: 'scatter',
                mode: 'none',
                hoverinfo: 'skip',
                xaxis: 'x',
                yaxis: 'y'
            },
            // 2. Spectrum (Top)
            {
                x: chartData.labels,
                y: chartData.data,
                type: 'scatter',
                line: { color: '#0d6efd' },
                xaxis: 'x',
                yaxis: 'y'
            },
            // 3. Spectrogram / Waterfall (Bottom)
            {
                x: chartData.labels,
                z: history.current,
                type: 'heatmap',
                colorscale: 'Jet',
                showscale: false, 
                xaxis: 'x',
                yaxis: 'y2'
            }
        ];

        const layout = {
            margin: { t: 10, r: 10, b: 30, l: 50 },
            showlegend: false,
            xaxis: { title: 'MHz' },
            yaxis: { title: 'dBm/Hz', domain: [0.55, 1], range: [bottomY, maxY + 20] },
            yaxis2: { title: 'Time', domain: [0, 0.45], autorange: 'reversed' }
        };

        Plotly.react(plotRef.current, traces, layout, { responsive: true });
        
    }, [chartData]);

    return (
        <div className="col-xl-8 col-lg-7 mb-4">
            <div className="card h-100">
                <div className="card-header d-flex justify-content-between align-items-center py-3">
                    <span className="fs-6">∿ Densidad Espectral & Waterfall</span>
                    <span className={status === 'STANDBY' ? "badge bg-light text-dark border" : "badge badge-active"}>
                        {status === 'STANDBY' ? 'STANDBY' : '∿ RX ACTIVE'}
                    </span>
                </div>
                <div className="card-body bg-white rounded-bottom">
                    <div ref={plotRef} style={{ height: 'calc(100vh - 200px)', minHeight: '400px', width: '100%' }} />
                </div>
            </div>
        </div>
    );
}