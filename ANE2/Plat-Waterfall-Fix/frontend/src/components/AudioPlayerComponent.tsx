import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Volume2, VolumeX, Activity, Signal } from 'lucide-react';

interface AudioPlayerProps {
  sensorId: string;
  wsUrl?: string;
}

interface AudioMetrics {
  framesPerSecond: number;
  queueLength: number;
  rms: number;
  isPlaying: boolean;
  isConnected: boolean;
}

const AudioPlayerComponent: React.FC<AudioPlayerProps> = ({ 
  sensorId,
  wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}${window.location.protocol === 'https:' ? ':12443' : ':3000'}`
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [metrics, setMetrics] = useState<AudioMetrics>({
    framesPerSecond: 0,
    queueLength: 0,
    rms: 0,
    isPlaying: false,
    isConnected: false
  });
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  // Referencias para Audio API
  const audioCtxRef = useRef<AudioContext | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const sampleRateRef = useRef<number>(48000);
  const queueRef = useRef<Float32Array[]>([]);
  const gainNodeRef = useRef<GainNode | null>(null);
  
  // Métricas
  const metricsRef = useRef({
    framesRx: 0,
    t0: performance.now()
  });

  const TARGET_BUFFER_FRAMES = 10; // 200 ms

  const addLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-20), `${new Date().toLocaleTimeString()}: ${msg}`]);
  }, []);

  // Convertir PCM s16le a Float32
  const pcmLEToFloat32 = useCallback((buffer: ArrayBuffer, offset: number, samples: number) => {
    const dataView = new DataView(buffer, offset);
    const out = new Float32Array(samples);
    let acc = 0;

    for (let i = 0; i < samples; i++) {
      const value = dataView.getInt16(i * 2, true); // Little Endian
      const floatValue = value / 32768.0;
      out[i] = floatValue;
      acc += floatValue * floatValue;
    }

    const rms = Math.sqrt(acc / samples);
    return { out, rms };
  }, []);

  // Schedule audio frame
  const scheduleFrame = useCallback((pcmData: Float32Array) => {
    const audioCtx = audioCtxRef.current;
    const gainNode = gainNodeRef.current;
    if (!audioCtx || !gainNode) return;

    const buffer = audioCtx.createBuffer(1, pcmData.length, sampleRateRef.current);
    const channelData = new Float32Array(pcmData);
    buffer.copyToChannel(channelData, 0);

    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(gainNode);

    const now = audioCtx.currentTime;
    if (nextPlayTimeRef.current < now) {
      nextPlayTimeRef.current = now + 0.05; // Catch-up de 50ms
    }

    source.start(nextPlayTimeRef.current);
    nextPlayTimeRef.current += buffer.duration;
  }, []);

  // Pump del buffer
  const pump = useCallback(() => {
    if (!isPlaying) return;
    if (queueRef.current.length < TARGET_BUFFER_FRAMES) return;

    while (queueRef.current.length > 0) {
      const frame = queueRef.current.shift();
      if (frame) scheduleFrame(frame);
    }
  }, [isPlaying, scheduleFrame]);

  // Actualizar métricas cada segundo
  useEffect(() => {
    const interval = setInterval(() => {
      const now = performance.now();
      const dt = (now - metricsRef.current.t0) / 1000;

      if (dt >= 1.0) {
        setMetrics({
          framesPerSecond: metricsRef.current.framesRx,
          queueLength: queueRef.current.length,
          rms: metrics.rms,
          isPlaying,
          isConnected: wsRef.current?.readyState === WebSocket.OPEN
        });

        metricsRef.current.framesRx = 0;
        metricsRef.current.t0 = now;
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isPlaying, metrics.rms]);

  // Manejar WebSocket
  const connectWebSocket = useCallback(() => {
    const url = `${wsUrl}/ws/audio/listen/${sensorId}`;
    addLog(`Conectando a ${url}...`);

    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      addLog('✓ WebSocket conectado');
      setMetrics(prev => ({ ...prev, isConnected: true }));
    };

    ws.onclose = () => {
      addLog('✗ WebSocket desconectado');
      setMetrics(prev => ({ ...prev, isConnected: false }));
      
      // Reconectar después de 2 segundos
      if (isPlaying) {
        setTimeout(connectWebSocket, 2000);
      }
    };

    ws.onerror = (err) => {
      addLog('✗ Error en WebSocket');
      console.error('WebSocket error:', err);
    };

    ws.onmessage = (event) => {
      // Config JSON inicial
      if (typeof event.data === 'string') {
        try {
          const config = JSON.parse(event.data);
          sampleRateRef.current = config.sample_rate || 48000;
          addLog(`Config: ${config.codec} @ ${config.sample_rate}Hz`);
        } catch (err) {
          addLog('Error parseando config');
        }
        return;
      }

      // Frame PCM binario
      const buffer = event.data as ArrayBuffer;
      const dataView = new DataView(buffer);

      // Parsear header PCM (Big Endian)
      // magic(4) seq(4) sample_rate(4) channels(2) samples(2)
      const sampleRate = dataView.getUint32(8, false);
      const numSamples = dataView.getUint16(14, false);

      if (sampleRate) sampleRateRef.current = sampleRate;

      // Decodificar PCM data (Little Endian)
      const { out, rms } = pcmLEToFloat32(buffer, 16, numSamples);

      // Agregar al buffer
      queueRef.current.push(out);
      pump();

      // Actualizar métricas
      metricsRef.current.framesRx++;
      setMetrics(prev => ({ ...prev, rms }));
    };

    // Mantener conexión viva
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 5000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [wsUrl, sensorId, isPlaying, addLog, pcmLEToFloat32, pump]);

  // Start/Stop audio
  const toggleAudio = async () => {
    if (!isPlaying) {
      // Iniciar
      try {
        // Crear AudioContext
        const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
        const audioCtx = new AudioContextClass();
        await audioCtx.resume();
        audioCtxRef.current = audioCtx;

        // Crear GainNode para control de volumen
        const gainNode = audioCtx.createGain();
        gainNode.connect(audioCtx.destination);
        gainNode.gain.value = isMuted ? 0 : volume;
        gainNodeRef.current = gainNode;

        addLog('✓ AudioContext iniciado');
        
        // Conectar WebSocket
        connectWebSocket();
        
        setIsPlaying(true);
      } catch (err) {
        addLog('✗ Error iniciando audio');
        console.error(err);
      }
    } else {
      // Detener
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      if (audioCtxRef.current) {
        await audioCtxRef.current.close();
        audioCtxRef.current = null;
      }

      queueRef.current = [];
      setIsPlaying(false);
      addLog('Audio detenido');
    }
  };

  // Control de volumen
  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Audio en Tiempo Real</h2>
          <p className="text-sm text-gray-600">Sensor: {sensorId}</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${metrics.isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-gray-600">
            {metrics.isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Controles principales */}
      <div className="flex items-center space-x-4 mb-6">
        <button
          onClick={toggleAudio}
          className={`px-6 py-3 rounded-lg font-semibold text-white transition-colors ${
            isPlaying
              ? 'bg-red-500 hover:bg-red-600'
              : 'bg-blue-500 hover:bg-blue-600'
          }`}
        >
          {isPlaying ? 'Detener' : 'Iniciar'} Audio
        </button>

        {/* Control de volumen */}
        <div className="flex items-center space-x-2 flex-1">
          <button
            onClick={() => setIsMuted(!isMuted)}
            className="p-2 rounded hover:bg-gray-100"
          >
            {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={(e) => setVolume(parseFloat(e.target.value))}
            className="flex-1"
            disabled={!isPlaying}
          />
          <span className="text-sm text-gray-600 w-12">
            {Math.round(volume * 100)}%
          </span>
        </div>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center space-x-2 mb-2">
            <Activity className="w-4 h-4 text-blue-500" />
            <span className="text-sm font-medium text-gray-700">Frames/s</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{metrics.framesPerSecond}</p>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center space-x-2 mb-2">
            <Signal className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-gray-700">Buffer</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{metrics.queueLength}</p>
        </div>

        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex items-center space-x-2 mb-2">
            <Volume2 className="w-4 h-4 text-purple-500" />
            <span className="text-sm font-medium text-gray-700">RMS</span>
          </div>
          <p className="text-2xl font-bold text-gray-900">{metrics.rms.toFixed(4)}</p>
        </div>
      </div>

      {/* Visualizador simple */}
      {isPlaying && (
        <div className="mb-6 h-24 bg-gray-900 rounded-lg flex items-center justify-center overflow-hidden">
          <div 
            className="bg-blue-500 transition-all duration-100 rounded"
            style={{ 
              width: '4px',
              height: `${Math.min(metrics.rms * 200, 100)}%` 
            }}
          />
        </div>
      )}

      {/* Logs */}
      <div className="bg-gray-50 rounded-lg p-4 max-h-48 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Registro</h3>
        <div className="space-y-1 font-mono text-xs text-gray-600">
          {logs.map((log, i) => (
            <div key={i}>{log}</div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AudioPlayerComponent;
