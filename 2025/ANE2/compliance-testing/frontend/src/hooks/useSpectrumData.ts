import { useState, useEffect, useCallback, useRef } from 'react';
import { sensorDataAPI, SpectrumData } from '../services/api';

export function useSpectrumData(sensorMac: string | null, autoRefresh: boolean = false, refreshInterval: number = 1000, resetKey: number = 0) {
  const [data, setData] = useState<SpectrumData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false); // Para evitar llamadas simultáneas
  const lastResetKeyRef = useRef(resetKey);
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0); // Para detectar respuestas tardías (stale)
  const lastValidSensorMacRef = useRef<string | null>(null); // Último sensor que recibió datos exitosamente

  const loadData = useCallback(async () => {
    if (!sensorMac || loadingRef.current) return;
    
    // Cancelar request anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    const currentRequestId = ++requestIdRef.current;
    const currentSensorMac = sensorMac;
    
    loadingRef.current = true;
    setError(null);
    
    try {
      const result = await sensorDataAPI.getLatestData(sensorMac, 1);
      
      // VALIDACIÓN CRÍTICA: ¿El sensor cambió mientras esperábamos la respuesta?
      // O ¿la respuesta es del sensor correcto?
      if (abortControllerRef.current?.signal.aborted) {
        console.log('🚫 Spectrum request abortado - respuesta descartada', { currentSensorMac });
        return;
      }
      
      // Verificar que la respuesta corresponde al sensor actual (anti-stale)
      if (currentSensorMac !== sensorMac) {
        console.log('⚠️ Spectrum data mismatch: respuesta es de sensor anterior', {
          originalSensor: currentSensorMac,
          currentSensor: sensorMac,
          requestId: currentRequestId
        });
        return;
      }
      
      // Validar que la respuesta tenga datos del sensor correcto
      // (Si el backend devuelve datos, validar que sea del sensor solicitado)
      if (result && result.length > 0 && result[0].mac && result[0].mac !== currentSensorMac) {
        console.warn('⚠️ Backend devolvió datos de otro sensor:', {
          requested: currentSensorMac,
          received: result[0].mac
        });
        return;
      }
      
      lastValidSensorMacRef.current = currentSensorMac;
      setData(result);
    } catch (err: any) {
      // Ignorar errores de abort (son normales al cambiar sensor)
      if (err.name === 'AbortError') {
        console.log('🚫 Spectrum request abortado');
        return;
      }
      setError(err.message);
      console.error('Error loading spectrum data:', err);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [sensorMac]);

  // NO cargar datos automáticamente al montar
  // Solo cargar cuando autoRefresh está activo (modo monitoreo)
  const prevAutoRefreshRef = useRef(autoRefresh);
  const prevSensorMacRef = useRef(sensorMac);

  // Cleanup: Cancelar request cuando se desmontar o cambiar sensor
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Resetear estado cuando cambia el sensor o autoRefresh
  useEffect(() => {
    const sensorChanged = sensorMac !== prevSensorMacRef.current;
    const autoRefreshChanged = autoRefresh !== prevAutoRefreshRef.current;

    if (sensorChanged) {
      console.log('🔄 Spectrum reset: sensor changed', { 
        from: prevSensorMacRef.current, 
        to: sensorMac 
      });
      
      // Cancelar request en vuelo del sensor anterior
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();
      
      // Limpiar datos del sensor anterior
      setData([]);
      setError(null);
      requestIdRef.current = 0;
    }

    if (!sensorChanged && autoRefreshChanged) {
      if (!autoRefresh && prevAutoRefreshRef.current) {
        // Al detener monitoreo, limpiar datos
        console.log('🔄 Spectrum reset: monitoring stopped');
        setData([]);
        setError(null);
      } else if (autoRefresh && !prevAutoRefreshRef.current) {
        // Al iniciar monitoreo, limpiar datos para empezar fresco
        console.log('🔄 Spectrum reset: monitoring started');
        setData([]);
        setError(null);
      }
    }

    prevAutoRefreshRef.current = autoRefresh;
    prevSensorMacRef.current = sensorMac;
  }, [sensorMac, autoRefresh]);

  // Resetear cuando cambia el resetKey (cambio de parámetros en vivo)
  useEffect(() => {
    if (resetKey !== lastResetKeyRef.current) {
      console.log('🔄 Spectrum reset: config updated in-flight (resetKey)', resetKey);
      setData([]);
      setError(null);
      lastResetKeyRef.current = resetKey;
    }
  }, [resetKey]);

  // Setup interval de polling - Mejorado para evitar stale closures
  useEffect(() => {
    if (!autoRefresh || !sensorMac) {
      return;
    }

    // Cargar datos inmediatamente
    loadData();

    // Configurar polling en intervalo
    const interval = setInterval(() => {
      loadData();
    }, refreshInterval);

    return () => {
      clearInterval(interval);
      // Nota: No cancelamos el AbortController aquí porque se maneja en el otro useEffect
    };
  }, [autoRefresh, sensorMac, refreshInterval, loadData]);

  const convertToChartFormat = (spectrumData: SpectrumData[]) => {
    if (spectrumData.length === 0) return [];

    const latest = spectrumData[0];
    if (!latest || !latest.Pxx || !Array.isArray(latest.Pxx)) {
      console.error('Invalid spectrum data format:', latest);
      return [];
    }

    const freqStep = (latest.end_freq_hz - latest.start_freq_hz) / latest.Pxx.length;
    
    const chartData = latest.Pxx.map((power, index) => ({
      frequency: latest.start_freq_hz + (index * freqStep),
      power: power,
    }));

    // Calcular min/max sin desbordar el stack
    let minPower = Infinity;
    let maxPower = -Infinity;
    for (let i = 0; i < latest.Pxx.length; i++) {
      if (latest.Pxx[i] < minPower) minPower = latest.Pxx[i];
      if (latest.Pxx[i] > maxPower) maxPower = latest.Pxx[i];
    }

    console.log('📊 Spectrum data converted:', {
      points: chartData.length,
      freqRange: `${(latest.start_freq_hz / 1e6).toFixed(1)} - ${(latest.end_freq_hz / 1e6).toFixed(1)} MHz`,
      powerRange: `${minPower.toFixed(1)} - ${maxPower.toFixed(1)} dBm`,
      sample: chartData[0]
    });
    
    return chartData;
  };

  return {
    data,
    chartData: convertToChartFormat(data),
    loading,
    error,
    reload: loadData,
  };
}

// Hook para cargar datos de múltiples capturas (para waterfall)
export function useWaterfallData(sensorMac: string | null, limit: number = 100, autoRefresh: boolean = false, refreshInterval: number = 3000) {
  const [history, setHistory] = useState<{ frequency: number; power: number }[][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastTimestampRef = useRef<number>(0);
  const lastAutoRefreshRef = useRef(autoRefresh);
  const loadingHistoryRef = useRef(false); // Para evitar llamadas simultáneas
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestIdRef = useRef(0); // Para detectar respuestas tardías (stale)
  const prevSensorMacRef = useRef<string | null>(null);

  const loadHistory = useCallback(async () => {
    if (!sensorMac || loadingHistoryRef.current) return;
    
    // Cancelar request anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    const currentRequestId = ++requestIdRef.current;
    const currentSensorMac = sensorMac;
    
    loadingHistoryRef.current = true;
    setError(null);
    
    try {
      const result = await sensorDataAPI.getLatestData(sensorMac, limit);
      
      // VALIDACIÓN CRÍTICA: ¿El sensor cambió o fue abortado?
      if (abortControllerRef.current?.signal.aborted) {
        console.log('🚫 Waterfall request abortado - respuesta descartada', { currentSensorMac });
        return;
      }
      
      // Verificar que la respuesta corresponde al sensor actual
      if (currentSensorMac !== sensorMac) {
        console.log('⚠️ Waterfall data mismatch: respuesta es de sensor anterior', {
          originalSensor: currentSensorMac,
          currentSensor: sensorMac,
          requestId: currentRequestId
        });
        return;
      }
      
      // Validar que la respuesta tenga datos del sensor correcto
      if (result && result.length > 0 && result[0].mac && result[0].mac !== currentSensorMac) {
        console.warn('⚠️ Backend devolvió waterfall de otro sensor:', {
          requested: currentSensorMac,
          received: result[0].mac
        });
        return;
      }
      
      // Si es la primera carga (inicio de monitoreo), solo establecer el timestamp
      // y NO cargar datos antiguos - empezar con waterfall vacío
      if (lastTimestampRef.current === 0) {
        console.log('🌊 Waterfall first load - setting timestamp, starting fresh');
        if (result.length > 0) {
          lastTimestampRef.current = result[0].timestamp;
        }
        // NO establecer history aquí - dejarlo vacío para empezar limpio
        return;
      }
      
      // En cargas subsecuentes, solo agregar datos NUEVOS al principio
      const newData = result.filter(item => item.timestamp > lastTimestampRef.current);
      
      if (newData.length > 0) {
        console.log(`🌊 Waterfall adding ${newData.length} new captures`);
        
        const newConverted = newData.map(item => {
          const freqStep = (item.end_freq_hz - item.start_freq_hz) / item.Pxx.length;
          return item.Pxx.map((power, index) => ({
            frequency: item.start_freq_hz + (index * freqStep),
            power: power,
          }));
        });
        
        setHistory(prev => {
          // Agregar nuevos datos al principio y mantener el límite
          const updated = [...newConverted, ...prev];
          return updated.slice(0, limit);
        });
        
        lastTimestampRef.current = newData[0].timestamp;
      }
    } catch (err: any) {
      // Ignorar errores de abort (son normales al cambiar sensor)
      if (err.name === 'AbortError') {
        console.log('🚫 Waterfall request abortado');
        return;
      }
      setError(err.message);
      console.error('Error loading waterfall data:', err);
    } finally {
      loadingHistoryRef.current = false;
      setLoading(false);
    }
  }, [sensorMac, limit]);

  // Cleanup: Cancelar request cuando se desmonte
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Resetear cuando cambia el sensor o cambia el estado de autoRefresh
  useEffect(() => {
    const sensorChanged = sensorMac !== prevSensorMacRef.current;
    const autoRefreshChanged = autoRefresh !== lastAutoRefreshRef.current;

    if (sensorChanged) {
      console.log('🔄 Waterfall reset: sensor changed', { 
        from: prevSensorMacRef.current, 
        to: sensorMac 
      });
      
      // Cancelar request en vuelo del sensor anterior
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();
      
      // Resetear timestamp y limpiar histórico
      lastTimestampRef.current = 0;
      setHistory([]);
      setError(null);
      requestIdRef.current = 0;
    }

    if (!sensorChanged && autoRefreshChanged) {
      // Limpiar waterfall cuando:
      // 1. Se DETIENE el monitoreo (autoRefresh: true → false)
      // 2. Se INICIA el monitoreo (autoRefresh: false → true)
      if (!autoRefresh && lastAutoRefreshRef.current) {
        console.log('🔄 Waterfall reset: monitoring stopped');
        lastTimestampRef.current = 0;
        setHistory([]);
        setError(null);
      } else if (autoRefresh && !lastAutoRefreshRef.current) {
        console.log('🔄 Waterfall reset: monitoring started');
        lastTimestampRef.current = 0;
        setHistory([]);
        setError(null);
      }
    }

    prevSensorMacRef.current = sensorMac;
    lastAutoRefreshRef.current = autoRefresh;
  }, [sensorMac, autoRefresh]);

  // NO cargar historial automáticamente al montar
  // Solo cargar cuando autoRefresh está activo (modo monitoreo)
  useEffect(() => {
    if (!autoRefresh || !sensorMac) {
      return;
    }

    // Cargar datos inmediatamente
    loadHistory();

    // Configurar polling en intervalo
    const interval = setInterval(loadHistory, refreshInterval);

    return () => {
      clearInterval(interval);
      // Nota: No cancelamos el AbortController aquí porque se maneja en el otro useEffect
    };
  }, [autoRefresh, sensorMac, refreshInterval, loadHistory]);

  return {
    history,
    loading,
    error,
    reload: loadHistory,
  };
}

// Hook para cargar datos desde archivos locales (para desarrollo/demo)
export function useLocalSpectrumData(folderPath: 'AM' | 'FM' | null) {
  const [data, setData] = useState<{ frequency: number; power: number }[]>([]);
  const [waterfallHistory, setWaterfallHistory] = useState<{ frequency: number; power: number }[][]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!folderPath) return;

    // Simular carga de archivos JSON locales
    const loadLocalData = async () => {
      try {
        // En un entorno real, necesitarías listar los archivos del directorio
        // Por ahora, vamos a simular con datos de ejemplo
        const basePath = `/data/comparative_${folderPath}_json/`;
        
        // Cargar un archivo de ejemplo
        const response = await fetch(`${basePath}1764533478142.json`);
        const jsonData: SpectrumData = await response.json();
        
        // Convertir a formato de gráfico
        const freqStep = (jsonData.end_freq_hz - jsonData.start_freq_hz) / jsonData.Pxx.length;
        const chartData = jsonData.Pxx.map((power, index) => ({
          frequency: jsonData.start_freq_hz + (index * freqStep),
          power: power,
        }));
        
        setData(chartData);
        setWaterfallHistory(prev => [...prev, chartData].slice(-200));
      } catch (error) {
        console.error('Error loading local data:', error);
      }
    };

    loadLocalData();
  }, [folderPath, currentIndex]);

  const nextFile = () => {
    setCurrentIndex(prev => (prev + 1) % 20);
  };

  const prevFile = () => {
    setCurrentIndex(prev => (prev - 1 + 20) % 20);
  };

  return {
    data,
    waterfallHistory,
    nextFile,
    prevFile,
    currentIndex,
  };
}
