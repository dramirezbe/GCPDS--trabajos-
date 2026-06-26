import { useState, useEffect } from 'react';
import { sensorAPI, sensorDataAPI, alertsAPI } from '../services/api';
import { AlertTriangle, CheckCircle, Server, Activity, ArrowRight, XCircle, Clock } from 'lucide-react';
import axios from 'axios';
import { analizarEmisiones } from './ComplianceReport';
import { ComplianceReport } from './ComplianceReport';

import { MapContainer, TileLayer } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface Campaign {
  id: number;
  name: string;
  status: 'scheduled' | 'running' | 'completed' | 'cancelled';
  start_date: string;
  end_date: string;
}

export function AlertsPanel() {
  const [loading, setLoading] = useState(true);
  const [allSensors, setAllSensors] = useState<any[]>([]);
  
  // Estados para Sensores
  const [alertSensors, setAlertSensors] = useState<any[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<any>(null);
  const [sensorDateFilter, setSensorDateFilter] = useState<'today' | 'all' | 'custom'>('today');
  const [sensorCustomDate, setSensorCustomDate] = useState<string>('');
  const [currentPageSensors, setCurrentPageSensors] = useState(1);

  // Estados para Campañas
  const [alertCampaigns, setAlertCampaigns] = useState<any[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [campaignDateFilter, setCampaignDateFilter] = useState<'today' | 'all' | 'custom'>('today');
  const [campaignCustomDate, setCampaignCustomDate] = useState<string>('');
  const [currentPageCampaigns, setCurrentPageCampaigns] = useState(1);

  const itemsPerPage = 5;

  // Cargar lista de todos los sensores al inicio
  useEffect(() => {
    sensorAPI.getAll().then(setAllSensors).catch(console.error);
  }, []);

  // Cargar datos de sensores cuando cambian los filtros
  useEffect(() => {
    loadSensorAlerts();
  }, [sensorDateFilter, sensorCustomDate, allSensors]);

  // Cargar datos de campañas al inicio
  useEffect(() => {
    loadCampaignAlerts();
  }, []);

  const loadSensorAlerts = async () => {
    if (allSensors.length === 0) return; // Esperar a que carguen los sensores
    
    setLoading(true);
    try {
      if (sensorDateFilter === 'today') {
        // Lógica COMBINADA: Estado Actual + Historial del Día
        
        // 1. Obtener alertas históricas del día actual
        const todayStart = new Date();
        todayStart.setHours(0, 0, 0, 0);
        const todayEnd = new Date();
        todayEnd.setHours(23, 59, 59, 999);
        
        const { alerts: todayAlerts } = await alertsAPI.getHistory({
          start_date: todayStart.getTime(),
          end_date: todayEnd.getTime(),
          limit: 1000
        });

        // Agrupar alertas históricas por sensor
        const alertsBySensor: Record<string, any[]> = {};
        todayAlerts.forEach(alert => {
          if (!alertsBySensor[alert.sensor_mac]) alertsBySensor[alert.sensor_mac] = [];
          alertsBySensor[alert.sensor_mac].push(alert);
        });

        // 2. Evaluar estado actual de cada sensor
        const sensorPromises = allSensors.map(async (sensor) => {
          try {
            if (!sensor.mac) return null;
            
            let status = null;
            try {
              status = await sensorDataAPI.getLatestStatus(sensor.mac);
            } catch (statusError) {
              // Si falla el status, se trata más adelante
            }
            
            let hasIssue = false;
            const issues: string[] = [];
            const historyAlerts = alertsBySensor[sensor.mac] || [];

            // Agregar alertas del historial del día
            if (historyAlerts.length > 0) {
              hasIssue = true;
              const lastAlert = historyAlerts[0];
              issues.push(`${historyAlerts.length} alertas hoy (Última: ${lastAlert.alert_type})`);
            }

            // 1. Validar estado de conexión ACTUAL
            if (sensor.status === 'error') {
               hasIssue = true;
               issues.push('Error Crítico');
            } else if (sensor.status === 'offline' || sensor.status === 'inactive') {
               hasIssue = true;
               issues.push('Offline');
            } else if (!status) {
               hasIssue = true;
               issues.push('Sin respuesta');
            }

            // 2. Validar métricas ACTUALES
            if (status) {
               if (status.logs && status.logs.includes('ERROR')) {
                 hasIssue = true;
                 issues.push('Error en Logs');
               }

               if (status.metrics?.cpu && Array.isArray(status.metrics.cpu)) {
                 // Usar MAX de núcleos activos (>0), no promedio de los 4 slots incluyendo
                 // los que se rellenaron con 0 para sensores de 1 o 2 núcleos.
                 // Así coincide con el umbral rojo de la tarjeta Estado del Sensor.
                 const activeCores = status.metrics.cpu.map((c: number) => Number(c)).filter((c: number) => c > 0);
                 if (activeCores.length > 0) {
                   const maxCpu = Math.max(...activeCores);
                   if (maxCpu > 80) {
                     hasIssue = true;
                     issues.push(`CPU Alta (${maxCpu.toFixed(1)}%)`);
                   }
                 }
               }

               if (Number(status.total_metrics?.ram_mb) > 0) {
                 const ramUsage = (Number(status.metrics.ram_mb) / Number(status.total_metrics.ram_mb)) * 100;
                 if (ramUsage > 80) {
                   hasIssue = true;
                   issues.push(`RAM Alta (${ramUsage.toFixed(1)}%)`);
                 }
               }

               if (Number(status.total_metrics?.disk_mb) > 0) {
                 const diskUsage = (Number(status.metrics.disk_mb) / Number(status.total_metrics.disk_mb)) * 100;
                 if (diskUsage > 85) {
                   hasIssue = true;
                   issues.push(`Disco Alto (${diskUsage.toFixed(1)}%)`);
                 }
               }

               // Validar temperatura (ignorar valores 0 o negativos que son claramente inválidos)
               if (status.metrics?.temp_c && Number(status.metrics.temp_c) > 0) {
                 const temp = Number(status.metrics.temp_c);
                 console.log(`🌡️ Sensor ${sensor.name} (${sensor.mac}) - Temperatura: ${temp.toFixed(1)}°C`);
                 if (temp > 70) {
                   hasIssue = true;
                   issues.push(`Temperatura Alta (${temp.toFixed(1)}°C)`);
                   console.warn(`⚠️ ALERTA: Sensor ${sensor.name} con temperatura alta: ${temp.toFixed(1)}°C`);
                 }
               }

               // Validar Swap
               if (Number(status.total_metrics?.swap_mb) > 0) {
                 const swapUsage = (Number(status.metrics.swap_mb) / Number(status.total_metrics.swap_mb)) * 100;
                 if (swapUsage > 80) {
                   hasIssue = true;
                   issues.push(`Swap Alto (${swapUsage.toFixed(1)}%)`);
                 }
               }

               if (status.ping_ms) {
                 const ping = Number(status.ping_ms);
                 if (ping > 250) {
                   hasIssue = true;
                   issues.push(`Latencia Alta (${ping.toFixed(0)}ms)`);
                 }
               }
            }

            if (hasIssue) {
              return { 
                ...sensor, 
                statusData: status, 
                issueType: issues.join(', '), 
                isHistory: historyAlerts.length > 0,
                historyAlerts: historyAlerts,
                timestamp: sensor.updated_at ? Number(sensor.updated_at) : Date.now()
              };
            }
          } catch (e) {
            return { 
                ...sensor, 
                statusData: null, 
                issueType: 'Error de conexión', 
                isHistory: false,
                historyAlerts: [],
                timestamp: Date.now()
            };
          }
          return null;
        });

        const sensorResults = await Promise.all(sensorPromises);
        setAlertSensors(sensorResults.filter(s => s !== null));

      } else {
        // Lógica de Historial
        let start, end;
        if (sensorDateFilter === 'custom' && sensorCustomDate) {
            // Usar fecha local para inicio y fin del día
            
            // Asegurar que tomamos desde el inicio del día local hasta el final
            // Sin embargo, new Date(string) asume UTC si es ISO, o local si es YYYY-MM-DD.
            // input type="date" devuelve YYYY-MM-DD.
            // new Date('2023-01-01') es UTC. new Date('2023-01-01T00:00') es local.
            // Mejor construir manualmente.
            const [year, month, day] = sensorCustomDate.split('-').map(Number);
            start = new Date(year, month - 1, day, 0, 0, 0).getTime();
            end = new Date(year, month - 1, day, 23, 59, 59, 999).getTime();
        } else {
            // 'all' -> Últimos 30 días por defecto para no saturar
            end = Date.now();
            start = end - (30 * 24 * 60 * 60 * 1000); 
        }

        const { alerts } = await alertsAPI.getHistory({
            start_date: start,
            end_date: end,
            limit: 1000
        });

        // Agrupar alertas por sensor
        const grouped: Record<string, any[]> = {};
        alerts.forEach(alert => {
            if (!grouped[alert.sensor_mac]) grouped[alert.sensor_mac] = [];
            grouped[alert.sensor_mac].push(alert);
        });

        const mappedSensors = Object.keys(grouped).map(mac => {
            const sensorInfo = allSensors.find(s => s.mac === mac) || { mac, name: 'Sensor Desconocido' };
            // Determinar el tipo de problema más común o reciente
            const lastAlert = grouped[mac][0]; // Asumiendo que vienen ordenados por fecha desc
            return {
                ...sensorInfo,
                isHistory: true,
                historyAlerts: grouped[mac],
                issueType: `${grouped[mac].length} Alertas (Última: ${lastAlert.alert_type})`,
                timestamp: Number(lastAlert.timestamp)
            };
        });

        setAlertSensors(mappedSensors);
      }
    } catch (error) {
      console.error("Error loading sensor alerts", error);
    } finally {
      setLoading(false);
    }
  };

  const loadCampaignAlerts = async () => {
    try {
      const campaignsRes = await axios.get(`${API_BASE_URL}/campaigns`);
      const completedCampaigns = campaignsRes.data.filter((c: any) => c.status === 'completed');
      
      // Procesar campañas en serie (de a 1) para no saturar el backend/Python
      const campaignResults: any[] = [];
      for (const camp of completedCampaigns) {
        try {
          // Usar POST pero el backend devuelve cache si existe (umbral=5, sin sensor)
          const reportRes = await axios.post(`${API_BASE_URL}/reports/compliance/${camp.id}`, {}, {
            timeout: 120000 // 2 minutos max por campaña
          });
          const reportData = reportRes.data;
          
          if (reportData.mediciones) {
             const analisis = analizarEmisiones(reportData.mediciones);
             if (analisis.fueraParametros.length > 0 || analisis.sinLicencia.length > 0) {
                 campaignResults.push({ 
                   ...camp, 
                   report: reportData, 
                   analisis, 
                   issueCount: analisis.fueraParametros.length + analisis.sinLicencia.length,
                   issues: {
                     outOfRange: analisis.fueraParametros.length,
                     noLicense: analisis.sinLicencia.length
                   }
                 });
             }
          }
        } catch (e) {
          console.error(`Error loading report for campaign ${camp.id}`, e);
        }
      }

      setAlertCampaigns(campaignResults);
    } catch (error) {
      console.error("Error loading campaign alerts", error);
    }
  };

  const getFilteredCampaigns = () => {
    let filtered = [...alertCampaigns];
    
    if (campaignDateFilter === 'today') {
      const today = new Date().toISOString().split('T')[0];
      filtered = filtered.filter(camp => {
        const campDate = new Date(camp.start_date).toISOString().split('T')[0];
        return campDate === today;
      });
    } else if (campaignDateFilter === 'custom' && campaignCustomDate) {
      filtered = filtered.filter(camp => {
        const campDate = new Date(camp.start_date).toISOString().split('T')[0];
        return campDate === campaignCustomDate;
      });
    }
    
    return filtered;
  };

  const filteredCampaigns = getFilteredCampaigns();
  
  // Paginación
  const totalPagesSensors = Math.ceil(alertSensors.length / itemsPerPage);
  const paginatedSensors = alertSensors.slice(
    (currentPageSensors - 1) * itemsPerPage,
    currentPageSensors * itemsPerPage
  );

  const totalPagesCampaigns = Math.ceil(filteredCampaigns.length / itemsPerPage);
  const paginatedCampaigns = filteredCampaigns.slice(
    (currentPageCampaigns - 1) * itemsPerPage,
    currentPageCampaigns * itemsPerPage
  );

  return (
    <div className="flex-1 bg-gray-50 h-screen overflow-hidden flex flex-col relative">
      {/* Mapa de fondo */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <MapContainer
          center={[4.6097, -74.0817]}
          zoom={6}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          boxZoom={false}
          keyboard={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
        </MapContainer>
      </div>

      {/* Header */}
      <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200 px-8 py-6 relative z-10 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Panel de Alertas</h1>
          <p className="text-gray-600 mt-1">Monitoreo de anomalías en dispositivos y cumplimiento normativo</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 relative z-10">
        {loading && allSensors.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Columna Sensores */}
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <Server className="text-gray-700" size={24} />
                <h2 className="text-xl font-semibold text-gray-800">Alertas de Sensores</h2>
                <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded-full">
                  {alertSensors.length}
                </span>
              </div>

              {/* Filtros de Fecha para Sensores */}
              <div className="bg-white p-3 rounded-lg border border-gray-200 mb-4 flex flex-wrap gap-2 items-center">
                <span className="text-sm font-medium text-gray-700 mr-2">Filtrar:</span>
                
                <button
                  onClick={() => {
                    setSensorDateFilter('today');
                    setCurrentPageSensors(1);
                  }}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    sensorDateFilter === 'today' 
                      ? 'bg-red-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Hoy (Tiempo Real + Historial)
                </button>
                
                <button
                  onClick={() => {
                    setSensorDateFilter('all');
                    setCurrentPageSensors(1);
                  }}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    sensorDateFilter === 'all' 
                      ? 'bg-red-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Histórico (30 días)
                </button>
                
                <div className="flex items-center gap-2 ml-auto">
                  <input
                    type="date"
                    value={sensorCustomDate}
                    onChange={(e) => {
                      setSensorCustomDate(e.target.value);
                      setSensorDateFilter('custom');
                      setCurrentPageSensors(1);
                    }}
                    className={`px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-red-500 ${
                      sensorDateFilter === 'custom' ? 'border-red-500 bg-red-50' : 'border-gray-300'
                    }`}
                  />
                </div>
              </div>
              
              {alertSensors.length === 0 ? (
                <div className="bg-white p-6 rounded-lg border border-gray-200 text-center text-gray-500">
                  <CheckCircle className="mx-auto text-green-500 mb-2" size={32} />
                  <p className="font-medium">
                    {sensorDateFilter === 'today'
                        ? '✓ Todos los sensores operando correctamente'
                        : 'No se encontraron alertas en el período seleccionado'}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    {sensorDateFilter === 'today'
                        ? 'No hay problemas de conectividad, métricas críticas ni alertas históricas hoy'
                        : 'Intenta seleccionar otro rango de fechas'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4">
                    {paginatedSensors.map((sensor) => (
                      <div 
                        key={`${sensor.mac}-${sensor.isHistory ? 'hist' : 'real'}`}
                        onClick={() => setSelectedSensor(sensor)}
                        className="bg-white p-4 rounded-lg border-l-4 border-red-500 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-bold text-gray-800 group-hover:text-red-600 transition-colors">
                              {sensor.name}
                            </h3>
                            <p className="text-sm text-gray-500 mb-2">{sensor.description}</p>
                            <div className="flex items-center gap-2 text-xs flex-wrap">
                              <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded">
                                {sensor.issueType}
                              </span>
                              <span className="text-gray-400 font-mono">{sensor.mac}</span>
                              {sensor.timestamp && (
                                <span className="text-gray-500 flex items-center gap-1 ml-2">
                                    <Clock size={12} />
                                    {new Date(sensor.timestamp).toLocaleString('es-CO', { timeZone: 'UTC' })}
                                </span>
                              )}
                            </div>
                          </div>
                          <ArrowRight className="text-gray-300 group-hover:text-red-500" size={20} />
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Paginación Sensores */}
                  {totalPagesSensors > 1 && (
                    <div className="flex justify-center mt-4 gap-2">
                      <button 
                        onClick={() => setCurrentPageSensors(p => Math.max(1, p - 1))}
                        disabled={currentPageSensors === 1}
                        className="px-3 py-1 bg-white border rounded hover:bg-gray-100 disabled:opacity-50"
                      >
                        Anterior
                      </button>
                      <span className="px-3 py-1 text-sm text-gray-600 flex items-center">
                        {currentPageSensors} / {totalPagesSensors}
                      </span>
                      <button 
                        onClick={() => setCurrentPageSensors(p => Math.min(totalPagesSensors, p + 1))}
                        disabled={currentPageSensors === totalPagesSensors}
                        className="px-3 py-1 bg-white border rounded hover:bg-gray-100 disabled:opacity-50"
                      >
                        Siguiente
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Columna Campañas */}
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="text-gray-700" size={24} />
                  <h2 className="text-xl font-semibold text-gray-800">Campañas Fuera de Parámetros</h2>
                  <span className="bg-orange-100 text-orange-700 text-xs font-bold px-2 py-1 rounded-full">
                    {filteredCampaigns.length}
                  </span>
                </div>
              </div>

              {/* Filtros de Fecha Campañas */}
              <div className="bg-white p-3 rounded-lg border border-gray-200 mb-4 flex flex-wrap gap-2 items-center">
                <span className="text-sm font-medium text-gray-700 mr-2">Filtrar:</span>
                
                <button
                  onClick={() => {
                    setCampaignDateFilter('today');
                    setCurrentPageCampaigns(1);
                  }}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    campaignDateFilter === 'today' 
                      ? 'bg-orange-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Hoy
                </button>
                
                <button
                  onClick={() => {
                    setCampaignDateFilter('all');
                    setCurrentPageCampaigns(1);
                  }}
                  className={`px-3 py-1 text-sm rounded-full transition-colors ${
                    campaignDateFilter === 'all' 
                      ? 'bg-orange-500 text-white' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  Todas
                </button>
                
                <div className="flex items-center gap-2 ml-auto">
                  <input
                    type="date"
                    value={campaignCustomDate}
                    onChange={(e) => {
                      setCampaignCustomDate(e.target.value);
                      setCampaignDateFilter('custom');
                      setCurrentPageCampaigns(1);
                    }}
                    className={`px-2 py-1 text-sm border rounded focus:outline-none focus:ring-1 focus:ring-orange-500 ${
                      campaignDateFilter === 'custom' ? 'border-orange-500 bg-orange-50' : 'border-gray-300'
                    }`}
                  />
                </div>
              </div>

              {filteredCampaigns.length === 0 ? (
                <div className="bg-white p-6 rounded-lg border border-gray-200 text-center text-gray-500">
                  <CheckCircle className="mx-auto text-green-500 mb-2" size={32} />
                  <p>
                    {campaignDateFilter === 'today' 
                      ? 'No hay campañas fuera de parámetros hoy' 
                      : 'No hay campañas que coincidan con el filtro'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="grid gap-4">
                    {paginatedCampaigns.map((camp) => (
                      <div 
                        key={camp.id}
                        onClick={() => setSelectedCampaign(camp)}
                        className="bg-white p-4 rounded-lg border-l-4 border-orange-500 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h3 className="font-bold text-gray-800 group-hover:text-orange-600 transition-colors">
                              {camp.name}
                            </h3>
                            <p className="text-sm text-gray-500 mb-2">
                              {new Date(camp.start_date).toLocaleDateString()}
                            </p>
                            <div className="flex items-center gap-2 text-xs flex-wrap">
                              {camp.issues?.outOfRange > 0 && (
                                <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded flex items-center gap-1">
                                  <XCircle size={12} />
                                  {camp.issues.outOfRange} fuera de rango
                                </span>
                              )}
                              {camp.issues?.noLicense > 0 && (
                                <span className="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded flex items-center gap-1">
                                  <AlertTriangle size={12} />
                                  {camp.issues.noLicense} sin licencia
                                </span>
                              )}
                            </div>
                          </div>
                          <ArrowRight className="text-gray-300 group-hover:text-orange-500" size={20} />
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Paginación Campañas */}
                  {totalPagesCampaigns > 1 && (
                    <div className="flex justify-center mt-4 gap-2">
                      <button 
                        onClick={() => setCurrentPageCampaigns(p => Math.max(1, p - 1))}
                        disabled={currentPageCampaigns === 1}
                        className="px-3 py-1 bg-white border rounded hover:bg-gray-100 disabled:opacity-50"
                      >
                        Anterior
                      </button>
                      <span className="px-3 py-1 text-sm text-gray-600 flex items-center">
                        {currentPageCampaigns} / {totalPagesCampaigns}
                      </span>
                      <button 
                        onClick={() => setCurrentPageCampaigns(p => Math.min(totalPagesCampaigns, p + 1))}
                        disabled={currentPageCampaigns === totalPagesCampaigns}
                        className="px-3 py-1 bg-white border rounded hover:bg-gray-100 disabled:opacity-50"
                      >
                        Siguiente
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal Detalle Sensor */}
      {selectedSensor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center bg-red-50">
              <h3 className="text-xl font-bold text-red-800 flex items-center gap-2">
                <AlertTriangle />
                Detalle de Alerta: {selectedSensor.name}
              </h3>
              <button 
                onClick={() => setSelectedSensor(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                <XCircle size={24} />
              </button>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-500">Estado / Tipo</label>
                  <div className="mt-1 text-lg font-semibold text-gray-900">{selectedSensor.issueType}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-500">MAC Address</label>
                  <div className="mt-1 text-lg font-mono text-gray-900">{selectedSensor.mac}</div>
                </div>
              </div>

              {/* Mostrar historial de alertas si existe */}
              {selectedSensor.historyAlerts && selectedSensor.historyAlerts.length > 0 && (
                <div className="mt-4">
                    <h4 className="text-gray-700 font-semibold mb-3 uppercase text-sm tracking-wider flex items-center gap-2">
                      <Clock size={16} />
                      Historial de Alertas ({selectedSensor.historyAlerts.length})
                    </h4>
                    <div className="border rounded-lg overflow-hidden max-h-96 overflow-y-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50 sticky top-0">
                                <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha y Hora</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Descripción</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {selectedSensor.historyAlerts.map((alert: any) => (
                                    <tr key={alert.id} className="hover:bg-gray-50">
                                        <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                                            {new Date(Number(alert.timestamp)).toLocaleString('es-CO', { timeZone: 'UTC' })}
                                        </td>
                                        <td className="px-4 py-3 text-sm">
                                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                              alert.alert_type.includes('CPU') ? 'bg-orange-100 text-orange-800' :
                                              alert.alert_type.includes('RAM') ? 'bg-purple-100 text-purple-800' :
                                              alert.alert_type.includes('Disco') ? 'bg-yellow-100 text-yellow-800' :
                                              alert.alert_type.includes('Temperatura') ? 'bg-red-100 text-red-800' :
                                              alert.alert_type.includes('Swap') ? 'bg-indigo-100 text-indigo-800' :
                                              alert.alert_type.includes('Latencia') ? 'bg-blue-100 text-blue-800' :
                                              alert.alert_type.includes('Offline') ? 'bg-gray-200 text-gray-700' :
                                              alert.alert_type.includes('Error') || alert.alert_type.includes('Crítico') ? 'bg-red-100 text-red-800' :
                                              alert.alert_type.includes('Advertencia') ? 'bg-yellow-100 text-yellow-800' :
                                              'bg-gray-100 text-gray-800'
                                            }`}>
                                              {alert.alert_type}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-700">
                                            {alert.description}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
              )}

              {/* Mostrar logs en tiempo real si están disponibles y no hay historial (o como info adicional) */}
              {selectedSensor.statusData && selectedSensor.statusData.logs && (
                <div className="bg-gray-900 rounded-lg p-4 text-gray-300 font-mono text-sm overflow-x-auto max-h-80 overflow-y-auto">
                  <h4 className="text-gray-400 mb-2 uppercase text-xs tracking-wider">Logs del Sistema (Tiempo Real)</h4>
                  <div className="whitespace-pre-wrap">
                    {selectedSensor.statusData.logs.split('\n').map((line: string, i: number) => (
                      <div key={i} className={line.includes('ERROR') ? 'text-red-400 font-bold' : line.includes('WARN') ? 'text-yellow-400' : ''}>
                        {line}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Métricas actuales del sensor */}
              {selectedSensor.statusData && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t">
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase mb-1">CPU Promedio</div>
                    <div className="text-lg font-bold text-gray-900">
                      {selectedSensor.statusData.metrics?.cpu && Array.isArray(selectedSensor.statusData.metrics.cpu) 
                        ? (selectedSensor.statusData.metrics.cpu.reduce((a: number, b: number) => a + Number(b), 0) / selectedSensor.statusData.metrics.cpu.length).toFixed(1) 
                        : 'N/A'}%
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase mb-1">RAM</div>
                    <div className="text-lg font-bold text-gray-900">
                      {selectedSensor.statusData.metrics?.ram_mb && selectedSensor.statusData.total_metrics?.ram_mb
                        ? ((Number(selectedSensor.statusData.metrics.ram_mb) / Number(selectedSensor.statusData.total_metrics.ram_mb)) * 100).toFixed(1)
                        : 'N/A'}%
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase mb-1">Disco</div>
                    <div className="text-lg font-bold text-gray-900">
                      {selectedSensor.statusData.metrics?.disk_mb && selectedSensor.statusData.total_metrics?.disk_mb
                        ? ((Number(selectedSensor.statusData.metrics.disk_mb) / Number(selectedSensor.statusData.total_metrics.disk_mb)) * 100).toFixed(1)
                        : 'N/A'}%
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase mb-1">Temperatura</div>
                    <div className="text-lg font-bold text-gray-900">
                      {selectedSensor.statusData.metrics?.temp_c && Number(selectedSensor.statusData.metrics.temp_c) > 0
                        ? `${Number(selectedSensor.statusData.metrics.temp_c).toFixed(1)}°C`
                        : 'N/A'}
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end">
              <button
                onClick={() => setSelectedSensor(null)}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Reporte Campaña */}
      {selectedCampaign && (
        <ComplianceReport 
          campaignId={selectedCampaign.id}
          campaignName={selectedCampaign.name}
          onClose={() => setSelectedCampaign(null)}
        />
      )}
    </div>
  );
}
