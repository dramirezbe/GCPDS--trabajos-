import { useState, useEffect, useRef } from 'react';
import { Network, Radio, BarChart3, Settings, HelpCircle, ChevronLeft, ChevronRight, X, Edit2, Trash2, Unlock } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Sidebar } from './components/Sidebar';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { AnalysisPanel, AnalysisPanelRef } from './components/AnalysisPanel';
import { MonitoringNetwork } from './components/MonitoringNetwork';
import { AntennaManagement } from './components/AntennaManagement';
import { CampaignsList } from './components/CampaignsList';
import { AlertsPanel } from './components/AlertsPanel';
import { UserManagement } from './components/UserManagement';
import { useSpectrumData } from './hooks/useSpectrumData';
import { sensorAPI, Sensor, statisticsAPI, Statistics, configAPI } from './services/api';
import { useAuth } from './contexts/AuthContext';
import axios from 'axios';
import Login from './components/Login';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

function AppContent() {
  const { user, logout, isAuthenticated, isAdmin, loading } = useAuth();
  
  console.log('🔵 [App] Estado actual - loading:', loading, ', isAuthenticated:', isAuthenticated, ', user:', user?.username || 'null');
  
  // Mostrar loading mientras se verifica la autenticación
  if (loading) {
    console.log('⏳ [App] Mostrando pantalla de carga...');
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div>Cargando...</div>
      </div>
    );
  }

  // Si no está autenticado, mostrar Login (Modo Azure por defecto)
  if (!isAuthenticated) {
    console.log('⚠️ [App] Usuario NO autenticado. Mostrando Login.');
    return <Login showLegacyForm={false} />;
  }

  console.log('✅ [App] Usuario autenticado. Mostrando Dashboard.');
  return <AuthenticatedApp user={user} logout={logout} isAdmin={isAdmin} />;
}

function AuthenticatedApp({ user, logout, isAdmin }: { user: any, logout: () => void, isAdmin: boolean }) {
  const [activeTab, setActiveTab] = useState('inicio');
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [isMonitoringActive, setIsMonitoringActive] = useState(false);
  const [maxMonitoringTime, setMaxMonitoringTime] = useState<number>(10); // Límite de tiempo en minutos
  const [centerFreqTolerance, setCenterFreqTolerance] = useState<number>(100); // kHz
  const [bandwidthTolerance, setBandwidthTolerance] = useState<number>(10); // kHz
  const [hideConfigPanel, setHideConfigPanel] = useState(false);
  const [showSensorModal, setShowSensorModal] = useState(false);
  const [showSensorsList, setShowSensorsList] = useState(false);
  const [isEditingSensor, setIsEditingSensor] = useState(false);
  const [sensorFormData, setSensorFormData] = useState<Partial<Sensor>>({
    mac: '',
    name: '',
    description: '',
    status: 'offline',
    status_admin: 'active'
  });
  const [validationErrors, setValidationErrors] = useState<{ [key: string]: string }>({});
  
  // Estados para datos WebSocket (Monitoreo sin persistencia)
  // const [wsSpectrumData, setWsSpectrumData] = useState<any[]>([]); // Deshabilitado: WS es solo para audio
  // const [wsWaterfallHistory, setWsWaterfallHistory] = useState<any[][]>([]); // Deshabilitado: WS es solo para audio

  const handleConfigUpdate = async (key: string, value: number) => {
    try {
      await configAPI.update({ [key]: value });
      // Actualizar estado local
      if (key === 'center_freq_tolerance_khz') setCenterFreqTolerance(value);
      if (key === 'bandwidth_tolerance_khz') setBandwidthTolerance(value);
      if (key === 'max_monitoring_time_min') setMaxMonitoringTime(value);
    } catch (error) {
      console.error('Error updating config:', error);
      alert('Error al guardar la configuración');
    }
  };

  const [config, setConfig] = useState({
    sampleRate: 20,
    rbw: '100000',
    vbw: 'RBW',
    centerFrequency: 97.5,
    bandwidth: 20,
    span: 20,
    device: 'MACOS',
    antenna: '',
    antennaGain: 0,
    startFrequency: 88,
    endFrequency: 108,
    preset: 'custom',
    lna_gain: 0,
    vga_gain: 0,
    antenna_amp: true,
  });

  const [demodType, setDemodType] = useState<'AM' | 'FM' | ''>('');
  const [demodMetrics, setDemodMetrics] = useState<{
    excursion_hz?: number;
    depth?: number;
  }>({});

  // Cache scope changes should clear Spectrum.
  const cacheScopeKey = `${selectedSensor?.mac ?? 'none'}|${config.preset ?? 'none'}`;

  // Estado para pre-llenar campaña desde monitoreo
  const [campaignPrefillData, setCampaignPrefillData] = useState<any>(null);

  // Ref para controlar el audio en AnalysisPanel
  const analysisPanelRef = useRef<AnalysisPanelRef>(null);

  const handleStopMonitoring = async (sensorMac: string) => {
    try {
      // Enviar configuración de parada explícita
      await axios.post(`${API_BASE_URL}/sensor/${sensorMac}/configure`, {
        mac: sensorMac,
        center_frequency: 0,
        sample_rate_hz: 0,
        resolution_hz: 0,
        vbw: 'auto',
        antenna_port: 0,
        window: 'hann',
        overlap: 0.5,
        lna_gain: 0,
        vga_gain: 0,
        antenna_amp: false,
        is_monitoring: true
      });

      // Llamar al endpoint de stop
      await axios.post(`${API_BASE_URL}/sensor/${sensorMac}/stop`);
      
      setIsMonitoringActive(false);
      if (analysisPanelRef.current) {
        analysisPanelRef.current.stopAudio();
      }
    } catch (error) {
      console.error('Error stopping monitoring:', error);
      throw error;
    }
  };

  const handleTabChange = async (newTab: string) => {
    if (isMonitoringActive && newTab !== 'monitoreo') {
      const confirmLeave = window.confirm('Hay una adquisición en curso. Si cambia de pestaña, la adquisición se detendrá. ¿Desea continuar?');
      if (!confirmLeave) return;
      
      if (selectedSensor) {
        try {
          await handleStopMonitoring(selectedSensor.mac);
        } catch (error) {
          console.error('Error stopping monitoring on tab change:', error);
          // Aún así cambiamos de pestaña? Mejor avisar al usuario
          alert('Error al detener el monitoreo. Por favor intente detenerlo manualmente.');
          return;
        }
      }
    }
    
    // Si cambiamos a pestañas donde se seleccionan sensores, recargar la lista
    // para asegurar que los estados (online/offline/busy) estén actualizados
    if (newTab === 'campañas' || newTab === 'monitoreo' || newTab === 'dispositivos') {
      try {
        // Forzar validación en backend antes de cargar
        await sensorAPI.validateStatus();
      } catch (e) {
        console.error('Error validating status:', e);
      }
      loadSensors();
    }
    
    setActiveTab(newTab);
  };

  const handleUnlockSensor = async (sensorMac: string) => {
    if (!window.confirm(`¿Está seguro de desbloquear el sensor ${sensorMac}? Esto detendrá cualquier adquisición en curso y liberará el sensor.`)) return;
    
    try {
      await handleStopMonitoring(sensorMac);
      alert('Sensor desbloqueado correctamente');
      loadSensors(); // Recargar lista para actualizar estado
    } catch (error) {
      console.error('Error unlocking sensor:', error);
      alert('Error al desbloquear sensor');
    }
  };

  const handleCreateCampaign = (configData: any) => {
    setCampaignPrefillData(configData);
    setActiveTab('campañas');
  };

  // Cargar sensores disponibles y configuración
  const loadSensors = async () => {
    try {
      const data = await sensorAPI.getAll();
      setSensors(data);
      if (data.length > 0 && !selectedSensor) {
        setSelectedSensor(data[0]);
      }
    } catch (error) {
      console.error('Error loading sensors:', error);
    }
  };

  const loadConfig = async () => {
    try {
      const configs = await configAPI.get();
      if (configs.center_freq_tolerance_khz) {
        setCenterFreqTolerance(Number(configs.center_freq_tolerance_khz));
      }
      if (configs.bandwidth_tolerance_khz) {
        setBandwidthTolerance(Number(configs.bandwidth_tolerance_khz));
      }
      if (configs.max_monitoring_time_min) {
        setMaxMonitoringTime(Number(configs.max_monitoring_time_min));
      }
    } catch (error) {
      console.error('Error loading config:', error);
    }
  };

  useEffect(() => {
    loadSensors();
    loadConfig();
  }, []);

  // Validar formulario de sensor
  const validateSensorForm = (): boolean => {
    const errors: { [key: string]: string } = {};
    
    // Validar nombre
    if (!sensorFormData.name || sensorFormData.name.trim() === '') {
      errors.name = 'El nombre del sensor es obligatorio';
    } else {
      // Validar duplicado de nombre
      // Si estamos editando, excluir el sensor actual de la validación
      const duplicate = sensors.find(s => 
        s.name.toLowerCase() === sensorFormData.name?.toLowerCase() && 
        (!isEditingSensor || s.id !== sensorFormData.id)
      );
      if (duplicate) {
        errors.name = 'Ya existe un sensor con este nombre';
      }
    }
    
    // Validar MAC
    if (!sensorFormData.mac || sensorFormData.mac.trim() === '') {
      errors.mac = 'La dirección MAC es obligatoria';
    } else {
      // Validar formato MAC (AA:BB:CC:DD:EE:FF)
      const macPattern = /^[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}$/;
      if (!macPattern.test(sensorFormData.mac)) {
        errors.mac = 'Formato de MAC inválido. Use formato AA:BB:CC:DD:EE:FF';
      }
    }
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Manejar envío de formulario de sensor
  const handleSubmitSensor = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateSensorForm()) {
      return;
    }
    
    try {
      if (isEditingSensor && sensorFormData.id) {
        await sensorAPI.update(sensorFormData.id, sensorFormData as Sensor);
        alert('Sensor actualizado exitosamente');
      } else {
        await sensorAPI.create(sensorFormData as Sensor);
        alert('Sensor creado exitosamente');
      }
      
      setShowSensorModal(false);
      setSensorFormData({
        mac: '',
        name: '',
        description: '',
        status: 'offline',
        status_admin: 'active'
      });
      setIsEditingSensor(false);
      setValidationErrors({});
      loadSensors();
    } catch (error) {
      console.error('Error saving sensor:', error);
      alert('Error al guardar el sensor. Verifica los datos.');
    }
  };

  const handleDeleteSensor = async (id: number) => {
    if (!window.confirm('¿Está seguro de eliminar este sensor? Esta acción no se puede deshacer.')) {
      return;
    }

    try {
      await sensorAPI.delete(id);
      loadSensors();
      alert('Sensor eliminado exitosamente');
    } catch (error) {
      console.error('Error deleting sensor:', error);
      alert('Error al eliminar el sensor');
    }
  };

  const handleEditSensor = (sensor: Sensor) => {
    setSensorFormData({
      id: sensor.id,
      name: sensor.name,
      mac: sensor.mac,
      description: sensor.description,
      status: sensor.status,
      status_admin: sensor.status_admin || 'active'
    });
    setIsEditingSensor(true);
    setShowSensorModal(true);
  };

  // Cargar estadísticas generales
  useEffect(() => {
    const loadStatistics = async () => {
      try {
        const data = await statisticsAPI.getSummary();
        setStatistics(data);
      } catch (error) {
        console.error('Error loading statistics:', error);
      }
    };
    loadStatistics();
    
    // Actualizar cada 30 segundos
    const interval = setInterval(loadStatistics, 30000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket para datos en tiempo real (Espectro, Waterfall y Métricas)
  useEffect(() => {
    if (!isMonitoringActive) {
      setDemodMetrics({});
      return;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsPort = window.location.protocol === 'https:' ? ':12443' : ':3000';
    const wsUrl = `${wsProtocol}//${window.location.hostname}${wsPort}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('📊 Conectado a WebSocket para Monitoreo Realtime');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        // NOTA: El WebSocket es principalmente para Audio (AM/FM) y Métricas
        // Los datos de espectro (Pxx) se obtienen por Polling a la API
        
        if (message.type === 'sensor_data' && message.data) {
          // Actualizar métricas si vienen en los datos
          if (message.data.excursion_hz !== undefined) {
            setDemodMetrics(prev => ({
              ...prev,
              excursion_hz: message.data.excursion_hz
            }));
          }
          if (message.data.depth !== undefined) {
            setDemodMetrics(prev => ({
              ...prev,
              depth: message.data.depth
            }));
          }

          // Actualizar Espectro y Waterfall (si es el sensor seleccionado)
          if (selectedSensor && message.data.mac === selectedSensor.mac) {
             // ... lógica de WS spectrum ...
          }
        }

        // Actualizar GPS en tiempo real
        if (message.type === 'sensor_gps' && message.data && selectedSensor) {
          // Solo actualizar si el GPS es del sensor seleccionado
          if (message.data.mac === selectedSensor.mac) {
            setSelectedSensor(prev => prev ? {
              ...prev,
              lat: message.data.lat,
              lng: message.data.lng,
              alt: message.data.alt
            } : null);
            console.log('📍 GPS actualizado:', message.data);
          }
        }
      } catch (error) {
        console.error('Error procesando mensaje WebSocket:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('Error WebSocket:', error);
    };

    return () => {
      ws.close();
    };
  }, [isMonitoringActive, selectedSensor]);

  // Hook para datos en tiempo real - activamos auto-refresh para polling (ya que WS es solo audio)
  const { chartData: realtimeSpectrumData, data: rawSpectrumData, loading: loadingRealtimeSpectrum, error: realtimeSpectrumError } = useSpectrumData(
    isMonitoringActive && selectedSensor ? selectedSensor.mac : null,
    isMonitoringActive, // Auto-refresh ACTIVADO si hay monitoreo
    200, // Polling cada 0.2s
    cacheScopeKey
  );

  // Waterfall independiente del panel de control:
  // Se alimenta unicamente de las trazas de espectro ya normalizadas.
  const [realtimeWaterfallHistory, setRealtimeWaterfallHistory] = useState<{ frequency: number; power: number }[][]>([]);
  const lastSpectrumSignatureRef = useRef<string>('');
  const selectedSensorMac = selectedSensor?.mac ?? null;
  const [waterfallResetToken, setWaterfallResetToken] = useState(0);
  const lastWaterfallResetTokenRef = useRef(0);
  const pendingWaterfallResetRef = useRef(false);
  const targetFreqRangeAfterResetRef = useRef<{ minHz: number; maxHz: number } | null>(null);
  const graceFramesRemainingRef = useRef(0);
  const RESET_GRACE_FRAMES = 3;

  // Actualizar métricas desde datos de polling (SpectrumData)
  useEffect(() => {
    if (rawSpectrumData && rawSpectrumData.length > 0) {
      const latest = rawSpectrumData[0];
      // Solo actualizar si hay valores válidos
      if (latest.excursion_hz !== undefined || latest.depth !== undefined) {
        setDemodMetrics(prev => ({
          ...prev,
          ...(latest.excursion_hz !== undefined && { excursion_hz: latest.excursion_hz }),
          ...(latest.depth !== undefined && { depth: latest.depth })
        }));
      }
    }
  }, [rawSpectrumData]);

  useEffect(() => {
    if (!isMonitoringActive || !selectedSensorMac) {
      setRealtimeWaterfallHistory([]);
      lastSpectrumSignatureRef.current = '';
      pendingWaterfallResetRef.current = false;
      targetFreqRangeAfterResetRef.current = null;
      graceFramesRemainingRef.current = 0;
      return;
    }

    // Reset atomico: cuando cambia el token, limpiar y esperar el siguiente frame
    // para iniciar una nueva sesion de waterfall sin mezclar filas antiguas.
    if (waterfallResetToken !== lastWaterfallResetTokenRef.current) {
      lastWaterfallResetTokenRef.current = waterfallResetToken;
      setRealtimeWaterfallHistory([]);
      lastSpectrumSignatureRef.current = '';
      pendingWaterfallResetRef.current = true;

      const minHz = (config.centerFrequency - config.span / 2) * 1e6;
      const maxHz = (config.centerFrequency + config.span / 2) * 1e6;
      targetFreqRangeAfterResetRef.current = { minHz, maxHz };
      graceFramesRemainingRef.current = RESET_GRACE_FRAMES;
      return;
    }

    if (!realtimeSpectrumData || realtimeSpectrumData.length === 0) {
      return;
    }

    const first = realtimeSpectrumData[0];
    const last = realtimeSpectrumData[realtimeSpectrumData.length - 1];

    // Ventana de gracia: descartar frames transitorios (stale) luego del reset
    // hasta que el rango de frecuencias coincida con la nueva configuracion.
    if (graceFramesRemainingRef.current > 0 && targetFreqRangeAfterResetRef.current) {
      const expected = targetFreqRangeAfterResetRef.current;
      const frameMinHz = first.frequency;
      const frameMaxHz = last.frequency;
      const expectedSpanHz = Math.max(expected.maxHz - expected.minHz, 1);
      const toleranceHz = Math.max(5_000, expectedSpanHz * 0.02);

      const rangeMatches =
        Math.abs(frameMinHz - expected.minHz) <= toleranceHz &&
        Math.abs(frameMaxHz - expected.maxHz) <= toleranceHz;

      if (!rangeMatches) {
        console.log('⏳ Waterfall grace window: dropping transient frame', {
          expectedMinHz: expected.minHz,
          expectedMaxHz: expected.maxHz,
          frameMinHz,
          frameMaxHz,
          toleranceHz,
          graceFramesRemaining: graceFramesRemainingRef.current,
        });
        return;
      }

      graceFramesRemainingRef.current -= 1;
      if (graceFramesRemainingRef.current === 0) {
        targetFreqRangeAfterResetRef.current = null;
      }
    }

    const signature = `${realtimeSpectrumData.length}|${first.frequency}|${last.frequency}|${first.power}|${last.power}`;

    // Evita duplicar filas cuando no hubo cambio real en el espectro.
    if (signature === lastSpectrumSignatureRef.current) {
      return;
    }

    lastSpectrumSignatureRef.current = signature;

    if (pendingWaterfallResetRef.current) {
      pendingWaterfallResetRef.current = false;
      setRealtimeWaterfallHistory([realtimeSpectrumData]);
      return;
    }

    setRealtimeWaterfallHistory(prev => [realtimeSpectrumData, ...prev].slice(0, 200));
  }, [isMonitoringActive, selectedSensorMac, realtimeSpectrumData, waterfallResetToken]);

  // Ya no se usan datos demo - solo tiempo real desde sensores activos

  // En monitoreo siempre se muestran datos en tiempo real (priorizando Polling ahora)
  const spectrumData = realtimeSpectrumData; // wsSpectrumData.length > 0 ? wsSpectrumData : realtimeSpectrumData;
  const waterfallHistory = realtimeWaterfallHistory; // wsWaterfallHistory.length > 0 ? wsWaterfallHistory : realtimeWaterfallHistory;
  const loading = loadingRealtimeSpectrum;
  const error = realtimeSpectrumError;

  // Debug: Log solo cuando cambian flags significativos (no en cada frame de espectro)
  useEffect(() => {
    console.log('🎯 App data update:', {
      mode: isMonitoringActive ? 'Monitoreo Activo' : 'Monitoreo Inactivo',
      sensor: selectedSensor?.name,
      loading,
      error
    });
  }, [isMonitoringActive, selectedSensor, loading, error]);

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar 
        activeTab={activeTab} 
        onTabChange={handleTabChange} 
        user={user}
        onLogout={logout}
        isAdmin={isAdmin}
      />

      {activeTab === 'inicio' ? (
        <div className="flex-1 relative overflow-hidden">
          {/* Mapa de fondo */}
          <div className="absolute inset-0">
            <MapContainer
              center={[4.6097, -74.0817]}
              zoom={6}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              {sensors.map((sensor) => {
                if (!sensor.lat || !sensor.lng) return null;
                const color = sensor.status === 'active' ? '#22c55e' : '#ef4444';
                return (
                  <Marker
                    key={sensor.id}
                    position={[sensor.lat, sensor.lng]}
                    icon={L.divIcon({
                      html: `<div style="background: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
                      iconSize: [12, 12],
                      iconAnchor: [6, 6]
                    })}
                  >
                    <Popup>
                      <strong>{sensor.name}</strong>
                      <br />
                      <small>{sensor.description || 'Sin descripción'}</small>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          </div>
          
          {/* Contenido sobre el mapa */}
          <div className="relative z-10 flex-1 overflow-auto">
            <div className="max-w-7xl mx-auto p-6">
            <div className="mb-6 text-center">
              <h1 className="text-3xl font-bold text-gray-900">Bienvenido a ANE | Plataforma de Sensado Espectral</h1>
            </div>
            
            {/* Estadísticas Generales */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Estadísticas Generales</h2>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Gráfico de Campañas */}
                <div>
                  <h3 className="text-center text-gray-700 font-medium mb-4">Campañas</h3>
                  <div className="flex items-center justify-center">
                    <div className="relative w-64 h-64">
                      <svg viewBox="0 0 200 200" className="w-full h-full">
                        {/* Anillo de dona para campañas */}
                        <circle cx="100" cy="100" r="70" fill="none" stroke="#e5e7eb" strokeWidth="30"/>
                        {statistics && statistics.campaigns.total > 0 && (
                          <>
                            {/* Programadas (verde) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#22c55e" strokeWidth="30"
                                    strokeDasharray={`${((statistics.campaigns.scheduled / statistics.campaigns.total) * 439.8)}, 439.8`} 
                                    transform="rotate(-90 100 100)"/>
                            {/* En ejecución (azul) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#3b82f6" strokeWidth="30"
                                    strokeDasharray={`${((statistics.campaigns.running / statistics.campaigns.total) * 439.8)}, 439.8`} 
                                    strokeDashoffset={`${-((statistics.campaigns.scheduled / statistics.campaigns.total) * 439.8)}`}
                                    transform="rotate(-90 100 100)"/>
                            {/* Terminadas (gris) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#9ca3af" strokeWidth="30"
                                    strokeDasharray={`${((statistics.campaigns.completed / statistics.campaigns.total) * 439.8)}, 439.8`} 
                                    strokeDashoffset={`${-(((statistics.campaigns.scheduled + statistics.campaigns.running) / statistics.campaigns.total) * 439.8)}`}
                                    transform="rotate(-90 100 100)"/>
                            {/* Canceladas (rojo) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#ef4444" strokeWidth="30"
                                    strokeDasharray={`${((statistics.campaigns.cancelled / statistics.campaigns.total) * 439.8)}, 439.8`} 
                                    strokeDashoffset={`${-(((statistics.campaigns.scheduled + statistics.campaigns.running + statistics.campaigns.completed) / statistics.campaigns.total) * 439.8)}`}
                                    transform="rotate(-90 100 100)"/>
                          </>                        
                        )}
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                          <p className="text-3xl font-bold text-gray-900">{statistics?.campaigns.total || 0}</p>
                          <p className="text-sm text-gray-600">Total</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <span className="text-sm text-gray-700">Programadas: {statistics?.campaigns.scheduled || 0}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                      <span className="text-sm text-gray-700">En ejecución: {statistics?.campaigns.running || 0}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                      <span className="text-sm text-gray-700">Terminadas: {statistics?.campaigns.completed || 0}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <span className="text-sm text-gray-700">Canceladas: {statistics?.campaigns.cancelled || 0}</span>
                    </div>
                  </div>
                </div>

                {/* Gráfico de Dispositivos */}
                <div>
                  <h3 className="text-center text-gray-700 font-medium mb-4">Dispositivos</h3>
                  <div className="flex items-center justify-center">
                    <div className="relative w-64 h-64">
                      <svg viewBox="0 0 200 200" className="w-full h-full">
                        {/* Anillo de dona para dispositivos */}
                        <circle cx="100" cy="100" r="70" fill="none" stroke="#e5e7eb" strokeWidth="30"/>
                        {statistics && statistics.sensors.total > 0 && (
                          <>
                            {/* Activos (verde) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#22c55e" strokeWidth="30"
                                    strokeDasharray={`${((statistics.sensors.active / statistics.sensors.total) * 439.8)}, 439.8`} 
                                    transform="rotate(-90 100 100)"/>
                            {/* Inactivos (gris) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#9ca3af" strokeWidth="30"
                                    strokeDasharray={`${((statistics.sensors.inactive / statistics.sensors.total) * 439.8)}, 439.8`} 
                                    strokeDashoffset={`${-((statistics.sensors.active / statistics.sensors.total) * 439.8)}`}
                                    transform="rotate(-90 100 100)"/>
                            {/* Error (rojo) */}
                            <circle cx="100" cy="100" r="70" fill="none" stroke="#ef4444" strokeWidth="30"
                                    strokeDasharray={`${((statistics.sensors.error / statistics.sensors.total) * 439.8)}, 439.8`} 
                                    strokeDashoffset={`${-(((statistics.sensors.active + statistics.sensors.inactive) / statistics.sensors.total) * 439.8)}`}
                                    transform="rotate(-90 100 100)"/>
                          </>
                        )}
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="text-center">
                          <p className="text-3xl font-bold text-gray-900">{statistics?.sensors.total || sensors.length}</p>
                          <p className="text-sm text-gray-600">Total</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-4">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-green-500"></div>
                      <span className="text-sm text-gray-700">Online: {sensors.filter(s => s.status === 'online' || s.status === 'active').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                      <span className="text-sm text-gray-700">Ocupado: {sensors.filter(s => s.status === 'busy').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                      <span className="text-sm text-gray-700">Delay: {sensors.filter(s => s.status === 'delay').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-gray-500"></div>
                      <span className="text-sm text-gray-700">Offline: {sensors.filter(s => s.status === 'offline' || s.status === 'inactive').length}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      <span className="text-sm text-gray-700">Error: {sensors.filter(s => s.status === 'error').length}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Accesos Rápidos */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Dispositivos</h3>
                  <Network className="w-8 h-8 text-orange-500" />
                </div>
                <p className="text-gray-600 mb-4">Gestiona y monitorea tus sensores en el mapa.</p>
                <button
                  onClick={() => handleTabChange('dispositivos')}
                  className="text-orange-600 hover:text-orange-700 font-medium"
                >
                  Ver dispositivos →
                </button>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Monitoreo</h3>
                  <Radio className="w-8 h-8 text-green-500" />
                </div>
                <p className="text-gray-600 mb-4">Visualiza espectro y waterfall en tiempo real.</p>
                <button
                  onClick={() => handleTabChange('monitoreo')}
                  className="text-orange-600 hover:text-orange-700 font-medium"
                >
                  Ir a monitoreo →
                </button>
              </div>

              <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Campañas</h3>
                  <BarChart3 className="w-8 h-8 text-blue-500" />
                </div>
                <p className="text-gray-600 mb-4">Organiza y analiza campañas de medición.</p>
                <button
                  onClick={() => handleTabChange('campañas')}
                  className="text-orange-600 hover:text-orange-700 font-medium"
                >
                  Ver campañas →
                </button>
              </div>
            </div>
          </div>
          </div>
          
          <style>{`
            @keyframes pulse {
              0%, 100% { opacity: 1; transform: scale(1); }
              50% { opacity: 0.5; transform: scale(1.1); }
            }
          `}</style>
        </div>
      ) : activeTab === 'alertas' ? (
        <AlertsPanel />
      ) : activeTab === 'dispositivos' ? (
        <MonitoringNetwork />
      ) : activeTab === 'campañas' ? (
        <CampaignsList sensors={sensors} isAdmin={isAdmin} prefillData={campaignPrefillData} />
      ) : activeTab === 'configuracion' ? (
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Configuración</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Antenas */}
              <AntennaManagement />

              {/* Sensores */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <Network className="w-5 h-5 text-blue-600" />
                    </div>
                    <h2 className="text-xl font-semibold text-gray-900">Sensores</h2>
                  </div>
                  <button 
                    onClick={() => {
                      setSensorFormData({
                        mac: '',
                        name: '',
                        description: '',
                        status: 'offline',
                        status_admin: 'active'
                      });
                      setIsEditingSensor(false);
                      setShowSensorModal(true);
                    }}
                    className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    + Agregar
                  </button>
                </div>
                <p className="text-gray-600 mb-4">Administra los sensores de monitoreo.</p>
                <div className="space-y-2">
                  <div className="p-3 bg-gray-50 rounded border border-gray-200">
                    <p className="font-medium text-gray-900">Sensores registrados: {sensors.length}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      Activos: {sensors.filter(s => s.status_admin !== 'inactive').length} | 
                      Inactivos: {sensors.filter(s => s.status_admin === 'inactive').length}
                    </p>
                  </div>
                  
                  {/* Lista desplegable de sensores */}
                  {showSensorsList && (
                    <div className="mt-3 max-h-64 overflow-y-auto space-y-2">
                      {sensors.map((sensor) => (
                        <div
                          key={sensor.id}
                          className="p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <h4 className="font-semibold text-gray-800 text-sm">{sensor.name}</h4>
                              <p className="text-xs text-gray-500 font-mono mt-1">{sensor.mac}</p>
                              {sensor.description && (
                                <p className="text-xs text-gray-600 mt-1">{sensor.description}</p>
                              )}
                              <div className="flex items-center gap-3 mt-2 text-xs text-gray-600">
                                <span>📍 {sensor.lat?.toFixed(4)}, {sensor.lng?.toFixed(4)}</span>
                                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                  sensor.status_admin === 'inactive'
                                    ? 'bg-gray-200 text-gray-600'
                                    : sensor.status === 'online'
                                      ? 'bg-green-100 text-green-800'
                                      : sensor.status === 'busy'
                                        ? 'bg-orange-100 text-orange-800'
                                        : sensor.status === 'delay'
                                          ? 'bg-yellow-100 text-yellow-800'
                                          : 'bg-red-100 text-red-800'
                                }`}>
                                  {sensor.status_admin === 'inactive' ? 'Inactivo' : (sensor.status || 'Offline').toUpperCase()}
                                </span>
                              </div>
                            </div>
                            <div className="flex flex-col gap-2 ml-4">
                              <button
                                onClick={() => handleEditSensor(sensor)}
                                className="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                title="Editar"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => sensor.id && handleDeleteSensor(sensor.id)}
                                className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors"
                                title="Eliminar"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <button 
                  onClick={() => setShowSensorsList(!showSensorsList)}
                  className="w-full mt-4 px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
                >
                  {showSensorsList ? 'Ocultar Sensores' : 'Ver Todos los Sensores'}
                </button>
              </div>

              {/* Gestión de Usuarios - Componente completo */}
              <div className="md:col-span-2">
                <UserManagement currentUser={user!} />
              </div>

              {/* Configuración General */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center">
                    <Settings className="w-5 h-5 text-purple-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900">Configuración General</h2>
                </div>
                <p className="text-gray-600 mb-4">Ajustes generales del sistema.</p>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">Puerto Backend:</span>
                    <span className="text-sm font-medium text-gray-900">3000</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">Puerto Frontend:</span>
                    <span className="text-sm font-medium text-gray-900">5173</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">Base de Datos:</span>
                    <span className="text-sm font-medium text-gray-900">PostgreSQL</span>
                  </div>
                  
                  {/* Límite de Tiempo de Adquisición en Realtime */}
                  <div className="pt-3 border-t border-gray-200">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Límite de Tiempo de Adquisición en Realtime:
                    </label>
                    <select
                      value={maxMonitoringTime}
                      onChange={(e) => handleConfigUpdate('max_monitoring_time_min', Number(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value={5}>5 minutos</option>
                      <option value={10}>10 minutos</option>
                      <option value={15}>15 minutos</option>
                      <option value={20}>20 minutos</option>
                      <option value={30}>30 minutos</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Duración máxima de monitoreo en tiempo real
                    </p>
                  </div>

                  {/* Tolerancia de Frecuencia Central */}
                  <div className="pt-3 border-t border-gray-200">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tolerancia de Frecuencia Central (kHz):
                    </label>
                    <input
                      type="number"
                      value={centerFreqTolerance}
                      onChange={(e) => handleConfigUpdate('center_freq_tolerance_khz', Number(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Valor por defecto: 100 kHz
                    </p>
                  </div>

                  {/* Tolerancia de Ancho de Banda */}
                  <div className="pt-3 border-t border-gray-200">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Tolerancia de Ancho de Banda (kHz):
                    </label>
                    <input
                      type="number"
                      value={bandwidthTolerance}
                      onChange={(e) => handleConfigUpdate('bandwidth_tolerance_khz', Number(e.target.value))}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Valor por defecto: 10 kHz
                    </p>
                  </div>
                </div>
              </div>

              {/* Desbloquear Sensor (Solution 2) */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                    <Unlock className="w-5 h-5 text-red-600" />
                  </div>
                  <h2 className="text-xl font-semibold text-gray-900">Desbloquear Sensor</h2>
                </div>
                <p className="text-gray-600 mb-4">
                  Libera sensores que hayan quedado bloqueados en estado "Ocupado".
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Sensor Ocupado:
                    </label>
                    <select
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                      onChange={(e) => {
                        if (e.target.value) {
                          handleUnlockSensor(e.target.value);
                          e.target.value = ""; // Reset select
                        }
                      }}
                      defaultValue=""
                    >
                      <option value="" disabled>Seleccione un sensor...</option>
                      {sensors.filter(s => s.status === 'busy').map(s => (
                        <option key={s.id} value={s.mac}>
                          {s.name} ({s.mac})
                        </option>
                      ))}
                    </select>
                  </div>
                  {sensors.filter(s => s.status === 'busy').length === 0 && (
                    <p className="text-sm text-green-600 italic">
                      No hay sensores bloqueados actualmente.
                    </p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : activeTab === 'ayuda' ? (
        <div className="flex-1 overflow-auto p-8">
          <div className="max-w-6xl mx-auto">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Ayuda</h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {/* Manual de Software */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center">
                    <HelpCircle className="w-6 h-6 text-orange-600" />
                  </div>
                  <h2 className="text-2xl font-semibold text-gray-900">Manual de Software</h2>
                </div>
                <p className="text-gray-600 mb-4">Documentación completa del sistema ANE.</p>
                
                <div className="space-y-3">
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Guía de Inicio Rápido</h3>
                    <p className="text-sm text-gray-600">Primeros pasos con el sistema ANE</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Gestión de Dispositivos</h3>
                    <p className="text-sm text-gray-600">Configuración de sensores y antenas</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Monitoreo de Espectro</h3>
                    <p className="text-sm text-gray-600">Análisis y visualización de señales</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Campañas de Medición</h3>
                    <p className="text-sm text-gray-600">Planificación y ejecución de campañas</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">API y Integración</h3>
                    <p className="text-sm text-gray-600">Documentación técnica de la API REST</p>
                  </div>
                </div>
                
                <button className="w-full mt-4 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors">
                  Ver Manual Completo
                </button>
              </div>

              {/* Manual de Hardware */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                    <Radio className="w-6 h-6 text-blue-600" />
                  </div>
                  <h2 className="text-2xl font-semibold text-gray-900">Manual de Hardware</h2>
                </div>
                <p className="text-gray-600 mb-4">Especificaciones técnicas y guías de instalación.</p>
                
                <div className="space-y-3">
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Especificaciones de Sensores</h3>
                    <p className="text-sm text-gray-600">Características técnicas del hardware</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Guía de Instalación</h3>
                    <p className="text-sm text-gray-600">Instalación física de sensores y antenas</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Configuración de Antenas</h3>
                    <p className="text-sm text-gray-600">Rangos de frecuencia y ganancia</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Mantenimiento</h3>
                    <p className="text-sm text-gray-600">Rutinas de mantenimiento preventivo</p>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 transition-colors cursor-pointer">
                    <h3 className="font-semibold text-gray-900 mb-1">Solución de Problemas</h3>
                    <p className="text-sm text-gray-600">Diagnóstico y resolución de fallas</p>
                  </div>
                </div>
                
                <button className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                  Ver Manual Completo
                </button>
              </div>
            </div>

            {/* Sección de contacto y soporte */}
            <div className="bg-gradient-to-r from-orange-50 to-blue-50 rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">¿Necesitas más ayuda?</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-900">Soporte Técnico</p>
                  <p className="text-sm text-gray-600 mt-1">soporte@ane.gov.co</p>
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-900">Documentación API</p>
                  <p className="text-sm text-gray-600 mt-1">docs.ane.gov.co</p>
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-900">Versión del Sistema</p>
                  <p className="text-sm text-gray-600 mt-1">ANE v1.0.0</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="relative flex flex-1 overflow-hidden">
          <div className={`w-[450px] overflow-y-auto border-r border-gray-200 ${hideConfigPanel ? 'hidden' : ''}`}>
            {/* Panel de monitoreo - datos en tiempo real */}
            <div className="p-4 bg-white border-b border-gray-200">
                {isMonitoringActive && selectedSensor && !loading && spectrumData.length > 0 && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-sm font-medium text-green-800 mb-1">🔴 Monitoreo Activo</p>
                    <p className="text-xs text-green-600">
                      Sensor: {selectedSensor.name} ({selectedSensor.mac})
                    </p>
                    <p className="text-xs text-green-600">
                      {spectrumData.length} puntos de frecuencia
                    </p>
                  </div>
                )}

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-2">
                    <p className="text-xs text-red-600">
                      Error: {error}
                    </p>
                  </div>
                )}
                {loading && isMonitoringActive && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-2">
                    <p className="text-xs text-blue-600">
                      Cargando datos...
                    </p>
                  </div>
                )}
              </div>

            <ConfigurationPanel 
              config={config} 
              onConfigChange={setConfig}
              onDemodTypeChange={setDemodType}
              onWaterfallResetRequested={() => setWaterfallResetToken(prev => prev + 1)}
              isMonitoring={isMonitoringActive}
              onCreateCampaign={handleCreateCampaign}
              onMonitoringChange={(isActive, sensorMac) => {
                setIsMonitoringActive(isActive);
                if (isActive && sensorMac) {
                  // Reiniciar waterfall con ventana de gracia al iniciar adquisicion.
                  setWaterfallResetToken(prev => prev + 1);
                  const sensor = sensors.find(s => s.mac === sensorMac);
                  setSelectedSensor(sensor || null);
                  // Si es preset AM/FM y hay demodType configurado, iniciar audio WebRTC
                  if (config.preset === 'amfm' && demodType) {
                    setTimeout(() => {
                      analysisPanelRef.current?.startAudio();
                    }, 1000); // Esperar 1 segundo para que el sensor esté listo
                  }
                } else {
                  // Al detener, también detener el audio
                  analysisPanelRef.current?.stopAudio();
                }
              }}
              maxMonitoringTime={maxMonitoringTime}
              sensors={sensors} // Pasar lista de sensores actualizada
            />
          </div>

          {/* Botón para ocultar/mostrar panel de configuración */}
          {isMonitoringActive && (
            <button
              onClick={() => setHideConfigPanel(!hideConfigPanel)}
              className={`absolute top-1/2 -translate-y-1/2 z-50 bg-orange-500 hover:bg-orange-600 text-white p-3 shadow-lg transition-all rounded-lg ${
                hideConfigPanel
                  ? 'left-2'
                  : 'left-[450px]'
              }`}
              title={hideConfigPanel ? 'Mostrar configuración' : 'Ocultar configuración'}
            >
              {hideConfigPanel ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
            </button>
          )}

          <AnalysisPanel 
            ref={analysisPanelRef}
            data={spectrumData} 
            history={waterfallHistory}
            sensorName={selectedSensor?.name}
            sensorMac={selectedSensor?.mac}
            isRealtime={isMonitoringActive}
            vbw={config.vbw}
            rbw={config.rbw}
            antennaGain={config.antennaGain}
            sensorGps={selectedSensor ? {
              lat: selectedSensor.lat || 0,
              lng: selectedSensor.lng || 0,
              alt: selectedSensor.alt
            } : undefined}
            demodType={config.preset === 'amfm' ? demodType : ''}
            demodMetrics={config.preset === 'amfm' ? demodMetrics : undefined}
          />
        </div>
      )}

      {/* Modal para agregar sensor */}
      {showSensorModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[2000]">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">Nuevo Sensor</h3>
              <button
                onClick={() => {
                  setShowSensorModal(false);
                  setValidationErrors({});
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmitSensor} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nombre del sensor *
                </label>
                <input
                  type="text"
                  required
                  value={sensorFormData.name}
                  onChange={(e) => {
                    setSensorFormData({ ...sensorFormData, name: e.target.value });
                    if (validationErrors.name) {
                      setValidationErrors({ ...validationErrors, name: '' });
                    }
                  }}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    validationErrors.name ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Ej: Sensor Medellín Centro"
                />
                {validationErrors.name && (
                  <p className="text-red-500 text-xs mt-1">{validationErrors.name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección MAC *
                </label>
                <input
                  type="text"
                  required
                  value={sensorFormData.mac}
                  onChange={(e) => {
                    setSensorFormData({ ...sensorFormData, mac: e.target.value });
                    if (validationErrors.mac) {
                      setValidationErrors({ ...validationErrors, mac: '' });
                    }
                  }}
                  className={`w-full px-3 py-2 border rounded-lg font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    validationErrors.mac ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="AA:BB:CC:DD:EE:FF"
                  pattern="[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}"
                />
                {validationErrors.mac && (
                  <p className="text-red-500 text-xs mt-1">{validationErrors.mac}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Descripción
                </label>
                <textarea
                  value={sensorFormData.description}
                  onChange={(e) => setSensorFormData({ ...sensorFormData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={2}
                  placeholder="Descripción del sensor..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Estado Administrativo *
                </label>
                <select
                  value={sensorFormData.status_admin || 'active'}
                  onChange={(e) => setSensorFormData({ ...sensorFormData, status_admin: e.target.value as 'active' | 'inactive' })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="active">Activo</option>
                  <option value="inactive">Inactivo</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  {sensorFormData.status_admin === 'inactive' 
                    ? 'El sensor estará oculto en el sistema excepto en configuración.' 
                    : 'El sensor estará visible y operativo.'}
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowSensorModal(false);
                    setValidationErrors({});
                    setIsEditingSensor(false);
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  {isEditingSensor ? 'Guardar Cambios' : 'Crear Sensor'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  return <AppContent />;
}

export default App;
