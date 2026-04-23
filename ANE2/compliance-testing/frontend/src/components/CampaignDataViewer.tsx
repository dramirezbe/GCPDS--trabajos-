import { useState, useEffect, useRef, useMemo } from 'react';
import { X, Download, Loader2, ZoomIn, ZoomOut, Trash2, Copy, RotateCcw, Maximize2, ChevronLeft, Settings, FileText, Layers, Activity, Info, ChevronDown } from 'lucide-react';
import Plotly from 'plotly.js-dist-min';
import { SpectrumChart } from './SpectrumChart';
import { Waterfall } from './Waterfall';
import axios from 'axios';
import { ComplianceReport } from './ComplianceReport';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface CampaignDataViewerProps {
  campaignId: number;
  campaignName: string;
  sensors: string[];
  allSensors?: { mac: string; name: string }[];
  onClose: () => void;
}

interface SpectrumData {
  frequency: number;
  power: number;
}

interface SpectrumSeries {
  name: string;
  data: SpectrumData[];
  color?: string;
}

interface Marker {
  id: string;
  frequency: number;
  power?: number;
  color: string;
  isDelta?: boolean;
  deltaRef?: string;
}

type FieldUnit = 'dBuV/m' | 'dBmV/m' | 'mV/m' | 'V/m' | 'W/m²' | 'dBW/m²/MHz';

interface MeasurementData {
  timestamp: string | number;
  lat: number | null;
  lng: number | null;
  spectrum: SpectrumData[];
}

export function CampaignDataViewer({ campaignId, campaignName, sensors, allSensors, onClose }: CampaignDataViewerProps) {
  const [loading, setLoading] = useState(true);
  
  // Estado para gestión de múltiples sensores
  const [selectedSensor, setSelectedSensor] = useState<string>(sensors[0] || '');
  const [viewMode, setViewMode] = useState<'individual' | 'combined'>('individual');
  const [multiSensorData, setMultiSensorData] = useState<Record<string, { spectrum: SpectrumData[][], measurements: MeasurementData[] }>>({});
  
  // Estado para datos actuales (del sensor seleccionado o combinados para visualización)
  const [spectrumData, setSpectrumData] = useState<SpectrumData[][]>([]);
  const [measurements, setMeasurements] = useState<MeasurementData[]>([]);
  
  const [currentMeasurementIndex, setCurrentMeasurementIndex] = useState(0); // Índice de medición actual
  const [isPlaying, setIsPlaying] = useState(false); // Estado de reproducción
  const [playSpeed, setPlaySpeed] = useState(1000); // Velocidad de reproducción en ms
  const [error, setError] = useState<string>('');
  
  // Estados para funcionalidad avanzada
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [powerUnit, setPowerUnit] = useState<string>('dBm');
  const [fieldUnit, setFieldUnit] = useState<FieldUnit>('dBuV/m'); // Usado en el select de unidades
  const [antennaGain, setAntennaGain] = useState<number>(0);
  const [maxHold, setMaxHold] = useState(false);
  const [minHold, setMinHold] = useState(false);
  const [activeStats, setActiveStats] = useState<Set<string>>(new Set());
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomMode, setZoomMode] = useState(false);
  const [zoomArea, setZoomArea] = useState<{minFreq: number, maxFreq: number, minPower: number, maxPower: number} | null>(null);
  const [freqUnit, setFreqUnit] = useState<'Hz' | 'kHz' | 'MHz' | 'GHz'>('MHz');
  const [showControlPanel, setShowControlPanel] = useState(false);
  const [showReportPanel, setShowReportPanel] = useState(false);
  const [umbral, setUmbral] = useState<number>(5);
  const [reportMode, setReportMode] = useState<'automatic' | 'manual'>('automatic');
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportData, setReportData] = useState<any>(null);
  const [showFullReportModal, setShowFullReportModal] = useState(false);
  const [campaignInfo, setCampaignInfo] = useState<any>(null);
  const [showCampaignInfo, setShowCampaignInfo] = useState(false);
  const chartRef = useRef<HTMLDivElement>(null);
  const playIntervalRef = useRef<NodeJS.Timeout | null>(null);


  // Auto-play: avanzar automáticamente cuando está reproduciendo
  useEffect(() => {
    if (isPlaying && spectrumData.length > 0) {
      playIntervalRef.current = setInterval(() => {
        setCurrentMeasurementIndex(prev => {
          if (prev >= spectrumData.length - 1) {
            setIsPlaying(false); // Detener al llegar al final
            return prev;
          }
          return prev + 1;
        });
      }, playSpeed);
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    }

    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, [isPlaying, spectrumData.length, playSpeed]);

  // Cargar configuración de la campaña para obtener ganancia de antena
  useEffect(() => {
    const fetchCampaignConfig = async () => {
      try {
        if (campaignId === 99999) return; // Simulado
        const response = await axios.get(`${API_BASE_URL}/campaigns/${campaignId}`);
        const campaignData = response.data;
        const config = campaignData.config;
        
        // Guardar info completa de la campaña
        setCampaignInfo(campaignData);
        
        // Determinar ganancia. Puede venir en 'config' o necesitar buscar la antena.
        // Si config tiene antenna (ID), buscar la antena.
        // Si config tiene ganancia manual (no común en este sistema, pero posible), usarla.
        
        if (config.antenna) {
            // El ID de antena suele ser "RX-1", "RX-2" o un ID numérico en string
            // Pero en CampaignModal vimos que se guarda el ID de la tabla antennas.
            const antennaId = config.antenna.replace('RX-', '');
            
            // Buscar detalles de la antena
            // Podríamos tener una lista de antenas cargada o hacer fetch
            try {
                const antResponse = await axios.get(`${API_BASE_URL}/antennas/${antennaId}`);
                if (antResponse.data && antResponse.data.gain_db) {
                    setAntennaGain(antResponse.data.gain_db);
                    console.log(`Ganancia de antena cargada: ${antResponse.data.gain_db} dBi`);
                }
            } catch (e) {
                console.warn('No se pudo cargar detalles de la antena, usando ganancia 0', e);
            }
        }
      } catch (err) {
        console.error('Error loading campaign config:', err);
      }
    };
    fetchCampaignConfig();
  }, [campaignId]);

  useEffect(() => {
    // Para campañas guardadas, cargar los datos automáticamente
    // SOLO iniciar en blanco si es campaña simulada (ID 99999) o si no hay campaignId
    if (campaignId && campaignId !== 99999) {
      loadCampaignData();
    } else {
      // Para campaña simulada o sin ID, solo establecer loading en false
      setLoading(false);
    }
  }, [campaignId, selectedSensor, viewMode]);

  const loadCampaignData = async () => {
    try {
      setLoading(true);
      setError('');

      // Si es la campaña simulada (ID 99999), usar datos generados localmente
      if (campaignId === 99999) {
        // Simular retardo de red
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // Generar datos simulados de espectro (ruido + picos)
        const { generateSpectrumData } = await import('../utils/generateData');
        const simulatedSpectrum = generateSpectrumData(470e6, 698e6, 1000);
        
        // Convertir a estructura de visualización
        const processedSpectrum = simulatedSpectrum.map(p => ({
          frequency: p.frequency,
          power: p.power
        }));
        
        // Crear una medición simulada
        const simulatedMeasurement: MeasurementData = {
          timestamp: Date.now(),
          lat: 4.7110,
          lng: -74.0721,
          spectrum: processedSpectrum
        };
        
        setSpectrumData([processedSpectrum]);
        setMeasurements([simulatedMeasurement]);
        setLoading(false);
        return;
      }

      // Determinar qué sensores necesitamos cargar
      const sensorsToFetch = viewMode === 'combined' ? sensors : [selectedSensor];
      const newMultiSensorData = { ...multiSensorData };
      let dataUpdated = false;

      for (const sensor of sensorsToFetch) {
        if (!sensor) continue;
        
        // Si ya tenemos datos para este sensor, marcar como actualizado pero no recargar
        if (newMultiSensorData[sensor]) {
          dataUpdated = true;
          console.log(`📦 Usando datos en caché para sensor ${sensor}`);
          continue;
        }

        // Cargar datos de la campaña desde el backend para este sensor
        console.log(`📡 Cargando datos desde backend para sensor ${sensor}`);
        const response = await axios.get(`${API_BASE_URL}/campaigns/${campaignId}/data?sensor_mac=${sensor}`);
        const data = response.data;
        
        // Procesar datos de espectro
        if (data.measurements && data.measurements.length > 0) {
          const processedMeasurements: MeasurementData[] = [];
          const processedSpectrum = data.measurements.map((measurement: any) => {
            const pxx = JSON.parse(measurement.pxx);
            // Convertir a número explícitamente
            const startFreq = Number(measurement.start_freq_hz);
            const endFreq = Number(measurement.end_freq_hz);
            const freqStep = (endFreq - startFreq) / (pxx.length - 1);
            
            const spectrumPoints = pxx.map((power: number, index: number) => ({
              frequency: startFreq + index * freqStep, // Hz
              power: power // dBm
            }));

            // Guardar medición completa con timestamp
            processedMeasurements.push({
              timestamp: typeof measurement.timestamp === 'string' ? parseInt(measurement.timestamp) : measurement.timestamp,
              lat: measurement.lat,
              lng: measurement.lng,
              spectrum: spectrumPoints
            });

            return spectrumPoints;
          });

          newMultiSensorData[sensor] = {
            spectrum: processedSpectrum,
            measurements: processedMeasurements
          };
          dataUpdated = true;
        }
      }

      if (dataUpdated) {
        setMultiSensorData(newMultiSensorData);
      }

      // Actualizar datos de visualización actual
      console.log(`📊 Actualizando visualización - Modo: ${viewMode}, Sensor seleccionado: ${selectedSensor}`);
      console.log(`📊 Sensores con datos:`, Object.keys(newMultiSensorData));
      
      if (viewMode === 'individual') {
        const sensorData = newMultiSensorData[selectedSensor];
        console.log(`📊 Buscando datos para sensor ${selectedSensor}:`, sensorData ? 'ENCONTRADO' : 'NO ENCONTRADO');
        if (sensorData) {
          console.log(`📊 Estableciendo ${sensorData.spectrum.length} mediciones en modo individual`);
          setSpectrumData(sensorData.spectrum);
          setMeasurements(sensorData.measurements);
        } else {
          console.warn(`⚠️ No hay datos para el sensor seleccionado ${selectedSensor}`);
          setSpectrumData([]);
          setMeasurements([]);
        }
      } else {
        // Modo combinado: Usar el sensor con MÁS mediciones como referencia
        // Todos los sensores de la misma campaña comparten el mismo inicio/fin/intervalo,
        // por lo que deberían tener la misma cantidad de muestras.
        // Usamos el máximo para garantizar consistencia en la navegación.
        let maxMeasurements = 0;
        let referenceSensorMac = selectedSensor || sensors[0];
        
        for (const [sensorMac, sData] of Object.entries(newMultiSensorData)) {
          if (sData.spectrum.length > maxMeasurements) {
            maxMeasurements = sData.spectrum.length;
            referenceSensorMac = sensorMac;
          }
        }
        
        const sensorData = newMultiSensorData[referenceSensorMac];
        
        if (sensorData) {
          setSpectrumData(sensorData.spectrum);
          setMeasurements(sensorData.measurements);
          console.log(`📊 Modo combinado: usando sensor ${referenceSensorMac} como referencia (${sensorData.spectrum.length} mediciones)`);
        } else if (Object.keys(newMultiSensorData).length > 0) {
          const firstAvailable = Object.values(newMultiSensorData)[0];
          setSpectrumData(firstAvailable.spectrum);
          setMeasurements(firstAvailable.measurements);
        }
      }

    } catch (err: any) {
      console.error('Error loading campaign data:', err);
      setError(err.message || 'Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  };

  // Funciones para marcadores
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
    const newMarker: Marker = {
      id: labels[markers.length],
      frequency,
      color: colors[markers.length % colors.length],
    };
    setMarkers([...markers, newMarker]);
  };

  const getMarkerPowerAtFrequency = (frequency: number): number => {
    if (!currentSpectrumData || currentSpectrumData.length === 0) return 0;
    let closest = currentSpectrumData[0];
    for (let i = 1; i < currentSpectrumData.length; i++) {
      if (Math.abs(currentSpectrumData[i].frequency - frequency) < Math.abs(closest.frequency - frequency)) {
        closest = currentSpectrumData[i];
      }
    }
    return Number.isFinite(closest?.power) ? closest.power : 0;
  };

  const getSafeConvertedMarkerPower = (frequency: number): number => {
    const rawPower = getMarkerPowerAtFrequency(frequency);
    const convertedPower = convertPower(Number.isFinite(rawPower) ? rawPower : 0, frequency);
    return Number.isFinite(convertedPower) ? convertedPower : 0;
  };

  // Convertir potencia de dBm a otras unidades
  const convertPower = (powerDbm: number, frequencyHz?: number): number => {
    switch (powerUnit) {
      case 'dBm':
        return powerDbm;
      case 'nW': {
        // dBm -> nW
        return Math.pow(10, (powerDbm + 60) / 10);
      }
      case 'mV': {
        // dBm -> mV (rms)
        return Math.sqrt(50) * Math.pow(10, (powerDbm + 30) / 20);
      }
      case 'dBmV': {
        // dBm -> dBmV
        return powerDbm + 46.99;
      }
      case 'dBuV': {
        // dBm -> dBµV
        return powerDbm + 106.99;
      }
      // Unidades de campo
      case 'dBuV/m': {
        if (!frequencyHz) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        return powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
      }
      case 'dBmV/m': {
        if (!frequencyHz) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
        return e_dbuv_m - 60;
      }
      case 'mV/m': {
        if (!frequencyHz) return 0;
        const freqMhz = frequencyHz / 1e6;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
        return Math.pow(10, (e_dbuv_m - 60) / 20);
      }
      case 'V/m': {
        if (!frequencyHz) return 0;
        const freqMhz = frequencyHz / 1e6;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
        return Math.pow(10, (e_dbuv_m - 120) / 20);
      }
      case 'W/m²': {
        if (!frequencyHz) return 0;
        const freqMhz = frequencyHz / 1e6;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
        const e_v_m = Math.pow(10, (e_dbuv_m - 120) / 20);
        return (e_v_m * e_v_m) / 377;
      }
      case 'dBW/m²/MHz': {
        if (!frequencyHz) return powerDbm;
        const freqMhz = frequencyHz / 1e6;
        const e_dbuv_m = powerDbm + 77.23 + 20 * Math.log10(freqMhz) - antennaGain;
        const e_v_m = Math.pow(10, (e_dbuv_m - 120) / 20);
        const s_w_m2 = (e_v_m * e_v_m) / 377;
        return 10 * Math.log10(s_w_m2);
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
    const p1 = getMarkerPowerAtFrequency(m1.frequency);
    const p2 = getMarkerPowerAtFrequency(m2.frequency);
    
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
      deltaPower: p2 - p1,
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

  // Colores para estadísticas (modo claro)
  const statColors = {
    min: '#65a30d',
    max: '#dc2626',
    avg: '#ca8a04',
    rms: '#c026d3',
    vbw: '#0891b2'
  };

  // Funciones de control
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
      // Verificar si el navegador soporta clipboard API
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

      const renderedChart = new Image();
      await new Promise<void>((resolve, reject) => {
        renderedChart.onload = () => resolve();
        renderedChart.onerror = () => reject(new Error('No se pudo cargar la imagen exportada del gráfico'));
        renderedChart.src = imageDataUrl;
      });

      // Crear canvas temporal con espacio para el título
      const tempCanvas = document.createElement('canvas');
      const ctx = tempCanvas.getContext('2d');
      if (!ctx) {
        alert('Error al crear el canvas temporal');
        return;
      }

      // Configurar dimensiones (agregar 60px arriba para el título)
      const titleHeight = 60;
      tempCanvas.width = renderedChart.width;
      tempCanvas.height = renderedChart.height + titleHeight;

      // Fondo blanco
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

      // Dibujar título
      
      // Línea 1: Sensor (centrado completo)
      ctx.font = 'bold 16px Arial';
      ctx.textAlign = 'center';
      const sensorName = allSensors?.find(s => s.mac === selectedSensor)?.name || selectedSensor;
      const sensorText = `Sensor: ${sensorName}`;
      
      // Calcular posición para centrar todo el texto
      const textMetrics = ctx.measureText(sensorText);
      const startX = (tempCanvas.width - textMetrics.width) / 2;
      
      // Dibujar "Sensor: " en gris
      ctx.fillStyle = '#1f2937';
      ctx.textAlign = 'left';
      const labelWidth = ctx.measureText('Sensor: ').width;
      ctx.fillText('Sensor: ', startX, 25);
      
      // Dibujar Nombre en naranja
      ctx.fillStyle = '#ea580c';
      ctx.fillText(sensorName, startX + labelWidth, 25);
      
      // Línea 2: Fecha y hora Colombia
      // El timestamp del sensor ya representa hora Colombia codificada como epoch UTC
          const timestamp = measurements[currentMeasurementIndex]?.timestamp;
          if (timestamp) {
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
              const dateStr = date.toLocaleString('es-CO', {
                timeZone: 'UTC',
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
              });
              
              ctx.font = '14px Arial';
              ctx.fillStyle = '#4b5563';
              ctx.fillText(dateStr, tempCanvas.width / 2, 48);
            }
          }

      // Dibujar el gráfico debajo del título
      ctx.drawImage(renderedChart, 0, titleHeight);

      // Convertir a blob
      const blob = await new Promise<Blob | null>((resolve) => {
        tempCanvas.toBlob(resolve, 'image/png');
      });

      if (!blob) {
        alert('Error al generar la imagen');
        return;
      }

      // Copiar al portapapeles
      const item = new ClipboardItem({ 'image/png': blob });
      await navigator.clipboard.write([item]);
      alert('✓ Imagen copiada al portapapeles');
    } catch (error: any) {
      console.error('Error al copiar imagen:', error);
      if (error.name === 'NotAllowedError') {
        alert('Permiso denegado. Por favor permite el acceso al portapapeles en la configuración del navegador.');
      } else {
        alert('Error al copiar imagen: ' + error.message);
      }
    }
  };

  const handleGenerateReport = async () => {
    try {
      setGeneratingReport(true);
      setError('');
      
      // Si es la campaña simulada, usar generador de datos local
      if (campaignId === 99999) {
        // Simular retardo de red
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Importar generador dinámicamente o usar la función si está disponible en el scope
        // Aquí asumimos que la función está disponible o la importamos arriba
        // Nota: Necesitamos importar generateSimulatedTDTReport arriba si no está
        const { generateSimulatedTDTReport } = await import('../utils/generateData');
        const simulatedData = generateSimulatedTDTReport(campaignId, campaignName);
        
        setReportData(simulatedData);
        
        // Procesar resultados para visualización (marcadores)
        if (simulatedData.mediciones && simulatedData.mediciones[0]?.emisiones) {
          const emisiones = simulatedData.mediciones[0].emisiones;
          const newMarkers: Marker[] = emisiones.map((em: any, index: number) => ({
            id: `E${index + 1}`,
            frequency: em.frecuencia_mhz * 1e6, // Convertir MHz a Hz para el marcador
            power: em.potencia_dbm,
            color: em.estado_cumplimiento === 'CUMPLE' ? '#10b981' : '#ef4444',
          }));
          
          setMarkers(newMarkers);
          setShowReportPanel(false);
          setShowFullReportModal(true); // Mostrar reporte completo automáticamente para la simulación
        }
        
        setGeneratingReport(false);
        return;
      }
      
      const response = await axios.post(`${API_BASE_URL}/reports/compliance/${campaignId}?sensor_mac=${selectedSensor}`, {
        umbral: isNaN(umbral) ? 0 : umbral
      });
      
      const data = response.data;
      setReportData(data);
      
      // Procesar resultados para visualización (marcadores)
      if (data.results && Array.isArray(data.results)) {
        // Mapear emisiones a marcadores
        const newMarkers: Marker[] = data.results
          .filter((res: any) => res.status === 'emision')
          .map((res: any, index: number) => ({
            id: `P${index + 1}`,
            frequency: res.fc_hz, 
            power: res.power_dbm,
            color: '#ef4444', // Rojo para emisiones detectadas
          }));
        
        setMarkers(newMarkers);
        setShowReportPanel(false);
        setShowFullReportModal(true); // Mostrar reporte automáticamente
      }
      
    } catch (err: any) {
      console.error('Error generando reporte:', err);
      setError(err.message || 'Error generando reporte');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleGenerateAutomaticReport = async () => {
    try {
      setGeneratingReport(true);
      setError('');
      
      // Si es la campaña simulada, usar generador de datos local
      if (campaignId === 99999) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const { generateSimulatedTDTReport } = await import('../utils/generateData');
        const simulatedData = generateSimulatedTDTReport(campaignId, campaignName);
        setReportData(simulatedData);
        if (simulatedData.mediciones && simulatedData.mediciones[0]?.emisiones) {
          const emisiones = simulatedData.mediciones[0].emisiones;
          const newMarkers: Marker[] = emisiones.map((em: any, index: number) => ({
            id: `E${index + 1}`,
            frequency: em.frecuencia_mhz * 1e6,
            power: em.potencia_dbm,
            color: em.estado_cumplimiento === 'CUMPLE' ? '#10b981' : '#ef4444',
          }));
          setMarkers(newMarkers);
          setShowReportPanel(false);
          setShowFullReportModal(true);
        }
        setGeneratingReport(false);
        return;
      }
      
      // Para reporte automático NO enviamos umbral
      const response = await axios.post(`${API_BASE_URL}/reports/compliance/${campaignId}?sensor_mac=${selectedSensor}`, {});
      
      const data = response.data;
      setReportData(data);
      
      if (data.results && Array.isArray(data.results)) {
        const newMarkers: Marker[] = data.results
          .filter((res: any) => res.status === 'emision')
          .map((res: any, index: number) => ({
            id: `P${index + 1}`,
            frequency: res.fc_hz, 
            power: res.power_dbm,
            color: '#ef4444',
          }));
        setMarkers(newMarkers);
        setShowReportPanel(false);
        setShowFullReportModal(true); // Mostrar reporte automáticamente
      }
      
    } catch (err: any) {
      console.error('Error generando reporte automático:', err);
      setError(err.message || 'Error generando reporte automático');
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleFullscreen = () => {
    if (!document.fullscreenElement && chartRef.current) {
      chartRef.current.requestFullscreen();
      setIsFullscreen(true);
    } else if (document.fullscreenElement) {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleDownloadCSV = () => {
    if (!currentSpectrumData || currentSpectrumData.length === 0) {
      alert('No hay datos disponibles para descargar');
      return;
    }

    const headers = ['Frecuencia (Hz)', 'Potencia (dBm)'];
    let csvContent = 'data:text/csv;charset=utf-8,';
    
    csvContent += `Campaña: ${campaignName}\n`;
    csvContent += `Medición: ${currentMeasurementIndex + 1} de ${spectrumData.length}\n\n`;
    csvContent += headers.join(',') + '\n';

    currentSpectrumData.forEach(point => {
      csvContent += `${point.frequency},${point.power}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
    link.setAttribute('download', `spectrum_${campaignName}_medicion${currentMeasurementIndex + 1}_${timestamp}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Funciones de control del player
  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleNext = () => {
    if (currentMeasurementIndex < spectrumData.length - 1) {
      setCurrentMeasurementIndex(prev => prev + 1);
      setIsPlaying(false);
    }
  };

  const handlePrevious = () => {
    if (currentMeasurementIndex > 0) {
      setCurrentMeasurementIndex(prev => prev - 1);
      setIsPlaying(false);
    }
  };

  const handleFirst = () => {
    setCurrentMeasurementIndex(0);
    setIsPlaying(false);
  };

  const handleLast = () => {
    setCurrentMeasurementIndex(spectrumData.length - 1);
    setIsPlaying(false);
  };

  // Obtener datos del espectro actual - pasar directamente sin transformar
  const currentSpectrumData = spectrumData.length > 0 && spectrumData[currentMeasurementIndex]
    ? spectrumData[currentMeasurementIndex]
    : [];

  // Preparar historial del waterfall
  // Invertir para que el elemento más reciente esté al principio (índice 0),
  // ya que Waterfall asume que history[0] es el snapshot más nuevo.
  const waterfallHistory = useMemo(() => {
    return spectrumData.slice(0, currentMeasurementIndex + 1).reverse();
  }, [spectrumData, currentMeasurementIndex]);

  const stepRatio = spectrumData.length > 0 ? 1 / spectrumData.length : 1;

  // Calcular rango de frecuencia para waterfall
  const spectrumRange = useMemo(() => {
    if (zoomArea) {
      return { minFreq: zoomArea.minFreq, maxFreq: zoomArea.maxFreq };
    }
    if (currentSpectrumData && currentSpectrumData.length > 0) {
      const minFreq = currentSpectrumData[0].frequency;
      const maxFreq = currentSpectrumData[currentSpectrumData.length - 1].frequency;
      return { minFreq, maxFreq };
    }
    return { minFreq: undefined, maxFreq: undefined };
  }, [zoomArea, currentSpectrumData]);

  // Construir series para vista combinada
  const chartSeries = useMemo(() => {
    if (viewMode === 'individual') return undefined;
    
    return sensors.map((sensor, index) => {
      const data = multiSensorData[sensor]?.spectrum[currentMeasurementIndex];
      if (!data) return null;
      
      // Colores vivos para distinguir sensores
      const colors = ['#f97316', '#3b82f6', '#10b981', '#a855f7', '#ef4444', '#eab308', '#ec4899', '#06b6d4'];
      
      const sensorName = allSensors?.find(s => s.mac === sensor)?.name || sensor;
      
      return {
        name: sensorName,
        data: data,
        color: colors[index % colors.length]
      };
    }).filter(Boolean) as SpectrumSeries[];
  }, [viewMode, sensors, multiSensorData, currentMeasurementIndex, allSensors]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 flex items-center justify-between shadow-lg flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">{campaignName}</h2>
            {campaignInfo && (
              <span className="text-xs bg-orange-700/50 px-2 py-0.5 rounded-full">#{campaignId}</span>
            )}
          </div>
          
          <div className="flex items-center gap-3 mt-2">
            {/* Selector de modo de vista */}
            <div className="bg-orange-700/50 rounded-lg p-0.5 flex">
              <button
                onClick={() => setViewMode('individual')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1 ${
                  viewMode === 'individual' ? 'bg-white text-orange-600 shadow-sm' : 'text-orange-100 hover:bg-orange-600/50'
                }`}
              >
                <Activity size={14} />
                Individual
              </button>
              <button
                onClick={() => setViewMode('combined')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1 ${
                  viewMode === 'combined' ? 'bg-white text-orange-600 shadow-sm' : 'text-orange-100 hover:bg-orange-600/50'
                }`}
              >
                <Layers size={14} />
                Combinado
              </button>
            </div>

            {/* Selector de sensor */}
            <div className="relative">
              <select
                value={selectedSensor}
                onChange={(e) => setSelectedSensor(e.target.value)}
                className="appearance-none bg-orange-700/50 hover:bg-orange-700/70 text-white text-sm rounded-lg pl-3 pr-8 py-1.5 focus:outline-none focus:ring-2 focus:ring-white/50 transition-colors cursor-pointer border border-orange-400/30"
              >
                {sensors.map(s => {
                  const sensorName = allSensors?.find(sensor => sensor.mac === s)?.name || s;
                  return (
                    <option key={s} value={s} className="text-gray-900">
                      Sensor: {sensorName}
                    </option>
                  );
                })}
              </select>
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none">
                <svg className="w-4 h-4 text-orange-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>

            {/* Botón info de campaña */}
            <button
              onClick={() => setShowCampaignInfo(!showCampaignInfo)}
              className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                showCampaignInfo 
                  ? 'bg-white text-orange-600 border-white shadow-sm' 
                  : 'bg-orange-700/50 text-orange-100 hover:bg-orange-700/70 border-orange-400/30'
              }`}
              title="Información de la campaña"
            >
              <Info size={14} />
              Info
              <ChevronDown size={12} className={`transition-transform ${showCampaignInfo ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadCSV}
            disabled={loading || spectrumData.length === 0}
            className="p-2 hover:bg-orange-600 rounded-lg transition-colors disabled:opacity-50"
            title="Descargar datos CSV"
          >
            <Download size={20} />
          </button>
          <button
            onClick={onClose}
            className="p-2 hover:bg-orange-600 rounded-lg transition-colors"
            title="Cerrar visualización"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Panel de información de la campaña (desplegable) */}
      {showCampaignInfo && campaignInfo && (
        <div className="bg-white border-b border-orange-200 shadow-sm flex-shrink-0">
          <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm">
            {/* Columna 1: Info general */}
            <div className="space-y-1.5">
              <h4 className="font-semibold text-orange-600 text-xs uppercase tracking-wide mb-2">General</h4>
              <div className="flex justify-between">
                <span className="text-gray-500">Estado:</span>
                <span className={`font-medium ${
                  campaignInfo.status === 'completed' ? 'text-green-600' :
                  campaignInfo.status === 'running' ? 'text-blue-600' :
                  campaignInfo.status === 'cancelled' ? 'text-red-600' : 'text-gray-700'
                }`}>
                  {campaignInfo.status === 'completed' ? 'Terminada' :
                   campaignInfo.status === 'running' ? 'En ejecución' :
                   campaignInfo.status === 'scheduled' ? 'Programada' :
                   campaignInfo.status === 'cancelled' ? 'Cancelada' : campaignInfo.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Dispositivos:</span>
                <span className="text-gray-700 font-medium">{sensors.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Creada por:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.created_by_name || 'Sistema'}</span>
              </div>
              {campaignInfo.preset && campaignInfo.preset !== 'custom' && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Preset:</span>
                  <span className="text-gray-700 font-medium uppercase">{campaignInfo.preset}</span>
                </div>
              )}
            </div>

            {/* Columna 2: Frecuencias y espectro */}
            <div className="space-y-1.5">
              <h4 className="font-semibold text-orange-600 text-xs uppercase tracking-wide mb-2">Espectro</h4>
              <div className="flex justify-between">
                <span className="text-gray-500">Freq. Inicial:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.start_freq_mhz} MHz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Freq. Final:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.end_freq_mhz} MHz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Ancho de Banda:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.bandwidth_mhz} MHz</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Resolución:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.resolution_khz} kHz</span>
              </div>
            </div>

            {/* Columna 3: Programación */}
            <div className="space-y-1.5">
              <h4 className="font-semibold text-orange-600 text-xs uppercase tracking-wide mb-2">Programación</h4>
              <div className="flex justify-between">
                <span className="text-gray-500">Fecha Inicio:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.start_date ? new Date(campaignInfo.start_date).toLocaleDateString() : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Fecha Fin:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.end_date ? new Date(campaignInfo.end_date).toLocaleDateString() : 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Hora Inicio:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.start_time || 'No especificada'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Hora Fin:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.end_time || 'No especificada'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Intervalo:</span>
                <span className="text-gray-700 font-medium">{campaignInfo.interval_seconds} segundos</span>
              </div>
            </div>

            {/* Columna 4: Configuración de adquisición */}
            <div className="space-y-1.5">
              <h4 className="font-semibold text-orange-600 text-xs uppercase tracking-wide mb-2">Adquisición</h4>
              {campaignInfo.config && (
                <>
                  {campaignInfo.config.centerFrequency && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Freq. Central:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.centerFrequency} MHz</span>
                    </div>
                  )}
                  {campaignInfo.config.span && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Span/Sample Rate:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.span} MHz</span>
                    </div>
                  )}
                  {campaignInfo.config.rbw && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">RBW:</span>
                      <span className="text-gray-700 font-medium">
                        {Number(campaignInfo.config.rbw) >= 1000000
                          ? `${Number(campaignInfo.config.rbw) / 1000000} MHz`
                          : Number(campaignInfo.config.rbw) >= 1000
                            ? `${Number(campaignInfo.config.rbw) / 1000} kHz`
                            : `${campaignInfo.config.rbw} Hz`}
                      </span>
                    </div>
                  )}
                  {campaignInfo.config.vbw && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">VBW:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.vbw}</span>
                    </div>
                  )}
                  {campaignInfo.config.lna_gain !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">LNA Gain:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.lna_gain} dB</span>
                    </div>
                  )}
                  {campaignInfo.config.vga_gain !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">VGA Gain:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.vga_gain} dB</span>
                    </div>
                  )}
                  {campaignInfo.config.antenna_amp !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Antenna Amp:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.antenna_amp ? 'Sí' : 'No'}</span>
                    </div>
                  )}
                  {campaignInfo.config.antenna && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Puerto Antena:</span>
                      <span className="text-gray-700 font-medium">{campaignInfo.config.antenna}</span>
                    </div>
                  )}
                </>
              )}
              {campaignInfo.gps_coordinates && campaignInfo.gps_coordinates.length > 0 && (
                <div className="mt-1 pt-1 border-t border-gray-100">
                  <span className="text-gray-500 text-xs">Coordenadas GPS:</span>
                  {campaignInfo.gps_coordinates.map((gps: any) => {
                    const sName = allSensors?.find(s => s.mac === gps.mac)?.name || gps.mac;
                    return (
                      <div key={gps.mac} className="flex justify-between text-xs">
                        <span className="text-gray-400">{sName}:</span>
                        <span className="text-gray-600 font-mono">{gps.lat?.toFixed(5)}, {gps.lng?.toFixed(5)}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden flex flex-col p-4">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
              <span className="ml-2 text-gray-600">Cargando datos...</span>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700">{error}</p>
            </div>
          ) : spectrumData.length === 0 ? (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-700">No hay datos disponibles para esta campaña</p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Gráfico de espectro */}
              <div ref={chartRef} className="bg-white border border-orange-200 rounded-lg shadow-sm">
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
                    
                    <button 
                      onClick={() => setShowReportPanel(!showReportPanel)}
                      className={`px-3 py-2 rounded transition-colors flex items-center gap-2 ${
                        showReportPanel ? 'bg-orange-100 text-orange-600' : 'text-gray-600 hover:bg-gray-100'
                      }`}
                      title="Reporte de Cumplimiento"
                    >
                      <FileText className="w-4 h-4" />
                      <span className="text-sm font-medium">Reporte</span>
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
                      className={`p-2 rounded transition-colors ${
                        isFullscreen ? 'bg-orange-100 text-orange-600' : 'text-gray-600 hover:bg-gray-100'
                      }`}
                      title="Pantalla completa"
                    >
                      <Maximize2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                
                {/* Reproductor de mediciones */}
                <div className="px-4 py-2 border-t border-gray-200">
                  <div className="flex items-center gap-3">
                    {/* Fecha y hora actual */}
                    <div className="flex flex-col text-xs min-w-fit">
                      <span className="font-semibold text-gray-700">
                        {(() => {
                          const timestamp = measurements[currentMeasurementIndex]?.timestamp;
                          if (!timestamp) return 'N/A';
                          const date = new Date(timestamp);
                          if (isNaN(date.getTime())) return 'Invalid Date';
                          return date.toLocaleDateString('es-CO', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            timeZone: 'UTC'
                          });
                        })()}
                      </span>
                      <span className="text-gray-500">
                        {(() => {
                          const timestamp = measurements[currentMeasurementIndex]?.timestamp;
                          if (!timestamp) return 'N/A';
                          const date = new Date(timestamp);
                          if (isNaN(date.getTime())) return 'Invalid Date';
                          return date.toLocaleTimeString('es-CO', {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            timeZone: 'UTC'
                          });
                        })()}
                      </span>
                    </div>

                    {/* Separador */}
                    <div className="border-l border-gray-300 h-8"></div>
                    
                    {/* Medición actual */}
                    <div className="flex items-center gap-2 text-xs text-gray-600 min-w-fit">
                      <span className="font-semibold text-orange-600">{currentMeasurementIndex + 1}</span>
                      <span>/</span>
                      <span>{spectrumData.length}</span>
                    </div>
                    
                    {/* Controles de reproducción */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={handleFirst}
                        disabled={currentMeasurementIndex === 0}
                        className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Primera medición"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z"/>
                        </svg>
                      </button>
                      
                      <button
                        onClick={handlePrevious}
                        disabled={currentMeasurementIndex === 0}
                        className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Medición anterior"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"/>
                        </svg>
                      </button>

                      <button
                        onClick={handlePlayPause}
                        className="p-2 bg-orange-500 hover:bg-orange-600 text-white rounded transition-colors"
                        title={isPlaying ? "Pausar" : "Reproducir"}
                      >
                        {isPlaying ? (
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd"/>
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd"/>
                          </svg>
                        )}
                      </button>

                      <button
                        onClick={handleNext}
                        disabled={currentMeasurementIndex === spectrumData.length - 1}
                        className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Medición siguiente"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/>
                        </svg>
                      </button>

                      <button
                        onClick={handleLast}
                        disabled={currentMeasurementIndex === spectrumData.length - 1}
                        className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Última medición"
                      >
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798l-5.445-3.63z"/>
                        </svg>
                      </button>
                    </div>
                    
                    {/* Barra de progreso */}
                    <input
                      type="range"
                      min="0"
                      max={spectrumData.length - 1}
                      value={currentMeasurementIndex}
                      onChange={(e) => {
                        setCurrentMeasurementIndex(parseInt(e.target.value));
                        setIsPlaying(false);
                      }}
                      className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-500"
                    />
                    
                    {/* Velocidad */}
                    <div className="flex items-center gap-2 text-xs text-gray-600 min-w-fit">
                      <span>Velocidad:</span>
                      <select
                        value={playSpeed}
                        onChange={(e) => setPlaySpeed(parseInt(e.target.value))}
                        className="px-2 py-1 text-xs border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value={2000}>0.5x (2s)</option>
                        <option value={1000}>1x (1s)</option>
                        <option value={500}>2x (0.5s)</option>
                        <option value={250}>4x (0.25s)</option>
                        <option value={100}>10x (0.1s)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Gráfico */}
                <div className="px-4 pt-2 pb-1">
                  <SpectrumChart 
                  data={currentSpectrumData}
                  series={chartSeries}
                  markers={markers} 
                  onMarkerAdd={handleAddMarker}
                  activeStats={activeStats}
                  statColors={statColors}
                  maxHold={maxHold}
                  minHold={minHold}
                  zoomMode={zoomMode}
                  zoomArea={zoomArea}
                  onZoomAreaChange={setZoomArea}
                  freqUnit={freqUnit}
                  powerUnit={powerUnit}
                  antennaGain={antennaGain}
                  umbral={reportData ? reportData.umbral_db : (isNaN(umbral) ? 0 : umbral)}
                  noiseFloor={reportData?.mediciones?.[currentMeasurementIndex]?.emisiones?.[0]?.nf_dbm ? reportData.mediciones[currentMeasurementIndex].emisiones[0].nf_dbm : undefined}
                  />
                </div>

                {/* Espectrograma integrado */}
                {waterfallHistory.length > 0 && (
                  <div className="px-4 pb-4 pt-0">
                    <Waterfall 
                      data={currentSpectrumData} 
                      history={waterfallHistory} 
                      freqUnit={freqUnit}
                      powerUnit={powerUnit}
                      stepRatio={stepRatio}
                      minFreq={spectrumRange.minFreq}
                      maxFreq={spectrumRange.maxFreq}
                    />
                  </div>
                )}
              </div>

            </div>
          )}
      </div>

      {/* Panel lateral desplegable */}
      <div className={`fixed top-0 right-0 h-full w-80 bg-white shadow-2xl transform transition-transform duration-300 z-50 ${
        showControlPanel ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header del panel */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Controles
          </h3>
          <button
            onClick={() => setShowControlPanel(false)}
            className="p-1 hover:bg-orange-600 rounded transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        {/* Contenido del panel con scroll */}
        <div className="overflow-y-auto h-[calc(100%-64px)] p-4 space-y-4">
          {/* Información general */}
          {spectrumData.length > 0 && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <h3 className="font-semibold text-gray-800 mb-2 text-sm flex items-center gap-2">
                <span className="text-orange-600">ℹ️</span> Información de la campaña
              </h3>
                <div className="grid grid-cols-1 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Mediciones:</span>
                    <span className="font-semibold text-gray-900">{spectrumData.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Puntos por medición:</span>
                    <span className="font-semibold text-gray-900">{spectrumData[0]?.length || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Rango de frecuencia:</span>
                    <span className="font-semibold text-gray-900">
                      {spectrumData[0]?.[0]?.frequency ? (spectrumData[0][0].frequency / 1e6).toFixed(3) : '0'} - {spectrumData[0]?.[spectrumData[0].length - 1]?.frequency ? (spectrumData[0][spectrumData[0].length - 1].frequency / 1e6).toFixed(3) : '0'} MHz
                    </span>
                  </div>
                </div>
              </div>
          )}

          {/* Controles de visualización */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Controles de visualización</h3>
                
                {/* Selector de unidades */}
                <div className="mb-3">
                  <div className="grid grid-cols-1 gap-2">
                    <div>
                      <label className="text-xs text-gray-600 block mb-1">Frecuencia:</label>
                      <select
                        value={freqUnit}
                        onChange={(e) => setFreqUnit(e.target.value as 'Hz' | 'kHz' | 'MHz' | 'GHz')}
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="Hz">Hz</option>
                        <option value="kHz">kHz</option>
                        <option value="MHz">MHz</option>
                        <option value="GHz">GHz</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-600 block mb-1">Potencia:</label>
                      <select
                        value={powerUnit}
                        onChange={(e) => setPowerUnit(e.target.value as any)}
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="dBm">dBm</option>
                        <option value="nW">nW</option>
                        <option value="mV">mV</option>
                        <option value="dBmV">dBmV</option>
                        <option value="dBuV">dBμV</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-gray-600 block mb-1">Campo:</label>
                      <select
                        value={fieldUnit}
                        onChange={(e) => {
                          const val = e.target.value as FieldUnit;
                          setFieldUnit(val);
                          setPowerUnit(val as any);
                        }}
                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                      >
                        <option value="dBuV/m">dBμV/m</option>
                        <option value="dBmV/m">dBmV/m</option>
                        <option value="mV/m">mV/m</option>
                        <option value="V/m">V/m</option>
                        <option value="W/m²">W/m²</option>
                        <option value="dBW/m²/MHz">dBW/m²/MHz</option>
                      </select>
                    </div>
                  </div>
                </div>
                
                {/* Marcadores */}
                <div className="mb-4 pb-4 border-b border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold text-gray-700">Marcadores ({markers.length}/4)</h4>
                    <button
                      onClick={() => setMarkers([])}
                      disabled={markers.length === 0}
                      className="text-xs text-red-600 hover:text-red-700 disabled:text-gray-400"
                    >
                      Limpiar todos
                    </button>
                  </div>
                  {markers.length > 0 && (
                    <div className="space-y-1">
                      {markers.map((marker) => (
                        <div key={marker.id} className="flex items-center justify-between text-xs bg-gray-50 p-2 rounded">
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: marker.color }}></span>
                            <span className="font-semibold">{marker.id}:</span>
                            <span>{(marker.frequency / 1e6).toFixed(3)} MHz</span>
                          <span className="text-gray-500">|</span>
                          <span>{getSafeConvertedMarkerPower(marker.frequency).toFixed(2)} {powerUnit}</span>
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
                                  {(getSafeConvertedMarkerPower(markers[i + 1].frequency) - getSafeConvertedMarkerPower(markers[i].frequency)).toFixed(2)} {powerUnit}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-2">Haga clic en el gráfico para agregar marcadores (máx. 4)</p>
                </div>

                {/* Retenciones */}
                <div className="mb-4 pb-4 border-b border-gray-200">
                  <div className="flex flex-wrap gap-3">
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={maxHold}
                        onChange={(e) => setMaxHold(e.target.checked)}
                        className="rounded text-orange-600 focus:ring-orange-500"
                      />
                      Traza máxima
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={minHold}
                        onChange={(e) => setMinHold(e.target.checked)}
                        className="rounded text-orange-600 focus:ring-orange-500"
                      />
                      Traza mínima
                    </label>
                  </div>
                </div>

                {/* Estadísticas */}
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => toggleStat('min')}
                    className={`px-4 py-2 text-sm rounded transition-colors font-medium ${
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
                    className={`px-4 py-2 text-sm rounded transition-colors font-medium ${
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
                    className={`px-4 py-2 text-sm rounded transition-colors font-medium ${
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
                    className={`px-4 py-2 text-sm rounded transition-colors font-medium ${
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

      {/* Panel de reporte */}
      <div className={`fixed top-0 right-0 h-full w-80 bg-white shadow-2xl transform transition-transform duration-300 z-50 ${
        showReportPanel ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header del panel */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Reporte
          </h3>
          <button
            onClick={() => setShowReportPanel(false)}
            className="p-1 hover:bg-orange-600 rounded transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        {/* Contenido */}
        <div className="p-4 space-y-4">
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
             <h3 className="text-sm font-semibold text-gray-800 mb-3">Configuración de Análisis</h3>
             
             <div className="mb-4">
               <label className="text-xs text-gray-600 block mb-1">Tipo de Reporte:</label>
               <select
                 value={reportMode}
                 onChange={(e) => setReportMode(e.target.value as 'automatic' | 'manual')}
                 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500 text-sm"
               >
                 <option value="automatic">Reporte Automático</option>
                 <option value="manual">Reporte con umbral</option>
               </select>
             </div>

             {reportMode === 'manual' && (
               <div className="mb-4">
                 <label className="text-xs text-gray-600 block mb-1">Umbral de detección (dBm):</label>
                 <div className="flex items-center gap-2">
                   <input 
                     type="number" 
                     min="0.5" 
                     max="10" 
                     step="0.1"
                     value={isNaN(umbral) ? '' : umbral}
                     onChange={(e) => {
                       const val = parseFloat(e.target.value);
                       if (e.target.value === '') {
                         setUmbral(NaN);
                       } else if (!isNaN(val) && val >= 0.5 && val <= 10) {
                         setUmbral(val);
                       }
                     }}
                     className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                   />
                   <span className="text-sm text-gray-500">dBm</span>
                 </div>
                 <p className="text-xs text-gray-500 mt-1">Rango: 0.5 - 10.0 dBm</p>
               </div>
             )}

             {reportMode === 'automatic' ? (
               <button
                 onClick={handleGenerateAutomaticReport}
                 disabled={generatingReport}
                 className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
               >
                 {generatingReport ? (
                   <>
                     <Loader2 className="w-4 h-4 animate-spin" />
                     Generando...
                   </>
                 ) : (
                   <>
                     <Activity className="w-4 h-4" />
                     Generar con umbral automático
                   </>
                 )}
               </button>
             ) : (
               <button
                 onClick={handleGenerateReport}
                 disabled={generatingReport}
                 className="w-full bg-orange-600 hover:bg-orange-700 text-white py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
               >
                 {generatingReport ? (
                   <>
                     <Loader2 className="w-4 h-4 animate-spin" />
                     Generando...
                   </>
                 ) : (
                   <>
                     <FileText className="w-4 h-4" />
                     Generar con Umbral manual
                   </>
                 )}
               </button>
             )}
          </div>

          {reportData && (
             <div className="mt-4">
               <button
                 onClick={() => setShowFullReportModal(true)}
                 className="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
               >
                 <FileText className="w-4 h-4" />
                 Ver Reporte Completo
               </button>
             </div>
          )}
        </div>
      </div>

      {/* Modal de Reporte Completo */}
      {showFullReportModal && (
        <ComplianceReport
          campaignId={campaignId}
          campaignName={campaignName}
          sensors={sensors}
          allSensors={allSensors}
          initialSensor={selectedSensor}
          onClose={() => setShowFullReportModal(false)}
          initialData={reportData}
          umbral={reportMode === 'manual' ? (isNaN(umbral) ? 0 : umbral) : undefined}
        />
      )}
    </div>
  );
}
