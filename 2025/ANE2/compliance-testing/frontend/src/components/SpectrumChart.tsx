import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';

interface Marker {
  id: string;
  frequency: number;
  power: number;
  color: string;
}

interface SpectrumSeries {
  name: string;
  data: { frequency: number; power: number }[];
  color?: string;
}

interface SpectrumChartProps {
  data?: { frequency: number; power: number }[];
  series?: SpectrumSeries[];
  markers: Marker[];
  onMarkerAdd?: (frequency: number) => void;
  activeStats?: Set<string>;
  statColors?: { [key: string]: string };
  maxHold?: boolean;
  minHold?: boolean;
  zoomMode?: boolean;
  zoomArea?: {minFreq: number, maxFreq: number, minPower: number, maxPower: number} | null;
  onZoomAreaChange?: (area: {minFreq: number, maxFreq: number, minPower: number, maxPower: number} | null) => void;
  vbw?: string | number;
  rbw?: string | number;
  freqUnit?: 'Hz' | 'kHz' | 'MHz' | 'GHz';
  powerUnit?: string;
  antennaGain?: number;
  umbral?: number;
  noiseFloor?: number;
}

export function SpectrumChart({ data, series, markers, onMarkerAdd, activeStats, statColors, maxHold, minHold, zoomMode, zoomArea, onZoomAreaChange, vbw, rbw, freqUnit = 'MHz', powerUnit = 'dBm', antennaGain = 0, umbral, noiseFloor }: SpectrumChartProps) {
  const plotRef = useRef<HTMLDivElement>(null);
  const resizeRafRef = useRef<number | null>(null);
  const [maxHoldData, setMaxHoldData] = useState<{ frequency: number; power: number }[]>([]);
  const [minHoldData, setMinHoldData] = useState<{ frequency: number; power: number }[]>([]);
  const lastFreqRangeRef = useRef<string>('');
  const clickHandlerRef = useRef<((freq: number) => void) | null>(null);
  const zoomCallbackRef = useRef<((area: {minFreq: number, maxFreq: number, minPower: number, maxPower: number} | null) => void) | null>(null);
  const primaryDataRef = useRef<{ frequency: number; power: number }[]>([]);
  const freqUnitRef = useRef<'Hz' | 'kHz' | 'MHz' | 'GHz'>(freqUnit);
  const eventsAttachedRef = useRef(false);

  const displaySeries = useMemo(() => {
    if (series && series.length > 0) return series;
    if (data && data.length > 0) return [{ name: 'Sensor', data: data, color: '#f97316' }];
    return [];
  }, [data, series]);

  const primaryData = useMemo(() => {
    return displaySeries.length > 0 ? displaySeries[0].data : [];
  }, [displaySeries]);

  // Keep click handler ref up to date
  useEffect(() => {
    clickHandlerRef.current = onMarkerAdd || null;
  }, [onMarkerAdd]);

  // Keep zoom callback ref up to date
  useEffect(() => {
    zoomCallbackRef.current = onZoomAreaChange || null;
  }, [onZoomAreaChange]);

  // Keep latest data/unit refs for stable Plotly event handlers
  useEffect(() => {
    primaryDataRef.current = primaryData;
  }, [primaryData]);

  useEffect(() => {
    freqUnitRef.current = freqUnit;
  }, [freqUnit]);

  // Convertir potencia de dBm a otras unidades
  const convertPower = useCallback((powerDbm: number, frequencyHz?: number): number => {
    const gain = antennaGain || 0;
    switch (powerUnit) {
      case 'dBm':
        return powerDbm;
      case 'nW':
        return Math.pow(10, (powerDbm + 60) / 10);
      case 'mV':
        return Math.sqrt(50) * Math.pow(10, (powerDbm + 30) / 20);
      case 'dBmV':
        return powerDbm + 46.99;
      case 'dBuV':
        return powerDbm + 106.99;
      case 'dBuV/m': {
        if (frequencyHz === undefined || frequencyHz === null) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return 0;
        return powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
      }
      case 'dBmV/m': {
        if (frequencyHz === undefined || frequencyHz === null) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return 0;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
        return e_dbuv_m - 60;
      }
      case 'mV/m': {
        if (frequencyHz === undefined || frequencyHz === null) return 0;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return 0;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
        return Math.pow(10, (e_dbuv_m - 60) / 20);
      }
      case 'V/m': {
        if (frequencyHz === undefined || frequencyHz === null) return 0;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return 0;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
        return Math.pow(10, (e_dbuv_m - 120) / 20);
      }
      case 'W/m²': {
        if (frequencyHz === undefined || frequencyHz === null) return 0;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return 0;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
        const e_v_m = Math.pow(10, (e_dbuv_m - 120) / 20);
        return (e_v_m * e_v_m) / 377;
      }
      case 'dBW/m²/MHz': {
        if (frequencyHz === undefined || frequencyHz === null) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        if (freqMhz <= 0) return -200;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - gain;
        const e_v_m = Math.pow(10, (e_dbuv_m - 120) / 20);
        const s_w_m2 = (e_v_m * e_v_m) / 377;
        if (s_w_m2 <= 0) return -200;
        return 10 * Math.log10(s_w_m2);
      }
      default:
        return powerDbm;
    }
  }, [powerUnit, antennaGain]);

  // Convertir frecuencia a la unidad seleccionada
  const convertFrequency = useCallback((freqHz: number): number => {
    switch (freqUnit) {
      case 'Hz': return freqHz;
      case 'kHz': return freqHz / 1e3;
      case 'MHz': return freqHz / 1e6;
      case 'GHz': return freqHz / 1e9;
      default: return freqHz / 1e6;
    }
  }, [freqUnit]);

  // VBW smoothing
  const applyVBWSmoothing = useCallback((dataToSmooth: { frequency: number; power: number }[]) => {
    if (!vbw || dataToSmooth.length === 0) return dataToSmooth;

    let smoothingFactor = 1;
    const rbwValue = typeof rbw === 'string' ? parseFloat(rbw) : (rbw || 1000);

    if (typeof vbw === 'string') {
      if (vbw === 'rbw/5') smoothingFactor = 7;
      else if (vbw === 'rbw/3') smoothingFactor = 5;
      else if (vbw === 'rbw/2') smoothingFactor = 3;
      else if (vbw === 'rbw') smoothingFactor = 1;
      else {
        const vbwValue = parseFloat(vbw);
        if (!isNaN(vbwValue) && vbwValue > 0) {
          const ratio = vbwValue / rbwValue;
          if (ratio <= 0.2) smoothingFactor = 7;
          else if (ratio <= 0.33) smoothingFactor = 5;
          else if (ratio <= 0.5) smoothingFactor = 3;
          else smoothingFactor = 1;
        }
      }
    }

    if (smoothingFactor <= 1) return dataToSmooth;

    const smoothed: { frequency: number; power: number }[] = [];
    const windowSize = Math.min(smoothingFactor * 2 + 1, dataToSmooth.length);
    const halfWindow = Math.floor(windowSize / 2);

    for (let i = 0; i < dataToSmooth.length; i++) {
      let sum = 0;
      let count = 0;
      for (let j = Math.max(0, i - halfWindow); j <= Math.min(dataToSmooth.length - 1, i + halfWindow); j++) {
        sum += dataToSmooth[j].power;
        count++;
      }
      smoothed.push({ frequency: dataToSmooth[i].frequency, power: sum / count });
    }
    return smoothed;
  }, [vbw, rbw]);

  const getPowerAtFrequency = useCallback((frequencyHz: number): number => {
    if (primaryData.length === 0) return 0;
    let closest = primaryData[0];
    for (let i = 1; i < primaryData.length; i++) {
      if (Math.abs(primaryData[i].frequency - frequencyHz) < Math.abs(closest.frequency - frequencyHz)) {
        closest = primaryData[i];
      }
    }
    return closest.power;
  }, [primaryData]);

  // Reset maxHold/minHold when frequency range changes
  useEffect(() => {
    if (primaryData.length === 0) {
      if (lastFreqRangeRef.current !== '') {
        setMaxHoldData([]);
        setMinHoldData([]);
        lastFreqRangeRef.current = '';
      }
      return;
    }
    const firstFreq = primaryData[0]?.frequency ?? 0;
    const lastFreq = primaryData[primaryData.length - 1]?.frequency ?? 0;
    const rangeKey = `${primaryData.length}-${firstFreq.toFixed(0)}-${lastFreq.toFixed(0)}`;
    if (lastFreqRangeRef.current !== '' && lastFreqRangeRef.current !== rangeKey) {
      setMaxHoldData([]);
      setMinHoldData([]);
    }
    lastFreqRangeRef.current = rangeKey;
  }, [primaryData]);

  // Update hold data
  useEffect(() => {
    if (primaryData.length === 0) return;
    if (maxHold) {
      setMaxHoldData(prev => {
        if (prev.length === 0) return primaryData;
        return primaryData.map((point, i) => ({
          frequency: point.frequency,
          power: Math.max(point.power, prev[i]?.power || point.power)
        }));
      });
    } else {
      setMaxHoldData([]);
    }
    if (minHold) {
      setMinHoldData(prev => {
        if (prev.length === 0) return primaryData;
        return primaryData.map((point, i) => ({
          frequency: point.frequency,
          power: Math.min(point.power, prev[i]?.power || point.power)
        }));
      });
    } else {
      setMinHoldData([]);
    }
  }, [primaryData, maxHold, minHold]);

  // Cleanup Plotly on unmount
  useEffect(() => {
    return () => {
      if (resizeRafRef.current !== null) {
        cancelAnimationFrame(resizeRafRef.current);
      }
      if (plotRef.current) {
        Plotly.purge(plotRef.current);
      }
    };
  }, []);

  // Keep Plotly canvas in sync with container size changes (sidebar toggle/fullscreen).
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;

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
      observer.disconnect();
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      if (resizeRafRef.current !== null) {
        cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }
    };
  }, []);

  // Main render with Plotly
  useEffect(() => {
    if (!plotRef.current) return;
    if (displaySeries.length === 0) {
      Plotly.react(plotRef.current, [], {
        margin: { t: 10, r: 40, b: 40, l: 70 },
        plot_bgcolor: '#ffffff',
        paper_bgcolor: '#ffffff',
        xaxis: { title: { text: `Frecuencia (${freqUnit})` } },
        yaxis: { title: { text: powerUnit } },
      }, { responsive: true, displayModeBar: false });
      return;
    }

    // Calculate ranges
    let minFreq = Infinity, maxFreq = -Infinity;
    let minPower = Infinity, maxPower = -Infinity;

    if (zoomArea) {
      minFreq = zoomArea.minFreq;
      maxFreq = zoomArea.maxFreq;
      minPower = zoomArea.minPower;
      maxPower = zoomArea.maxPower;
    } else {
      displaySeries.forEach(serie => {
        if (!serie.data) return;
        for (const pt of serie.data) {
          if (pt.frequency < minFreq) minFreq = pt.frequency;
          if (pt.frequency > maxFreq) maxFreq = pt.frequency;
          if (pt.power < minPower) minPower = pt.power;
          if (pt.power > maxPower) maxPower = pt.power;
        }
      });
      if (minFreq === Infinity) return;
      minPower -= 5;
      maxPower += 5;
    }

    const defaultColors = ['#f97316', '#3b82f6', '#10b981', '#a855f7', '#ef4444', '#eab308', '#6366f1', '#ec4899'];
    const traces: Plotly.Data[] = [];

    // Series traces
    displaySeries.forEach((serie, index) => {
      let visibleData = serie.data.filter(pt => pt.frequency >= minFreq && pt.frequency <= maxFreq);
      visibleData = applyVBWSmoothing(visibleData);

      if (visibleData.length > 0) {
        const color = serie.color || defaultColors[index % defaultColors.length];
        traces.push({
          x: visibleData.map(pt => convertFrequency(pt.frequency)),
          y: visibleData.map(pt => convertPower(pt.power, pt.frequency)),
          type: 'scatter',
          mode: 'lines',
          name: serie.name,
          line: { color, width: 2 },
          hovertemplate: `Freq: %{x:.3f} ${freqUnit}<br>Power: %{y:.2f} ${powerUnit}<extra>${serie.name}</extra>`,
        });
      }
    });

    // Max hold trace
    if (maxHold && maxHoldData.length > 0) {
      let visibleMaxHold = maxHoldData.filter(pt => pt.frequency >= minFreq && pt.frequency <= maxFreq);
      visibleMaxHold = applyVBWSmoothing(visibleMaxHold);
      if (visibleMaxHold.length > 0) {
        traces.push({
          x: visibleMaxHold.map(pt => convertFrequency(pt.frequency)),
          y: visibleMaxHold.map(pt => convertPower(pt.power, pt.frequency)),
          type: 'scatter',
          mode: 'lines',
          name: 'Max Hold',
          line: { color: '#ff4444', width: 1.5, dash: 'dash' },
          hoverinfo: 'skip',
        });
      }
    }

    // Min hold trace
    if (minHold && minHoldData.length > 0) {
      let visibleMinHold = minHoldData.filter(pt => pt.frequency >= minFreq && pt.frequency <= maxFreq);
      visibleMinHold = applyVBWSmoothing(visibleMinHold);
      if (visibleMinHold.length > 0) {
        traces.push({
          x: visibleMinHold.map(pt => convertFrequency(pt.frequency)),
          y: visibleMinHold.map(pt => convertPower(pt.power, pt.frequency)),
          type: 'scatter',
          mode: 'lines',
          name: 'Min Hold',
          line: { color: '#44ff44', width: 1.5, dash: 'dash' },
          hoverinfo: 'skip',
        });
      }
    }

    // VBW stat trace (smooth overlay)
    if (activeStats?.has('vbw') && data && data.length > 0) {
      const windowSize = Math.max(3, Math.floor(data.length / 20));
      const vbwSmoothed: { frequency: number; power: number }[] = [];
      for (let i = 0; i < data.length; i++) {
        const start = Math.max(0, i - Math.floor(windowSize / 2));
        const end = Math.min(data.length, i + Math.ceil(windowSize / 2));
        let sum = 0;
        for (let j = start; j < end; j++) sum += data[j].power;
        vbwSmoothed.push({ frequency: data[i].frequency, power: sum / (end - start) });
      }
      traces.push({
        x: vbwSmoothed.map(pt => convertFrequency(pt.frequency)),
        y: vbwSmoothed.map(pt => convertPower(pt.power, pt.frequency)),
        type: 'scatter',
        mode: 'lines',
        name: 'VBW',
        line: { color: statColors?.vbw || '#8b5cf6', width: 2 },
        hoverinfo: 'skip',
      });
    }

    // Marker scatter points
    if (markers.length > 0) {
      traces.push({
        x: markers.map(m => convertFrequency(m.frequency)),
        y: markers.map(m => convertPower(getPowerAtFrequency(m.frequency), m.frequency)),
        type: 'scatter',
        mode: 'text+markers' as Plotly.PlotData['mode'],
        name: 'Markers',
        marker: {
          size: 10,
          color: markers.map(m => m.color),
          symbol: 'circle',
          line: { width: 1, color: '#fff' },
        },
        text: markers.map(m => m.id),
        textposition: 'top center',
        textfont: { size: 11, color: markers.map(m => m.color) },
        hovertemplate: markers.map(m => {
          const rawPower = getPowerAtFrequency(m.frequency);
          const val = convertPower(Number.isFinite(rawPower) ? rawPower : 0, m.frequency);
          const displayVal = Number.isFinite(val) ? val : 0;
          return `${m.id}<br>Freq: ${convertFrequency(m.frequency).toFixed(3)} ${freqUnit}<br>Power: ${displayVal.toFixed(2)} ${powerUnit}<extra></extra>`;
        }),
        showlegend: false,
      });
    }

    // Build shapes and annotations
    const shapes: Partial<Plotly.Shape>[] = [];
    const annotations: Partial<Plotly.Annotations>[] = [];

    // Marker vertical dashed lines
    markers.forEach(m => {
      const freqConverted = convertFrequency(m.frequency);
      shapes.push({
        type: 'line',
        x0: freqConverted,
        x1: freqConverted,
        y0: 0,
        y1: 1,
        yref: 'paper',
        line: { color: m.color, width: 1, dash: 'dot' },
      });
    });

    // Delta lines between marker pairs
    const deltaColors = ['#4F46E5', '#DB2777', '#059669', '#7C3AED', '#0891B2'];
    for (let i = 0; i < markers.length - 1; i += 2) {
      const m1 = markers[i];
      const m2 = markers[i + 1];
      if (!m2) break;
      const color = deltaColors[Math.floor(i / 2)] || '#4F46E5';
      const f1 = convertFrequency(m1.frequency);
      const f2 = convertFrequency(m2.frequency);
      const p1 = convertPower(getPowerAtFrequency(m1.frequency), m1.frequency);
      const p2 = convertPower(getPowerAtFrequency(m2.frequency), m2.frequency);

      // Horizontal delta line
      shapes.push({
        type: 'line',
        x0: f1, x1: f2,
        y0: p1, y1: p1,
        line: { color, width: 2 },
      });
      // Vertical delta line
      shapes.push({
        type: 'line',
        x0: f2, x1: f2,
        y0: p1, y1: p2,
        line: { color, width: 2 },
      });

      const deltaFreq = Math.abs(m2.frequency - m1.frequency);
      const deltaPower = convertPower(m2.power, m2.frequency) - convertPower(m1.power, m1.frequency);
      annotations.push({
        x: (f1 + f2) / 2,
        y: p1,
        text: `Δf: ${(deltaFreq / 1e6).toFixed(3)} MHz`,
        showarrow: false,
        font: { color, size: 11, family: 'sans-serif' },
        yshift: 12,
      });
      annotations.push({
        x: f2,
        y: (p1 + p2) / 2,
        text: `Δp: ${deltaPower.toFixed(2)} ${powerUnit}`,
        showarrow: false,
        font: { color, size: 11, family: 'sans-serif' },
        xshift: 40,
      });
    }

    // Stat horizontal lines (min / max / avg / rms)
    if (activeStats && activeStats.size > 0 && statColors && data && data.length > 0) {
      let sum = 0, sumLinearPower = 0, min = Infinity, max = -Infinity;
      for (const pt of data) {
        sum += pt.power;
        const linearPower = Math.pow(10, pt.power / 10);
        sumLinearPower += linearPower * linearPower;
        if (pt.power < min) min = pt.power;
        if (pt.power > max) max = pt.power;
      }
      const avg = sum / data.length;
      const rmsLinear = Math.sqrt(sumLinearPower / data.length);
      const rms = 10 * Math.log10(rmsLinear);
      const centerFreq = minFreq + (maxFreq - minFreq) / 2;

      const statEntries: { key: string; val: number }[] = [];
      if (activeStats.has('min')) statEntries.push({ key: 'min', val: min });
      if (activeStats.has('max')) statEntries.push({ key: 'max', val: max });
      if (activeStats.has('avg')) statEntries.push({ key: 'avg', val: avg });
      if (activeStats.has('rms')) statEntries.push({ key: 'rms', val: rms });

      statEntries.forEach(({ key, val }) => {
        const convertedVal = convertPower(val, centerFreq);
        shapes.push({
          type: 'line',
          x0: 0, x1: 1,
          xref: 'paper',
          y0: convertedVal, y1: convertedVal,
          line: { color: statColors[key], width: 1.5, dash: 'dashdot' },
        });
        annotations.push({
          x: 0.01,
          xref: 'paper',
          y: convertedVal,
          text: `${key.toUpperCase()}: ${convertedVal.toFixed(1)} ${powerUnit}`,
          showarrow: false,
          font: { color: statColors[key], size: 11, family: 'sans-serif' },
          yshift: -12,
          xanchor: 'left',
        });
      });
    }

    // Threshold line (umbral)
    if (umbral !== undefined && noiseFloor !== undefined) {
      const thresholdLevel = noiseFloor + umbral;
      const centerFreq = minFreq + (maxFreq - minFreq) / 2;
      const convertedThreshold = convertPower(thresholdLevel, centerFreq);
      shapes.push({
        type: 'line',
        x0: 0, x1: 1,
        xref: 'paper',
        y0: convertedThreshold, y1: convertedThreshold,
        line: { color: '#ef4444', width: 2, dash: 'dash' },
      });
      annotations.push({
        x: 0.99,
        xref: 'paper',
        y: convertedThreshold,
        text: `Umbral: ${convertedThreshold.toFixed(1)} ${powerUnit} (NF+${umbral}dB)`,
        showarrow: false,
        font: { color: '#ef4444', size: 12, family: 'sans-serif' },
        yshift: -14,
        xanchor: 'right',
      });
    }

    // Compute Y-axis range in converted units
    const centerFreqForRange = minFreq + (maxFreq - minFreq) / 2;
    const yMin = convertPower(minPower, centerFreqForRange);
    const yMax = convertPower(maxPower, centerFreqForRange);

    const layout: Partial<Plotly.Layout> = {
      margin: { t: 10, r: 40, b: 40, l: 70 },
      showlegend: displaySeries.length > 1 || (maxHold === true && maxHoldData.length > 0) || (minHold === true && minHoldData.length > 0),
      legend: {
        x: 1, y: 1,
        xanchor: 'right',
        bgcolor: 'rgba(255,255,255,0.8)',
        bordercolor: '#e5e7eb',
        borderwidth: 1,
        font: { size: 11 },
      },
      xaxis: {
        title: { text: `Frecuencia (${freqUnit})`, font: { size: 12, color: '#4b5563' } },
        range: [convertFrequency(minFreq), convertFrequency(maxFreq)],
        gridcolor: '#e5e7eb',
        linecolor: '#d1d5db',
        zerolinecolor: '#e5e7eb',
        fixedrange: !zoomMode,
      },
      yaxis: {
        title: { text: powerUnit, font: { size: 12, color: '#4b5563' } },
        range: [yMin, yMax],
        gridcolor: '#e5e7eb',
        linecolor: '#d1d5db',
        zerolinecolor: '#e5e7eb',
        fixedrange: !zoomMode,
      },
      plot_bgcolor: '#ffffff',
      paper_bgcolor: '#ffffff',
      shapes,
      annotations,
      dragmode: zoomMode ? 'zoom' : 'pan',
    };

    const config: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: false,
      scrollZoom: false,
    };

    Plotly.react(plotRef.current, traces, layout, config);

    // Attach events after Plotly has initialized the DOM element
    if (!eventsAttachedRef.current) {
      eventsAttachedRef.current = true;
      const el = plotRef.current as any;

      el.addEventListener('click', (event: MouseEvent) => {
        if (!clickHandlerRef.current) return;
        const rect = el.getBoundingClientRect();
        const fullLayout = el._fullLayout;
        const clickedFreqConverted = fullLayout.xaxis.p2l(event.clientX - rect.left - fullLayout._size.l);
        const currentFreqUnit = freqUnitRef.current;
        let clickedFreqHz: number;
        switch (currentFreqUnit) {
          case 'Hz': clickedFreqHz = clickedFreqConverted; break;
          case 'kHz': clickedFreqHz = clickedFreqConverted * 1e3; break;
          case 'GHz': clickedFreqHz = clickedFreqConverted * 1e9; break;
          default: clickedFreqHz = clickedFreqConverted * 1e6; break;
        }
        clickHandlerRef.current(clickedFreqHz);
      });

      el.on('plotly_relayout', (eventData: any) => {
        if (!zoomCallbackRef.current) return;
        if (eventData['xaxis.range[0]'] !== undefined && eventData['yaxis.range[0]'] !== undefined) {
          const xMin = eventData['xaxis.range[0]'];
          const xMax = eventData['xaxis.range[1]'];
          const yMinVal = eventData['yaxis.range[0]'];
          const yMaxVal = eventData['yaxis.range[1]'];
          let freqMultiplier = 1e6;
          switch (freqUnit) {
            case 'Hz': freqMultiplier = 1; break;
            case 'kHz': freqMultiplier = 1e3; break;
            case 'GHz': freqMultiplier = 1e9; break;
          }
          zoomCallbackRef.current({
            minFreq: xMin * freqMultiplier,
            maxFreq: xMax * freqMultiplier,
            minPower: yMinVal,
            maxPower: yMaxVal,
          });
        } else if (eventData['xaxis.autorange'] || eventData['yaxis.autorange']) {
          zoomCallbackRef.current(null);
        }
      });
    }
  }, [displaySeries, markers, activeStats, statColors, maxHold, minHold, maxHoldData, minHoldData,
      zoomArea, zoomMode, vbw, rbw, freqUnit, powerUnit, convertPower, convertFrequency,
      applyVBWSmoothing, umbral, noiseFloor, data]);

  return (
    <div className="relative">
      <div
        ref={plotRef}
        style={{ width: '100%', height: '400px' }}
        className="border border-gray-300 rounded"
      />
    </div>
  );
}
