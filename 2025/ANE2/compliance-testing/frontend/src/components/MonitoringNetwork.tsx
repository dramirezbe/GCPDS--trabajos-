import { useEffect, useState } from 'react';
import { MapPin, Radio, X, Cpu, HardDrive, Thermometer, Activity, Antenna as AntennaIcon } from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { sensorAPI, antennaAPI, sensorDataAPI, Sensor, Antenna } from '../services/api';

// Fix para los iconos de Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

  // Crear iconos SVG personalizados
const createSensorIcon = (color: string, isActive: boolean, hasAlert: boolean = false) => {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
      <defs>
        <filter id="shadow-${color}" x="-50%" y="-50%" width="200%" height="200%">
          <feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.3"/>
        </filter>
      </defs>
      <!-- Base circular -->
      <circle cx="20" cy="20" r="18" fill="${color}" stroke="white" stroke-width="2.5" filter="url(#shadow-${color})">
        ${hasAlert ? '<animate attributeName="opacity" values="1;0.6;1" dur="1.5s" repeatCount="indefinite"/>' : ''}
      </circle>
      <!-- Ondas de señal -->
      <path d="M 20 8 L 20 15" stroke="white" stroke-width="2.5" stroke-linecap="round" opacity="${isActive ? '1' : '0.5'}"/>
      <path d="M 14 10 L 16 13" stroke="white" stroke-width="2" stroke-linecap="round" opacity="${isActive ? '0.8' : '0.4'}"/>
      <path d="M 26 10 L 24 13" stroke="white" stroke-width="2" stroke-linecap="round" opacity="${isActive ? '0.8' : '0.4'}"/>
      <!-- Antena central -->
      <circle cx="20" cy="20" r="3" fill="white" opacity="${isActive ? '1' : '0.7'}"/>
      <rect x="18.5" y="15" width="3" height="5" fill="white" rx="1" opacity="${isActive ? '1' : '0.7'}"/>
      <!-- Ondas inferiores -->
      <path d="M 12 25 Q 14 23, 16 24" stroke="white" stroke-width="1.5" fill="none" opacity="${isActive ? '0.7' : '0.4'}"/>
      <path d="M 28 25 Q 26 23, 24 24" stroke="white" stroke-width="1.5" fill="none" opacity="${isActive ? '0.7' : '0.4'}"/>
      ${hasAlert ? '<circle cx="20" cy="28" r="5" fill="white"/><text x="20" y="31" font-size="8" font-weight="bold" fill="#ef4444" text-anchor="middle">!</text>' : ''}
    </svg>
  `;
  
  return new L.Icon({
    iconUrl: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg),
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20],
  });
};

// Función helper para obtener estado legible y colores
const getSensorStatusInfo = (status?: string) => {
  switch (status) {
    case 'online':
    case 'active': // Legacy support
      return { label: 'Online', colorClass: 'bg-green-100 text-green-800', hexColor: '#10b981', isActive: true };
    case 'busy':
      return { label: 'Ocupado', colorClass: 'bg-orange-100 text-orange-800', hexColor: '#f59e0b', isActive: true };
    case 'delay':
      return { label: 'Delay', colorClass: 'bg-yellow-100 text-yellow-800', hexColor: '#eab308', isActive: false };
    case 'offline':
    case 'inactive': // Legacy support
      return { label: 'Offline', colorClass: 'bg-gray-100 text-gray-800', hexColor: '#9ca3af', isActive: false };
    case 'error':
      return { label: 'Error', colorClass: 'bg-red-100 text-red-800', hexColor: '#ef4444', isActive: false };
    default:
      return { label: 'Offline', colorClass: 'bg-gray-100 text-gray-800', hexColor: '#9ca3af', isActive: false };
  }
};

// Componente para centrar el mapa cuando se selecciona un sensor
function MapUpdater({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// Helper para normalizar números que pueden venir como strings desde PostgreSQL
const toNumber = (value: any): number | undefined => {
  if (value === null || value === undefined) return undefined;
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return isNaN(num) ? undefined : num;
};

// Helper para normalizar datos de sensores
const normalizeSensor = (sensor: any): Sensor => ({
  ...sensor,
  id: toNumber(sensor.id),
  lat: toNumber(sensor.lat),
  lng: toNumber(sensor.lng),
  alt: toNumber(sensor.alt),
  created_at: toNumber(sensor.created_at),
  updated_at: toNumber(sensor.updated_at),
});

// Helper para formatear fecha en UTC-5
const formatDateUTC5 = (timestampMs: number | undefined | null): string => {
  if (!timestampMs) return '';
  const date = new Date(Number(timestampMs));
  // El sensor ya envía la hora local (UTC-5) en el timestamp, por lo que no debemos restar 5 horas.
  // Usamos toISOString para obtener la fecha "cruda" tal cual viene en el timestamp.
  return date.toISOString().replace('T', ' ').substring(0, 19);
};

export function MonitoringNetwork() {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null);
  const [sensorStatus, setSensorStatus] = useState<any>(null);
  const [realtimeSensorStatus, setRealtimeSensorStatus] = useState<any>(null);
  const [sensorAntennas, setSensorAntennas] = useState<any[]>([]);
  const [showAntennaAssignForm, setShowAntennaAssignForm] = useState(false);
  const [antennaAssignData, setAntennaAssignData] = useState({
    antenna_id: 0,
    port: 1
  });
  const [availableAntennas, setAvailableAntennas] = useState<Antenna[]>([]); // Para el formulario de asignación
  const [mapCenter, setMapCenter] = useState<[number, number]>([4.7110, -74.0721]); // Centro de Colombia
  const [mapZoom, setMapZoom] = useState(6);

  useEffect(() => {
    loadSensors();
    
    // Polling para actualizar el estado de los sensores desde el backend cada 30 segundos
    const pollingInterval = setInterval(() => {
      loadSensors();
    }, 30000);

    return () => clearInterval(pollingInterval);
  }, []);

  // Cargar status y antenas cuando se selecciona un sensor
  useEffect(() => {
    if (selectedSensor) {
      loadSensorStatus();
      loadSensorAntennas();
    }
  }, [selectedSensor]);

  // WebSocket para datos en tiempo real del sensor seleccionado
  useEffect(() => {
    if (!selectedSensor) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsPort = window.location.protocol === 'https:' ? ':12443' : ':3000';
    const wsUrl = `${wsProtocol}//${window.location.hostname}${wsPort}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('📊 WebSocket conectado para dispositivos');
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        // Actualizar estado del sensor en tiempo real
        if (message.type === 'sensor_status' && message.data) {
          const statusData = message.data;
          
          // Actualizar el sensor en la lista a 'online' ya que acaba de enviar datos
          setSensors(prev => prev.map(s => 
            s.mac === statusData.mac ? { ...s, status: 'online', updated_at: Date.now() } : s
          ));
          
          // Si es el sensor seleccionado, actualizar su status detallado
          if (statusData.mac === selectedSensor.mac) {
            setRealtimeSensorStatus(statusData);
            setSelectedSensor(prev => prev ? { ...prev, status: 'online', updated_at: Date.now() } : null);
            console.log('📊 Estado del sensor actualizado:', statusData);
          }
        }

        // Actualizar GPS del sensor en tiempo real
        if (message.type === 'sensor_gps' && message.data) {
          if (message.data.mac === selectedSensor.mac) {
            setSelectedSensor(prev => prev ? {
              ...prev,
              lat: message.data.lat,
              lng: message.data.lng,
              alt: message.data.alt
            } : null);
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
  }, [selectedSensor]);

  const loadSensors = async () => {
    try {
      const data = await sensorAPI.getAll();
      // Filtrar sensores administrativamente inactivos
      const activeSensors = data.filter(s => s.status_admin !== 'inactive');
      
      // Normalizar los datos para asegurar que lat/lng sean números
      const normalizedData = activeSensors.map(normalizeSensor);
      setSensors(normalizedData);
    } catch (error) {
      console.error('Error loading sensors:', error);
    }
  };

  const loadAvailableAntennas = async () => {
    try {
      const data = await antennaAPI.getAll();
      setAvailableAntennas(data);
    } catch (error) {
      console.error('Error loading available antennas:', error);
    }
  };

  const loadSensorStatus = async () => {
    if (!selectedSensor) return;
    try {
      const status = await sensorDataAPI.getLatestStatus(selectedSensor.mac);
      setSensorStatus(status);
    } catch (error) {
      console.error('Error loading sensor status:', error);
      setSensorStatus(null);
    }
  };

  const loadSensorAntennas = async () => {
    if (!selectedSensor || !selectedSensor.id) return;
    try {
      const data = await sensorAPI.getAntennas(selectedSensor.id);
      setSensorAntennas(data);
    } catch (error) {
      console.error('Error loading sensor antennas:', error);
      setSensorAntennas([]);
    }
  };

  const handleAssignAntenna = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSensor || !selectedSensor.id) return;
    
    // Validar que el sensor no tenga ya 4 antenas asignadas
    if (sensorAntennas.length >= 4) {
      alert('Este sensor ya tiene el máximo de 4 antenas asignadas.');
      return;
    }
    
    // Validar que el puerto no esté ocupado
    const portOccupied = sensorAntennas.some((ant: any) => ant.port === antennaAssignData.port);
    if (portOccupied) {
      alert(`El puerto ${antennaAssignData.port} ya está ocupado. Por favor, seleccione otro puerto.`);
      return;
    }
    
    try {
      await sensorAPI.assignAntenna(selectedSensor.id, antennaAssignData.antenna_id, antennaAssignData.port);
      setShowAntennaAssignForm(false);
      setAntennaAssignData({ antenna_id: 0, port: 1 });
      loadSensorAntennas();
      alert('Antena asignada exitosamente');
    } catch (error) {
      console.error('Error assigning antenna:', error);
      alert('Error al asignar antena.');
    }
  };

  const handleUnassignAntenna = async (antennaId: number, antennaName: string) => {
    if (!selectedSensor || !selectedSensor.id) return;
    if (!confirm(`¿Está seguro de desasignar la antena "${antennaName}" de este sensor?`)) return;
    try {
      await sensorAPI.unassignAntenna(selectedSensor.id, antennaId);
      loadSensorAntennas();
      alert('Antena desasignada exitosamente');
    } catch (error) {
      console.error('Error unassigning antenna:', error);
      alert('Error al desasignar antena.');
    }
  };

  const handleSensorClick = (sensor: Sensor) => {
    // Normalizar el sensor antes de seleccionarlo
    const normalizedSensor = normalizeSensor(sensor);
    setSelectedSensor(normalizedSensor);
    if (normalizedSensor.lat && normalizedSensor.lng) {
      setMapCenter([normalizedSensor.lat, normalizedSensor.lng]);
      setMapZoom(13);
    }
  };

  return (
    <div className="flex h-screen w-full">
      {/* Panel izquierdo - Lista de sensores */}
      <div className="w-96 border-r border-gray-200 overflow-y-auto bg-white">
        <div className="p-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Sensores</h2>
          </div>
        </div>

        <div className="divide-y divide-gray-200">
          {sensors.map((sensor) => (
            <div
              key={sensor.id}
              onClick={() => handleSensorClick(sensor)}
              className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                selectedSensor?.id === sensor.id ? 'bg-orange-50 border-l-4 border-orange-500' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Radio className="w-4 h-4 text-orange-600" />
                    <h3 className="font-semibold text-gray-800">{sensor.name}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{sensor.description}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-600">
                    <MapPin className="w-3 h-3" />
                    <span>
                      {sensor.lat?.toFixed(4)}, {sensor.lng?.toFixed(4)}
                    </span>
                  </div>
                  <div className="mt-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        getSensorStatusInfo(sensor.status).colorClass
                      }`}
                    >
                      {getSensorStatusInfo(sensor.status).label}
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                MAC: {sensor.mac}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Panel derecho - Mapa */}
      <div className="flex-1 relative bg-gray-100">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '100%', width: '100%' }}
          className="z-0"
        >
          <MapUpdater center={mapCenter} zoom={mapZoom} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {/* Marcadores de sensores */}
          {sensors.map((sensor) => {
            if (!sensor.lat || !sensor.lng) return null;
            
            // Seleccionar color e icono según el estado
            const hasAlert = false; // Cambiar a true cuando se implemente sistema de alertas
            const statusInfo = getSensorStatusInfo(sensor.status);
            
            return (
              <Marker
                key={sensor.id}
                position={[sensor.lat, sensor.lng]}
                icon={createSensorIcon(statusInfo.hexColor, statusInfo.isActive, hasAlert)}
                eventHandlers={{
                  click: () => handleSensorClick(sensor)
                }}
              >
                <Popup>
                  <div className="p-2">
                    <h3 className="font-semibold text-gray-800 mb-1">{sensor.name}</h3>
                    <p className="text-xs text-gray-600 mb-2">{sensor.description}</p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between gap-4">
                        <span className="text-gray-500">MAC:</span>
                        <span className="font-mono">{sensor.mac}</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-gray-500">Estado:</span>
                        <span className={`font-medium ${statusInfo.label === 'Online' ? 'text-green-600' : statusInfo.label === 'Ocupado' ? 'text-orange-600' : 'text-gray-500'}`}>
                          {statusInfo.label}
                        </span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Info del sensor seleccionado */}
        {selectedSensor && (
          <div className="absolute bottom-4 left-4 right-4 max-w-4xl z-[1000] max-h-[calc(100vh-120px)] overflow-y-auto">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Tarjeta 1: Información Básica */}
              <div className="bg-white rounded-lg shadow-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-800">{selectedSensor.name}</h3>
                    <p className="text-sm text-gray-500">{selectedSensor.description}</p>
                  </div>
                  <button
                    onClick={() => setSelectedSensor(null)}
                    className="text-gray-400 hover:text-gray-600 ml-2"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">MAC:</span>
                    <span className="font-mono text-gray-800">{selectedSensor.mac}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Ubicación:</span>
                    <span className="text-gray-800">
                      {selectedSensor.lat?.toFixed(4)}, {selectedSensor.lng?.toFixed(4)}
                    </span>
                  </div>
                  {selectedSensor.alt !== undefined && selectedSensor.alt !== null && (
                    <div className="flex justify-between">
                      <span className="text-gray-600">Altitud:</span>
                      <span className="text-gray-800">{selectedSensor.alt.toFixed(1)} m</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-600">Estado:</span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        getSensorStatusInfo(selectedSensor.status).colorClass
                      }`}
                    >
                      {getSensorStatusInfo(selectedSensor.status).label}
                    </span>
                  </div>
                </div>

                {/* Antenas Asignadas */}
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
                      <AntennaIcon className="w-4 h-4" />
                      Antenas ({sensorAntennas.length}/4)
                    </h4>
                    <button
                      onClick={() => {
                        loadAvailableAntennas();
                        setShowAntennaAssignForm(true);
                      }}
                      disabled={sensorAntennas.length >= 4}
                      className={`text-xs font-medium ${
                        sensorAntennas.length >= 4
                          ? 'text-gray-400 cursor-not-allowed'
                          : 'text-blue-600 hover:text-blue-800'
                      }`}
                      title={sensorAntennas.length >= 4 ? 'Máximo de 4 antenas alcanzado' : 'Asignar nueva antena'}
                    >
                      + Asignar
                    </button>
                  </div>
                  {sensorAntennas.length > 0 ? (
                    <div className="space-y-2">
                      {sensorAntennas.map((ant: any) => (
                        <div key={ant.id} className="bg-gray-50 rounded p-2 text-xs">
                          <div className="flex justify-between items-start gap-2">
                            <div className="flex-1">
                              <div className="font-medium text-gray-800">{ant.name}</div>
                              <div className="text-gray-600">{ant.type}</div>
                              <div className="text-gray-500">
                                {((ant.frequency_min_hz || 0) / 1e6).toFixed(0)} - {((ant.frequency_max_hz || 0) / 1e6).toFixed(0)} MHz
                              </div>
                            </div>
                            <div className="text-right flex-shrink-0">
                              <div className="text-gray-800 font-medium">Puerto {ant.port}</div>
                              <div className="text-blue-600 font-medium">{ant.gain_db} dB</div>
                            </div>
                            <button
                              onClick={() => handleUnassignAntenna(ant.id, ant.name)}
                              className="text-red-600 hover:text-red-800 p-1 rounded hover:bg-red-50 transition-colors flex-shrink-0"
                              title="Desasignar antena"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500 italic">No hay antenas asignadas</p>
                  )}
                </div>
              </div>

              {/* Tarjeta 2: Status del Sensor */}
              <div className="bg-white rounded-lg shadow-lg p-4">
                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Estado del Sensor
                  {realtimeSensorStatus && (
                    <span className="text-xs text-green-600 font-normal">(En tiempo real)</span>
                  )}
                </h4>
                {(() => {
                  // Priorizar datos en tiempo real sobre datos de DB
                  const displayStatus = realtimeSensorStatus || sensorStatus;
                  return displayStatus ? (
                  <div className="space-y-3 text-sm">
                    {/* CPU */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-gray-600 flex items-center gap-1">
                          <Cpu className="w-3 h-3" />
                          CPU
                        </span>
                      </div>
                      {displayStatus.metrics?.cpu && displayStatus.metrics.cpu.map((cpu: number, idx: number) => (
                        <div key={idx} className="flex justify-between text-xs mb-1">
                          <span className="text-gray-500">Core {idx}:</span>
                          <span className={`font-medium ${Number(cpu) > 80 ? 'text-red-600' : Number(cpu) > 20 ? 'text-yellow-600' : 'text-green-600'}`}>
                            {Number(cpu).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* RAM */}
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 flex items-center gap-1">
                          <HardDrive className="w-3 h-3" />
                          RAM
                        </span>
                        <span className="text-gray-800 font-medium text-xs">
                          {Number(displayStatus.metrics?.ram_mb || 0).toFixed(0)} / {Number(displayStatus.total_metrics?.ram_mb || 0).toFixed(0)} MB
                          <span className={`ml-2 ${((Number(displayStatus.metrics?.ram_mb) / Number(displayStatus.total_metrics?.ram_mb)) * 100) > 80 ? 'text-red-600' : ((Number(displayStatus.metrics?.ram_mb) / Number(displayStatus.total_metrics?.ram_mb)) * 100) > 20 ? 'text-yellow-600' : 'text-green-600'}`}>
                            ({(((Number(displayStatus.metrics?.ram_mb) || 0) / (Number(displayStatus.total_metrics?.ram_mb) || 1)) * 100).toFixed(1)}%)
                          </span>
                        </span>
                      </div>
                    </div>

                    {/* Swap */}
                    {displayStatus.metrics?.swap_mb !== undefined && displayStatus.total_metrics?.swap_mb !== undefined && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 text-xs">Swap:</span>
                          <span className="text-gray-800 font-medium text-xs">
                            {Number(displayStatus.metrics?.swap_mb || 0)} / {Number(displayStatus.total_metrics?.swap_mb || 0)} MB
                            <span className={`ml-2 ${((Number(displayStatus.metrics?.swap_mb) / Number(displayStatus.total_metrics?.swap_mb)) * 100) > 80 ? 'text-red-600' : ((Number(displayStatus.metrics?.swap_mb) / Number(displayStatus.total_metrics?.swap_mb)) * 100) > 20 ? 'text-yellow-600' : 'text-green-600'}`}>
                              ({(((Number(displayStatus.metrics?.swap_mb) || 0) / (Number(displayStatus.total_metrics?.swap_mb) || 1)) * 100).toFixed(1)}%)
                            </span>
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Disco */}
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600 flex items-center gap-1">
                          <HardDrive className="w-3 h-3" />
                          Disco
                        </span>
                        <span className="text-gray-800 font-medium text-xs">
                          {(Number(displayStatus.metrics?.disk_mb || 0) / 1024).toFixed(1)} / {(Number(displayStatus.total_metrics?.disk_mb || 0) / 1024).toFixed(1)} GB
                          <span className={`ml-2 ${((Number(displayStatus.metrics?.disk_mb) / Number(displayStatus.total_metrics?.disk_mb)) * 100) > 85 ? 'text-red-600' : ((Number(displayStatus.metrics?.disk_mb) / Number(displayStatus.total_metrics?.disk_mb)) * 100) > 40 ? 'text-yellow-600' : 'text-green-600'}`}>
                            ({(((Number(displayStatus.metrics?.disk_mb) || 0) / (Number(displayStatus.total_metrics?.disk_mb) || 1)) * 100).toFixed(1)}%)
                          </span>
                        </span>
                      </div>
                    </div>

                    {/* Temperatura */}
                    {displayStatus.metrics?.temp_c !== undefined && displayStatus.metrics?.temp_c !== null && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 flex items-center gap-1">
                            <Thermometer className="w-3 h-3" />
                            Temperatura
                          </span>
                          <span className={`font-medium text-xs ${Number(displayStatus.metrics.temp_c) > 70 ? 'text-red-600' : Number(displayStatus.metrics.temp_c) > 50 ? 'text-yellow-600' : 'text-green-600'}`}>
                            {Number(displayStatus.metrics.temp_c).toFixed(1)}°C
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Ping */}
                    {displayStatus.ping_ms !== undefined && displayStatus.ping_ms !== null && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 text-xs">Ping:</span>
                          <span className={`font-medium text-xs ${Number(displayStatus.ping_ms) > 250 ? 'text-red-600' : Number(displayStatus.ping_ms) > 50 ? 'text-yellow-600' : 'text-green-600'}`}>
                            {Number(displayStatus.ping_ms).toFixed(1)} ms
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Tiempo de Transacción */}
                    {displayStatus.delta_t_ms !== undefined && displayStatus.delta_t_ms !== null && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 text-xs">Tiempo de Transacción:</span>
                          <span className="text-gray-800 font-medium text-xs">
                            {Number(displayStatus.delta_t_ms).toFixed(0)} ms
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Última sincronización de reloj (NTP) */}
                    {displayStatus.last_ntp_ms !== undefined && displayStatus.last_ntp_ms !== null && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 text-xs">Última sincronización de reloj:</span>
                          <span className="text-gray-800 font-medium text-xs">
                            {formatDateUTC5(displayStatus.last_ntp_ms)} UTC-5
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Última calibración en frecuencia (Kalman) */}
                    {displayStatus.last_kal_ms !== undefined && displayStatus.last_kal_ms !== null && (
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-gray-600 text-xs">Última calibración en frecuencia:</span>
                          <span className="text-gray-800 font-medium text-xs">
                            {formatDateUTC5(displayStatus.last_kal_ms)} UTC-5
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Última actualización */}
                    {displayStatus.timestamp_ms && (
                      <div className="pt-2 border-t border-gray-200">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-500">Última actualización:</span>
                          <span className="text-gray-700 font-medium">
                            {formatDateUTC5(displayStatus.timestamp_ms)} UTC-5
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Logs */}
                    {displayStatus.logs && (
                      <div className="pt-2 border-t border-gray-200">
                        <div className="text-xs mb-1">
                          <span className="text-gray-600 font-medium">Logs recientes:</span>
                        </div>
                        <div className="bg-gray-900 text-gray-100 rounded p-2 max-h-32 overflow-y-auto font-mono text-xs">
                          {displayStatus.logs.split('\n').map((line: string, idx: number) => {
                            // Detectar tipo de log (WARNING o ERROR)
                            const isError = line.includes('ERROR');
                            const isWarning = line.includes('WARNING');
                            return (
                              <div 
                                key={idx} 
                                className={`py-0.5 ${isError ? 'text-red-400' : isWarning ? 'text-yellow-400' : 'text-gray-300'}`}
                              >
                                {line}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-gray-500 italic">No hay información de status disponible</p>
                  </div>
                );
                })()}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal para asignar antena a sensor */}
      {showAntennaAssignForm && selectedSensor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[2000]">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-800">Asignar Antena</h3>
              <button
                onClick={() => setShowAntennaAssignForm(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleAssignAntenna} className="p-4 space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">
                  <span className="font-semibold">Sensor:</span> {selectedSensor.name}
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  {selectedSensor.mac}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Antena *
                </label>
                <select
                  required
                  value={antennaAssignData.antenna_id}
                  onChange={(e) => setAntennaAssignData({ ...antennaAssignData, antenna_id: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  <option value={0}>Seleccione una antena...</option>
                  {availableAntennas.map((antenna) => (
                    <option key={antenna.id} value={antenna.id}>
                      {antenna.name} ({antenna.type}) - {antenna.gain_db} dB
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Si no encuentra la antena,{' '}
                  <span className="text-blue-600 font-medium">
                    regístrela en la sección de Configuración
                  </span>
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Puerto del sensor *
                </label>
                <select
                  required
                  value={antennaAssignData.port}
                  onChange={(e) => setAntennaAssignData({ ...antennaAssignData, port: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                >
                  {[1, 2, 3, 4].map(port => {
                    const occupied = sensorAntennas.some((ant: any) => ant.port === port);
                    return (
                      <option key={port} value={port} disabled={occupied}>
                        Puerto {port}{occupied ? ' (Ocupado)' : ''}
                      </option>
                    );
                  })}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Cada puerto solo puede tener una antena asignada. Puertos ocupados están deshabilitados.
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAntennaAssignForm(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
                >
                  Asignar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
