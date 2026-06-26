import { useEffect, useState, useRef } from 'react';
import { sensorAPI, Sensor } from '../services/api';
import { Play, Square, Loader2, ChevronDown, ChevronUp, AlertTriangle, Plus } from 'lucide-react';
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
  port?: number; // Puerto al que está conectada la antena
}

interface ConfigurationPanelProps {
  config: {
    sampleRate: number;
    rbw: string | number;
    vbw?: string | number;
    centerFrequency: number;
    bandwidth: number;
    span: number;
    device: string;
    antenna: string;
    antennaGain?: number;
    startFrequency: number;
    endFrequency: number;
    preset: string;
  };
  onConfigChange: (config: any) => void;
  onDemodTypeChange?: (type: 'AM' | 'FM' | '') => void;
  isMonitoring?: boolean;
  onMonitoringChange?: (isActive: boolean, selectedSensor: string | null) => void;
  onLiveConfigUpdate?: () => void; // Notificar cuando se actualizan parámetros durante adquisición activa
  onWaterfallResetRequested?: () => void; // Solicitar reset de waterfall solo cuando el usuario confirma con Enter
  maxMonitoringTime?: number; // Tiempo máximo en minutos
  onCreateCampaign?: (config: any) => void;
  sensors?: Sensor[];
}

// Datos de la tabla de frecuencias
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

export function ConfigurationPanel({ 
  config, 
  onConfigChange, 
  onDemodTypeChange,
  isMonitoring = false,
  onMonitoringChange,
  onLiveConfigUpdate,
  onWaterfallResetRequested,
  maxMonitoringTime = 10, // Default 10 minutos
  onCreateCampaign,
  sensors: propSensors
}: ConfigurationPanelProps) {
  const [internalSensors, setInternalSensors] = useState<Sensor[]>([]);
  const [selectedSensor, setSelectedSensor] = useState<string>('');
  const [isStarting, setIsStarting] = useState(false);
  const [loading, setLoading] = useState(false); // Default false si usamos props
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [presetService, setPresetService] = useState<string>('');
  const [presetChannel, setPresetChannel] = useState<string>('');
  const [demodType, setDemodType] = useState<'AM' | 'FM' | ''>('');
  const [antennas, setAntennas] = useState<Antenna[]>([]);
  const [remainingTime, setRemainingTime] = useState<number>(0);
  const [validationError, setValidationError] = useState<string>('');
  
  // Estado local para Span (para evitar problemas con el estado padre)
  const [localSpan, setLocalSpan] = useState<number>(config.span);
  
  // Filtros: ahora usa start_freq_hz y end_freq_hz (slider doble)
  const [filterEnabled, setFilterEnabled] = useState<boolean>(false);
  const [filterStartFreqMhz, setFilterStartFreqMhz] = useState<number>(87.5); // Frecuencia inicial del filtro
  const [filterEndFreqMhz, setFilterEndFreqMhz] = useState<number>(107.5); // Frecuencia final del filtro

  // Sincronizar localSpan con config.span cuando cambia el preset
  useEffect(() => {
    setLocalSpan(config.span);
  }, [config.preset]);

  // Actualizar rangos del filtro cuando cambien centerFrequency o span
  // Ref para guardar el estado previo del filtro
  const prevFilterEnabledRef = useRef(filterEnabled);

  useEffect(() => {
    const minFreq = config.centerFrequency - config.span / 2;
    const maxFreq = config.centerFrequency + config.span / 2;
    
    // Solo ajustar si el filtro ya estaba habilitado y cambió el span/centro
    // NO ajustar cuando se habilita por primera vez (eso lo maneja el onChange del checkbox)
    if (filterEnabled && prevFilterEnabledRef.current) {
      if (filterStartFreqMhz < minFreq) {
        setFilterStartFreqMhz(minFreq);
      }
      if (filterEndFreqMhz > maxFreq) {
        setFilterEndFreqMhz(maxFreq);
      }
    }
    // Si está deshabilitado, NO hacer nada (mantener los valores previos)
    
    prevFilterEnabledRef.current = filterEnabled;
  }, [config.centerFrequency, config.span, filterEnabled]);

  // Usar sensores pasados por props (filtrados) o carga interna
  const sensors = (propSensors || internalSensors).filter(s => s.status_admin !== 'inactive');

  useEffect(() => {
    // Si no vienen sensores por props, cargarlos
    if (!propSensors) {
      loadSensors();
    }
  }, [propSensors]);

  // Seleccionar el primer sensor disponible si no hay uno seleccionado
  useEffect(() => {
    // No auto-seleccionar: el usuario debe elegir manualmente
  }, [sensors]);

  // Cargar antenas cuando cambia el sensor seleccionado
  useEffect(() => {
    if (selectedSensor) {
      loadAntennasBySensor(selectedSensor);
    }
  }, [selectedSensor]);

  const loadSensors = async () => {
    try {
      setLoading(true);
      const data = await sensorAPI.getAll();
      // Guardar todos, el filtro se hace en la constante 'sensors'
      setInternalSensors(data);
    } catch (error) {
      console.error('Error loading sensors:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAntennasBySensor = async (mac: string) => {
    try {
      // Primero obtener el ID del sensor desde la MAC
      const sensor = sensors.find(s => s.mac === mac);
      if (!sensor || !sensor.id) {
        console.warn('Sensor no encontrado o sin ID:', mac);
        setAntennas([]);
        return;
      }

      // Obtener las antenas asignadas a este sensor
      const response = await axios.get(`${API_BASE_URL}/sensors/${sensor.id}/antennas`);
      const data = response.data;
      console.log(`📡 Antenas cargadas para sensor ${mac}:`, data);
      setAntennas(data);
      
      // SOLO establecer antena por defecto si NO hay ninguna seleccionada aún
      // Si ya hay una antena seleccionada, NUNCA sobrescribirla
      if (data.length > 0 && !config.antenna) {
        console.log(`📡 Estableciendo antena inicial: RX-${data[0].port}`);
        handleChange('antenna', `RX-${data[0].port}`);
      } else if (config.antenna) {
        console.log(`📡 Manteniendo antena ya seleccionada: ${config.antenna}`);
      }
    } catch (error) {
      console.error('Error loading antennas:', error);
      setAntennas([]);
    }
  };

  const handleChange = (field: string, value: any) => {
    onConfigChange({ ...config, [field]: value });
  };

  // Validar y actualizar frecuencia central
  const handleCenterFrequencyChange = (value: string) => {
    const numValue = parseFloat(value);
    
    // Permitir campo vacío mientras se escribe
    if (value === '' || value === '-') {
      handleChange('centerFrequency', value);
      return;
    }
    
    // Validar rango: 1 MHz - 6000 MHz
    if (!isNaN(numValue)) {
      if (numValue < 1) {
        handleChange('centerFrequency', 1);
      } else if (numValue > 6000) {
        handleChange('centerFrequency', 6000);
      } else {
        handleChange('centerFrequency', numValue);
      }
    }
  };

  const calculatePresetParams = (minFreq: number, maxFreq: number) => {
    // Calcular frecuencia central
    const centerFreq = minFreq + (maxFreq - minFreq) / 2;
    
    // Calcular Span/Sample Rate: (max - min) + 0.5 MHz, máximo 20 MHz
    let span = (maxFreq - minFreq) + 0.5;
    if (span > 20) span = 20;
    
    // Actualizar configuración
    onConfigChange({
      ...config,
      centerFrequency: centerFreq,
      span: span,
      sampleRate: span,
      rbw: config.preset === 'rmtdt' ? '30000' : '1000',
      antenna: config.antenna, // Preservar la antena seleccionada
      antennaGain: config.antennaGain // Preservar la ganancia
    });
  };

  const handlePresetChange = (preset: string) => {
    // Limpiar selecciones previas
    setPresetService('');
    setPresetChannel('');
    setDemodType('');
    
    // Actualizar preset y resetear valores según el tipo
    if (preset === 'amfm') {
      // AM/FM: configuración fija
      // LNA ajustable (por defecto 0), VGA fijo 40, SPAN fijo 2 MHz, Antena amp true
      onConfigChange({
        ...config,
        preset: 'amfm',
        centerFrequency: 97.5,
        span: 2,
        sampleRate: 2,
        rbw: '10000', // Cambiado de 1000 (1 KHz) a 10000 (10 KHz)
        lna_gain: 0,
        vga_gain: 40,
        antenna_amp: true,
        antenna: config.antenna, // Preservar la antena seleccionada
        antennaGain: config.antennaGain // Preservar la ganancia
      });
      // Asegurar que el filtro esté deshabilitado
      setFilterEnabled(false);
    } else if (preset === 'custom') {
      // Personalizado: valores predeterminados
      onConfigChange({
        ...config,
        preset: 'custom',
        centerFrequency: 97.5,
        span: 20,
        sampleRate: 20,
        rbw: '100000',
        antenna: config.antenna, // Preservar la antena seleccionada
        antennaGain: config.antennaGain // Preservar la ganancia
      });
    } else if (preset === 'rmer' || preset === 'rni' || preset === 'rmtdt') {
      // RMER, RNI, RMTDT: resetear a valores por defecto (se actualizarán al seleccionar servicio/canal)
      onConfigChange({
        ...config,
        preset: preset,
        centerFrequency: 97.5,
        span: preset === 'rmtdt' ? 6.5 : 20,
        sampleRate: preset === 'rmtdt' ? 6.5 : 20,
        rbw: preset === 'rmtdt' ? '30000' : '1000',
        antenna: config.antenna, // Preservar la antena seleccionada
        antennaGain: config.antennaGain // Preservar la ganancia
      });
    } else {
      // Otros casos: solo cambiar el preset
      handleChange('preset', preset);
    }
  };

  const handleServiceChange = (service: string) => {
    setPresetService(service);
    setPresetChannel('');
  };

  const handleChannelChange = (channel: string) => {
    setPresetChannel(channel);
    
    // Obtener frecuencias según preset
    let freqData: any = null;
    
    if (config.preset === 'rmer' || config.preset === 'rni') {
      const data = config.preset === 'rmer' ? PRESET_DATA.rmer : PRESET_DATA.rni;
      freqData = (data as any)[presetService]?.[channel];
    } else if (config.preset === 'rmtdt') {
      freqData = PRESET_DATA.rmtdt[channel as keyof typeof PRESET_DATA.rmtdt];
    }
    
    if (freqData) {
      calculatePresetParams(freqData.min, freqData.max);
    }
  };

  const handleDemodTypeChange = (type: 'AM' | 'FM') => {
    setDemodType(type);
    if (onDemodTypeChange) {
      onDemodTypeChange(type);
    }
  };

  // Validar disponibilidad del sensor
  const validateSensorAvailability = async (sensorMac: string): Promise<{ available: boolean; message: string }> => {
    try {
      // 1. Verificar si el sensor está ejecutando una medición actualmente
      try {
        const statusResponse = await axios.get(`${API_BASE_URL}/sensor/${sensorMac}/status`);
        if (statusResponse.data.is_measuring) {
          return {
            available: false,
            message: 'El sensor está ejecutando una medición actualmente. Debe finalizar antes de iniciar una nueva adquisición.'
          };
        }
      } catch (error) {
        console.error('Error checking sensor status:', error);
      }

      // 2. Verificar si está programado en una campaña próxima o activa
      try {
        const campaignsResponse = await axios.get(`${API_BASE_URL}/campaigns`);
        const campaigns = campaignsResponse.data;
        const now = new Date();
        const maxMonitoringTimeMs = maxMonitoringTime * 60 * 1000;
        
        for (const campaign of campaigns) {
          // Solo validar campañas en ejecución o programadas
          if (campaign.status !== 'running' && campaign.status !== 'scheduled') continue;
          
          // Verificar si este sensor pertenece a la campaña
          const campaignSensors: string[] = campaign.sensors || [];
          if (!campaignSensors.includes(sensorMac)) continue;
          
          // Caso 1: Campaña actualmente en ejecución
          if (campaign.status === 'running') {
            return {
              available: false,
              message: `El sensor está ejecutando la campaña "${campaign.name}" actualmente. Debe finalizar antes de iniciar una adquisición en tiempo real.`
            };
          }
          
          // Caso 2: Campaña programada - verificar si inicia dentro del límite de tiempo
          if (campaign.status === 'scheduled') {
            // Construir fecha-hora de inicio combinando start_date y start_time
            const startDateStr = campaign.start_date ? campaign.start_date.split('T')[0] : null;
            const startTimeStr = campaign.start_time || '00:00:00';
            
            if (startDateStr) {
              // Crear fecha del inicio de la campaña en hora local Colombia
              const campaignStartDate = new Date(`${startDateStr}T${startTimeStr}`);
              const timeDiff = campaignStartDate.getTime() - now.getTime();
              
              // Si la campaña inicia dentro del período de monitoreo
              if (timeDiff > 0 && timeDiff < maxMonitoringTimeMs) {
                const minutesLeft = Math.ceil(timeDiff / 60000);
                const horaInicio = startTimeStr.substring(0, 5); // HH:MM
                return {
                  available: false,
                  message: `El sensor tiene la campaña "${campaign.name}" programada para iniciar a las ${horaInicio} (en ${minutesLeft} minuto(s)). El límite de adquisición en tiempo real es de ${maxMonitoringTime} minutos. No se puede iniciar el monitoreo porque interferiría con la campaña.`
                };
              }
              
              // Si la campaña ya debería haber iniciado (timeDiff <= 0) pero está en scheduled
              // esto normalmente no pasa, pero por seguridad
              if (timeDiff <= 0 && timeDiff > -maxMonitoringTimeMs) {
                return {
                  available: false,
                  message: `El sensor tiene la campaña "${campaign.name}" que debería estar en ejecución. No se puede iniciar el monitoreo.`
                };
              }
            }
          }
        }
      } catch (error) {
        console.error('Error checking campaigns:', error);
      }

      return { available: true, message: '' };
    } catch (error) {
      console.error('Error validando disponibilidad:', error);
      return { available: true, message: '' };
    }
  };

  const handleStartScan = async () => {
    if (!selectedSensor) {
      setValidationError('Por favor seleccione un sensor');
      return;
    }

    // Validar que si es preset AM/FM, se haya seleccionado el tipo
    if (config.preset === 'amfm' && !demodType) {
      setValidationError('Por favor seleccione el tipo de modulación (AM o FM)');
      return;
    }

    // Validar filtro: start_freq debe ser menor que end_freq
    if (filterEnabled) {
      if (filterStartFreqMhz >= filterEndFreqMhz) {
        setValidationError(`La frecuencia inicial (${filterStartFreqMhz} MHz) debe ser menor que la frecuencia final (${filterEndFreqMhz} MHz)`);
        return;
      }
    }

    // Validar disponibilidad del sensor
    const validation = await validateSensorAvailability(selectedSensor);
    if (!validation.available) {
      setValidationError(validation.message);
      return;
    }

    setValidationError('');
    setIsStarting(true);
    try {
      // Convertir RBW a Hz (puede ser 'auto' o un número)
      let rbwHz = 1000; // Valor por defecto si es 'auto'
      if (config.rbw !== 'auto') {
        rbwHz = typeof config.rbw === 'string' ? parseFloat(config.rbw) : config.rbw;
      }
      
      // Preparar la configuración para enviar al sensor (NUEVO FORMATO JSON)
      // Extraer el número de puerto desde el formato "RX-N"
      const antennaPort = config.antenna ? parseInt(config.antenna.replace('RX-', '')) : 1;
      const spanHz = config.span * 1e6; // Convertir MHz a Hz
      
      const scanConfig: any = {
        mac: selectedSensor,
        center_frequency: config.centerFrequency * 1e6, // Convertir MHz a Hz
        sample_rate_hz: spanHz, // Ya no se envía 'span', solo sample_rate_hz
        resolution_hz: rbwHz, // RBW ya en Hz
        vbw: config.vbw || 'auto', // Video Bandwidth
        antenna_port: antennaPort, // Puerto real de la antena (1, 2, 3, 4)
        window: 'hann',
        overlap: 0.5,
        lna_gain: (config as any).lna_gain || 0,
        vga_gain: (config as any).vga_gain || 0,
        antenna_amp: (config as any).antenna_amp !== false,
        is_monitoring: true, // Flag para indicar al backend que NO guarde en DB
        monitoring_timeout_minutes: maxMonitoringTime // Timeout server-side para auto-stop
      };

      // SOLO agregar filtro si está explícitamente habilitado Y tiene valores válidos
      if (filterEnabled && filterStartFreqMhz < filterEndFreqMhz) {
        scanConfig.filter = {
          start_freq_hz: Math.round(filterStartFreqMhz * 1e6),
          end_freq_hz: Math.round(filterEndFreqMhz * 1e6)
        };
        console.log('🎛️ Filtro habilitado:', filterStartFreqMhz, '-', filterEndFreqMhz, 'MHz');
        console.log('   → Start:', scanConfig.filter.start_freq_hz, 'Hz');
        console.log('   → End:', scanConfig.filter.end_freq_hz, 'Hz');
      } else {
        console.log('🎛️ Filtro DESHABILITADO - NO se enviará la propiedad "filter" al backend');
        console.log('   filterEnabled:', filterEnabled);
        // NO agregar la propiedad filter al objeto scanConfig
        // Esto significa que el sensor usará el rango completo del span
      }

      // Si es preset AM/FM, agregar configuración de demodulación (nuevo formato: string simple)
      if (config.preset === 'amfm' && demodType) {
        scanConfig.demodulation = demodType.toLowerCase(); // "am" o "fm"
      }

      // LOG DETALLADO de configuración enviada
      console.log('📡 ===== CONFIGURACIÓN ENVIADA AL SENSOR =====');
      console.log('Sensor MAC:', selectedSensor);
      console.log('Frecuencia Central:', config.centerFrequency, 'MHz →', scanConfig.center_frequency, 'Hz');
      console.log('Span/Sample Rate:', config.span, 'MHz →', scanConfig.sample_rate_hz, 'Hz');
      console.log('RBW:', config.rbw, '→', scanConfig.resolution_hz, 'Hz');
      console.log('Antena Puerto:', config.antenna, '→', scanConfig.antenna_port);
      console.log('Filtro Habilitado:', filterEnabled);
      if (scanConfig.filter) {
        console.log('  → Filtro Start:', filterStartFreqMhz, 'MHz →', scanConfig.filter.start_freq_hz, 'Hz');
        console.log('  → Filtro End:', filterEndFreqMhz, 'MHz →', scanConfig.filter.end_freq_hz, 'Hz');
      }
      console.log('Preset:', config.preset);
      if (scanConfig.demodulation) {
        console.log('Demodulación:', scanConfig.demodulation);
      }
      console.log('==========================================');

      // Enviar configuración al backend
      const response = await axios.post(`${API_BASE_URL}/sensor/${selectedSensor}/configure`, scanConfig);
      const result = response.data;
      console.log('✅ Adquisición iniciada:', result);
      
      // Notificar al componente padre que el monitoreo está activo
      if (onMonitoringChange) {
        onMonitoringChange(true, selectedSensor);
      }

      // Iniciar temporizador
      setRemainingTime(maxMonitoringTime * 60); // Convertir minutos a segundos
      
    } catch (error: any) {
      console.error('Error starting scan:', error);
      setValidationError(error.message || 'Error al iniciar la adquisición');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopScan = async () => {
    if (!selectedSensor) return;

    setIsStarting(true);
    try {
      // Enviar explícitamente configuración con frecuencia 0 para detener el sensor
      // Esto asegura que el sensor reciba la orden de parada
      const stopConfig = {
        mac: selectedSensor,
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
      };

      console.log('🛑 Enviando configuración de parada (Frecuencia 0)...');
      await axios.post(`${API_BASE_URL}/sensor/${selectedSensor}/configure`, stopConfig);

      // Llamar al endpoint de stop original
      await axios.post(`${API_BASE_URL}/sensor/${selectedSensor}/stop`);

      console.log('✅ Adquisición detenida');
      
      // Notificar al componente padre que el monitoreo se detuvo
      if (onMonitoringChange) {
        onMonitoringChange(false, null);
      }

      setRemainingTime(0);
      
    } catch (error: any) {
      console.error('Error stopping scan:', error);
      setValidationError(error.message || 'Error al detener la adquisición');
    } finally {
      setIsStarting(false);
    }
  };

  // Función para actualizar parámetros durante la adquisición sin detenerla
  const handleUpdateConfig = async (overrides?: Partial<ConfigurationPanelProps['config']>) => {
    if (!selectedSensor || !isMonitoring) return;

    try {
      const effectiveConfig = { ...config, ...(overrides || {}) };

      // Convertir RBW a Hz (puede ser 'auto' o un número)
      let rbwHz = 1000; // Valor por defecto si es 'auto'
      if (effectiveConfig.rbw !== 'auto') {
        rbwHz = typeof effectiveConfig.rbw === 'string' ? parseFloat(effectiveConfig.rbw) : effectiveConfig.rbw;
      }
      
      // Preparar la configuración para enviar al sensor (NUEVO FORMATO JSON)
      const antennaPort = effectiveConfig.antenna ? parseInt(effectiveConfig.antenna.replace('RX-', '')) : 1;
      const spanHz = effectiveConfig.span * 1e6; // Convertir MHz a Hz
      
      const scanConfig: any = {
        mac: selectedSensor,
        center_frequency: effectiveConfig.centerFrequency * 1e6, // Convertir MHz a Hz
        sample_rate_hz: spanHz, // Ya no se envía 'span', solo sample_rate_hz
        resolution_hz: rbwHz, // RBW ya en Hz
        vbw: effectiveConfig.vbw || 'auto', // Video Bandwidth
        antenna_port: antennaPort, // Puerto real de la antena (1, 2, 3, 4)
        window: 'hann',
        overlap: 0.5,
        lna_gain: (effectiveConfig as any).lna_gain || 0,
        vga_gain: (effectiveConfig as any).vga_gain || 0,
        antenna_amp: (effectiveConfig as any).antenna_amp !== false
      };

      // SOLO agregar filtro si está explícitamente habilitado Y tiene valores válidos
      if (filterEnabled && filterStartFreqMhz < filterEndFreqMhz) {
        scanConfig.filter = {
          start_freq_hz: Math.round(filterStartFreqMhz * 1e6),
          end_freq_hz: Math.round(filterEndFreqMhz * 1e6)
        };
        console.log('🎛️ Filtro actualizado:', filterStartFreqMhz, '-', filterEndFreqMhz, 'MHz');
        console.log('   → Start:', scanConfig.filter.start_freq_hz, 'Hz');
        console.log('   → End:', scanConfig.filter.end_freq_hz, 'Hz');
      } else if (filterEnabled) {
        console.log('⚠️ Filtro habilitado pero valores inválidos (start >= end)');
      } else {
        console.log('🎛️ Filtro DESHABILITADO - NO se enviará la propiedad "filter" al backend');
      }
      // Si filterEnabled es false, NO agregar la propiedad filter

      // Si es preset AM/FM, agregar configuración de demodulación (nuevo formato: string simple)
      if (effectiveConfig.preset === 'amfm' && demodType) {
        scanConfig.demodulation = demodType.toLowerCase(); // "am" o "fm"
      }

      console.log('🔄 Actualizando configuración en tiempo real:', scanConfig);
      
      // Usar el mismo endpoint que handleStartScan
      await axios.post(`${API_BASE_URL}/sensor/${selectedSensor}/configure`, scanConfig);
      console.log('✅ Configuración actualizada correctamente');
      
      // Notificar al padre para limpiar espectrograma y waterfall
      if (onLiveConfigUpdate) {
        onLiveConfigUpdate();
      }
      
      // Limpiar mensaje de error si lo había
      setValidationError('');
      
    } catch (error: any) {
      console.error('Error actualizando configuración:', error);
      setValidationError('Error al actualizar configuración: ' + (error.message || 'Error desconocido'));
    }
  };

  // Ref para controlar el inicio del temporizador y evitar paradas prematuras
  const hasStartedTimer = useRef(false);

  // 1. Rastrear si el temporizador ha iniciado (para evitar que el 0 inicial detenga la adquisición)
  useEffect(() => {
    if (isMonitoring && remainingTime > 0) {
      hasStartedTimer.current = true;
    }
    if (!isMonitoring) {
      hasStartedTimer.current = false;
    }
  }, [isMonitoring, remainingTime]);

  // 2. Detener cuando el tiempo se agota
  useEffect(() => {
    if (isMonitoring && remainingTime === 0 && hasStartedTimer.current) {
       handleStopScan();
       hasStartedTimer.current = false;
    }
  }, [remainingTime, isMonitoring]);

  // 3. Cuenta regresiva
  useEffect(() => {
    if (!isMonitoring || remainingTime <= 0) return;

    const interval = setInterval(() => {
      setRemainingTime((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [isMonitoring, remainingTime]);

  // Formatear tiempo restante
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-sm">
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-green-100 transition-colors"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <h2 className="text-lg font-semibold text-gray-800">Configuración de Adquisición</h2>
        {isCollapsed ? <ChevronDown className="w-5 h-5 text-gray-600" /> : <ChevronUp className="w-5 h-5 text-gray-600" />}
      </div>
      
      {!isCollapsed && (
        <div className="p-3">
          <div className="bg-white rounded-lg p-3 mb-3">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Dispositivo de medición</h3>

        <div className="mb-3">
          <label className="block text-xs text-gray-600 mb-1">Seleccionar sensor*</label>
          {loading ? (
            <div className="flex items-center justify-center py-1">
              <Loader2 className="w-4 h-4 animate-spin text-orange-500" />
              <span className="ml-2 text-xs text-gray-600">Cargando sensores...</span>
            </div>
          ) : sensors.length === 0 ? (
            <div className="text-xs text-gray-500 py-1">
              No hay sensores disponibles. Agregue sensores en la sección Red de Monitoreo.
            </div>
          ) : (
            <select
              value={selectedSensor}
              onChange={(e) => setSelectedSensor(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
            >
              <option value="" disabled>— Seleccione sensor —</option>
              {sensors.map((sensor) => {
                 const isOnline = sensor.status === 'online' || sensor.status === 'active';
                 const isBusy = sensor.status === 'busy';
                 const isDelay = sensor.status === 'delay';
                 let statusLabel = '⚫ Offline';
                 if (isOnline) statusLabel = '🟢 Online';
                 if (isBusy) statusLabel = '🟠 Ocupado';
                 if (isDelay) statusLabel = '🟡 Delay';
                 
                 // Deshabilitar si está busy, delay u offline
                 return (
                  <option key={sensor.id} value={sensor.mac} disabled={!isOnline || isBusy || isDelay}>
                    {sensor.name} ({sensor.mac}) - {statusLabel}
                  </option>
                );
              })}
            </select>
          )}
          <p className="text-xs text-gray-400 mt-0.5">Seleccione un sensor online y disponible</p>
        </div>

        <div className="mb-3">
          <label className="block text-xs text-gray-600 mb-1">Puerto / Antena*</label>
          <select
            value={config.antenna}
            onChange={(e) => {
              const val = e.target.value;
              
              // Buscar ganancia de la antena seleccionada
              const selectedAntenna = antennas.find(a => `RX-${a.port}` === val);
              const newGain = selectedAntenna ? selectedAntenna.gain_db : 0;
              
              // Actualizar ambos valores en UNA SOLA llamada para evitar race conditions
              onConfigChange({ 
                ...config, 
                antenna: val,
                antennaGain: newGain
              });

              if (isMonitoring) handleUpdateConfig();
            }}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
            disabled={antennas.length === 0}
          >
            {antennas.length === 0 ? (
              <option value="">No hay antenas asignadas a este sensor</option>
            ) : (
              antennas.map((antenna) => (
                <option key={`${antenna.id}-${antenna.port}`} value={`RX-${antenna.port}`}>
                  Puerto {antenna.port} - {antenna.name} ({(antenna.frequency_min_hz / 1000000).toFixed(0)}-{(antenna.frequency_max_hz / 1000000).toFixed(0)} MHz)
                </option>
              ))
            )}
          </select>
          <p className="text-xs text-gray-400 mt-0.5">
            {antennas.length > 0 
              ? 'Selecciona la antena configurada en este puerto' 
              : 'Este sensor no tiene antenas asignadas. Configúralas en el menú Dispositivos.'}
          </p>
        </div>

        {/* Botón Crear Campaña (Solution 1) - Movido aquí */}
        {onCreateCampaign && isMonitoring && (
          <button
            onClick={async () => {
              if (isMonitoring) {
                await handleStopScan();
              }
              onCreateCampaign({ ...config, sensor: selectedSensor });
            }}
            disabled={isStarting || !selectedSensor}
            className={`w-full mb-3 flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg font-medium transition-all shadow-sm border border-orange-500 text-orange-600 hover:bg-orange-50 bg-white ${
              (isStarting || !selectedSensor) ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <Plus className="w-4 h-4" />
            Crear campaña
          </button>
        )}
      </div>

          <div className="bg-white rounded-lg p-3">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Configuración de Adquisición</h3>

        {/* Preajustes */}
        <div className="mb-3">
          <label className="block text-xs font-medium text-gray-700 mb-1">Preajustes</label>
          <select
            value={config.preset}
            onChange={(e) => handlePresetChange(e.target.value)}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="custom">Personalizado</option>
            <option value="rmer">RMER</option>
            <option value="rmtdt">RMTDT</option>
            <option value="rni">RNI</option>
            <option value="amfm">AM/FM</option>
          </select>
          <p className="text-xs text-gray-400 mt-0.5">Configuraciones preestablecidas para la adquisición</p>
        </div>

        {/* Submenús para RMER y RNI */}
        {(config.preset === 'rmer' || config.preset === 'rni') && (
          <>
            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-700 mb-1">Servicio</label>
              <select
                value={presetService}
                onChange={(e) => handleServiceChange(e.target.value)}
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
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
                  className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
                >
                  <option value="">Seleccione canal...</option>
                  {Object.keys((config.preset === 'rmer' ? PRESET_DATA.rmer : PRESET_DATA.rni)[presetService as keyof typeof PRESET_DATA.rmer] || {}).map(channel => (
                    <option key={channel} value={channel}>{channel}</option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}

        {/* Submenú para RMTDT */}
        {config.preset === 'rmtdt' && (
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Canal</label>
            <select
              value={presetChannel}
              onChange={(e) => handleChannelChange(e.target.value)}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
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
        {config.preset === 'amfm' && (
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-700 mb-1">Tipo de Modulación</label>
            <select
              value={demodType}
              onChange={(e) => handleDemodTypeChange(e.target.value as 'AM' | 'FM')}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
            >
              <option value="">Seleccione tipo...</option>
              <option value="AM">AM (Amplitude Modulation)</option>
              <option value="FM">FM (Frequency Modulation)</option>
            </select>
            <p className="text-xs text-gray-400 mt-0.5">Span fijo: 8 MHz • RBW fijo: 1 kHz</p>
          </div>
        )}

        {/* Rango de Frecuencias */}
        <div className="mb-3">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Rango de frecuencias</h4>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-gray-600 mb-1">Frecuencia Central*</label>
              <div className="flex">
                <input
                  type="number"
                  value={config.centerFrequency}
                  onChange={(e) => handleCenterFrequencyChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && isMonitoring) {
                      onWaterfallResetRequested?.();
                      handleUpdateConfig();
                    }
                  }}
                  onBlur={(e) => {
                    // Al perder el foco, asegurar que hay un valor válido
                    if (e.target.value === '' || e.target.value === '-') {
                      handleChange('centerFrequency', 97.5);
                    }
                  }}
                  disabled={config.preset !== 'custom' && config.preset !== 'amfm'}
                  min="1"
                  max="6000"
                  step="0.1"
                  className={`w-full px-2 py-1 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:ring-1 focus:ring-orange-500 ${
                    (config.preset !== 'custom' && config.preset !== 'amfm') ? 'bg-gray-100 cursor-not-allowed' : ''
                  }`}
                  placeholder="97.5"
                />
                <span className="px-2 py-1 bg-gray-100 border border-l-0 border-gray-300 rounded-r-md text-xs whitespace-nowrap">
                  MHz
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                {config.preset !== 'custom' && config.preset !== 'amfm' ? 'Calculado automáticamente' : '1 MHz - 6 GHz'}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                Span / Sample Rate
              </label>
              <div className="flex">
                <input
                  type="number"
                  value={localSpan}
                  onChange={(e) => {
                    const value = e.target.value;
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {
                      setLocalSpan(numValue);
                      if (numValue >= 8 && numValue <= 20) {
                        // Actualizar span y sampleRate en UNA SOLA llamada
                        onConfigChange({ 
                          ...config, 
                          span: numValue, 
                          sampleRate: numValue 
                        });
                      }
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && isMonitoring) {
                      const minSpan = config.preset === 'rmtdt' ? 6 : 8;
                      const clampedSpan = Math.min(20, Math.max(minSpan, localSpan));
                      setLocalSpan(clampedSpan);
                      onConfigChange({ ...config, span: clampedSpan, sampleRate: clampedSpan });
                      onWaterfallResetRequested?.();
                      handleUpdateConfig({ span: clampedSpan, sampleRate: clampedSpan });
                    }
                  }}
                  onBlur={() => {
                    // Al salir del campo, ajustar al rango si está fuera
                    const minSpan = config.preset === 'rmtdt' ? 6 : 8;
                    let finalSpan = localSpan;
                    
                    if (localSpan < minSpan) {
                      finalSpan = minSpan;
                      setLocalSpan(minSpan);
                      onConfigChange({ ...config, span: minSpan, sampleRate: minSpan });
                    } else if (localSpan > 20) {
                      finalSpan = 20;
                      setLocalSpan(20);
                      onConfigChange({ ...config, span: 20, sampleRate: 20 });
                    }

                    if (isMonitoring) {
                      handleUpdateConfig({ span: finalSpan, sampleRate: finalSpan });
                    }
                  }}
                  disabled={config.preset === 'amfm' || config.preset === 'rmtdt'}
                  min={config.preset === 'rmtdt' ? "6" : "8"}
                  max="20"
                  step="0.1"
                  className={`w-full px-2 py-1 text-sm border border-gray-300 rounded-l-md focus:outline-none focus:ring-1 focus:ring-orange-500 ${
                    (config.preset === 'amfm' || config.preset === 'rmtdt') ? 'bg-gray-100 cursor-not-allowed' : ''
                  }`}
                />
                <span className="px-2 py-1 bg-gray-100 border border-l-0 border-gray-300 rounded-r-md text-xs">
                  MHz
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                {config.preset === 'rmtdt' 
                  ? 'Span fijo: 6.5 MHz' 
                  : (config.preset === 'amfm' ? 'Span fijo: 2 MHz' : '8 - 20 MHz')}
              </p>
            </div>
          </div>
        </div>

        {/* Ganancias LNA y VGA en la misma línea */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          {/* Ganancia LNA */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              LNA Gain: {(config as any).lna_gain || 0} dB
            </label>
            <input
              type="range"
              min="0"
              max="40"
              step="8"
              value={(config as any).lna_gain || 0}
              onChange={(e) => handleChange('lna_gain', parseInt(e.target.value))}
              onMouseUp={() => isMonitoring && handleUpdateConfig()}
              onTouchEnd={() => isMonitoring && handleUpdateConfig()}
              disabled={false}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0</span>
              <span>8</span>
              <span>16</span>
              <span>24</span>
              <span>32</span>
              <span>40</span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Amplificador de bajo ruido</p>
          </div>

          {/* Ganancia VGA */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              VGA Gain: {(config as any).vga_gain || 0} dB
            </label>
            <input
              type="range"
              min="0"
              max="62"
              step="2"
              value={(config as any).vga_gain || 0}
              onChange={(e) => handleChange('vga_gain', parseInt(e.target.value))}
              onMouseUp={() => isMonitoring && handleUpdateConfig()}
              onTouchEnd={() => isMonitoring && handleUpdateConfig()}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>0</span>
              <span>16</span>
              <span>32</span>
              <span>48</span>
              <span>62</span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Amplificador de ganancia variable</p>
          </div>
        </div>

        {/* Antenna Amp */}
        <div className="mb-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={(config as any).antenna_amp !== false}
              onChange={(e) => {
                handleChange('antenna_amp', e.target.checked);
                if (isMonitoring) handleUpdateConfig();
              }}
              className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 focus:ring-2"
            />
            <span className="text-sm font-medium text-gray-700">Antenna Amp</span>
          </label>
          <p className="text-xs text-gray-400 mt-0.5">Amplificador externo de antena</p>
        </div>

        {/* Parámetros de Adquisición */}
        <div className="mb-3">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Parámetros de adquisición</h4>
          <div>
            <label className="block text-xs text-gray-600 mb-1">RBW (Resolution Bandwidth)</label>
            <select
              value={config.rbw}
              onChange={(e) => {
                const rbwValue = e.target.value;
                handleChange('rbw', rbwValue);
                if (isMonitoring) handleUpdateConfig({ rbw: rbwValue });
              }}
              disabled={config.preset !== 'custom' && config.preset !== 'rmtdt'}
              className={`w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500 ${
                (config.preset !== 'custom' && config.preset !== 'rmtdt') ? 'bg-gray-100 cursor-not-allowed' : ''
              }`}
            >
              <option value="1000">1 kHz</option>
              <option value="3000">3 kHz</option>
              <option value="10000">10 kHz</option>
              <option value="30000">30 kHz</option>
              <option value="100000">100 kHz</option>
              <option value="300000">300 kHz</option>
              <option value="1000000">1 MHz</option>
            </select>
            <p className="text-xs text-gray-400 mt-0.5">Desde 1 kHz en adelante</p>
          </div>
        </div>

        {/* VBW */}
        <div className="mb-3">
          <label className="block text-xs text-gray-600 mb-1">VBW (Video Bandwidth)</label>
          <select
            value={config.vbw || 'RBW'}
            onChange={(e) => {
              handleChange('vbw', e.target.value);
              if (isMonitoring) handleUpdateConfig();
            }}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-orange-500"
          >
            <option value="RBW">RBW</option>
            <option value="rbw/2">RBW / 2</option>
            <option value="rbw/3">RBW / 3</option>
            <option value="rbw/5">RBW / 5</option>
          </select>
          <p className="text-xs text-gray-400 mt-0.5">Filtro de video para suavizado de traza</p>
        </div>

        {/* Panel de Filtros - SIMPLIFICADO con slider doble */}
        <div className="mb-3">
          {/* Checkbox para habilitar filtro */}
          <label className="flex items-center gap-2 cursor-pointer mb-2">
            <input
              type="checkbox"
              checked={filterEnabled}
              onChange={(e) => {
                const newFilterEnabled = e.target.checked;
                setFilterEnabled(newFilterEnabled);
                
                // Si se está habilitando el filtro, ajustar al rango completo del span actual
                if (newFilterEnabled) {
                  const minFreq = config.centerFrequency - config.span / 2;
                  const maxFreq = config.centerFrequency + config.span / 2;
                  setFilterStartFreqMhz(minFreq);
                  setFilterEndFreqMhz(maxFreq);
                }
                
                // Si está monitoreando, actualizar la configuración con un pequeño delay
                // para asegurar que los estados se hayan actualizado
                if (isMonitoring) {
                  setTimeout(() => handleUpdateConfig(), 50);
                }
              }}
              className="w-4 h-4 text-orange-600 bg-gray-100 border-gray-300 rounded focus:ring-orange-500 focus:ring-2"
            />
            <span className="text-sm font-medium text-gray-700">Habilitar Filtro de Frecuencias</span>
          </label>

          {/* Slider doble con información de frecuencias */}
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
                  className="absolute top-1/2 transform -translate-y-1/2 h-2 bg-orange-500 rounded-full pointer-events-none"
                  style={{
                    left: `${((filterStartFreqMhz - (config.centerFrequency - config.span / 2)) / config.span) * 100}%`,
                    width: `${((filterEndFreqMhz - filterStartFreqMhz) / config.span) * 100}%`
                  }}
                ></div>
                
                {/* Slider izquierdo (start) - Posicionado arriba */}
                <input
                  type="range"
                  min={(config.centerFrequency - config.span / 2).toFixed(2)}
                  max={(config.centerFrequency + config.span / 2).toFixed(2)}
                  step="0.25"
                  value={filterStartFreqMhz}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (value < filterEndFreqMhz - 0.25) {
                      setFilterStartFreqMhz(value);
                    }
                  }}
                  onMouseUp={() => isMonitoring && handleUpdateConfig()}
                  onTouchEnd={() => isMonitoring && handleUpdateConfig()}
                  className="range-slider-start absolute w-full top-0"
                  style={{ 
                    zIndex: 5,
                    pointerEvents: 'auto'
                  }}
                />
                
                {/* Slider derecho (end) - Posicionado abajo */}
                <input
                  type="range"
                  min={(config.centerFrequency - config.span / 2).toFixed(2)}
                  max={(config.centerFrequency + config.span / 2).toFixed(2)}
                  step="0.25"
                  value={filterEndFreqMhz}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (value > filterStartFreqMhz + 0.25) {
                      setFilterEndFreqMhz(value);
                    }
                  }}
                  onMouseUp={() => isMonitoring && handleUpdateConfig()}
                  onTouchEnd={() => isMonitoring && handleUpdateConfig()}
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
                Rango disponible: {(config.centerFrequency - config.span / 2).toFixed(2)} - {(config.centerFrequency + config.span / 2).toFixed(2)} MHz
              </p>
            </div>
          )}
        </div>

        {/* Botón Iniciar/Detener Adquisición */}
        <div className="mt-4 pt-3 border-t border-gray-200">
          {validationError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-700">{validationError}</p>
            </div>
          )}
          
          {isMonitoring && remainingTime > 0 && (
            <div className="mb-3 p-2 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-xs text-green-700 text-center font-medium">
                ⏱️ Tiempo restante: {formatTime(remainingTime)}
              </p>
            </div>
          )}

          <button
            onClick={isMonitoring ? handleStopScan : handleStartScan}
            disabled={(() => {
              if (isStarting || !selectedSensor || sensors.length === 0) return true;
              // Deshabilitar si el sensor seleccionado no está online
              const sensor = sensors.find(s => s.mac === selectedSensor);
              if (!sensor) return true;
              const isOnline = sensor.status === 'online' || sensor.status === 'active';
              return !isOnline && !isMonitoring; // Solo bloquear al iniciar, no al detener
            })()}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-semibold text-sm shadow-md hover:shadow-lg ${
              isMonitoring 
                ? 'bg-red-500 hover:bg-red-600' 
                : 'bg-orange-500 hover:bg-orange-600'
            }`}
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{isMonitoring ? 'Deteniendo...' : 'Iniciando...'}</span>
              </>
            ) : isMonitoring ? (
              <>
                <Square className="w-4 h-4" />
                <span>Detener Adquisición</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                <span>Iniciar Adquisición</span>
              </>
            )}
          </button>

          {isMonitoring && (
            <p className="text-xs text-gray-400 mt-2 text-center">
              Puedes cambiar parámetros y presionar Enter para actualizar sin detener
            </p>
          )}
        </div>
      </div>
    </div>
  )}
</div>
  );
}
