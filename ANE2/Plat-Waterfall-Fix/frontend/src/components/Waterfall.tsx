import { useEffect, useRef, useMemo, useState } from 'react';
import Plotly from 'plotly.js-dist-min';

interface WaterfallProps {
  data: { frequency: number; power: number }[];
  history: { frequency: number; power: number }[][];
  freqUnit?: 'Hz' | 'kHz' | 'MHz' | 'GHz';
  powerUnit?: string;
  stepRatio?: number;
  minFreq?: number;
  maxFreq?: number;
}

export function Waterfall({ history, freqUnit = 'MHz', powerUnit = 'dBm' }: WaterfallProps) {
  const MAX_CACHED_SIGNALS = 5;
  const plotRef = useRef<HTMLDivElement>(null);
  const resizeRafRef = useRef<number | null>(null);
  const lastHistoryHashRef = useRef<string>('');
  const [showColorbar, setShowColorbar] = useState(false);

  const convertFrequency = useMemo(() => {
    return (freqHz: number): number => {
      switch (freqUnit) {
        case 'Hz': return freqHz;
        case 'kHz': return freqHz / 1e3;
        case 'MHz': return freqHz / 1e6;
        case 'GHz': return freqHz / 1e9;
        default: return freqHz / 1e6;
      }
    };
  }, [freqUnit]);

  // Block wheel events on the plot div
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const blockWheel = (e: WheelEvent) => { e.preventDefault(); e.stopPropagation(); };
    el.addEventListener('wheel', blockWheel, { passive: false });

    const scheduleResize = () => {
      if (resizeRafRef.current !== null) {
        cancelAnimationFrame(resizeRafRef.current);
      }
      resizeRafRef.current = requestAnimationFrame(() => {
        if (plotRef.current) {
          Plotly.Plots.resize(plotRef.current);
        }
      });
    };

    const observer = new ResizeObserver(() => {
      scheduleResize();
    });
    observer.observe(el);

    const handleFullscreenChange = () => {
      scheduleResize();
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      el.removeEventListener('wheel', blockWheel);
      observer.disconnect();
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      if (resizeRafRef.current !== null) {
        cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
      Plotly.purge(el);
    };
  }, []);

  useEffect(() => {
    if (!plotRef.current) return;

    if (!history || history.length === 0) {
      // Render empty state
      const currentHash = '';
      if (lastHistoryHashRef.current !== currentHash) {
        lastHistoryHashRef.current = currentHash;
        Plotly.react(plotRef.current, [], {
          margin: { t: 10, r: 40, b: 40, l: 70 },
          plot_bgcolor: '#ffffff',
          paper_bgcolor: '#ffffff',
          xaxis: {},
          yaxis: {},
          dragmode: false,
        }, { responsive: true, displayModeBar: false });
      }
      return;
    }

    // history[0] is expected to be the newest snapshot.
    // Keep a fixed FIFO window of 5 rows in the heatmap.
    const cachedHistory = history.slice(0, MAX_CACHED_SIGNALS);

    // Build frequency labels from the first snapshot (assumed same for all)
    const refSnapshot = cachedHistory[0];
    if (!refSnapshot || refSnapshot.length === 0) return;

    // Keep cache independent from external central-frequency/range changes.
    // Always use the snapshot's own frequency span for cached rows.
    const actualMinFreq = refSnapshot[0].frequency;
    const actualMaxFreq = refSnapshot[refSnapshot.length - 1].frequency;

    // Build x-axis labels (frequency values)
    // We resample each history snapshot to a consistent set of frequency bins
    const numBins = Math.min(refSnapshot.length, 600); // limit bins for performance
    const freqStep = (actualMaxFreq - actualMinFreq) / numBins;
    const freqLabels: number[] = [];
    for (let i = 0; i < numBins; i++) {
      freqLabels.push(convertFrequency(actualMinFreq + i * freqStep));
    }

    // Build z matrix: each row is a time slice (history[0] = most recent)
    // Limit to cached signal window for performance
    const maxHistory = cachedHistory.length;
    const builtRows: number[][] = [];

    for (let hi = 0; hi < maxHistory; hi++) {
      const snapshot = cachedHistory[hi];
      if (!snapshot || snapshot.length === 0) {
        builtRows.push(new Array(numBins).fill(-100));
        continue;
      }

      const row: number[] = new Array(numBins);
      const snapshotMinFreq = snapshot[0].frequency;
      const snapshotMaxFreq = snapshot[snapshot.length - 1].frequency;
      const snapshotRange = snapshotMaxFreq - snapshotMinFreq;

      for (let i = 0; i < numBins; i++) {
        const targetFreq = actualMinFreq + i * freqStep;
        
        if (snapshotRange <= 0) {
          row[i] = snapshot[0]?.power ?? -100;
          continue;
        }

        // Map target frequency to source index
        const sourceIndex = ((targetFreq - snapshotMinFreq) / snapshotRange) * (snapshot.length - 1);
        const lowerIdx = Math.max(0, Math.min(Math.floor(sourceIndex), snapshot.length - 1));
        const upperIdx = Math.max(0, Math.min(lowerIdx + 1, snapshot.length - 1));

        if (lowerIdx === upperIdx) {
          row[i] = snapshot[lowerIdx]?.power ?? -100;
        } else {
          const fraction = sourceIndex - lowerIdx;
          const lowerPower = snapshot[lowerIdx]?.power ?? -100;
          const upperPower = snapshot[upperIdx]?.power ?? -100;
          row[i] = lowerPower + (upperPower - lowerPower) * fraction;
        }
      }
      builtRows.push(row);
    }

    // Keep a fixed 5-row grid at all times.
    // Missing rows are null so they render as empty space instead of stretching existing frames.
    const ySlots = Array.from({ length: MAX_CACHED_SIGNALS }, (_, i) => i + 1);
    const zData: (number | null)[][] = Array.from({ length: MAX_CACHED_SIGNALS }, (_, rowIndex) => {
      if (rowIndex < builtRows.length) return builtRows[rowIndex];
      return new Array(numBins).fill(null);
    });

    // Hash check to avoid unnecessary full redraws (just length + first snapshot identity)
    const newHash = `${cachedHistory.length}-${refSnapshot.length}-${actualMinFreq.toFixed(0)}-${actualMaxFreq.toFixed(0)}`;

    const traces: Plotly.Data[] = [
      {
        x: freqLabels,
        y: ySlots,
        z: zData,
        type: 'heatmap',
        colorscale: [
          [0, '#0000ff'],
          [0.25, '#00ffff'],
          [0.5, '#00ff00'],
          [0.75, '#ffff00'],
          [1, '#ff0000'],
        ],
        hoverongaps: false,
        showscale: showColorbar,
        colorbar: {
          title: { text: powerUnit, side: 'right', font: { size: 11 } },
          thickness: 15,
          len: 0.9,
        },
        hovertemplate: `Freq: %{x:.3f} ${freqUnit}<br>Power: %{z:.1f} ${powerUnit}<br>Sweep: %{y}<extra></extra>`,
      },
    ];

    const layout: Partial<Plotly.Layout> = {
      margin: { t: 10, r: showColorbar ? 80 : 40, b: 40, l: 70 },
      xaxis: {
        gridcolor: '#e5e7eb',
        linecolor: '#d1d5db',
        fixedrange: true,
      },
      yaxis: {
        autorange: 'reversed',
        range: [MAX_CACHED_SIGNALS + 0.5, 0.5],
        tickmode: 'array',
        tickvals: ySlots,
        ticktext: ySlots.map(value => `${value}`),
        gridcolor: '#e5e7eb',
        linecolor: '#d1d5db',
        fixedrange: true,
      },
      plot_bgcolor: '#ffffff',
      paper_bgcolor: '#ffffff',
      dragmode: false,
    };

    const config: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: false,
      scrollZoom: false,
      doubleClick: false,
      staticPlot: true,
    };

    Plotly.react(plotRef.current, traces, layout, config);
    lastHistoryHashRef.current = newHash;
  }, [history, freqUnit, powerUnit, convertFrequency, showColorbar]);

  return (
    <div className="-mt-3 relative">
      <button
        onClick={() => setShowColorbar(prev => !prev)}
        className="absolute top-1 right-1 z-10 px-1.5 py-0.5 text-xs bg-gray-100 hover:bg-gray-200 border border-gray-300 rounded text-gray-600"
        title={showColorbar ? 'Ocultar escala de color' : 'Mostrar escala de color'}
      >
        {showColorbar ? '🎨 ✕' : '🎨'}
      </button>
      <div
        ref={plotRef}
        style={{ width: '100%', height: '200px' }}
        className="border border-gray-300 rounded bg-white"
      />
    </div>
  );
}
