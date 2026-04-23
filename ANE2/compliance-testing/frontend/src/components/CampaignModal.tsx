import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { Sensor } from '../services/api';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

interface Antenna {
  id: number;
  name: string;
  type: string;
  frequency_min_hz: number;
  frequency_max_hz: number;
  gain_db: number;
  description: string;
}

interface SensorAntenna {
  sensor_id: number;
  sensor_mac: string;
  antenna_id: number;
  port: number;
}

interface CampaignModalProps {
  sensors: Sensor[];
  onClose: () => void;
  onSave: () => void;
  initialData?: any;
}

export function CampaignModal({ sensors, onClose, onSave, initialData }: CampaignModalProps) {
  // Usar fecha local en lugar de UTC para evitar problemas de zona horaria (UTC-5)
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  
  const [formData, setFormData] = useState({
    name: '',
    startDate: today,
    endDate: today,
    startTime: '',
    endTime: '',
    interval: '120',
    preset: 'custom',
    minFreq: 2,
    maxFreq: 6000,
    centerFrequency: 97.5,
    span: 20,
    rbw: '100000',
    antenna: '1',
    lna_gain: 0,
    vga_gain: 0,
    antenna_amp: true,
    gpsEnabled: false,
    gpsLat: 0,
    gpsLng: 0,
    gpsAlt: 0
  });

  // Cargar datos iniciales si existen
  useEffect(() => {
    if (initialData && initialData.config) {
      const { config, sensor } = initialData;
      setFormData(prev => ({
        ...prev,
        preset: config.preset || 'custom',
        centerFrequency: config.centerFrequency,
        span: config.span,
        rbw: config.rbw.toString(),
        antenna: config.antenna ? config.antenna.replace('RX-', '') : '1',
        lna_gain: config.lna_gain || 0,
        vga_gain: config.vga_gain || 0,
        antenna_amp: config.antenna_amp !== false,
      }));
      
      if (sensor) {
        setSelectedSensors(new Set([sensor]));
      }
    }
  }, [initialData]);

  const [selectedSensors, setSelectedSensors] = useState<Set<string>>(new Set());
  const [antennas, setAntennas] = useState<Antenna[]>([]);
  const [sensorAntennas, setSensorAntennas] = useState<SensorAntenna[]>([]);
  const [errors, setErrors] = useState<{[key: string]: string}>({});
  
  // Estados para filtros de frecuencia
  const [filterEnabled, setFilterEnabled] = useState<boolean>(false);
  const [filterStartFreqMhz, setFilterStartFreqMhz] = useState<number>(87.5);
  const [filterEndFreqMhz, setFilterEndFreqMhz] = useState<number>(107.5);
  
  // Estados para presets (servicio/canal)
  const [presetService, setPresetService] = useState<string>('');
  const [presetChannel, setPresetChannel] = useState<string>('');
  const [demodType, setDemodType] = useState<'AM' | 'FM' | ''>('');
  // const [demodBwHz, setDemodBwHz] = useState<number>(250000); // Unused

  // Datos de presets (copiado de ConfigurationPanel)
  const PRESET_DATA = {
    rmer: {
      VHF: {
        VHF1: { min: 88, max: 108 },
        VHF2: { min: 137, max: 157 },
        VHF3: { min: 148, max: 168 },
        VHF4: { min: 154, max: 174 }
      },
      UHF: {
        UHF1: { min: 400, max: 420 },
        UHF2: { min: 420, max: 440 },
        UHF3: { min: 440, max: 460 },
        UHF4: { min: 450, max: 470 },
        UHF5: { min: 1708, max: 1728 },
        UHF6: { min: 1735, max: 1755 },
        UHF7: { min: 1805, max: 1825 },
        UHF8: { min: 1848, max: 1868 },
        UHF9: { min: 1868, max: 1888 },
        UHF10: { min: 1877, max: 1897 }
      },
      SHF: {
        SHF1: { min: 2550, max: 2570 },
        SHF2: { min: 3295, max: 3315 },
        SHF3: { min: 3338, max: 3358 }
      }
    },
    rmtdt: {
      'Canal 14': { min: 470, max: 476 },
      'Canal 15': { min: 476, max: 482 },
      'Canal 16': { min: 482, max: 488 },
      'Canal 17': { min: 488, max: 494 },
      'Canal 18': { min: 494, max: 500 },
      'Canal 19': { min: 500, max: 506 },
      'Canal 20': { min: 506, max: 512 },
      'Canal 21': { min: 512, max: 518 },
      'Canal 22': { min: 518, max: 524 },
      'Canal 23': { min: 524, max: 530 },
      'Canal 24': { min: 530, max: 536 },
      'Canal 25': { min: 536, max: 542 },
      'Canal 26': { min: 542, max: 548 },
      'Canal 27': { min: 548, max: 554 },
      'Canal 28': { min: 554, max: 560 },
      'Canal 29': { min: 560, max: 566 },
      'Canal 30': { min: 566, max: 572 },
      'Canal 31': { min: 572, max: 578 },
      'Canal 32': { min: 578, max: 584 },
      'Canal 33': { min: 584, max: 590 },
      'Canal 34': { min: 590, max: 596 },
      'Canal 35': { min: 596, max: 602 },
      'Canal 36': { min: 602, max: 608 },
      'Canal 37': { min: 608, max: 614 },
      'Canal 38': { min: 614, max: 620 },
      'Canal 39': { min: 620, max: 626 },
      'Canal 40': { min: 626, max: 632 },
      'Canal 41': { min: 632, max: 638 },
      'Canal 42': { min: 638, max: 644 },
      'Canal 43': { min: 644, max: 650 },
      'Canal 44': { min: 650, max: 656 },
      'Canal 45': { min: 656, max: 662 },
      'Canal 46': { min: 662, max: 668 },
      'Canal 47': { min: 668, max: 674 },
      'Canal 48': { min: 674, max: 680 },
      'Canal 49': { min: 680, max: 686 }
    },
    rni: {
      VHF: {
        VHF1: { min: 88, max: 108 },
        VHF2: { min: 137, max: 157 },
        VHF3: { min: 148, max: 168 },
        VHF4: { min: 154, max: 174 }
      },
      UHF: {
        UHF1: { min: 400, max: 420 },
        UHF2: { min: 420, max: 440 },
        UHF3: { min: 440, max: 460 },
        UHF4: { min: 450, max: 470 },
        UHF5: { min: 1708, max: 1728 },
        UHF6: { min: 1735, max: 1755 },
        UHF7: { min: 1805, max: 1825 },
        UHF8: { min: 1848, max: 1868 },
        UHF9: { min: 1868, max: 1888 },
        UHF10: { min: 1877, max: 1897 }
      },
      SHF: {
        SHF1: { min: 2550, max: 2570 },
        SHF2: { min: 3295, max: 3315 },
        SHF3: { min: 3338, max: 3358 },
        SHF4: { min: 3375, max: 3395 },
        SHF5: { min: 3444, max: 3464 }
      }
    }
  };

  // Cargar antenas y asignaciones al montar el componente
  useEffect(() => {
    const loadData = async () => {
      try {
        // Cargar antenas
        const antennasResponse = await axios.get(`${API_BASE_URL}/antennas`);
        const antennasData = antennasResponse.data;
        setAntennas(antennasData);
        if (antennasData.length > 0) {
          setFormData(prev => ({ ...prev, antenna: antennasData[0].id.toString() }));
        }

        // Cargar asignaciones de antenas a sensores
        const assignmentsPromises = sensors.map(async (sensor) => {
          try {
            const response = await axios.get(`${API_BASE_URL}/sensors/${sensor.id}/antennas`);
            const assignments = response.data;
            return assignments.map((a: any) => ({
              sensor_id: sensor.id,
              sensor_mac: sensor.mac,
              antenna_id: a.id, // El endpoint devuelve el id de la antena como 'id'
              port: a.port
            }));
          } catch (error) {
            console.error(`Error loading antennas for sensor ${sensor.mac}:`, error);
          }
          return [];
        });

        const allAssignments = await Promise.all(assignmentsPromises);
        setSensorAntennas(allAssignments.flat());
      } catch (error) {
        console.error('Error loading data:', error);
      }
    };
    loadData();
  }, [sensors]);

  const calculatePresetParams = (minFreq: number, maxFreq: number) => {
    // Calcular frecuencia central
    const centerFreq = minFreq + (maxFreq - minFreq) / 2;
    
    // Calcular Span/Sample Rate: (max - min) + 0.5 MHz, máximo 20 MHz
    let span = (maxFreq - minFreq) + 0.5;
    if (span > 20) span = 20;
    
    // Actualizar configuración
    setFormData(prev => ({
      ...prev,
      centerFrequency: centerFreq,
      span: span,
      rbw: prev.preset === 'rmtdt' ? '30000' : '1000'
    }));
  };

  const handlePresetChange = (preset: string) => {
    // Limpiar selecciones previas
    setPresetService('');
    setPresetChannel('');
    setDemodType('');
    
    const newFormData = { ...formData, preset };

    // Actualizar preset y resetear valores según el tipo
    if (preset === 'amfm') {
      // AM/FM: configuración fija
      newFormData.centerFrequency = 97.5;
      newFormData.span = 2;
      newFormData.rbw = '1000';
      newFormData.lna_gain = 0;
      newFormData.vga_gain = 40;
      newFormData.antenna_amp = true;
      setFilterEnabled(false);
    } else if (preset === 'custom') {
      // Personalizado: valores predeterminados
      newFormData.centerFrequency = 97.5;
      newFormData.span = 20;
      newFormData.rbw = '100000';
    } else if (preset === 'rmer' || preset === 'rni' || preset === 'rmtdt') {
      // RMER, RNI, RMTDT: resetear a valores por defecto
      newFormData.centerFrequency = 97.5;
      newFormData.span = preset === 'rmtdt' ? 6.5 : 20;
      newFormData.rbw = preset === 'rmtdt' ? '30000' : '1000';
      // No forzamos ganancias para RMER/RMTDT aquí, se mantienen las del usuario o defaults
    }
    
    setFormData(newFormData);
  };

  const handleServiceChange = (service: string) => {
    setPresetService(service);
    setPresetChannel('');
  };

  const handleChannelChange = (channel: string) => {
    setPresetChannel(channel);
    
    // Obtener frecuencias según preset
    let freqData: any = null;
    
    if (formData.preset === 'rmer' || formData.preset === 'rni') {
      const data = formData.preset === 'rmer' ? PRESET_DATA.rmer : PRESET_DATA.rni;
      freqData = (data as any)[presetService]?.[channel];
    } else if (formData.preset === 'rmtdt') {
      freqData = PRESET_DATA.rmtdt[channel as keyof typeof PRESET_DATA.rmtdt];
    }
    
    if (freqData) {
      calculatePresetParams(freqData.min, freqData.max);
    }
  };

  // Validar formulario
  const validateForm = (): boolean => {
    const newErrors: {[key: string]: string} = {};

    // Validar nombre
    if (!formData.name.trim()) {
      newErrors.name = 'El nombre es requerido';
    }

    // Validar que la fecha de inicio no sea anterior a hoy
    const now = new Date();
    // Usar fecha local para validación
    const currentDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    
    if (formData.startDate < currentDate) {
      newErrors.dates = 'La fecha de inicio no puede ser anterior a la fecha actual';
    } else if (formData.startDate === currentDate && formData.startTime) {
      // Si es hoy, validar que la hora de inicio no sea anterior a la hora actual
      const startMinutes = getTimeInMinutes(formData.startTime);
      const currentMinutes = getTimeInMinutes(currentTime);
      
      if (startMinutes < currentMinutes) {
        newErrors.startTime = 'La hora de inicio no puede ser anterior a la hora actual';
      } else if (startMinutes < currentMinutes + 3) {
        // Mínimo 3 minutos de margen para calibración del sensor
        newErrors.startTime = 'La hora de inicio debe ser al menos 3 minutos posterior a la hora actual para permitir la calibración del sensor';
      }
    }

    // Validar fechas
    if (formData.startDate > formData.endDate) {
      newErrors.dates = 'La fecha de inicio no puede ser posterior a la fecha de fin';
    }

    // Validar horas si ambas están definidas
    if (formData.startTime && formData.endTime) {
      const startMinutes = getTimeInMinutes(formData.startTime);
      const endMinutes = getTimeInMinutes(formData.endTime);
      
      // Si es el mismo día, validar que hora inicio < hora fin
      if (formData.startDate === formData.endDate && startMinutes >= endMinutes) {
        newErrors.times = 'La hora de inicio debe ser anterior a la hora de fin';
      }

      // Validar que los minutos sean válidos según la frecuencia
      const intervalMinutes = parseInt(formData.interval) / 60;
      const allowedMinutes = getAllowedMinutes(intervalMinutes);
      
      const startTimeMinutes = parseInt(formData.startTime.split(':')[1]);
      const endTimeMinutes = parseInt(formData.endTime.split(':')[1]);

      if (!allowedMinutes.includes(startTimeMinutes)) {
        newErrors.startTime = `Los minutos deben ser múltiplos de ${intervalMinutes} para la frecuencia seleccionada`;
      }

      if (!allowedMinutes.includes(endTimeMinutes)) {
        newErrors.endTime = `Los minutos deben ser múltiplos de ${intervalMinutes} para la frecuencia seleccionada`;
      }
    }

    // Validar sensores
    if (selectedSensors.size === 0) {
      newErrors.sensors = 'Debe seleccionar al menos un dispositivo';
    }

    // Validar Span para configuración personalizada
    if (formData.preset === 'custom') {
      if (formData.span < 8 || formData.span > 20 || isNaN(formData.span)) {
        newErrors.span = 'El Span debe estar entre 8 y 20 MHz';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const getTimeInMinutes = (time: string): number => {
    const [hours, minutes] = time.split(':').map(Number);
    return hours * 60 + minutes;
  };

  const getAllowedMinutes = (intervalMinutes: number): number[] => {
    const minutes: number[] = [];
    for (let i = 0; i < 60; i++) {
      if (i % intervalMinutes === 0) {
        minutes.push(i);
      }
    }
    return minutes;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const config: any = {
        centerFrequency: formData.centerFrequency,
        span: formData.span,
        rbw: formData.rbw,
        antenna: formData.antenna,
        sample_rate_hz: formData.span * 1e6, // Sample rate siempre igual a span (MHz a Hz)
        lna_gain: formData.lna_gain,
        vga_gain: formData.vga_gain,
        antenna_amp: formData.antenna_amp
      };

      if (formData.preset === 'amfm' && demodType) {
        config.demodulation = demodType.toLowerCase();
      }

      // Agregar filtro si está habilitado
      if (filterEnabled) {
        config.filter = {
          start_freq_hz: Math.round(filterStartFreqMhz * 1e6),
          end_freq_hz: Math.round(filterEndFreqMhz * 1e6)
        };
      }

      // Agregar configuración GPS manual si está habilitada
      if (formData.gpsEnabled) {
        config.gps = {
          lat: formData.gpsLat,
          lng: formData.gpsLng,
          alt: formData.gpsAlt
        };
      }

      const campaign = {
        name: formData.name,
        start_date: formData.startDate,
        end_date: formData.endDate,
        start_time: formData.startTime,
        end_time: formData.endTime,
        interval_seconds: parseInt(formData.interval),
        start_freq_mhz: formData.centerFrequency - formData.span / 2,
        end_freq_mhz: formData.centerFrequency + formData.span / 2,
        bandwidth_mhz: formData.span,
        resolution_khz: parseFloat(formData.rbw) / 1000,
        sensors: Array.from(selectedSensors),
        preset: formData.preset,
        config: config
      };

      await axios.post(`${API_BASE_URL}/campaigns`, campaign);

      alert('Campaña programada exitosamente');
      onSave();
    } catch (error: any) {
      console.error('Error:', error);
      if (error.response && error.response.data && error.response.data.error) {
        alert(error.response.data.error);
      } else {
        alert('Error al programar la campaña');
      }
    }
  };

  const toggleSensor = (mac: string) => {
    const newSelected = new Set(selectedSensors);
    if (newSelected.has(mac)) {
      newSelected.delete(mac);
    } else {
      newSelected.add(mac);
    }
    setSelectedSensors(newSelected);
    // Limpiar error de sensores si se selecciona alguno
    if (newSelected.size > 0 && errors.sensors) {
      setErrors(prev => {
        const newErrors = {...prev};
        delete newErrors.sensors;
        return newErrors;
      });
    }
  };

  // Filtrar sensores según la antena seleccionada en configuración
  const selectedAntennaId = parseInt(formData.antenna);
  console.log('🔍 Debug filtro de sensores:');
  console.log('  selectedAntennaId:', selectedAntennaId);
  console.log('  sensorAntennas:', sensorAntennas);
  console.log('  sensors disponibles:', sensors.length);
  
  const filteredSensors = sensors.filter(s => 
    sensorAntennas.some(sa => {
      const match = sa.sensor_mac === s.mac && sa.antenna_id === selectedAntennaId;
      if (match) {
        console.log(`  ✅ Match: sensor ${s.mac} tiene antena ${selectedAntennaId} en puerto ${sa.port}`);
      }
      return match;
    })
  );
  
  console.log('  filteredSensors:', filteredSensors.length);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-bold text-gray-800">Programar campaña</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-full">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 flex gap-6">
          {/* Formulario izquierdo */}
          <div className="flex-1 space-y-4">
            {/* Nombre */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre de la campaña
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => {
                  setFormData({ ...formData, name: e.target.value });
                  if (e.target.value.trim() && errors.name) {
                    setErrors(prev => {
                      const newErrors = {...prev};
                      delete newErrors.name;
                      return newErrors;
                    });
                  }
                }}
                placeholder="Nombre asignado para identificar la campaña de medición."
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                  errors.name ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                }`}
              />
              {errors.name && (
                <p className="text-xs text-red-600 mt-1">{errors.name}</p>
              )}
            </div>

            {/* Rango de fecha */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ingrese un rango de fecha
              </label>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-600 mb-1">Fecha de inicio</label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => {
                      setFormData({ ...formData, startDate: e.target.value });
                      if (errors.dates || errors.startTime) {
                        setErrors(prev => {
                          const newErrors = {...prev};
                          delete newErrors.dates;
                          delete newErrors.startTime;
                          return newErrors;
                        });
                      }
                    }}
                    min={today}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                      errors.dates ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">Fecha de fin</label>
                  <input
                    type="date"
                    value={formData.endDate}
                    onChange={(e) => {
                      setFormData({ ...formData, endDate: e.target.value });
                      if (errors.dates) {
                        setErrors(prev => {
                          const newErrors = {...prev};
                          delete newErrors.dates;
                          return newErrors;
                        });
                      }
                    }}
                    min={formData.startDate}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                      errors.dates ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                </div>
              </div>
              {errors.dates && (
                <p className="text-xs text-red-600 mt-1">{errors.dates}</p>
              )}
              <p className="text-xs text-gray-500 mt-1">Período durante el cual se realizará la campaña de medición</p>
            </div>

            {/* Frecuencia de adquisición */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Frecuencia de adquisición
              </label>
              <select
                value={formData.interval}
                onChange={(e) => {
                  setFormData({ ...formData, interval: e.target.value, startTime: '', endTime: '' });
                  // Limpiar errores de tiempo al cambiar la frecuencia
                  setErrors(prev => {
                    const newErrors = {...prev};
                    delete newErrors.startTime;
                    delete newErrors.endTime;
                    delete newErrors.times;
                    return newErrors;
                  });
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="120">Cada 2 minutos</option>
                <option value="300">Cada 5 minutos</option>
                <option value="600">Cada 10 minutos</option>
                <option value="1200">Cada 20 minutos</option>
                <option value="1800">Cada 30 minutos</option>
                <option value="3600">Cada 60 minutos</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">Intervalo de tiempo entre mediciones consecutivas. Los minutos de inicio/fin deben ser múltiplos de esta frecuencia.</p>
            </div>

            {/* Horas */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hora de inicio
                </label>
                <input
                  type="time"
                  value={formData.startTime}
                  onChange={(e) => {
                    setFormData({ ...formData, startTime: e.target.value });
                    if (errors.startTime || errors.times) {
                      setErrors(prev => {
                        const newErrors = {...prev};
                        delete newErrors.startTime;
                        delete newErrors.times;
                        return newErrors;
                      });
                    }
                  }}
                  placeholder="Hora de comienzo de las mediciones"
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    errors.startTime || errors.times ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {errors.startTime && (
                  <p className="text-xs text-red-600 mt-1">{errors.startTime}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Hora de finalización
                </label>
                <input
                  type="time"
                  value={formData.endTime}
                  onChange={(e) => {
                    setFormData({ ...formData, endTime: e.target.value });
                    if (errors.endTime || errors.times) {
                      setErrors(prev => {
                        const newErrors = {...prev};
                        delete newErrors.endTime;
                        delete newErrors.times;
                        return newErrors;
                      });
                    }
                  }}
                  placeholder="Hora de finalización de las mediciones"
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    errors.endTime || errors.times ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {errors.endTime && (
                  <p className="text-xs text-red-600 mt-1">{errors.endTime}</p>
                )}
              </div>
            </div>
            {errors.times && (
              <p className="text-xs text-red-600 -mt-2">{errors.times}</p>
            )}
            <p className="text-xs text-gray-500 -mt-2">
              Los minutos deben ser múltiplos de {parseInt(formData.interval) / 60}. 
              Ej: {getAllowedMinutes(parseInt(formData.interval) / 60).slice(0, 5).map(m => String(m).padStart(2, '0')).join(', ')}...
            </p>

            {/* Configuración espectral */}
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Configuración espectral</h3>
              
              {/* Preajustes */}
              <div className="mb-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">Preajustes</label>
                <select
                  value={formData.preset}
                  onChange={(e) => handlePresetChange(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="custom">Personalizado</option>
                  <option value="rmer">RMER</option>
                  <option value="rmtdt">RMTDT</option>
                  <option value="rni">RNI</option>
                  {/* <option value="amfm">AM/FM</option> */}
                </select>
                <p className="text-xs text-gray-500 mt-1">Configuraciones preestablecidas para la programación de la campaña</p>
              </div>

              {/* Submenús para RMER (y RNI si estuviera activo) */}
              {(formData.preset === 'rmer' || formData.preset === 'rni') && (
                <>
                  <div className="mb-3">
                    <label className="block text-xs font-medium text-gray-700 mb-1">Servicio</label>
                    <select
                      value={presetService}
                      onChange={(e) => handleServiceChange(e.target.value)}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="">Seleccione servicio...</option>
                      <option value="VHF">VHF</option>
                      <option value="UHF">UHF</option>
                      <option value="SHF">SHF</option>
                    </select>
                  </div>
                  
                  {presetService && (
                    <div className="mb-3">
                      <label className="block text-xs font-medium text-gray-700 mb-1">Canal / Notación</label>
                      <select
                        value={presetChannel}
                        onChange={(e) => handleChannelChange(e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Seleccione canal...</option>
                        {Object.keys((formData.preset === 'rmer' ? PRESET_DATA.rmer : PRESET_DATA.rni)[presetService as keyof typeof PRESET_DATA.rmer] || {}).map(channel => (
                          <option key={channel} value={channel}>{channel}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </>
              )}

              {/* Submenú para RMTDT */}
              {formData.preset === 'rmtdt' && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Canal</label>
                  <select
                    value={presetChannel}
                    onChange={(e) => handleChannelChange(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccione canal...</option>
                    {Object.keys(PRESET_DATA.rmtdt)
                      .sort((a, b) => {
                        const numA = parseInt(a.replace('Canal ', ''));
                        const numB = parseInt(b.replace('Canal ', ''));
                        return numA - numB;
                      })
                      .map(channel => (
                        <option key={channel} value={channel}>{channel}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Selector AM/FM */}
              {formData.preset === 'amfm' && (
                <div className="mb-3">
                  <label className="block text-xs font-medium text-gray-700 mb-1">Tipo de Modulación</label>
                  <select
                    value={demodType}
                    onChange={(e) => setDemodType(e.target.value as 'AM' | 'FM')}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Seleccione tipo...</option>
                    <option value="AM">AM (Amplitude Modulation)</option>
                    <option value="FM">FM (Frequency Modulation)</option>
                  </select>
                </div>
              )}

              {/* Rangos de frecuencia (Unificado para todos los presets soportados) */}
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Frecuencia Central
                  </label>
                  <div className="flex">
                    <input
                      type="number"
                      value={formData.centerFrequency}
                      onChange={(e) => setFormData({ ...formData, centerFrequency: parseFloat(e.target.value) })}
                      min="1"
                      max="6000"
                      step="0.1"
                      disabled={formData.preset !== 'custom' && formData.preset !== 'amfm'}
                      className={`w-full px-2 py-1 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                        (formData.preset !== 'custom' && formData.preset !== 'amfm') ? 'bg-gray-100 cursor-not-allowed' : ''
                      }`}
                    />
                    <span className="px-2 py-1 bg-gray-100 border border-l-0 border-gray-300 rounded-r-md text-xs">
                      MHz
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formData.preset !== 'custom' && formData.preset !== 'amfm' ? 'Calculado automáticamente' : '1 MHz - 6 GHz'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Span / Sample Rate
                  </label>
                  <div className="flex">
                    <input
                      type="number"
                      value={formData.span}
                      onChange={(e) => {
                        let val = parseFloat(e.target.value);
                        // Si es NaN (input vacío), permitimos para que el usuario pueda borrar y escribir
                        if (isNaN(val)) {
                          setFormData({ ...formData, span: 0 }); // 0 temporalmente
                          return;
                        }
                        // Clamp máximo inmediato para UX (solo si es custom)
                        if (formData.preset === 'custom' && val > 20) val = 20;
                        
                        setFormData({ ...formData, span: val });
                        
                        // Limpiar error si el valor es válido
                        if (formData.preset === 'custom' && val >= 8 && val <= 20 && errors.span) {
                          setErrors(prev => {
                            const newErrors = {...prev};
                            delete newErrors.span;
                            return newErrors;
                          });
                        }
                      }}
                      onBlur={() => {
                        // Clamp mínimo al perder el foco (solo si es custom)
                        if (formData.preset === 'custom') {
                          if (formData.span < 8) {
                            setFormData(prev => ({ ...prev, span: 8 }));
                          } else if (formData.span > 20) {
                             // Redundante pero seguro
                            setFormData(prev => ({ ...prev, span: 20 }));
                          }
                        }
                      }}
                      min="8"
                      max="20"
                      step="0.1"
                      disabled={formData.preset === 'rmtdt' || formData.preset === 'amfm'}
                      className={`w-full px-2 py-1 text-sm border rounded-l-md focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                        (formData.preset === 'rmtdt' || formData.preset === 'amfm') 
                          ? 'bg-gray-100 cursor-not-allowed border-gray-300' 
                          : (errors.span ? 'border-red-500 focus:ring-red-500' : 'border-gray-300')
                      }`}
                    />
                    <span className={`px-2 py-1 bg-gray-100 border border-l-0 rounded-r-md text-xs ${errors.span ? 'border-red-500' : 'border-gray-300'}`}>
                      MHz
                    </span>
                  </div>
                  {errors.span && (
                    <p className="text-xs text-red-600 mt-0.5">{errors.span}</p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formData.preset === 'rmtdt' 
                      ? 'Span fijo: 6.5 MHz' 
                      : (formData.preset === 'amfm' ? 'Span fijo: 2 MHz' : '8 - 20 MHz')}
                  </p>
                </div>
              </div>

              {/* Ganancias LNA y VGA en la misma línea */}
              <div className="grid grid-cols-2 gap-3 mb-3">
                {/* Ganancia LNA */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    LNA Gain: {formData.lna_gain} dB
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="40"
                    step="8"
                    value={formData.lna_gain}
                    onChange={(e) => setFormData({ ...formData, lna_gain: parseInt(e.target.value) })}
                    disabled={formData.preset === 'amfm'}
                    className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 ${
                      formData.preset === 'amfm' ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0</span>
                    <span>8</span>
                    <span>16</span>
                    <span>24</span>
                    <span>32</span>
                    <span>40</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Amplificador de bajo ruido</p>
                </div>

                {/* Ganancia VGA */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-2">
                    VGA Gain: {formData.vga_gain} dB
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="62"
                    step="2"
                    value={formData.vga_gain}
                    onChange={(e) => setFormData({ ...formData, vga_gain: parseInt(e.target.value) })}
                    disabled={formData.preset === 'amfm'}
                    className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 ${
                      formData.preset === 'amfm' ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>0</span>
                    <span>16</span>
                    <span>32</span>
                    <span>48</span>
                    <span>62</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Amplificador de ganancia variable</p>
                </div>
              </div>

              {/* Antenna Amp debajo de LNA y VGA */}
              <div className="mb-3">
                <label className={`flex items-center gap-2 cursor-pointer ${formData.preset === 'amfm' ? 'opacity-50 cursor-not-allowed' : ''}`}>
                  <input
                    type="checkbox"
                    checked={formData.antenna_amp}
                    onChange={(e) => setFormData({ ...formData, antenna_amp: e.target.checked })}
                    disabled={formData.preset === 'amfm'}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="text-sm font-medium text-gray-700">Antenna Amp</span>
                </label>
                <p className="text-xs text-gray-500 mt-1">Amplificador externo de antena (activado por defecto)</p>
              </div>

              {/* Resolución (RBW) */}
              <div className="mb-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">Resolución (RBW)</label>
                <select
                  value={formData.rbw}
                  onChange={(e) => setFormData({ ...formData, rbw: e.target.value })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="1000">1 kHz</option>
                  <option value="3000">3 kHz</option>
                  <option value="10000">10 kHz</option>
                  <option value="30000">30 kHz</option>
                  <option value="100000">100 kHz</option>
                  <option value="1000000">1 MHz</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">Resolución espectral de la medición (ancho de banda del filtro)</p>
              </div>

              {/* Configuración de antena */}
              <div className="mb-3">
                <h4 className="text-xs font-semibold text-gray-700 mb-2">Configuración de antena</h4>
                <select
                  value={formData.antenna}
                  onChange={(e) => setFormData({ ...formData, antenna: e.target.value })}
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {antennas.map((antenna) => (
                    <option key={antenna.id} value={antenna.id}>
                      {antenna.name} ({(antenna.frequency_min_hz / 1000000).toFixed(0)}-{(antenna.frequency_max_hz / 1000000).toFixed(0)} MHz)
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Selecciona la antena que se usará durante la campaña de medición</p>
              </div>

              {/* Filtro de Frecuencias - Slider doble igual que en ConfigurationPanel */}
              <div className="mb-3 border-t pt-3">
                <label className="flex items-center gap-2 cursor-pointer mb-2">
                  <input
                    type="checkbox"
                    checked={filterEnabled}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setFilterEnabled(enabled);
                      if (enabled) {
                        // Inicializar con el rango completo
                        const minFreq = formData.centerFrequency - formData.span / 2;
                        const maxFreq = formData.centerFrequency + formData.span / 2;
                        setFilterStartFreqMhz(minFreq);
                        setFilterEndFreqMhz(maxFreq);
                      }
                    }}
                    className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                  />
                  <span className="text-sm font-medium text-gray-700">Habilitar Filtro de Frecuencias</span>
                </label>

                {filterEnabled && (
                  <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-md">
                    {/* Título con rango actual */}
                    <label className="block text-xs font-medium text-gray-700 mb-3 text-center">
                      Rango: {filterStartFreqMhz.toFixed(2)} - {filterEndFreqMhz.toFixed(2)} MHz
                    </label>
                    
                    {/* Slider doble estilo range */}
                    <div className="relative h-10 mb-3">
                      {/* Track base */}
                      <div className="absolute top-1/2 transform -translate-y-1/2 w-full h-2 bg-gray-200 rounded-full pointer-events-none"></div>
                      
                      {/* Track activo (entre los dos valores) */}
                      <div 
                        className="absolute top-1/2 transform -translate-y-1/2 h-2 bg-blue-500 rounded-full pointer-events-none"
                        style={{
                          left: `${((filterStartFreqMhz - (formData.centerFrequency - formData.span / 2)) / formData.span) * 100}%`,
                          width: `${((filterEndFreqMhz - filterStartFreqMhz) / formData.span) * 100}%`
                        }}
                      ></div>
                      
                      {/* Slider izquierdo (start) - Posicionado arriba */}
                      <input
                        type="range"
                        min={(formData.centerFrequency - formData.span / 2).toFixed(2)}
                        max={(formData.centerFrequency + formData.span / 2).toFixed(2)}
                        step="0.25"
                        value={filterStartFreqMhz}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          if (value < filterEndFreqMhz - 0.25) {
                            setFilterStartFreqMhz(value);
                          }
                        }}
                        className="range-slider-start absolute w-full top-0"
                        style={{ 
                          zIndex: 5,
                          pointerEvents: 'auto'
                        }}
                      />
                      
                      {/* Slider derecho (end) - Posicionado abajo */}
                      <input
                        type="range"
                        min={(formData.centerFrequency - formData.span / 2).toFixed(2)}
                        max={(formData.centerFrequency + formData.span / 2).toFixed(2)}
                        step="0.25"
                        value={filterEndFreqMhz}
                        onChange={(e) => {
                          const value = parseFloat(e.target.value);
                          if (value > filterStartFreqMhz + 0.25) {
                            setFilterEndFreqMhz(value);
                          }
                        }}
                        className="range-slider-end absolute w-full bottom-0"
                        style={{ 
                          zIndex: 5,
                          pointerEvents: 'auto'
                        }}
                      />
                    </div>
                    
                    {/* Información de frecuencias en lugar de "Límites" */}
                    <div className="flex justify-between items-center text-xs text-gray-600 px-1">
                      <div>
                        <span className="text-gray-500">Inicial:</span>
                        <span className="font-medium ml-1">{filterStartFreqMhz.toFixed(2)} MHz</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Final:</span>
                        <span className="font-medium ml-1">{filterEndFreqMhz.toFixed(2)} MHz</span>
                      </div>
                    </div>
                    
                    <p className="text-xs text-gray-400 mt-2 text-center">
                      Rango disponible: {(formData.centerFrequency - formData.span / 2).toFixed(2)} - {(formData.centerFrequency + formData.span / 2).toFixed(2)} MHz
                    </p>
                  </div>
                )}
              </div>

              {/* GPS - Configuración manual */}
              <div className="border-t pt-4 mt-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold text-gray-700">GPS - Configuración manual</h4>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.gpsEnabled}
                      onChange={(e) => setFormData({ ...formData, gpsEnabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                
                {formData.gpsEnabled && (
                  <div className="space-y-3 bg-blue-50 p-3 rounded-lg border border-blue-200">
                    <p className="text-xs text-blue-700 mb-2">
                      📍 Estas coordenadas serán enviadas al sensor durante la campaña
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Latitud *
                        </label>
                        <input
                          type="number"
                          step="any"
                          value={formData.gpsLat}
                          onChange={(e) => setFormData({ ...formData, gpsLat: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="4.7110"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Longitud *
                        </label>
                        <input
                          type="number"
                          step="any"
                          value={formData.gpsLng}
                          onChange={(e) => setFormData({ ...formData, gpsLng: parseFloat(e.target.value) || 0 })}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                          placeholder="-74.0721"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Altitud (metros)
                      </label>
                      <input
                        type="number"
                        step="any"
                        value={formData.gpsAlt}
                        onChange={(e) => setFormData({ ...formData, gpsAlt: parseFloat(e.target.value) || 0 })}
                        className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
                        placeholder="2640"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Panel derecho - Selección de dispositivos */}
          <div className="w-96 border-l pl-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Seleccionar dispositivos para la campaña
            </h3>

            {/* Lista de dispositivos */}
            <div className="space-y-2 max-h-48 overflow-y-auto border rounded p-2">
                {sensors.filter(s =>
                  sensorAntennas.some(sa => sa.sensor_mac === s.mac && sa.antenna_id.toString() === formData.antenna)
                ).length > 0 ? (
                  sensors
                    .filter(s =>
                      sensorAntennas.some(sa => sa.sensor_mac === s.mac && sa.antenna_id.toString() === formData.antenna)
                    )
                    .map((sensor) => {
                      const statusColors: Record<string, string> = {
                        online: 'text-green-600',
                        active: 'text-green-600',
                        busy: 'text-yellow-600',
                        delay: 'text-yellow-600',
                        offline: 'text-gray-500',
                        inactive: 'text-gray-500',
                        error: 'text-red-600',
                      };
                      const dotColors: Record<string, string> = {
                        online: 'bg-green-500',
                        active: 'bg-green-500',
                        busy: 'bg-yellow-500',
                        delay: 'bg-yellow-500',
                        offline: 'bg-gray-400',
                        inactive: 'bg-gray-400',
                        error: 'bg-red-500',
                      };
                      const statusColor = statusColors[sensor.status] ?? 'text-gray-500';
                      const dotColor = dotColors[sensor.status] ?? 'bg-gray-400';
                      return (
                    <label
                      key={sensor.id}
                      className={`flex items-center justify-between p-2 rounded cursor-pointer transition-colors ${
                        selectedSensors.has(sensor.mac)
                          ? 'bg-blue-50 border border-blue-200'
                          : 'hover:bg-gray-50 border border-transparent'
                      }`}
                    >
                      <div>
                        <div className="font-medium text-gray-800">{sensor.name}</div>
                        <div className="text-xs text-gray-500">{sensor.mac}</div>
                        <div className={`text-xs flex items-center gap-1 ${statusColor}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`}></span>
                          {sensor.status}
                        </div>
                      </div>
                      <input
                        type="checkbox"
                        checked={selectedSensors.has(sensor.mac)}
                        onChange={() => toggleSensor(sensor.mac)}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                      />
                    </label>
                  );
                })
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p className="text-sm">No hay dispositivos disponibles con esta antena</p>
                </div>
              )}
            </div>

            <div className="text-sm text-gray-600">
              Se han seleccionado <strong>{selectedSensors.size}</strong> dispositivo{selectedSensors.size !== 1 ? 's' : ''}.
            </div>
            {errors.sensors && (
              <p className="text-xs text-red-600 mt-1">{errors.sensors}</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!formData.name || selectedSensors.size === 0}
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Programar campaña
          </button>
        </div>
      </div>
    </div>
  );
}
