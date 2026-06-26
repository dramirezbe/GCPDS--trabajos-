import { useState, useEffect } from 'react';
import { FileText, X, Download, CheckCircle, XCircle, MapPin, Activity, BarChart3, Zap, ChevronDown, ChevronUp, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import axios from 'axios';
import { configAPI } from '../services/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Función helper para mostrar fechas en hora de Colombia
// Los timestamps del sensor ya representan hora local Colombia (UTC-5) codificada como epoch UTC,
// por lo que NO se debe restar 5 horas adicionales. Se usan métodos UTC para leer directamente.
function toColombiaTime(timestamp: string | number | Date): string {
  const date = new Date(timestamp);
  if (isNaN(date.getTime())) return 'Fecha inválida';
  
  // El timestamp del sensor ya representa hora Colombia, usar UTC para leer directamente
  const day = String(date.getUTCDate()).padStart(2, '0');
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const year = date.getUTCFullYear();
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');
  
  return `${day}/${month}/${year}, ${hours}:${minutes}:${seconds}`;
}

interface ComplianceReportProps {
  campaignId: number;
  campaignName: string;
  sensors?: string[];
  allSensors?: { mac: string; name: string }[];
  initialSensor?: string;
  onClose: () => void;
  initialData?: ReportData | null;
  umbral?: number;
}

interface ReportData {
  reporte_automatico: boolean | string;
  plataforma?: string;
  fecha_generacion?: string;
  fecha_medicion: string;
  servicio_medido?: string;
  ocupacion_banda?: string;
  ubicacion: {
    estacion: string;
    sensor_mac?: string;
    departamento: string;
    municipio: string;
    codigo_dane: string;
    coordenadas: {
      latitud: number | string;
      longitud: number | string;
    };
  };
  campana: {
    id: number;
    nombre: string;
    estado: string;
    fecha_inicio: string;
    fecha_fin: string;
    hora_inicio?: string;
    hora_fin?: string;
    intervalo_muestreo_s?: number;
    rango_frecuencias: {
      inicio_mhz: number;
      fin_mhz: number;
      ancho_banda_mhz: number;
      resolucion_khz: number;
    };
  };
  analisis_espectral?: {
    modo: string;
    cumplimiento_general: boolean | number;
    emisiones_detectadas: number;
    umbral_db?: number;
    umbral?: number;
    tolerancia_fc_khz?: number;
    tolerancia_bw_khz?: number;
    picos_analizados?: number;
    correccion_aplicada: boolean;
    metodo_deteccion?: string;
    algoritmo?: string;
  };
  estadisticas: {
    total_mediciones?: number;
    total_emisiones?: number;
    autorizadas?: number;
    emisiones_autorizadas?: number;
    no_autorizadas?: number;
    emisiones_no_autorizadas?: number;
    emisiones_sin_licencia?: number;
    porcentaje_cumplimiento: string;
    frecuencias_unicas_autorizadas?: number;
    mediciones_analizadas?: number;
  };
  mediciones?: Array<{
    timestamp: number;
    fecha_hora: string;
    num_emisiones: number;
    emisiones_autorizadas: number;
    emisiones_sin_licencia: number;
    porcentaje_cumplimiento: string;
    emisiones: Array<{
      frecuencia_mhz: number;
      dane_asociado?: string;
      potencia_dbm: number;
      ancho_banda_khz: number;
      estado_cumplimiento: string;
      cumple_fc?: string;
      cumple_bw?: string;
      licencia?: string;
      fc_nominal_mhz?: number;
      delta_f_mhz?: number;
      bw_nominal_khz?: number;
      delta_bw_khz?: number;
      p_nominal_dbm?: number;
      delta_p_db?: number;
    }>;
    datos_tecnicos?: any;
  }>;
  emisiones?: Array<{
    frecuencia_hz?: number;
    frecuencia_mhz: string | number;
    potencia_dbm: string | number;
    ancho_banda_hz?: number;
    ancho_banda_khz?: string | number;
    estado_cumplimiento?: string;
    licencia_asociada?: any;
    detalles?: any;
  }>;
  frecuencias_autorizadas_municipio?: Array<{
    frecuencia_mhz: number;
    ancho_banda: number;
    unidad_ancho_banda: string;
    potencia: number;
    unidad_potencia: string;
    servicio: string;
  }>;
  datos_tecnicos?: {
    timestamp_analizado: number;
    fecha_hora_medicion: string;
    puntos_fft: number;
    frecuencia_inicio_hz: number;
    frecuencia_fin_hz: number;
    resolucion_hz: number;
    total_mediciones?: number;
    primera_medicion?: string;
    ultima_medicion?: string;
    metricas_demodulacion?: {
      excursion_fm?: any;
      profundidad_am?: any;
    };
  };
}

// Componente para mostrar emisiones con análisis detallado expandible
function EmisionesDetalladas({ emisiones }: { emisiones: any[] }) {
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  return (
    <div className="border rounded-lg p-6 bg-gradient-to-br from-yellow-50 to-amber-50">
      <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <Zap size={20} className="text-yellow-500" />
        Emisiones Detectadas con Análisis Avanzado ({emisiones.length})
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-white">
            <tr>
              <th className="px-2 py-2"></th>
              <th className="px-4 py-2 text-left">#</th>
              <th className="px-4 py-2 text-left">Frecuencia (MHz)</th>
              <th className="px-4 py-2 text-left">Potencia (dBm)</th>
              <th className="px-4 py-2 text-left">Ancho Banda (kHz)</th>
              <th className="px-4 py-2 text-left">Estado</th>
              <th className="px-4 py-2 text-left">Análisis</th>
            </tr>
          </thead>
          <tbody className="divide-y bg-white">
            {emisiones.map((emision, idx) => {
              const isExpanded = expandedRow === idx;
              const detalles = emision.detalles || {};
              
              const freqMhz = typeof emision.frecuencia_mhz === 'number' 
                ? emision.frecuencia_mhz.toFixed(3)
                : emision.frecuencia_mhz;
              const potencia = typeof emision.potencia_dbm === 'number'
                ? emision.potencia_dbm.toFixed(2)
                : emision.potencia_dbm;
              const bw = typeof emision.ancho_banda_khz === 'number'
                ? emision.ancho_banda_khz.toFixed(1)
                : emision.ancho_banda_khz;
              
              const estado = emision.estado_cumplimiento || 'DESCONOCIDO';
              let estadoColor = 'bg-gray-100 text-gray-700';
              let estadoIcon = null;
              
              if (estado === 'CUMPLE') {
                estadoColor = 'bg-green-100 text-green-700';
                estadoIcon = <CheckCircle size={12} />;
              } else if (estado === 'NO_CUMPLE' || estado === 'FUERA_PARAMETROS') {
                estadoColor = 'bg-red-100 text-red-700';
                estadoIcon = <XCircle size={12} />;
              } else if (estado === 'SIN_LICENCIA') {
                estadoColor = 'bg-orange-100 text-orange-700';
                estadoIcon = <XCircle size={12} />;
              }

              // Análisis de cumplimiento de parámetros
              const cumpleFC = detalles.Cumple_FC;
              const cumpleBW = detalles.Cumple_BW;
              const tieneAnalisis = detalles.delta_f_MHz !== null || detalles.delta_p_dB !== null || detalles.delta_bw_kHz !== null;
              
              // Variables TDT (MER/BER)
              const hasTDT = emision.mer_db !== undefined || emision.ber_est !== undefined;
              const merDb = emision.mer_db;
              const berEst = emision.ber_est;

              return (
                <>
                  <tr 
                    key={idx} 
                    className={`hover:bg-yellow-50 cursor-pointer ${isExpanded ? 'bg-yellow-100' : ''}`}
                    onClick={() => setExpandedRow(isExpanded ? null : idx)}
                  >
                    <td className="px-2 py-2">
                      {(tieneAnalisis || hasTDT) && (
                        <button className="text-gray-500 hover:text-gray-700">
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-2 font-medium text-gray-500">{idx + 1}</td>
                    <td className="px-4 py-2 font-bold text-blue-600">
                      {freqMhz}
                      {emision.dane_asociado && (
                        <span className="ml-2 text-[10px] bg-gray-200 text-gray-600 px-1 rounded">
                          DANE: {emision.dane_asociado}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 font-mono">{potencia}</td>
                    <td className="px-4 py-2">{bw}</td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {merDb !== undefined ? merDb.toFixed(1) : '-'}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">
                      {berEst !== undefined ? berEst.toExponential(1) : '-'}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${estadoColor}`}>
                        {estadoIcon}
                        {estado === 'FUERA_PARAMETROS' ? 'FUERA PARAMETROS' : estado.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {tieneAnalisis ? (
                        <div className="flex gap-1">
                          {cumpleFC === true && <span className="text-xs text-green-600">✓FC</span>}
                          {cumpleFC === false && <span className="text-xs text-red-600">✗FC</span>}
                          {cumpleBW === true && <span className="text-xs text-green-600">✓BW</span>}
                          {cumpleBW === false && <span className="text-xs text-red-600">✗BW</span>}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">Sin licencia</span>
                      )}
                    </td>
                  </tr>
                  
                  {/* Fila expandida con análisis detallado */}
                  {isExpanded && tieneAnalisis && (
                    <tr className="bg-blue-50">
                      <td colSpan={7} className="px-6 py-4">
                        <div className="space-y-3">
                          <h5 className="font-semibold text-sm text-gray-700 mb-3">
                            📊 Análisis Detallado de Parámetros
                          </h5>
                          
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Frecuencia Central */}
                            <div className="bg-white p-3 rounded-lg border">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-gray-600">Frecuencia Central</span>
                                {cumpleFC === true && <CheckCircle size={14} className="text-green-600" />}
                                {cumpleFC === false && <XCircle size={14} className="text-red-600" />}
                              </div>
                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Medida:</span>
                                  <span className="font-mono font-semibold">{detalles.fc_medida_MHz?.toFixed(3)} MHz</span>
                                </div>
                                {detalles.fc_nominal_MHz && (
                                  <>
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Nominal:</span>
                                      <span className="font-mono">{detalles.fc_nominal_MHz?.toFixed(3)} MHz</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                      <span className="text-gray-600">Delta:</span>
                                      <span className={`font-mono font-semibold flex items-center gap-1 ${
                                        Math.abs(detalles.delta_f_MHz || 0) < 0.001 ? 'text-green-600' : 'text-orange-600'
                                      }`}>
                                        {detalles.delta_f_MHz > 0 ? <TrendingUp size={12} /> : detalles.delta_f_MHz < 0 ? <TrendingDown size={12} /> : <Minus size={12} />}
                                        {Math.abs(detalles.delta_f_MHz || 0).toFixed(3)} MHz
                                      </span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>

                            {/* Potencia */}
                            <div className="bg-white p-3 rounded-lg border">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-gray-600">Potencia</span>
                              </div>
                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Medida:</span>
                                  <span className="font-mono font-semibold">{detalles.p_medida_dBm?.toFixed(2)} dBm</span>
                                </div>
                                {detalles.p_nominal_dBm && (
                                  <>
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Nominal:</span>
                                      <span className="font-mono">{detalles.p_nominal_dBm?.toFixed(2)} dBm</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                      <span className="text-gray-600">Delta:</span>
                                      <span className={`font-mono font-semibold flex items-center gap-1 ${
                                        Math.abs(detalles.delta_p_dB || 0) < 1 ? 'text-green-600' : 'text-orange-600'
                                      }`}>
                                        {detalles.delta_p_dB > 0 ? <TrendingUp size={12} /> : detalles.delta_p_dB < 0 ? <TrendingDown size={12} /> : <Minus size={12} />}
                                        {Math.abs(detalles.delta_p_dB || 0).toFixed(2)} dB
                                      </span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>

                            {/* Ancho de Banda */}
                            <div className="bg-white p-3 rounded-lg border">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-semibold text-gray-600">Ancho de Banda</span>
                                {cumpleBW === true && <CheckCircle size={14} className="text-green-600" />}
                                {cumpleBW === false && <XCircle size={14} className="text-red-600" />}
                              </div>
                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-gray-600">Medido:</span>
                                  <span className="font-mono font-semibold">{detalles.bw_medido_kHz?.toFixed(1)} kHz</span>
                                </div>
                                {detalles.bw_nominal_kHz && (
                                  <>
                                    <div className="flex justify-between">
                                      <span className="text-gray-600">Nominal:</span>
                                      <span className="font-mono">{detalles.bw_nominal_kHz?.toFixed(1)} kHz</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                      <span className="text-gray-600">Delta:</span>
                                      <span className={`font-mono font-semibold flex items-center gap-1 ${
                                        Math.abs(detalles.delta_bw_kHz || 0) < 10 ? 'text-green-600' : 'text-orange-600'
                                      }`}>
                                        {detalles.delta_bw_kHz > 0 ? <TrendingUp size={12} /> : detalles.delta_bw_kHz < 0 ? <TrendingDown size={12} /> : <Minus size={12} />}
                                        {Math.abs(detalles.delta_bw_kHz || 0).toFixed(1)} kHz
                                      </span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>

                            {/* Variables TDT (MER/BER) - Solo si están presentes */}
                            {hasTDT && (
                              <div className="bg-white p-3 rounded-lg border border-blue-200 bg-blue-50/30">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-semibold text-blue-800">Parámetros TDT</span>
                                  <Activity size={14} className="text-blue-600" />
                                </div>
                                <div className="space-y-2 text-xs">
                                  {merDb !== undefined && (
                                    <div className="flex justify-between items-center">
                                      <span className="text-gray-600">MER:</span>
                                      <span className={`font-mono font-bold ${merDb >= 20 ? 'text-green-600' : 'text-orange-600'}`}>
                                        {merDb.toFixed(2)} dB
                                      </span>
                                    </div>
                                  )}
                                  {berEst !== undefined && (
                                    <div className="flex justify-between items-center">
                                      <span className="text-gray-600">BER (Est.):</span>
                                      <span className="font-mono font-semibold">
                                        {berEst.toExponential(2)}
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Interpretación */}
                          <div className="bg-blue-100 p-3 rounded-lg text-xs">
                            <p className="font-semibold text-blue-900 mb-1">💡 Interpretación:</p>
                            <ul className="list-disc list-inside space-y-1 text-blue-800">
                              {cumpleFC === true && <li>La frecuencia central está dentro de tolerancia</li>}
                              {cumpleFC === false && <li className="text-red-700">⚠️ La frecuencia central excede la tolerancia permitida</li>}
                              {cumpleBW === true && <li>El ancho de banda cumple con las especificaciones</li>}
                              {cumpleBW === false && <li className="text-red-700">⚠️ El ancho de banda excede los límites permitidos</li>}
                              {!detalles.fc_nominal_MHz && <li className="text-orange-700">No hay licencia asignada para comparar parámetros</li>}
                            </ul>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ==================== FUNCIONES DE ANÁLISIS Y AGRUPACIÓN ====================

// Analizar todas las emisiones de todas las mediciones
export function analizarEmisiones(mediciones: any[]) {
  const fueraParametros: any[] = [];
  const sinLicencia: any[] = [];
  const conformes: any[] = [];

  mediciones.forEach((medicion, medIdx) => {
    medicion.emisiones?.forEach((emision: any, emIdx: number) => {
      const emisionConContexto = {
        ...emision,
        medicionIdx: medIdx,
        emisionIdx: emIdx,
        fecha_hora: medicion.fecha_hora,
        timestamp: medicion.timestamp
      };

      const estado = emision.estado_cumplimiento;
      const cumpleFC = emision.cumple_fc;
      const cumpleBW = emision.cumple_bw;

      // Prioridad 1: Fuera de Parámetros (tiene licencia pero no cumple FC o BW)
      if (estado === 'FUERA_PARAMETROS' || ((cumpleFC === 'NO' || cumpleBW === 'NO') && emision.fc_nominal_mhz)) {
        fueraParametros.push(emisionConContexto);
      }
      // Prioridad 2: Sin Licencia
      else if (estado === 'SIN_LICENCIA' || !emision.fc_nominal_mhz) {
        sinLicencia.push(emisionConContexto);
      }
      // Conforme
      else {
        conformes.push(emisionConContexto);
      }
    });
  });

  return { fueraParametros, sinLicencia, conformes };
}

// Agrupar emisiones fuera de parámetros por licencia nominal
function agruparPorLicencia(emisiones: any[]) {
  const grupos: { [key: string]: any } = {};

  emisiones.forEach(emision => {
    const key = `${emision.fc_nominal_mhz?.toFixed(3)}_${emision.bw_nominal_khz?.toFixed(1)}_${emision.dane_asociado || 'N/A'}`;
    
    if (!grupos[key]) {
      grupos[key] = {
        fc_nominal: emision.fc_nominal_mhz,
        bw_nominal: emision.bw_nominal_khz,
        dane_asociado: emision.dane_asociado,
        emisiones: [],
        problemaFC: emision.cumple_fc === 'NO',
        problemaBW: emision.cumple_bw === 'NO'
      };
    }
    
    grupos[key].emisiones.push(emision);
  });

  return Object.values(grupos);
}

// Agrupar emisiones sin licencia por frecuencia similar (±0.1 MHz)
function agruparPorFrecuencia(emisiones: any[]) {
  const grupos: any[] = [];

  emisiones.forEach(emision => {
    const freq = emision.frecuencia_mhz;
    
    // Buscar grupo existente cercano
    let grupoEncontrado = grupos.find(g => 
      Math.abs(g.frecuencia_promedio - freq) < 0.1
    );

    if (!grupoEncontrado) {
      grupoEncontrado = {
        frecuencia_promedio: freq,
        potencia_promedio: emision.potencia_dbm,
        bw_promedio: emision.ancho_banda_khz,
        emisiones: []
      };
      grupos.push(grupoEncontrado);
    }

    grupoEncontrado.emisiones.push(emision);
    
    // Recalcular promedios
    grupoEncontrado.frecuencia_promedio = 
      grupoEncontrado.emisiones.reduce((sum: number, e: any) => sum + e.frecuencia_mhz, 0) / grupoEncontrado.emisiones.length;
    grupoEncontrado.potencia_promedio = 
      grupoEncontrado.emisiones.reduce((sum: number, e: any) => sum + e.potencia_dbm, 0) / grupoEncontrado.emisiones.length;
    grupoEncontrado.bw_promedio = 
      grupoEncontrado.emisiones.reduce((sum: number, e: any) => sum + e.ancho_banda_khz, 0) / grupoEncontrado.emisiones.length;
  });

  return grupos.sort((a, b) => b.emisiones.length - a.emisiones.length); // Más ocurrencias primero
}

// Banner de Estado
// Resumen Ejecutivo
function ResumenEjecutivo({ gruposFueraParametros, gruposSinLicencia, maxEmisiones }: { gruposFueraParametros: any[], gruposSinLicencia: any[], maxEmisiones: number }) {
  const conformesCount = maxEmisiones - gruposSinLicencia.length - gruposFueraParametros.length;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* Card Fuera de Parámetros */}
      <div className="bg-gradient-to-br from-orange-50 to-red-50 border-2 border-orange-300 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-3">
          <XCircle size={28} className="text-orange-600" />
          <div>
            <h4 className="font-bold text-gray-800">Fuera de Parámetros</h4>
            <p className="text-xs text-gray-600">Emisiones</p>
          </div>
        </div>
        <div className="text-3xl font-bold text-orange-600 mb-2">{gruposFueraParametros.length}</div>
      </div>

      {/* Card Sin Licencia */}
      <div className="bg-gradient-to-br from-yellow-50 to-orange-50 border-2 border-yellow-400 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-3">
          <Zap size={28} className="text-yellow-600" />
          <div>
            <h4 className="font-bold text-gray-800">Sin Licencia</h4>
            <p className="text-xs text-gray-600">Emisiones</p>
          </div>
        </div>
        <div className="text-3xl font-bold text-yellow-600 mb-2">{gruposSinLicencia.length}</div>
      </div>

      {/* Card Conformes */}
      <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-300 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-3">
          <CheckCircle size={28} className="text-green-600" />
          <div>
            <h4 className="font-bold text-gray-800">Conformes</h4>
            <p className="text-xs text-gray-600">Emisiones</p>
          </div>
        </div>
        <div className="text-3xl font-bold text-green-600 mb-2">{conformesCount >= 0 ? conformesCount : 0}</div>
      </div>
    </div>
  );
}

// Sección: Emisiones Fuera de Parámetros (Agrupadas)
function SeccionFueraParametros({ grupos, tolerancias }: { grupos: any[], tolerancias?: { fc_khz: number, bw_khz: number } }) {
  const [expandedGrupo, setExpandedGrupo] = useState<number | null>(null);

  if (grupos.length === 0) return null;

  const tolFC_MHz = tolerancias?.fc_khz ? tolerancias.fc_khz / 1000 : 0.010; // Default 10 kHz
  const tolBW_kHz = tolerancias?.bw_khz || 10; // Default 10 kHz

  return (
    <div className="border-2 border-orange-400 rounded-lg p-6 mb-6 bg-gradient-to-br from-orange-50 to-red-50">
      <h3 className="text-xl font-bold text-orange-800 mb-4 flex items-center gap-2">
        <XCircle size={24} />
        🚨 Emisiones Fuera de Parámetros ({grupos.length} emisiones con {grupos.reduce((sum, g) => sum + g.emisiones.length, 0)} concurrencias)
      </h3>
      <p className="text-sm text-gray-700 mb-4">
        Estas emisiones tienen licencia pero sus parámetros medidos exceden las tolerancias permitidas.
      </p>

      <div className="space-y-3">
        {grupos.map((grupo, idx) => {
          const isExpanded = expandedGrupo === idx;
          const primeraEmision = grupo.emisiones[0];
          const problemas = [];
          if (grupo.problemaFC) problemas.push('Frecuencia Central');
          if (grupo.problemaBW) problemas.push('Ancho de Banda');

          return (
            <div key={idx} className="bg-white rounded-lg border-2 border-orange-300 overflow-hidden">
              <button
                onClick={() => setExpandedGrupo(isExpanded ? null : idx)}
                className="w-full p-4 text-left hover:bg-orange-50 transition-colors flex items-center justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-lg font-bold text-orange-700">
                      📋 Licencia: {grupo.fc_nominal?.toFixed(3)} MHz
                    </span>
                    <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-semibold">
                      {grupo.emisiones.length} ocurrencia{grupo.emisiones.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mt-2">
                    <div>
                      <span className="text-gray-600">FC Nominal:</span>
                      <span className="ml-2 font-mono font-semibold">{grupo.fc_nominal?.toFixed(3)} MHz</span>
                    </div>
                    <div>
                      <span className="text-gray-600">BW Nominal:</span>
                      <span className="ml-2 font-mono font-semibold">{grupo.bw_nominal?.toFixed(1)} kHz</span>
                    </div>
                    <div>
                      <span className="text-gray-600">FC Medida:</span>
                      <span className="ml-2 font-mono font-semibold text-orange-600">
                        {primeraEmision.frecuencia_mhz?.toFixed(3)} MHz
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Problemas:</span>
                      <span className="ml-2 font-semibold text-red-600">{problemas.join(', ')}</span>
                    </div>
                  </div>

                  {primeraEmision.delta_f_mhz !== null && primeraEmision.delta_f_mhz !== undefined && (
                    <div className="mt-2 text-sm">
                      <span className="text-gray-600">Delta FC:</span>
                      <span className={`ml-2 font-mono font-bold ${grupo.problemaFC ? 'text-red-600' : 'text-green-600'}`}>
                        {primeraEmision.delta_f_mhz > 0 ? '+' : ''}{primeraEmision.delta_f_mhz?.toFixed(3)} MHz
                        {grupo.problemaFC && ` ⚠️ Fuera de tolerancia (±${tolFC_MHz.toFixed(3)} MHz)`}
                      </span>
                    </div>
                  )}

                  {primeraEmision.delta_bw_khz !== null && primeraEmision.delta_bw_khz !== undefined && (
                    <div className="mt-1 text-sm">
                      <span className="text-gray-600">Delta BW:</span>
                      <span className={`ml-2 font-mono font-bold ${grupo.problemaBW ? 'text-red-600' : 'text-green-600'}`}>
                        {primeraEmision.delta_bw_khz > 0 ? '+' : ''}{primeraEmision.delta_bw_khz?.toFixed(1)} kHz
                        {grupo.problemaBW && ` ⚠️ Fuera de tolerancia (+${tolBW_kHz} kHz)`}
                      </span>
                    </div>
                  )}
                </div>
                
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>

              {isExpanded && (
                <div className="p-4 bg-gray-50 border-t">
                  <h5 className="font-semibold text-sm text-gray-700 mb-3">
                    Todas las ocurrencias ({grupo.emisiones.length}):
                  </h5>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-white">
                        <tr>
                          <th className="px-3 py-2 text-left">#</th>
                          <th className="px-3 py-2 text-left">Fecha/Hora</th>
                          <th className="px-3 py-2 text-left">FC Medida</th>
                          <th className="px-3 py-2 text-left">Δ FC</th>
                          <th className="px-3 py-2 text-left">BW Medido</th>
                          <th className="px-3 py-2 text-left">Δ BW</th>
                          <th className="px-3 py-2 text-left">Potencia</th>
                          <th className="px-3 py-2 text-left">MER</th>
                          <th className="px-3 py-2 text-left">BER</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {grupo.emisiones.map((em: any, emIdx: number) => (
                          <tr key={emIdx} className="hover:bg-orange-50">
                            <td className="px-3 py-2">{emIdx + 1}</td>
                            <td className="px-3 py-2 text-xs">{em.fecha_hora}</td>
                            <td className="px-3 py-2 font-mono">{em.frecuencia_mhz?.toFixed(3)} MHz</td>
                            <td className="px-3 py-2 font-mono">
                              <span className={em.cumple_fc === 'NO' ? 'text-red-600 font-bold' : 'text-green-600'}>
                                {em.delta_f_mhz > 0 ? '+' : ''}{em.delta_f_mhz?.toFixed(3)} MHz
                              </span>
                            </td>
                            <td className="px-3 py-2 font-mono">{em.ancho_banda_khz?.toFixed(1)} kHz</td>
                            <td className="px-3 py-2 font-mono">
                              <span className={em.cumple_bw === 'NO' ? 'text-red-600 font-bold' : 'text-green-600'}>
                                {em.delta_bw_khz > 0 ? '+' : ''}{em.delta_bw_khz?.toFixed(1)} kHz
                              </span>
                            </td>
                            <td className="px-3 py-2 font-mono">{em.potencia_dbm?.toFixed(2)} dBm</td>
                            <td className="px-3 py-2 font-mono text-xs">
                              {em.mer_db !== undefined ? em.mer_db.toFixed(1) : '-'}
                            </td>
                            <td className="px-3 py-2 font-mono text-xs">
                              {em.ber_est !== undefined ? em.ber_est.toExponential(1) : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Sección: Emisiones Sin Licencia (Agrupadas)
function SeccionSinLicencia({ grupos }: { grupos: any[] }) {
  const [expandedGrupo, setExpandedGrupo] = useState<number | null>(null);

  if (grupos.length === 0) return null;

  return (
    <div className="border-2 border-yellow-400 rounded-lg p-6 mb-6 bg-gradient-to-br from-yellow-50 to-orange-50">
      <h3 className="text-xl font-bold text-yellow-800 mb-4 flex items-center gap-2">
        <Zap size={24} />
        🔴 Emisiones Sin Licencia ({grupos.length} frecuencias, {grupos.reduce((sum, g) => sum + g.emisiones.length, 0)} concurrencias)
      </h3>
      <p className="text-sm text-gray-700 mb-4">
        Estas emisiones no tienen autorización registrada en el municipio.
      </p>

      <div className="space-y-3">
        {grupos.map((grupo, idx) => {
          const isExpanded = expandedGrupo === idx;
          const primeraDeteccion = grupo.emisiones[0].fecha_hora;
          const ultimaDeteccion = grupo.emisiones[grupo.emisiones.length - 1].fecha_hora;

          return (
            <div key={idx} className="bg-white rounded-lg border-2 border-yellow-300 overflow-hidden">
              <button
                onClick={() => setExpandedGrupo(isExpanded ? null : idx)}
                className="w-full p-4 text-left hover:bg-yellow-50 transition-colors flex items-center justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-lg font-bold text-yellow-700">
                      📡 Frecuencia: {grupo.frecuencia_promedio?.toFixed(3)} MHz
                    </span>
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-semibold">
                      {grupo.emisiones.length} ocurrencia{grupo.emisiones.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mt-2">
                    <div>
                      <span className="text-gray-600">Potencia Prom:</span>
                      <span className="ml-2 font-mono font-semibold">{grupo.potencia_promedio?.toFixed(2)} dBm</span>
                    </div>
                    <div>
                      <span className="text-gray-600">BW Prom:</span>
                      <span className="ml-2 font-mono font-semibold">{grupo.bw_promedio?.toFixed(1)} kHz</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Primera:</span>
                      <span className="ml-2 text-xs">{primeraDeteccion}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Última:</span>
                      <span className="ml-2 text-xs">{ultimaDeteccion}</span>
                    </div>
                  </div>
                </div>
                
                {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>

              {isExpanded && (
                <div className="p-4 bg-gray-50 border-t">
                  <h5 className="font-semibold text-sm text-gray-700 mb-3">
                    Todas las detecciones ({grupo.emisiones.length}):
                  </h5>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-white">
                        <tr>
                          <th className="px-3 py-2 text-left">#</th>
                          <th className="px-3 py-2 text-left">Fecha/Hora</th>
                          <th className="px-3 py-2 text-left">Frecuencia</th>
                          <th className="px-3 py-2 text-left">Potencia</th>
                          <th className="px-3 py-2 text-left">Ancho Banda</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {grupo.emisiones.map((em: any, emIdx: number) => (
                          <tr key={emIdx} className="hover:bg-yellow-50">
                            <td className="px-3 py-2">{emIdx + 1}</td>
                            <td className="px-3 py-2 text-xs">{em.fecha_hora}</td>
                            <td className="px-3 py-2 font-mono font-semibold text-yellow-700">
                              {em.frecuencia_mhz?.toFixed(3)} MHz
                            </td>
                            <td className="px-3 py-2 font-mono">{em.potencia_dbm?.toFixed(2)} dBm</td>
                            <td className="px-3 py-2 font-mono">{em.ancho_banda_khz?.toFixed(1)} kHz</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ==================== COMPONENTES DE REPORTE ====================

// Componente para mostrar TODAS las mediciones de la campaña
function MedicionesCompletas({ mediciones, tolerancias }: { mediciones: any[], tolerancias?: { fc_khz: number, bw_khz: number } }) {
  const [expandedMedicion, setExpandedMedicion] = useState<number | null>(null);
  const [filtroEstado, setFiltroEstado] = useState<string>('todas');
  const [currentPage, setCurrentPage] = useState(1);
  const medicionesPorPagina = 10;

  const tolFC_MHz = tolerancias?.fc_khz ? tolerancias.fc_khz / 1000 : 0.001;
  const tolBW_kHz = tolerancias?.bw_khz || 10;

  // Filtrar mediciones
  const medicionesFiltradas = mediciones.filter(med => {
    if (filtroEstado === 'todas') return true;
    if (filtroEstado === 'con_emisiones') return med.num_emisiones > 0;
    if (filtroEstado === 'sin_emisiones') return med.num_emisiones === 0;
    return true;
  });

  // Paginación
  const totalPaginas = Math.ceil(medicionesFiltradas.length / medicionesPorPagina);
  const inicio = (currentPage - 1) * medicionesPorPagina;
  const medicionesPaginadas = medicionesFiltradas.slice(inicio, inicio + medicionesPorPagina);

  return (
    <div className="border rounded-lg p-6 bg-gradient-to-br from-purple-50 to-pink-50">
      <div className="flex items-center justify-between mb-4">
        <h4 className="font-semibold text-gray-800 flex items-center gap-2">
          <Activity size={20} className="text-purple-500" />
          Todas las Mediciones ({mediciones.length} adquisiciones)
        </h4>
        <div className="flex gap-2">
          <select 
            value={filtroEstado}
            onChange={(e) => {
              setFiltroEstado(e.target.value);
              setCurrentPage(1);
            }}
            className="text-sm border rounded px-3 py-1"
          >
            <option value="todas">Todas</option>
            <option value="con_emisiones">Con emisiones</option>
            <option value="sin_emisiones">Sin emisiones</option>
          </select>
        </div>
      </div>

      <div className="space-y-3">
        {medicionesPaginadas.map((medicion, idx) => {
          const medicionIndex = inicio + idx;
          const isExpanded = expandedMedicion === medicionIndex;
          const fecha = new Date(medicion.fecha_hora);
          
          return (
            <div key={medicionIndex} className="bg-white rounded-lg border shadow-sm">
              <div 
                className="p-4 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedMedicion(isExpanded ? null : medicionIndex)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button className="text-gray-500">
                      {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                    <div>
                      <div className="font-semibold text-gray-800">
                        Medición #{medicionIndex + 1}
                      </div>
                      <div className="text-sm text-gray-600">
                        {toColombiaTime(fecha)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">{medicion.num_emisiones}</div>
                      <div className="text-xs text-gray-600">Emisiones</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{medicion.emisiones_autorizadas}</div>
                      <div className="text-xs text-gray-600">Autorizadas</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">{medicion.emisiones_sin_licencia}</div>
                      <div className="text-xs text-gray-600">Sin Licencia</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">
                        {medicion.num_emisiones > 0
                          ? ((medicion.emisiones_autorizadas / medicion.num_emisiones) * 100).toFixed(2)
                          : '0.00'}%
                      </div>
                      <div className="text-xs text-gray-600">Cumplimiento</div>
                    </div>
                  </div>
                </div>
              </div>

              {isExpanded && medicion.emisiones && medicion.emisiones.length > 0 && (
                <div className="border-t p-4 bg-gray-50">
                  <h5 className="font-semibold text-sm text-gray-700 mb-3">
                    Emisiones Detectadas en esta Medición
                  </h5>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-white">
                        <tr>
                          <th className="px-3 py-2 text-left">#</th>
                          <th className="px-3 py-2 text-left">Frecuencia (MHz)</th>
                          <th className="px-3 py-2 text-left">Potencia (dBm)</th>
                          <th className="px-3 py-2 text-left">BW (kHz)</th>
                          <th className="px-3 py-2 text-left">FC</th>
                          <th className="px-3 py-2 text-left">BW</th>
                          <th className="px-3 py-2 text-left">Estado</th>
                          <th className="px-3 py-2 text-left">MER (dB)</th>
                          <th className="px-3 py-2 text-left">BER</th>
                          <th className="px-3 py-2 text-left">Δ Freq</th>
                          <th className="px-3 py-2 text-left">Δ BW</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y bg-white">
                        {medicion.emisiones.map((emision: any, eIdx: number) => {
                          const cumpleFC = emision.cumple_fc;
                          const cumpleBW = emision.cumple_bw;
                          const estado = emision.estado_cumplimiento;

                          let estadoColor = 'bg-gray-100 text-gray-700';
                          if (estado === 'CUMPLE') estadoColor = 'bg-green-100 text-green-700';
                          else if (estado === 'NO_CUMPLE') estadoColor = 'bg-red-100 text-red-700';
                          else if (estado === 'SIN_LICENCIA') estadoColor = 'bg-orange-100 text-orange-700';

                          return (
                            <tr key={eIdx} className="hover:bg-blue-50">
                              <td className="px-3 py-2 font-medium text-gray-500">{eIdx + 1}</td>
                              <td className="px-3 py-2 font-bold text-blue-600">
                                {emision.frecuencia_mhz?.toFixed(3) || 'N/A'}
                              </td>
                              <td className="px-3 py-2 font-mono">
                                {emision.potencia_dbm?.toFixed(2) || 'N/A'}
                              </td>
                              <td className="px-3 py-2">
                                {emision.ancho_banda_khz?.toFixed(1) || 'N/A'}
                              </td>
                              <td className="px-3 py-2">
                                {cumpleFC === 'SI' && <span className="text-green-600 font-bold">✓</span>}
                                {cumpleFC === 'NO' && <span className="text-red-600 font-bold">✗</span>}
                                {!cumpleFC && <span className="text-gray-400">-</span>}
                              </td>
                              <td className="px-3 py-2">
                                {cumpleBW === 'SI' && <span className="text-green-600 font-bold">✓</span>}
                                {cumpleBW === 'NO' && <span className="text-red-600 font-bold">✗</span>}
                                {!cumpleBW && <span className="text-gray-400">-</span>}
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-2 py-1 rounded-full text-xs ${estadoColor}`}>
                                  {estado || 'N/A'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-xs font-mono">
                                {emision.mer_db !== undefined && emision.mer_db !== null ? `${emision.mer_db.toFixed(1)} dB` : '-'}
                              </td>
                              <td className="px-3 py-2 text-xs font-mono">
                                {emision.ber_est !== undefined && emision.ber_est !== null ? emision.ber_est.toExponential(1) : '-'}
                              </td>
                              <td className="px-3 py-2 text-xs">
                                {emision.delta_f_mhz !== null && emision.delta_f_mhz !== undefined ? (
                                  <span className={Math.abs(emision.delta_f_mhz) <= tolFC_MHz ? 'text-green-600' : 'text-orange-600'}>
                                    {emision.delta_f_mhz > 0 ? '+' : ''}{emision.delta_f_mhz.toFixed(3)} MHz
                                  </span>
                                ) : '-'}
                              </td>
                              <td className="px-3 py-2 text-xs">
                                {emision.delta_bw_khz !== null && emision.delta_bw_khz !== undefined ? (
                                  <span className={Math.abs(emision.delta_bw_khz) <= tolBW_kHz ? 'text-green-600' : 'text-orange-600'}>
                                    {emision.delta_bw_khz > 0 ? '+' : ''}{emision.delta_bw_khz.toFixed(1)} kHz
                                  </span>
                                ) : '-'}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {isExpanded && (!medicion.emisiones || medicion.emisiones.length === 0) && (
                <div className="border-t p-4 bg-gray-50 text-center text-gray-500">
                  No se detectaron emisiones en esta medición
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Paginación */}
      {totalPaginas > 1 && (
        <div className="flex items-center justify-center gap-2 mt-4">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Anterior
          </button>
          <span className="text-sm text-gray-600">
            Página {currentPage} de {totalPaginas}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPaginas, currentPage + 1))}
            disabled={currentPage === totalPaginas}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      )}
    </div>
  );
}

export function ComplianceReport({ campaignId, campaignName, sensors = [], allSensors, initialSensor, onClose, initialData, umbral }: ComplianceReportProps) {
  const [report, setReport] = useState<ReportData | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const [selectedSensor, setSelectedSensor] = useState<string>(initialSensor || sensors[0] || '');
  const [filtroDane, setFiltroDane] = useState<string>('todos');
  const [generatingAllReports, setGeneratingAllReports] = useState(false);
  const [allReports, setAllReports] = useState<Record<string, ReportData>>({});

  const generateReport = async () => {
    // Si ya tenemos datos iniciales y no estamos forzando regeneración (porque cambiaron campaignId o algo),
    // no hacemos nada si initialData coincide.
    // Pero aquí generateReport se llama en useEffect.
    
    setLoading(true);
    setError(null);
    
    try {
      // Si es la campaña simulada (ID 99999), generar datos localmente
      if (campaignId === 99999) {
        // Obtener configuración real del sistema para aplicar tolerancias
        let systemConfig = { center_freq_tolerance_khz: '100', bandwidth_tolerance_khz: '10' };
        try {
          systemConfig = await configAPI.get() as any;
        } catch (e) {
          console.warn('No se pudo cargar configuración del sistema, usando defaults para simulación');
        }

        await new Promise(resolve => setTimeout(resolve, 1500)); // Simular delay
        const { generateSimulatedTDTReport } = await import('../utils/generateData');
        const simulatedData: any = generateSimulatedTDTReport(campaignId, campaignName);
        
        // Inyectar tolerancias reales en el reporte simulado
        if (simulatedData.analisis_espectral) {
          simulatedData.analisis_espectral.tolerancia_fc_khz = Number(systemConfig.center_freq_tolerance_khz || 100);
          simulatedData.analisis_espectral.tolerancia_bw_khz = Number(systemConfig.bandwidth_tolerance_khz || 10);
        }

        setReport(simulatedData as unknown as ReportData); // Cast necesario si los tipos no coinciden exactamente
        setLoading(false);
        return;
      }

      const response = await axios.post(`${API_BASE_URL}/reports/compliance/${campaignId}?sensor_mac=${selectedSensor}`, {
        umbral: umbral // Enviar el umbral si existe
      });
      setReport(response.data);
    } catch (err: any) {
      const backendMsg = err.response?.data?.error || err.response?.data?.details || err.message;
      const status = err.response?.status;
      setError(status ? `${status}::${backendMsg}` : backendMsg);
      console.error('Error generating report:', err);
    } finally {
      if (campaignId !== 99999) setLoading(false);
    }
  };

  // Generar reporte automáticamente al montar o cambiar sensor
  useEffect(() => {
    // Si tenemos datos iniciales y coinciden con el sensor seleccionado (o es el primero), usarlos
    if (initialData && selectedSensor === sensors[0] && !report) {
      setReport(initialData);
      setLoading(false);
    } else {
      generateReport();
    }
  }, [campaignId, selectedSensor]);

  const downloadReport = () => {
    if (!report) return;
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte_cumplimiento_${campaignId}_${selectedSensor}_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateAllReports = async () => {
    if (sensors.length <= 1) {
      alert('Esta campaña solo tiene un sensor.');
      return;
    }

    setGeneratingAllReports(true);
    setError(null);
    const reports: Record<string, ReportData> = {};
    const errors: string[] = [];

    for (const sensorMac of sensors) {
      try {
        console.log(`📊 Generando reporte para sensor ${sensorMac}...`);
        
        if (campaignId === 99999) {
          // Simular para campaña de prueba
          await new Promise(resolve => setTimeout(resolve, 500));
          const { generateSimulatedTDTReport } = await import('../utils/generateData');
          const simulatedData = generateSimulatedTDTReport(campaignId, campaignName);
          reports[sensorMac] = simulatedData as unknown as ReportData;
        } else {
          const response = await axios.post(`${API_BASE_URL}/reports/compliance/${campaignId}?sensor_mac=${sensorMac}`, {
            umbral: umbral
          });
          reports[sensorMac] = response.data;
        }
        
        console.log(`✅ Reporte generado para sensor ${sensorMac}`);
      } catch (err: any) {
        console.error(`❌ Error generando reporte para sensor ${sensorMac}:`, err);
        errors.push(`${sensorMac}: ${err.message}`);
      }
    }

    setAllReports(reports);
    setGeneratingAllReports(false);

    if (errors.length > 0) {
      setError(`Algunos reportes fallaron: ${errors.join(', ')}`);
    }

    // Descargar todos los reportes en un archivo ZIP o individual
    downloadAllReports(reports);
  };

  const downloadAllReports = (reports: Record<string, ReportData>) => {
    // Por simplicidad, descargar cada reporte como un archivo JSON separado
    Object.entries(reports).forEach(([sensorMac, reportData]) => {
      const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reporte_cumplimiento_${campaignId}_${sensorMac}_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      // Pequeño delay para evitar bloquear el navegador
      setTimeout(() => {}, 100);
    });

    alert(`Se descargaron ${Object.keys(reports).length} reportes exitosamente.`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <FileText size={28} />
            <div>
              <h2 className="text-2xl font-bold">Reporte de Cumplimiento Normativo</h2>
              <p className="text-orange-100 text-sm mt-1">{campaignName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="hover:bg-white/20 p-2 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {(loading || generatingAllReports) && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-orange-500 mx-auto mb-4"></div>
              <p className="text-gray-600">
                {generatingAllReports 
                  ? `Generando reportes para ${sensors.length} sensores...` 
                  : 'Generando reporte...'}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                {generatingAllReports
                  ? 'Por favor espera, esto puede tomar varios minutos'
                  : 'Consultando geolocalización y analizando mediciones'}
              </p>
            </div>
          )}

          {error && !generatingAllReports && (() => {
            const is404 = error.includes('404');
            const is400 = error.startsWith('400::');
            const otherSensors = sensors.filter(s => s !== selectedSensor);
            return (
              <div className={`border rounded-lg p-6 text-center ${
                is400 ? 'bg-yellow-50 border-yellow-300' : 'bg-red-50 border-red-200'
              }`}>
                <XCircle size={48} className={`mx-auto mb-4 ${
                  is400 ? 'text-yellow-500' : 'text-red-500'
                }`} />
                <h3 className={`text-lg font-semibold mb-2 ${
                  is400 ? 'text-yellow-800' : 'text-red-800'
                }`}>
                  {is404
                    ? 'No hay datos disponibles'
                    : is400
                    ? 'Este sensor no generó datos en la campaña'
                    : 'Error al generar reporte'}
                </h3>
                <p className={`${
                  is400 ? 'text-yellow-700' : 'text-red-600'
                }`}>
                  {is404
                    ? 'No se encontraron mediciones para esta campaña. Es posible que el sensor no haya estado activo durante el periodo programado o no haya capturado información.'
                    : is400
                    ? `El sensor ${selectedSensor} no registró mediciones durante el período de la campaña. Esto puede ocurrir si el dispositivo estuvo fuera de línea, presentó una falla de comunicación o fue reiniciado durante la ejecución.`
                    : error.replace(/^\d+::/, '')}
                </p>
                {is400 && otherSensors.length > 0 && (
                  <div className="mt-5 text-left bg-white border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm font-semibold text-yellow-800 mb-3">Para ver el reporte de los sensores que sí funcionaron:</p>
                    <ol className="text-sm text-yellow-700 space-y-2 list-decimal list-inside">
                      <li>Selecciona otro sensor en el selector de la parte superior de este panel.</li>
                      <li>El reporte se generará automáticamente para ese sensor.</li>
                    </ol>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {otherSensors.map(s => {
                        const sensorName = allSensors?.find(a => a.mac === s)?.name || s;
                        return (
                          <button
                            key={s}
                            onClick={() => setSelectedSensor(s)}
                            className="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-white text-sm rounded-lg transition-colors"
                          >
                            Ver: {sensorName}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
                {!is404 && !is400 && (
                  <button
                    onClick={generateReport}
                    className="mt-4 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                  >
                    Reintentar
                  </button>
                )}
              </div>
            );
          })()}

          {report && !generatingAllReports && (
            <div className="space-y-6">
              {/* Header del reporte */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-xl font-bold text-gray-800 mb-1">
                      {report.plataforma || report.reporte_automatico}
                    </h3>
                    <p className="text-gray-600">Fecha de medición: {report.fecha_medicion}</p>
                    {report.fecha_generacion && (
                      <p className="text-sm text-gray-500">
                        Generado: {new Date(report.fecha_generacion).toLocaleString('es-CO', { timeZone: 'America/Bogota' })}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={downloadReport}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                    >
                      <Download size={18} />
                      Descargar JSON
                    </button>
                    {sensors.length > 1 && (
                      <button
                        onClick={generateAllReports}
                        disabled={generatingAllReports}
                        className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Generar y descargar reportes individuales para cada sensor"
                      >
                        {generatingAllReports ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Generando...
                          </>
                        ) : (
                          <>
                            <Download size={18} />
                            Todos los Sensores ({sensors.length})
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Información de la Campaña - Agrupada */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Datos Técnicos */}
                {report.datos_tecnicos && (
                  <div className="border rounded-lg p-5 bg-gradient-to-br from-slate-50 to-gray-50">
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2 text-sm">
                      <BarChart3 size={18} className="text-slate-500" />
                      Datos Técnicos
                    </h4>
                    <div className="space-y-2 text-sm">
                      {report.datos_tecnicos.total_mediciones && (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Total Mediciones:</span>
                          <span className="font-bold text-gray-800">{report.datos_tecnicos.total_mediciones}</span>
                        </div>
                      )}
                      {report.datos_tecnicos.primera_medicion && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs block mb-1">Primera:</span>
                          <span className="font-medium text-gray-800 text-xs">
                            {toColombiaTime(report.datos_tecnicos.primera_medicion)}
                          </span>
                        </div>
                      )}
                      {report.datos_tecnicos.ultima_medicion && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs block mb-1">Última:</span>
                          <span className="font-medium text-gray-800 text-xs">
                            {toColombiaTime(report.datos_tecnicos.ultima_medicion)}
                          </span>
                        </div>
                      )}
                      {report.datos_tecnicos.puntos_fft && (
                        <>
                          <div className="flex justify-between items-center bg-white p-2 rounded">
                            <span className="text-gray-600 text-xs">Puntos FFT:</span>
                            <span className="font-bold text-gray-800">{report.datos_tecnicos.puntos_fft}</span>
                          </div>
                          <div className="flex justify-between items-center bg-white p-2 rounded">
                            <span className="text-gray-600 text-xs">Resolución:</span>
                            <span className="font-bold text-gray-800">
                              {(report.datos_tecnicos.resolucion_hz / 1000).toFixed(2)} kHz
                            </span>
                          </div>
                          <div className="flex justify-between items-center bg-white p-2 rounded">
                            <span className="text-gray-600 text-xs">Frec. Inicio:</span>
                            <span className="font-bold text-gray-800">
                              {(report.datos_tecnicos.frecuencia_inicio_hz / 1e6).toFixed(1)} MHz
                            </span>
                          </div>
                          <div className="flex justify-between items-center bg-white p-2 rounded">
                            <span className="text-gray-600 text-xs">Frec. Fin:</span>
                            <span className="font-bold text-gray-800">
                              {(report.datos_tecnicos.frecuencia_fin_hz / 1e6).toFixed(1)} MHz
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                {/* Ubicación */}
                <div className="border rounded-lg p-5 bg-gradient-to-br from-blue-50 to-indigo-50">
                  <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2 text-sm">
                    <MapPin size={18} className="text-orange-500" />
                    Ubicación
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between items-center bg-white p-2 rounded">
                      <span className="text-gray-600 text-xs">Sensor / Estación:</span>
                      {sensors.length > 0 ? (
                        <div className="flex items-center gap-2">
                           <select
                            value={selectedSensor}
                            onChange={(e) => setSelectedSensor(e.target.value)}
                            className="text-xs font-medium text-gray-800 border border-gray-200 rounded px-2 py-1 bg-gray-50 focus:ring-1 focus:ring-blue-500 focus:outline-none cursor-pointer"
                          >
                            {sensors.map(s => {
                              const sensorName = allSensors?.find(sensor => sensor.mac === s)?.name || s;
                              return (
                                <option key={s} value={s}>{sensorName}</option>
                              );
                            })}
                          </select>
                        </div>
                      ) : (
                         <span className="font-medium text-gray-800">{report.ubicacion.estacion}</span>
                      )}
                    </div>
                    <div className="flex justify-between items-center bg-white p-2 rounded">
                      <span className="text-gray-600 text-xs">Código DANE:</span>
                      <span className="font-medium text-gray-800">{report.ubicacion.codigo_dane}</span>
                    </div>
                    <div className="flex justify-between items-center bg-white p-2 rounded">
                      <span className="text-gray-600 text-xs">Departamento:</span>
                      <span className="font-medium text-gray-800">{report.ubicacion.departamento}</span>
                    </div>
                    <div className="flex justify-between items-center bg-white p-2 rounded">
                      <span className="text-gray-600 text-xs">Municipio:</span>
                      <span className="font-medium text-gray-800">{report.ubicacion.municipio}</span>
                    </div>
                    <div className="bg-white p-2 rounded">
                      <span className="text-gray-600 text-xs block mb-1">Coordenadas:</span>
                      <span className="font-medium text-gray-800 text-xs">
                        {Number(report.ubicacion.coordenadas.latitud).toFixed(6)}, {Number(report.ubicacion.coordenadas.longitud).toFixed(6)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Fecha y Análisis Espectral */}
                {report.analisis_espectral && (
                  <div className="border rounded-lg p-5 bg-gradient-to-br from-purple-50 to-pink-50">
                    <h4 className="font-semibold text-gray-800 mb-3 flex items-center gap-2 text-sm">
                      <Activity size={18} className="text-purple-500" />
                      Análisis Espectral
                    </h4>
                    <div className="space-y-2 text-sm">
                      {report.datos_tecnicos && (
                        <div className="bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs block mb-1">Fecha/Hora:</span>
                          <span className="font-medium text-gray-800 text-xs">
                            {toColombiaTime(report.datos_tecnicos.fecha_hora_medicion)}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between items-center bg-white p-2 rounded">
                        <span className="text-gray-600 text-xs">Modo:</span>
                        <span className="font-bold text-gray-800 capitalize">{report.analisis_espectral.modo}</span>
                      </div>
                      <div className="flex justify-between items-center bg-white p-2 rounded">
                        <span className="text-gray-600 text-xs">Máx. total de Emisiones:</span>
                        <span className="font-bold text-yellow-600">
                          {report.mediciones && report.mediciones.length > 0
                            ? Math.max(...report.mediciones.map(m => m.num_emisiones ?? 0))
                            : report.analisis_espectral.emisiones_detectadas}
                        </span>
                      </div>
                      {report.analisis_espectral.umbral !== undefined ? (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Umbral (Calculado):</span>
                          <span className="font-bold text-purple-600">{report.analisis_espectral.umbral.toFixed(4)} dBm</span>
                        </div>
                      ) : report.analisis_espectral.umbral_db !== undefined && (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Umbral:</span>
                          <span className="font-bold text-purple-600">{report.analisis_espectral.umbral_db} dBm</span>
                        </div>
                      )}
                      {report.analisis_espectral.tolerancia_fc_khz !== undefined && (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Tol. Frecuencia:</span>
                          <span className="font-bold text-gray-800">±{report.analisis_espectral.tolerancia_fc_khz} kHz</span>
                        </div>
                      )}
                      {report.analisis_espectral.tolerancia_bw_khz !== undefined && (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Tol. Ancho Banda:</span>
                          <span className="font-bold text-gray-800">+{report.analisis_espectral.tolerancia_bw_khz} kHz</span>
                        </div>
                      )}
                      {report.analisis_espectral.picos_analizados !== undefined && (
                        <div className="flex justify-between items-center bg-white p-2 rounded">
                          <span className="text-gray-600 text-xs">Picos:</span>
                          <span className="font-bold text-blue-600">{report.analisis_espectral.picos_analizados}</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center bg-white p-2 rounded">
                        <span className="text-gray-600 text-xs">Cumplimiento:</span>
                        <span className={`font-bold ${report.analisis_espectral.cumplimiento_general ? 'text-green-600' : 'text-red-600'}`}>
                          {report.analisis_espectral.cumplimiento_general ? 'SÍ' : 'NO'}
                        </span>
                      </div>
                    </div>
                    {report.analisis_espectral.metodo_deteccion && (
                      <div className="bg-white p-2 rounded text-xs mt-2">
                        <p className="text-gray-700">
                          <span className="font-semibold">Método:</span> {report.analisis_espectral.metodo_deteccion}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* ====== NUEVO: ANÁLISIS PRIORITARIO DE INCUMPLIMIENTOS ====== */}
              {report.mediciones && report.mediciones.length > 0 && (() => {
                // Obtener DANEs disponibles
                const danesDisponibles = Array.from(new Set(
                  report.mediciones.flatMap(m => 
                    m.emisiones.map(e => e.dane_asociado).filter(Boolean)
                  )
                )).sort();

                // Filtrar por DANE seleccionado
                const medicionesFiltradas = report.mediciones.map(med => ({
                  ...med,
                  emisiones: med.emisiones.filter(e => filtroDane === 'todos' || String(e.dane_asociado) === filtroDane)
                }));

                const analisis = analizarEmisiones(medicionesFiltradas);
                const gruposFueraParametros = agruparPorLicencia(analisis.fueraParametros);
                const gruposSinLicencia = agruparPorFrecuencia(analisis.sinLicencia);

                return (
                  <>
                    {/* Selector de Filtro DANE */}
                    {danesDisponibles.length > 1 && (
                      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6 flex items-center gap-4 shadow-sm">
                        <div className="flex items-center gap-2 text-gray-700">
                          <MapPin size={20} className="text-blue-500" />
                          <span className="font-semibold">Filtrar por Código DANE:</span>
                        </div>
                        <select
                          value={filtroDane}
                          onChange={(e) => setFiltroDane(e.target.value)}
                          className="border border-gray-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="todos">Todos los Municipios</option>
                          {danesDisponibles.map(dane => (
                            <option key={String(dane)} value={String(dane)}>
                              {dane} {String(dane) === String(report.ubicacion.codigo_dane) ? '(Principal)' : '(Adyacente)'}
                            </option>
                          ))}
                        </select>
                        <div className="text-sm text-gray-500 ml-auto">
                          Mostrando resultados para: <strong>{filtroDane === 'todos' ? 'Todos' : filtroDane}</strong>
                        </div>
                      </div>
                    )}

                    {/* Resumen Ejecutivo */}
                    <ResumenEjecutivo
                      gruposFueraParametros={gruposFueraParametros}
                      gruposSinLicencia={gruposSinLicencia}
                      maxEmisiones={report.mediciones ? Math.max(...report.mediciones.map((m: any) => m.num_emisiones ?? 0)) : 0}
                    />

                    {/* PRIORIDAD 1: Emisiones Fuera de Parámetros */}
                    <SeccionFueraParametros 
                      grupos={gruposFueraParametros} 
                      tolerancias={{
                        fc_khz: report.analisis_espectral?.tolerancia_fc_khz ?? 100,
                        bw_khz: report.analisis_espectral?.tolerancia_bw_khz ?? 10
                      }}
                    />

                    {/* PRIORIDAD 2: Emisiones Sin Licencia */}
                    <SeccionSinLicencia grupos={gruposSinLicencia} />
                  </>
                );
              })()}

              {/* ====== TABLA COMPLETA DE MEDICIONES (Colapsable) ====== */}
              {report.mediciones && report.mediciones.length > 0 && (
                <details className="border-2 border-gray-300 rounded-lg overflow-hidden">
                  <summary className="cursor-pointer bg-gray-100 hover:bg-gray-200 p-4 font-semibold text-gray-800 flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <BarChart3 size={20} />
                      📋 Ver Todas las Mediciones Detalladas ({report.mediciones.length} adquisiciones)
                    </span>
                    <span className="text-sm text-gray-600">Clic para expandir</span>
                  </summary>
                  <div className="p-4">
                    <MedicionesCompletas 
                      mediciones={report.mediciones} 
                      tolerancias={{
                        fc_khz: report.analisis_espectral?.tolerancia_fc_khz ?? 100,
                        bw_khz: report.analisis_espectral?.tolerancia_bw_khz ?? 10
                      }}
                    />
                  </div>
                </details>
              )}

              {/* LEGACY: Mostrar emisiones si no hay mediciones */}
              {!report.mediciones && report.emisiones && report.emisiones.length > 0 && (
                <>
                  <div className="border rounded-lg p-4 bg-yellow-50">
                    <p className="text-sm text-yellow-800">
                      ⚠️ Este reporte usa formato legacy (sin agrupación por mediciones)
                    </p>
                  </div>
                  <EmisionesDetalladas emisiones={report.emisiones} />
                </>
              )}



              {/* Frecuencias autorizadas */}
              {report.frecuencias_autorizadas_municipio && report.frecuencias_autorizadas_municipio.length > 0 && (
              <div className="border rounded-lg p-6">
                <h4 className="font-semibold text-gray-800 mb-4">
                  Frecuencias Autorizadas en {report.ubicacion.municipio} ({report.frecuencias_autorizadas_municipio.length})
                </h4>
                <div className="overflow-x-auto max-h-96">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 sticky top-0">
                      <tr>
                        <th className="px-4 py-2 text-left">Frecuencia (MHz)</th>
                        <th className="px-4 py-2 text-left">Ancho de Banda</th>
                        <th className="px-4 py-2 text-left">Potencia</th>
                        <th className="px-4 py-2 text-left">Servicio</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {report.frecuencias_autorizadas_municipio.slice(0, 50).map((freq, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-2 font-medium">{freq.frecuencia_mhz.toFixed(2)}</td>
                          <td className="px-4 py-2">
                            {freq.ancho_banda.toFixed(2)} {freq.unidad_ancho_banda}
                          </td>
                          <td className="px-4 py-2">
                            {freq.potencia.toFixed(2)} {freq.unidad_potencia}
                          </td>
                          <td className="px-4 py-2 text-xs">{freq.servicio}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


