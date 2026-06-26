/**
 * Simulador de Sensor de Espectro Radioeléctrico
 * 
 * Este script simula un sensor que envía datos de espectro en tiempo real
 * a la API del backend, permitiendo probar la funcionalidad de polling.
 */

import axios from 'axios';

const API_URL = 'http://localhost:3000/api';
const SENSOR_MAC = '11:22:33:44:55:66'; // MAC del sensor Cali Sur
const SENSOR_NAME = 'Sensor Cali Sur';

// Configuración del espectro
const START_FREQ_HZ = 88e6;  // 88 MHz (FM Radio)
const END_FREQ_HZ = 108e6;   // 108 MHz
let NUM_POINTS = 1000;       // Número de puntos de frecuencia (configurable)
const UPDATE_INTERVAL_MS = 2000; // Actualizar cada 2 segundos
const AUDIO_INTERVAL_MS = 500; // Enviar audio cada 500ms

let DEMOD_TYPE: 'AM' | 'FM' | null = null; // Tipo de demodulación activa
let DEMOD_CENTER_FREQ: number = 95.5e6; // Frecuencia central para demodulación

interface SpectrumData {
  mac: string;
  timestamp: number;
  start_freq_hz: number;
  end_freq_hz: number;
  Pxx: number[];
  gps_lat?: number;
  gps_lon?: number;
  gps_alt?: number;
  excursion?: {
    unit: string;
    peak_to_peak_hz: number;
    peak_deviation_hz: number;
    rms_deviation_hz: number;
  };
  depth?: {
    unit: string;
    peak_to_peak: number;
    peak_deviation: number;
    rms_deviation: number;
  };
}

/**
 * Genera métricas simuladas de modulación AM
 */
function generateAMMetrics() {
  return {
    unit: 'percent',
    peak_to_peak: 30 + Math.random() * 20, // 30-50%
    peak_deviation: 90 + Math.random() * 10, // 90-100%
    rms_deviation: 15 + Math.random() * 10 // 15-25%
  };
}

/**
 * Genera métricas simuladas de modulación FM
 */
function generateFMMetrics() {
  return {
    unit: 'hz',
    peak_to_peak_hz: 70000 + Math.random() * 10000, // 70-80 kHz
    peak_deviation_hz: 220000 + Math.random() * 15000, // 220-235 kHz
    rms_deviation_hz: 40000 + Math.random() * 10000 // 40-50 kHz
  };
}

/**
 * Genera datos de espectro sintéticos con señales FM simuladas
 */
function generateSpectrumData(): SpectrumData {
  const freqStep = (END_FREQ_HZ - START_FREQ_HZ) / NUM_POINTS;
  const Pxx: number[] = [];
  
  // Ruido de fondo base
  const noiseFloor = -95;
  
  // Estaciones FM simuladas (frecuencias en Hz)
  const fmStations = [
    { freq: 88.9e6, power: -45, bandwidth: 200e3 },
    { freq: 92.1e6, power: -50, bandwidth: 200e3 },
    { freq: 95.5e6, power: -40, bandwidth: 200e3 },
    { freq: 98.1e6, power: -48, bandwidth: 200e3 },
    { freq: 101.3e6, power: -43, bandwidth: 200e3 },
    { freq: 104.7e6, power: -52, bandwidth: 200e3 },
  ];
  
  for (let i = 0; i < NUM_POINTS; i++) {
    const frequency = START_FREQ_HZ + (i * freqStep);
    let power = noiseFloor + (Math.random() * 5); // Ruido aleatorio
    
    // Agregar señales de estaciones FM
    for (const station of fmStations) {
      const freqDiff = Math.abs(frequency - station.freq);
      if (freqDiff < station.bandwidth) {
        // Forma de campana gaussiana para la señal
        const attenuation = Math.exp(-(freqDiff * freqDiff) / (2 * (station.bandwidth / 4) ** 2));
        const signalPower = station.power + (Math.random() * 2 - 1); // Variación aleatoria
        power = Math.max(power, signalPower * attenuation + noiseFloor * (1 - attenuation));
      }
    }
    
    Pxx.push(power);
  }
  
  const data: SpectrumData = {
    mac: SENSOR_MAC,
    timestamp: Date.now(),
    start_freq_hz: START_FREQ_HZ,
    end_freq_hz: END_FREQ_HZ,
    Pxx,
    gps_lat: 6.2442 + (Math.random() * 0.001 - 0.0005), // Medellín con variación
    gps_lon: -75.5812 + (Math.random() * 0.001 - 0.0005),
    gps_alt: 1495 + (Math.random() * 10 - 5),
  };

  // Agregar métricas de demodulación si están activas
  if (DEMOD_TYPE === 'AM') {
    data.depth = generateAMMetrics();
  } else if (DEMOD_TYPE === 'FM') {
    data.excursion = generateFMMetrics();
  }

  return data;
}

/**
 * Genera audio simulado PCM en formato base64
 * Simula una onda sinusoidal de 1kHz con ruido
 */
function generateSimulatedAudio(): string {
  const sampleRate = 48000; // 48 kHz
  const duration = 0.5; // 500ms
  const numSamples = Math.floor(sampleRate * duration);
  const frequency = 1000; // 1 kHz tone
  
  let audioString = '';
  
  for (let i = 0; i < numSamples; i++) {
    // Onda sinusoidal con un poco de ruido
    const t = i / sampleRate;
    const signal = Math.sin(2 * Math.PI * frequency * t);
    const noise = (Math.random() - 0.5) * 0.1;
    const sample = signal * 0.8 + noise;
    
    // Convertir de [-1, 1] a [0, 255]
    const byte = Math.floor((sample + 1) * 127.5);
    audioString += String.fromCharCode(byte);
  }
  
  // Convertir a base64
  return Buffer.from(audioString, 'binary').toString('base64');
}

/**
 * Envía audio simulado a la API
 */
async function sendAudioData() {
  if (!DEMOD_TYPE) return;
  
  try {
    const audioData = {
      mac: SENSOR_MAC,
      audio: generateSimulatedAudio(),
      demodType: DEMOD_TYPE,
      timestamp: Date.now()
    };
    
    await axios.post(`${API_URL}/sensor/audio`, audioData);
    console.log(`🎵 [${new Date().toLocaleTimeString()}] Audio ${DEMOD_TYPE} enviado`);
  } catch (error: any) {
    console.error('❌ Error enviando audio:', error.response?.data || error.message);
  }
}

/**
 * Registra el sensor en el sistema si no existe
 */
async function registerSensor() {
  try {
    console.log('🔌 Registrando sensor simulado...');
    
    // Intentar crear el sensor
    await axios.post(`${API_URL}/sensors`, {
      name: SENSOR_NAME,
      mac: SENSOR_MAC,
      type: 'Simulador',
      location: 'Medellín, Colombia (Virtual)',
      latitude: 6.2442,
      longitude: -75.5812,
      altitude: 1495,
      status: 'active'
    });
    
    console.log('✅ Sensor registrado correctamente');
  } catch (error: any) {
    if (error.response?.status === 409) {
      console.log('ℹ️  Sensor ya existe en el sistema');
    } else {
      console.error('❌ Error registrando sensor:', error.message);
    }
  }
}

/**
 * Envía datos de espectro a la API
 */
async function sendSpectrumData() {
  try {
    const data = generateSpectrumData();
    
    await axios.post(`${API_URL}/sensor/data`, data);
    
    // Calcular estadísticas sin desbordar el stack
    let sumPower = 0;
    let maxPower = -Infinity;
    for (let i = 0; i < data.Pxx.length; i++) {
      sumPower += data.Pxx[i];
      if (data.Pxx[i] > maxPower) maxPower = data.Pxx[i];
    }
    const avgPower = sumPower / data.Pxx.length;
    
    console.log(`📡 [${new Date(data.timestamp).toLocaleTimeString()}] Datos enviados:`, {
      frecuencia: `${(data.start_freq_hz / 1e6).toFixed(1)} - ${(data.end_freq_hz / 1e6).toFixed(1)} MHz`,
      puntos: data.Pxx.length.toLocaleString(),
      potenciaPromedio: `${avgPower.toFixed(1)} dBm`,
      potenciaMax: `${maxPower.toFixed(1)} dBm`,
      gps: `${data.gps_lat?.toFixed(4)}, ${data.gps_lon?.toFixed(4)}`
    });
  } catch (error: any) {
    console.error('❌ Error enviando datos:', error.response?.data || error.message);
  }
}

/**
 * Muestra el menú de selección de puntos
 */
function showMenu(): Promise<number> {
  return new Promise((resolve) => {
    console.log('╔════════════════════════════════════════════════════════╗');
    console.log('║  SIMULADOR DE SENSOR DE ESPECTRO RADIOELÉCTRICO        ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    console.log('');
    console.log('Seleccione el número de puntos de frecuencia:');
    console.log('');
    console.log('  1) 1,000 puntos');
    console.log('  2) 10,000 puntos');
    console.log('  3) 100,000 puntos');
    console.log('  4) 500,000 puntos');
    console.log('');
    process.stdout.write('Opción (1-4): ');

    const stdin = process.stdin;
    stdin.setEncoding('utf8');
    stdin.once('data', (data) => {
      const option = data.toString().trim();
      let points = 1000;
      
      switch (option) {
        case '1': points = 1000; break;
        case '2': points = 10000; break;
        case '3': points = 100000; break;
        case '4': points = 500000; break;
        default:
          console.log('\n⚠️  Opción inválida, usando 1,000 puntos por defecto\n');
          points = 1000;
      }
      
      resolve(points);
    });
  });
}

/**
 * Muestra el menú de demodulación
 */
function showDemodMenu(): Promise<'AM' | 'FM' | null> {
  return new Promise((resolve) => {
    console.log('');
    console.log('¿Desea simular demodulación AM/FM con audio?');
    console.log('');
    console.log('  1) No (solo espectro)');
    console.log('  2) AM (Amplitude Modulation)');
    console.log('  3) FM (Frequency Modulation)');
    console.log('');
    process.stdout.write('Opción (1-3): ');

    const stdin = process.stdin;
    stdin.once('data', (data) => {
      const option = data.toString().trim();
      let type: 'AM' | 'FM' | null = null;
      
      switch (option) {
        case '1': type = null; break;
        case '2': type = 'AM'; break;
        case '3': type = 'FM'; break;
        default:
          console.log('\n⚠️  Opción inválida, continuando sin demodulación\n');
          type = null;
      }
      
      resolve(type);
    });
  });
}

/**
 * Inicia el simulador
 */
async function startSimulator() {
  // Verificar si se pasó el número de puntos como argumento
  const args = process.argv.slice(2);
  if (args.length > 0) {
    const points = parseInt(args[0]);
    if (!isNaN(points) && points > 0) {
      NUM_POINTS = points;
    }
  } else {
    // Mostrar menú interactivo
    NUM_POINTS = await showMenu();
  }

  // Preguntar por demodulación
  DEMOD_TYPE = await showDemodMenu();

  console.log('╔════════════════════════════════════════════════════════╗');
  console.log('║  SIMULADOR DE SENSOR DE ESPECTRO RADIOELÉCTRICO        ║');
  console.log('╚════════════════════════════════════════════════════════╝');
  console.log('');
  console.log(`📍 Sensor: ${SENSOR_NAME}`);
  console.log(`🆔 MAC: ${SENSOR_MAC}`);
  console.log(`📻 Rango: ${START_FREQ_HZ / 1e6} - ${END_FREQ_HZ / 1e6} MHz (FM)`);
  console.log(`📊 Puntos: ${NUM_POINTS.toLocaleString()}`);
  console.log(`⏱️  Intervalo: ${UPDATE_INTERVAL_MS / 1000}s`);
  if (DEMOD_TYPE) {
    console.log(`🎵 Demodulación: ${DEMOD_TYPE} en ${DEMOD_CENTER_FREQ / 1e6} MHz`);
    console.log(`🔊 Audio: Tono simulado de 1 kHz cada ${AUDIO_INTERVAL_MS}ms`);
  }
  console.log(`🌐 API: ${API_URL}`);
  console.log('');
  console.log('ℹ️  Usando sensor existente en la base de datos');
  console.log('');
  console.log('🚀 Iniciando transmisión de datos...');
  console.log('   Presiona Ctrl+C para detener');
  console.log('');
  
  // Enviar primera muestra inmediatamente
  await sendSpectrumData();
  
  // Configurar intervalo para envío continuo de espectro
  setInterval(sendSpectrumData, UPDATE_INTERVAL_MS);
  
  // Si hay demodulación activa, enviar audio periódicamente
  if (DEMOD_TYPE) {
    setInterval(sendAudioData, AUDIO_INTERVAL_MS);
  }
}

// Manejo de señales de terminación
process.on('SIGINT', () => {
  console.log('');
  console.log('🛑 Simulador detenido');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('');
  console.log('🛑 Simulador detenido');
  process.exit(0);
});

// Iniciar simulador
startSimulator().catch(error => {
  console.error('❌ Error fatal:', error);
  process.exit(1);
});
