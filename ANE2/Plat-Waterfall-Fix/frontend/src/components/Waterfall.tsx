import { memo, useEffect, useRef, useMemo, useState } from 'react';
import Plotly from 'plotly.js-dist-min';

const WATERFALL_POWER_LABEL = 'units';
const WATERFALL_MIN_POWER = -70;
const WATERFALL_MAX_POWER = 5;

interface WaterfallProps {
  history: { frequency: number; power: number }[][];
  freqUnit?: 'Hz' | 'kHz' | 'MHz' | 'GHz';
  powerUnit?: string;
  stepRatio?: number;
  minFreq?: number;
  maxFreq?: number;
}

export const Waterfall = memo(function Waterfall({ history, freqUnit = 'MHz', minFreq, maxFreq }: WaterfallProps) {
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

    // Base span from newest snapshot, then clamp/override with zoomed range when provided.
    const snapshotMinFreq = refSnapshot[0].frequency;
    const snapshotMaxFreq = refSnapshot[refSnapshot.length - 1].frequency;
    const requestedMinFreq = minFreq ?? snapshotMinFreq;
    const requestedMaxFreq = maxFreq ?? snapshotMaxFreq;
    const effectiveMinFreq = Math.max(snapshotMinFreq, Math.min(requestedMinFreq, requestedMaxFreq));
    const effectiveMaxFreq = Math.min(snapshotMaxFreq, Math.max(requestedMinFreq, requestedMaxFreq));

    if (effectiveMaxFreq <= effectiveMinFreq) return;

    // Build x-axis labels (frequency values)
    // We resample each history snapshot to a consistent set of frequency bins,
    // preserving relative resolution when a zoomed frequency window is active.
    const fullSpan = Math.max(snapshotMaxFreq - snapshotMinFreq, 1);
    const effectiveSpan = effectiveMaxFreq - effectiveMinFreq;
    const spanRatio = Math.max(0.01, Math.min(1, effectiveSpan / fullSpan));
    const numBins = Math.max(10, Math.min(600, Math.round(refSnapshot.length * spanRatio)));
    const freqStep = numBins > 1 ? effectiveSpan / (numBins - 1) : effectiveSpan;
    const freqLabels: number[] = [];
    for (let i = 0; i < numBins; i++) {
      freqLabels.push(convertFrequency(effectiveMinFreq + i * freqStep));
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
        const targetFreq = effectiveMinFreq + i * freqStep;
        
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
    const zData: number[][] = Array.from({ length: MAX_CACHED_SIGNALS }, (_, rowIndex) => {
      if (rowIndex < builtRows.length) return builtRows[rowIndex];
      // Use NaN for missing rows to avoid any color interpolation artifacts
      // while the fixed 5-row cache is being repopulated after a reset.
      return new Array(numBins).fill(Number.NaN);
    });

    const powerRange = Math.max(WATERFALL_MAX_POWER - WATERFALL_MIN_POWER, 1e-9);

    // Fixed normalization: -70 -> 0% and 0 -> 100%, clamped outside the range.
    const normalizedZData = zData.map(row =>
      row.map(value => {
        if (!Number.isFinite(value)) return Number.NaN;
        const normalized = ((value - WATERFALL_MIN_POWER) / powerRange) * 100;
        return Math.max(0, Math.min(100, normalized));
      })
    );

    // Hash check to avoid unnecessary full redraws (just length + first snapshot identity)
    const newHash = `${cachedHistory.length}-${refSnapshot.length}-${effectiveMinFreq.toFixed(0)}-${effectiveMaxFreq.toFixed(0)}`;

    const traces: Plotly.Data[] = [
      {
        x: freqLabels,
        y: ySlots,
        z: normalizedZData,
        customdata: zData,
        type: 'heatmap',
        zauto: false,
        zmin: 0,
        zmax: 100,
        zsmooth: false,
        connectgaps: false,
        colorscale: [
          [0.0, '#03061a'],
          [0.08, '#0a1c5c'],
          [0.16, '#1a4db5'],
          [0.24, '#148be6'],
          [0.32, '#00c2ff'],
          [0.4, '#00f0ff'],
          [0.48, '#00e070'],
          [0.56, '#7de000'],
          [0.64, '#d6f000'],
          [0.72, '#ffe100'],
          [0.8, '#ffad00'],
          [0.88, '#ff6900'],
          [0.94, '#ff2a00'],
          [1.0, '#fff2ea'],
        ],
        hoverongaps: false,
        showscale: showColorbar,
        colorbar: {
          title: { text: `${WATERFALL_POWER_LABEL} / %`, side: 'right', font: { size: 11 } },
          thickness: 15,
          len: 0.9,
          tickvals: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
          ticktext: ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'],
        },
        hovertemplate: `Freq: %{x:.3f} ${freqUnit}<br>Power: %{customdata:.1f} ${WATERFALL_POWER_LABEL}<br>Normalized: %{z:.0f}%<br>Sweep: %{y}<extra></extra>`,
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
  }, [history, freqUnit, convertFrequency, minFreq, maxFreq, showColorbar]);

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
}, (prevProps, nextProps) => {
  return (
    prevProps.history === nextProps.history &&
    prevProps.freqUnit === nextProps.freqUnit &&
    prevProps.powerUnit === nextProps.powerUnit &&
    prevProps.minFreq === nextProps.minFreq &&
    prevProps.maxFreq === nextProps.maxFreq
  );
});
