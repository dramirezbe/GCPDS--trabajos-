import { useState, useRef, forwardRef, useImperativeHandle } from 'react';
import { ZoomIn, ZoomOut, Trash2, Copy, RotateCcw, Maximize2, Settings, Download } from 'lucide-react';
import Plotly from 'plotly.js-dist-min';
import { SpectrumChart } from './SpectrumChart';
import { Waterfall } from './Waterfall';
import WebRTCAudioPlayer, { WebRTCAudioPlayerRef } from './WebRTCAudioPlayer';

interface Marker {
  id: string;
  frequency: number;
  power: number;
  color: string;
  isDelta?: boolean;
  deltaRef?: string;
}

type PowerUnit = 'dBm' | 'dBmV' | 'dBuV' | 'V' | 'W';
type FieldUnit = 'dBuV/m' | 'dBmV/m' | 'mV/m' | 'W/m²' | 'dBW/m²/MHz';

interface AnalysisPanelProps {
  data: { frequency: number; power: number }[];
  history: { frequency: number; power: number }[][];
  sensorName?: string;
  sensorMac?: string;
  isRealtime?: boolean;
  vbw?: string | number;
  rbw?: string | number;
  antennaGain?: number;
  sensorGps?: { lat: number; lng: number; alt?: number };
  demodType?: 'AM' | 'FM' | '';
  demodMetrics?: {
    excursion_hz?: number;
    depth?: number;
  };
}

export interface AnalysisPanelRef {
  startAudio: () => void;
  stopAudio: () => void;
}

export const AnalysisPanel = forwardRef<AnalysisPanelRef, AnalysisPanelProps>(({ data, history, sensorName, sensorMac, isRealtime, vbw, rbw, sensorGps, demodType, demodMetrics }, ref) => {
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [powerUnit, setPowerUnit] = useState<PowerUnit>('dBm');
  const [fieldUnit, setFieldUnit] = useState<FieldUnit>('dBuV/m');
  const [showControlPanel, setShowControlPanel] = useState(false);
  const [activeStats, setActiveStats] = useState<Set<string>>(new Set());
  const [zoomMode, setZoomMode] = useState(false);
  const [zoomArea, setZoomArea] = useState<{minFreq: number, maxFreq: number, minPower: number, maxPower: number} | null>(null);
  const [freqUnit, setFreqUnit] = useState<'Hz' | 'kHz' | 'MHz' | 'GHz'>('MHz');
  const chartRef = useRef<HTMLDivElement>(null);
  const audioPlayerRef = useRef<WebRTCAudioPlayerRef>(null);

  // Estados restaurados porque se usan en el JSX
  const [maxHold, setMaxHold] = useState(false);
  const [minHold, setMinHold] = useState(false);

  // Variables no usadas (limpieza)
  // const [activeTab, setActiveTab] = useState('radiodifusion');
  // const [showDeltaMarkers, setShowDeltaMarkers] = useState(false);
  // const [signalLevel, setSignalLevel] = useState(-60);
  // const [referenceLevel, setReferenceLevel] = useState(-30);

  // Exponer métodos de control de audio al componente padre
  useImperativeHandle(ref, () => ({
    startAudio: () => {
      audioPlayerRef.current?.startWebRTC();
    },
    stopAudio: () => {
      audioPlayerRef.current?.stopWebRTC();
    }
  }));

  const getPowerAtFrequency = (frequency: number): number => {
    if (!data || data.length === 0) return 0;
    let closest = data[0];
    for (let i = 1; i < data.length; i++) {
      if (Math.abs(data[i].frequency - frequency) < Math.abs(closest.frequency - frequency)) {
        closest = data[i];
      }
    }
    return Number.isFinite(closest?.power) ? closest.power : 0;
  };

  const getSafeConvertedPower = (powerDbm: number): number => {
    const safePower = Number.isFinite(powerDbm) ? powerDbm : 0;
    const converted = convertPower(safePower);
    return Number.isFinite(converted) ? converted : 0;
  };

  const handleAddMarker = (frequency: number) => {
    if (markers.length >= 10) {
      alert('Máximo 10 marcadores permitidos');
      return;
    }
    // Paleta de colores optimizada para fondo claro (evitando naranja #f97316)
    const colors = [
      '#DC2626', // Rojo
      '#2563EB', // Azul
      '#16A34A', // Verde
      '#9333EA', // Púrpura
      '#0891B2', // Cyan
      '#DB2777', // Rosa
      '#4F46E5', // Indigo
      '#0D9488', // Teal
      '#65A30D', // Lima
      '#475569'  // Slate
    ];
    const labels = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10'];
    const power = getPowerAtFrequency(frequency);
    const newMarker: Marker = {
      id: labels[markers.length],
      frequency,
      power,
      color: colors[markers.length % colors.length],
    };
    setMarkers([...markers, newMarker]);
  };

  // Convertir potencia de dBm a otras unidades
  const convertPower = (powerDbm: number): number => {
    switch (powerUnit) {
      case 'dBm':
        return powerDbm;
      case 'dBuV': {
        const powerW = Math.pow(10, powerDbm / 10) * 1e-3;
        const vrms = Math.sqrt(powerW * 50);
        return 20 * Math.log10(vrms / 1e-6);
      }
      case 'dBmV': {
        const powerW = Math.pow(10, powerDbm / 10) * 1e-3;
        const vrms = Math.sqrt(powerW * 50);
        return 20 * Math.log10(vrms / 1e-3);
      }
      default:
        return powerDbm;
    }
  };

  // Helper para calcular deltas
  const getDelta = (idx1: number, idx2: number) => {
    if (markers.length <= idx2) return null;
    const m1 = markers[idx1];
    const m2 = markers[idx2];
    
    // Colores para los deltas (distintos a naranja)
    const deltaColors = [
      '#4F46E5', // Indigo (M1-M2)
      '#DB2777', // Rosa (M3-M4)
      '#059669', // Emerald (M5-M6)
      '#7C3AED', // Violet (M7-M8)
      '#0891B2'  // Cyan (M9-M10)
    ];

    return {
      deltaFreq: Math.abs(m2.frequency - m1.frequency),
      deltaPower: m2.power - m1.power,
      marker1: m1.id,
      marker2: m2.id,
      color: deltaColors[Math.floor(idx1 / 2)]
    };
  };

  const toggleStat = (stat: string) => {
    const newStats = new Set(activeStats);
    if (newStats.has(stat)) {
      newStats.delete(stat);
    } else {
      newStats.add(stat);
    }
    setActiveStats(newStats);
  };

  // Colores para cada estadística
  const statColors = {
    min: '#10B981',     // Verde (tailwind green-500)
    max: '#EF4444',     // Rojo (tailwind red-500)
    avg: '#F59E0B',     // Naranja (tailwind amber-500)
    rms: '#8B5CF6',     // Violeta (tailwind violet-500)
    vbw: '#06B6D4'      // Cyan (tailwind cyan-500)
  };

  // Funciones de los botones
  const handleToggleZoom = () => {
    setZoomMode(!zoomMode);
  };

  const handleResetZoom = () => {
    setZoomArea(null);
    setZoomMode(false);
  };

  const handleReset = () => {
    setZoomArea(null);
    setZoomMode(false);
    setMarkers([]);
    setMaxHold(false);
    setMinHold(false);
    setActiveStats(new Set());
  };

  const handleCopyImage = async () => {
    const plotElement = chartRef.current?.querySelector('.js-plotly-plot') as Plotly.PlotlyHTMLElement | null;
    if (!plotElement) {
      alert('No se encontró el gráfico para copiar');
      return;
    }

    try {
      if (!navigator.clipboard || !navigator.clipboard.write || typeof ClipboardItem === 'undefined') {
        alert('Tu navegador no soporta copiar imágenes al portapapeles');
        return;
      }

      const width = Math.max(1, Math.round(plotElement.clientWidth || 1200));
      const height = Math.max(1, Math.round(plotElement.clientHeight || 400));
      const imageDataUrl = await Plotly.toImage(plotElement, {
        format: 'png',
        width,
        height,
        scale: 2,
      });

      const response = await fetch(imageDataUrl);
      const blob = await response.blob();
      const item = new ClipboardItem({ 'image/png': blob });
      await navigator.clipboard.write([item]);
      alert('Imagen copiada al portapapeles');
    } catch (error: any) {
      console.error('Error al copiar imagen:', error);
      if (error?.name === 'NotAllowedError') {
        alert('Permiso denegado. Permite el acceso al portapapeles en el navegador.');
      } else {
        alert('Error al copiar imagen');
      }
    }
  };

  const handleFullscreen = () => {
    if (!document.fullscreenElement && chartRef.current) {
      chartRef.current.requestFullscreen();
    } else if (document.fullscreenElement) {
      document.exitFullscreen();
    }
  };

  const handleDownloadCSV = () => {
    if (!data || data.length === 0) {
      alert('No hay datos disponibles para descargar');
      return;
    }

    // Crear encabezados CSV
    const headers = ['Frecuencia (Hz)', 'Potencia (dBm)'];
    
    // Agregar información adicional si está disponible
    let csvContent = 'data:text/csv;charset=utf-8,';
    
    // Información de metadata
    csvContent += `Sensor: ${sensorName || 'N/A'}\n`;
    csvContent += `Fecha: ${new Date().toLocaleString()}\n`;
    
    // Agregar GPS si está disponible
    if (sensorGps) {
      csvContent += `Latitud: ${Number(sensorGps.lat).toFixed(6)}\n`;
      csvContent += `Longitud: ${Number(sensorGps.lng).toFixed(6)}\n`;
      if (sensorGps.alt) {
        csvContent += `Altitud: ${Number(sensorGps.alt).toFixed(2)} m\n`;
      }
    }
    
    csvContent += `Número de puntos: ${data.length}\n`;
    csvContent += `Frecuencia mínima: ${Math.min(...data.map(d => d.frequency)).toFixed(2)} Hz\n`;
    csvContent += `Frecuencia máxima: ${Math.max(...data.map(d => d.frequency)).toFixed(2)} Hz\n`;
    csvContent += `Potencia mínima: ${Math.min(...data.map(d => d.power)).toFixed(2)} dBm\n`;
    csvContent += `Potencia máxima: ${Math.max(...data.map(d => d.power)).toFixed(2)} dBm\n`;
    csvContent += `\n`;
    
    // Encabezados de columnas
    csvContent += headers.join(',') + '\n';
    
    // Datos
    data.forEach(point => {
      const row = [
        point.frequency.toFixed(2),
        point.power.toFixed(2)
      ];
      csvContent += row.join(',') + '\n';
    });

    // Crear enlace de descarga
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    link.setAttribute('download', `spectrum_${sensorName || 'data'}_${timestamp}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex-1 bg-gray-50 p-3 md:p-6 overflow-y-auto">
      {/* Reproductor WebRTC con métricas de demodulación integradas */}
      {demodType && (demodType === 'AM' || demodType === 'FM') && (
        <WebRTCAudioPlayer 
          ref={audioPlayerRef}
          sensorId={sensorMac || sensorName || 'unknown'}
          wsUrl={`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:12443`}
          demodType={demodType}
          demodMetrics={demodMetrics}
        />
      )}

      {/* Header con estado de adquisición y GPS */}
      {isRealtime && sensorName && (
        <div className="mb-4 p-3 bg-gradient-to-r from-red-50 to-orange-50 border-2 border-red-300 rounded-lg shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
              </span>
              <p className="text-sm font-bold text-red-700">
                🔴 ADQUIRIENDO ESPECTRO - {sensorName}
              </p>
            </div>
            {sensorGps && (
              <div className="flex items-center gap-4 text-xs font-medium text-gray-700">
                <div>
                  <span className="text-gray-500">Lat:</span> {Number(sensorGps.lat).toFixed(6)}
                </div>
                <div>
                  <span className="text-gray-500">Lng:</span> {Number(sensorGps.lng).toFixed(6)}
                </div>
                {sensorGps.alt && (
                  <div>
                    <span className="text-gray-500">Alt:</span> {Number(sensorGps.alt).toFixed(1)}m
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      {!isRealtime && sensorName && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm text-blue-800">
              <span className="font-semibold">Sensor activo:</span> {sensorName}
            </p>
            {sensorGps && (
              <div className="flex items-center gap-4 text-xs font-medium text-gray-700">
                <div>
                  <span className="text-gray-500">Lat:</span> {Number(sensorGps.lat).toFixed(6)}
                </div>
                <div>
                  <span className="text-gray-500">Lng:</span> {Number(sensorGps.lng).toFixed(6)}
                </div>
                {sensorGps.alt && (
                  <div>
                    <span className="text-gray-500">Alt:</span> {Number(sensorGps.alt).toFixed(1)}m
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      {/* Contenedor de análisis (espectro + waterfall) para fullscreen */}
      <div ref={chartRef} className="bg-gray-50 rounded-lg p-1">
      {/* Gráfico de espectro */}
      <div className="bg-white border border-orange-200 rounded-lg shadow-sm mb-4">
        {/* Header con título y herramientas */}
        <div className="flex items-center justify-between p-4 pb-2">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            <span className="text-orange-600">📡</span> Espectro de Frecuencias
          </h3>
          
          {/* Botón de controles y herramientas */}
          <div className="flex gap-2">
            <button 
              onClick={() => setShowControlPanel(!showControlPanel)}
              className={`px-3 py-2 rounded transition-colors flex items-center gap-2 ${
                showControlPanel ? 'bg-orange-100 text-orange-600' : 'text-gray-600 hover:bg-gray-100'
              }`}
              title="Mostrar/ocultar controles"
            >
              <Settings className="w-4 h-4" />
              <span className="text-sm font-medium">Controles</span>
            </button>
            <div className="border-l border-gray-300 mx-1"></div>
            <button 
              onClick={handleToggleZoom}
              className={`p-2 rounded transition-colors ${
                zoomMode ? 'bg-orange-100 text-orange-600' : 'text-gray-600 hover:bg-gray-100'
              }`}
              title={zoomMode ? 'Desactivar selección de zoom' : 'Activar selección de zoom'}
            >
              <ZoomIn className="w-5 h-5" />
            </button>
            <button 
              onClick={handleResetZoom}
              className={`p-2 rounded transition-colors ${
                zoomArea ? 'text-gray-600 hover:bg-gray-100' : 'text-gray-300 cursor-not-allowed'
              }`}
              disabled={!zoomArea}
              title="Restablecer zoom"
            >
              <ZoomOut className="w-5 h-5" />
            </button>
            <button 
              onClick={() => setMarkers([])}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors" 
              title="Limpiar marcadores"
            >
              <Trash2 className="w-5 h-5" />
            </button>
            <button 
              onClick={handleCopyImage}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors" 
              title="Copiar imagen"
            >
              <Copy className="w-5 h-5" />
            </button>
            <button 
              onClick={handleDownloadCSV}
              className="p-2 text-orange-600 hover:bg-orange-100 rounded transition-colors" 
              title="Descargar datos CSV"
            >
              <Download className="w-5 h-5" />
            </button>
            <button 
              onClick={handleReset}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors" 
              title="Restablecer todo"
            >
              <RotateCcw className="w-5 h-5" />
            </button>
            <button 
              onClick={handleFullscreen}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded transition-colors" 
              title="Pantalla completa"
            >
              <Maximize2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Contenedor con gráfico y panel lateral */}
        <div className="relative">
          {/* Panel lateral de controles */}
          {showControlPanel && (
            <div className="absolute right-0 top-0 w-80 bg-white border-l border-gray-200 shadow-lg z-10 max-h-[600px] overflow-y-auto">
              <div className="p-4 space-y-4">
                {/* Selector de unidades */}
                <div className="space-y-3">
                  <h4 className="text-sm font-semibold text-gray-700">Unidades</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-xs text-gray-600">Frecuencia:</label>
                      <select
                        value={freqUnit}
                        onChange={(e) => setFreqUnit(e.target.value as 'Hz' | 'kHz' | 'MHz' | 'GHz')}
                        className="px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="Hz">Hz</option>
                        <option value="kHz">kHz</option>
                        <option value="MHz">MHz</option>
                        <option value="GHz">GHz</option>
                      </select>
                    </div>
                    <div className="flex items-center justify-between">
                      <label className="text-xs text-gray-600">Potencia:</label>
                      <select
                        value={powerUnit}
                        onChange={(e) => setPowerUnit(e.target.value as PowerUnit)}
                        className="px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="dBm">dBm</option>
                        <option value="dBmV">dBmV</option>
                        <option value="dBuV">dBμV</option>
                        <option value="V">V</option>
                        <option value="W">W</option>
                      </select>
                    </div>
                    <div className="flex items-center justify-between">
                      <label className="text-xs text-gray-600">Campo:</label>
                      <select
                        value={fieldUnit}
                        onChange={(e) => {
                          const val = e.target.value as FieldUnit;
                          setFieldUnit(val);
                          setPowerUnit(val as any);
                        }}
                        className="px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="dBuV/m">dBμV/m</option>
                        <option value="dBmV/m">dBmV/m</option>
                        <option value="mV/m">mV/m</option>
                        <option value="W/m²">W/m²</option>
                        <option value="dBW/m²/MHz">dBW/m²/MHz</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Marcadores */}
                <div className="border-t border-gray-200 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Marcadores</h4>
                  {markers.length > 0 ? (
                    <div className="space-y-1">
                      {markers.map((marker) => (
                        <div key={marker.id} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: marker.color }}></span>
                            <span className="font-semibold">{marker.id}:</span>
                            <span>{(marker.frequency / 1e6).toFixed(3)} MHz</span>
                            <span className="text-gray-500">|</span>
                            <span>{getSafeConvertedPower(marker.power).toFixed(2)} {powerUnit}</span>
                          </div>
                          <button
                            onClick={() => setMarkers(markers.filter(m => m.id !== marker.id))}
                            className="text-red-500 hover:text-red-700"
                          >
                            ×
                          </button>
                        </div>
                      ))}
                      {markers.length >= 2 && [0, 2, 4, 6, 8].map(i => {
                        const delta = getDelta(i, i + 1);
                        if (!delta) return null;
                        
                        // Determinar color de fondo basado en el color del delta (versión muy clara)
                        const bgStyle = {
                          backgroundColor: `${delta.color}10`, // 10% opacidad
                          borderColor: `${delta.color}40` // 40% opacidad para borde
                        };

                        return (
                          <div key={`delta-${i}`} className="mt-3 p-3 rounded border" style={bgStyle}>
                            <div className="text-xs font-semibold mb-2" style={{ color: delta.color }}>
                              Δ Delta ({delta.marker1} → {delta.marker2})
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="text-gray-600">Δ Frecuencia:</span>
                                <p className="font-semibold text-gray-900">
                                  {(delta.deltaFreq / 1e6).toFixed(6)} MHz
                                </p>
                              </div>
                              <div>
                                <span className="text-gray-600">Δ Potencia:</span>
                                <p className="font-semibold text-gray-900">
                                  {(getSafeConvertedPower(markers[i].power + delta.deltaPower) - getSafeConvertedPower(markers[i].power)).toFixed(2)} {powerUnit}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500">Haga clic en el gráfico para agregar marcadores (máx. 4)</p>
                  )}
                </div>

                {/* Retenciones */}
                <div className="border-t border-gray-200 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Retenciones</h4>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={maxHold}
                        onChange={(e) => setMaxHold(e.target.checked)}
                        className="rounded"
                      />
                      Traza máxima
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={minHold}
                        onChange={(e) => setMinHold(e.target.checked)}
                        className="rounded"
                      />
                      Traza mínima
                    </label>
                  </div>
                </div>

                {/* Estadísticas */}
                <div className="border-t border-gray-200 pt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Estadísticas</h4>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => toggleStat('min')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors font-medium ${
                        activeStats.has('min')
                          ? 'text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                      style={activeStats.has('min') ? { backgroundColor: statColors.min } : {}}
                    >
                      Min
                    </button>
                    <button
                      onClick={() => toggleStat('max')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors font-medium ${
                        activeStats.has('max')
                          ? 'text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                      style={activeStats.has('max') ? { backgroundColor: statColors.max } : {}}
                    >
                      Max
                    </button>
                    <button
                      onClick={() => toggleStat('avg')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors font-medium ${
                        activeStats.has('avg')
                          ? 'text-black shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                      style={activeStats.has('avg') ? { backgroundColor: statColors.avg } : {}}
                    >
                      Promedio
                    </button>
                    <button
                      onClick={() => toggleStat('rms')}
                      className={`px-3 py-1.5 text-xs rounded transition-colors font-medium ${
                        activeStats.has('rms')
                          ? 'text-white shadow-md'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                      style={activeStats.has('rms') ? { backgroundColor: statColors.rms } : {}}
                    >
                      RMS
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Gráfico principal */}
          <div className="px-4 pt-2 pb-1">
            <SpectrumChart
              data={data}
              markers={markers}
              onMarkerAdd={handleAddMarker}
              activeStats={activeStats}
              statColors={statColors}
              maxHold={maxHold}
              minHold={minHold}
              zoomMode={zoomMode}
              zoomArea={zoomArea}
              onZoomAreaChange={setZoomArea}
              vbw={vbw}
              rbw={rbw}
              freqUnit={freqUnit}
              powerUnit={powerUnit}
            />
          </div>
        </div>
      </div>

      <div className="px-4 pb-3">
        <Waterfall 
          history={history} 
          freqUnit={freqUnit} 
          minFreq={zoomArea?.minFreq}
          maxFreq={zoomArea?.maxFreq}
          stepRatio={0.1}
        />
      </div>
      </div>
    </div>
  );
});

AnalysisPanel.displayName = 'AnalysisPanel';
