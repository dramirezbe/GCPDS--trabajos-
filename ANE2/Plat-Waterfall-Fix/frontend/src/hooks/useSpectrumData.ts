import { useState, useEffect, useCallback, useRef } from 'react';
import { sensorDataAPI, SpectrumData } from '../services/api';

export function useSpectrumData(sensorMac: string | null, autoRefresh: boolean = false, refreshInterval: number = 1000, resetKey: number = 0) {
  const [data, setData] = useState<SpectrumData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false); // Para evitar llamadas simultáneas
  const lastResetKeyRef = useRef(resetKey);

  const loadData = useCallback(async () => {
    if (!sensorMac || loadingRef.current) return;
    
    loadingRef.current = true;
    setError(null);
    
    try {
      const result = await sensorDataAPI.getLatestData(sensorMac, 1);
      setData(result);
    } catch (err: any) {
      setError(err.message);
      console.error('Error loading spectrum data:', err);
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [sensorMac]);

  // NO cargar datos automáticamente al montar
  // Solo cargar cuando autoRefresh está activo (modo monitoreo)
  // useEffect(() => {
  //   loadData();
  // }, [loadData]);

  const prevAutoRefreshRef = useRef(autoRefresh);

  useEffect(() => {
    if (!autoRefresh || !sensorMac) {
      // Si el autoRefresh se desactiva, limpiar los datos
      if (prevAutoRefreshRef.current && !autoRefresh) {
        setData([]);
      }
      prevAutoRefreshRef.current = autoRefresh;
      return;
    }

    // Si autoRefresh acaba de activarse (inicio de monitoreo), resetear datos
    if (!prevAutoRefreshRef.current && autoRefresh) {
      console.log('🔄 Spectrum reset: monitoring started');
      setData([]);
    }
    prevAutoRefreshRef.current = autoRefresh;

    const interval = setInterval(() => {
      loadData();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, sensorMac, refreshInterval, loadData]);

  // Resetear cuando cambia el resetKey (cambio de parámetros en vivo)
  useEffect(() => {
    if (resetKey !== lastResetKeyRef.current) {
      console.log('🔄 Spectrum reset: config updated in-flight (resetKey)', resetKey);
      setData([]);
      lastResetKeyRef.current = resetKey;
    }
  }, [resetKey]);

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
export function useWaterfallData(sensorMac: string | null, limit: number = 100, autoRefresh: boolean = false, refreshInterval: number = 3000, resetKey: number = 0) {
  const [history, setHistory] = useState<{ frequency: number; power: number }[][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastTimestampRef = useRef<number>(0);
  const lastSensorMacRef = useRef<string | null>(null);
  const lastAutoRefreshRef = useRef(autoRefresh);
  const lastResetKeyRef = useRef(resetKey);

  // Resetear cuando cambia el sensor o cambia el estado de autoRefresh
  useEffect(() => {
    const sensorChanged = sensorMac !== lastSensorMacRef.current;
    const autoRefreshChanged = autoRefresh !== lastAutoRefreshRef.current;

    // Limpiar waterfall cuando:
    // 1. Cambia el sensor
    // 2. Se DETIENE el monitoreo (autoRefresh: true → false)
    // 3. Se INICIA el monitoreo (autoRefresh: false → true)
    if (sensorChanged || autoRefreshChanged) {
      console.log('🔄 Waterfall reset:', { 
        reason: sensorChanged ? 'sensor changed' : (autoRefresh ? 'monitoring started' : 'monitoring stopped'),
        sensorMac,
        autoRefresh
      });
      lastTimestampRef.current = 0;
      lastSensorMacRef.current = sensorMac;
      setHistory([]);
    }
    
    lastAutoRefreshRef.current = autoRefresh;
  }, [sensorMac, autoRefresh]);

  // Resetear cuando cambia el resetKey (cambio de parámetros en vivo)
  useEffect(() => {
    if (resetKey !== lastResetKeyRef.current) {
      console.log('🌊 Waterfall reset: config updated in-flight (resetKey)', resetKey);
      lastTimestampRef.current = 0;
      setHistory([]);
      lastResetKeyRef.current = resetKey;
    }
  }, [resetKey]);

  const loadingHistoryRef = useRef(false); // Para evitar llamadas simultáneas

  const loadHistory = useCallback(async () => {
    if (!sensorMac || loadingHistoryRef.current) return;
    
    loadingHistoryRef.current = true;
    setError(null);
    
    try {
      const result = await sensorDataAPI.getLatestData(sensorMac, limit);
      
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
      setError(err.message);
      console.error('Error loading waterfall data:', err);
    } finally {
      loadingHistoryRef.current = false;
      setLoading(false);
    }
  }, [sensorMac, limit]);

  // NO cargar historial automáticamente al montar
  // Solo cargar cuando autoRefresh está activo (modo monitoreo)
  // useEffect(() => {
  //   loadHistory();
  // }, [loadHistory]);

  useEffect(() => {
    if (!autoRefresh || !sensorMac) return;
    const interval = setInterval(loadHistory, refreshInterval);
    return () => clearInterval(interval);
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
