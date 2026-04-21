import { useState, useEffect, useRef, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Volume2, VolumeX, Activity, Radio } from 'lucide-react';
import { createSignalingClient, SignalingClient } from '../utils/signaling';

interface WebRTCAudioPlayerProps {
  sensorId: string;
  wsUrl?: string;
  demodType?: string;
  demodMetrics?: {
    excursion_hz?: number;
    depth?: number;
  };
}

export interface WebRTCAudioPlayerRef {
  startWebRTC: () => void;
  stopWebRTC: () => void;
}

interface AudioMetrics {
  isPlaying: boolean;
  isConnected: boolean;
  iceConnectionState: string;
  signalingState: string;
}

const WebRTCAudioPlayer = forwardRef<WebRTCAudioPlayerRef, WebRTCAudioPlayerProps>(({ 
  sensorId,
  wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:12443`,
  demodType,
  demodMetrics
}, ref) => {
  const [isStarted, setIsStarted] = useState(false);
  const [metrics, setMetrics] = useState<AudioMetrics>({
    isPlaying: false,
    isConnected: false,
    iceConnectionState: 'new',
    signalingState: 'stable'
  });
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  // Referencias para WebRTC y Signaling
  const signalingRef = useRef<SignalingClient | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  // Estado para manejo de candidatos
  const remoteDescSetRef = useRef(false);
  const pendingRemoteCandidatesRef = useRef<any[]>([]);
  const pendingLocalCandidatesRef = useRef<any[]>([]);

  // Audio Analysis Refs & State - REMOVED

  const addLog = useCallback((msg: string) => {
    console.log(msg);
    setLogs(prev => [...prev.slice(-15), `${new Date().toLocaleTimeString()}: ${msg}`]);
  }, []);

  // Exponer métodos para control externo
  useImperativeHandle(ref, () => ({
    startWebRTC: () => startWebRTC(),
    stopWebRTC: () => { cleanup(); setIsStarted(false); }
  }));

  // Limpiar conexiones
  const cleanup = useCallback(() => {
    if (signalingRef.current) {
      signalingRef.current.close();
      signalingRef.current = null;
    }
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.srcObject = null;
    }
    
    // Reset state refs
    remoteDescSetRef.current = false;
    pendingRemoteCandidatesRef.current = [];
    pendingLocalCandidatesRef.current = [];

    setMetrics({
      isPlaying: false,
      isConnected: false,
      iceConnectionState: 'closed',
      signalingState: 'closed'
    });
  }, []);

  // Helper functions for candidate handling
  const flushRemoteCandidates = useCallback(async () => {
    if (!remoteDescSetRef.current || !pcRef.current) return;
    for (const c of pendingRemoteCandidatesRef.current) {
      try {
        await pcRef.current.addIceCandidate(c);
      } catch (e) {
        addLog(`[client] addIceCandidate(flush) failed: ${e}`);
      }
    }
    pendingRemoteCandidatesRef.current = [];
  }, [addLog]);

  const addRemoteCandidateSafe = useCallback(async (c: any) => {
    if (!remoteDescSetRef.current) {
      pendingRemoteCandidatesRef.current.push(c);
      addLog(`[client] Queued remote candidate (remote desc not set). Queued=${pendingRemoteCandidatesRef.current.length}`);
      return;
    }
    if (pcRef.current) {
      try {
        await pcRef.current.addIceCandidate(c);
      } catch (e) {
        addLog(`[client] addIceCandidate failed: ${e}`);
      }
    }
  }, [addLog]);

  const flushLocalCandidates = useCallback(() => {
    if (!signalingRef.current || !signalingRef.current.isOpen()) return;
    if (pendingLocalCandidatesRef.current.length === 0) return;
    
    addLog(`[client] Flushing ${pendingLocalCandidatesRef.current.length} local candidates`);
    for (const msg of pendingLocalCandidatesRef.current) {
      signalingRef.current.send(msg);
    }
    pendingLocalCandidatesRef.current = [];
  }, [addLog]);

  // Iniciar conexión WebRTC
  const startWebRTC = useCallback(async () => {
    if (isStarted) return;
    setIsStarted(true);

    addLog(`Iniciando cliente WebRTC para sensor ${sensorId}`);

    // Crear RTCPeerConnection
    const pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        // Add TURN servers here if needed for LTE
      ]
    });
    pcRef.current = pc;

    // ICE candidate handler
    pc.onicecandidate = (ev) => {
      if (ev.candidate) {
        const msg = {
          type: 'candidate',
          candidate: ev.candidate.candidate,
          mlineindex: ev.candidate.sdpMLineIndex
        };

        if (signalingRef.current && signalingRef.current.isOpen()) {
          signalingRef.current.send(msg);
        } else {
          pendingLocalCandidatesRef.current.push(msg);
        }
      }
    };

    // Track handler - cuando llega el audio
    pc.ontrack = (ev) => {
      addLog('[client] Audio track recibido');
      if (audioRef.current) {
        audioRef.current.srcObject = ev.streams[0];
        audioRef.current.play().catch(err => addLog(`[audio] Play blocked: ${err}`));
        setMetrics(prev => ({ ...prev, isPlaying: true }));
      }
    };

    // Estado de conexión ICE
    pc.oniceconnectionstatechange = () => {
      addLog(`[client] ICE state: ${pc.iceConnectionState}`);
      setMetrics(prev => ({ ...prev, iceConnectionState: pc.iceConnectionState }));
    };

    // Estado de señalización
    pc.onsignalingstatechange = () => {
      addLog(`[client] Signaling state: ${pc.signalingState}`);
      setMetrics(prev => ({ ...prev, signalingState: pc.signalingState }));
    };

    // Inicializar cliente de señalización robusto
    signalingRef.current = createSignalingClient({
      sensorId,
      wsUrlBase: wsUrl,
      log: addLog,
      onConnected: () => {
        setMetrics(prev => ({ ...prev, isConnected: true }));
        flushLocalCandidates();
      },
      onDisconnected: () => {
        setMetrics(prev => ({ ...prev, isConnected: false }));
      },
      onMessage: async (msg) => {
        if (!pcRef.current) return;

        if (msg.type === 'offer') {
          addLog('[client] Oferta recibida del sensor');
          await pcRef.current.setRemoteDescription({ type: 'offer', sdp: msg.sdp });
          
          remoteDescSetRef.current = true;
          await flushRemoteCandidates();

          const answer = await pcRef.current.createAnswer();
          await pcRef.current.setLocalDescription(answer);
          
          if (signalingRef.current) {
            signalingRef.current.send({ type: 'answer', sdp: answer.sdp });
            addLog('[client] Answer enviado al sensor');
            flushLocalCandidates();
          }
        } else if (msg.type === 'candidate') {
          await addRemoteCandidateSafe({
            candidate: msg.candidate,
            sdpMLineIndex: msg.mlineindex
          });
        } else if (msg.type === 'pong') {
          // Heartbeat response (optional logging)
        }
      }
    });

    signalingRef.current.connect();

  }, [sensorId, wsUrl, addLog, isStarted, flushRemoteCandidates, addRemoteCandidateSafe, flushLocalCandidates]);

  // Manejar volumen
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Audio Analysis Effect - REMOVED
  useEffect(() => {
    // Local analysis removed in favor of sensor-provided metrics
  }, []);

  // Use props metrics directly
  const displayMetrics = demodMetrics;

  // Cleanup al desmontar
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  const toggleMute = () => setIsMuted(!isMuted);

  return (
    <div className="bg-white rounded-lg shadow-md p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          Audio en Tiempo Real (WebRTC)
        </h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${metrics.isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
          <span className="text-xs text-gray-600">
            {metrics.isConnected ? 'Conectado' : 'Desconectado'}
          </span>
        </div>
      </div>

      {/* Contenedor principal flex */}
      <div className="flex flex-col md:flex-row gap-4">
        {/* Columna Izquierda: Audio y controles */}
        <div className="flex-1">
          <audio
            ref={audioRef}
            autoPlay
            controls
            className="w-full mb-3"
          />

          {/* Controles de volumen */}
          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100 mb-3">
            <div className="flex items-center gap-3">
              <button
                onClick={toggleMute}
                className="p-1.5 hover:bg-gray-200 rounded-full transition-colors text-gray-600"
              >
                {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={isMuted ? 0 : volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
              <span className="text-sm font-medium text-gray-600 w-12 text-right">
                {Math.round((isMuted ? 0 : volume) * 100)}%
              </span>
            </div>
          </div>

          {/* Métricas de conexión (Compactas) */}
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="bg-gray-50 p-2 rounded border border-gray-100">
              <span className="text-gray-500 block mb-0.5">ICE</span>
              <span className="font-mono font-semibold text-gray-700">{metrics.iceConnectionState}</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100">
              <span className="text-gray-500 block mb-0.5">Señal</span>
              <span className="font-mono font-semibold text-gray-700">{metrics.signalingState}</span>
            </div>
            <div className="bg-gray-50 p-2 rounded border border-gray-100">
              <span className="text-gray-500 block mb-0.5">Estado</span>
              <span className={`font-semibold ${metrics.isPlaying ? 'text-green-600' : 'text-gray-500'}`}>
                {metrics.isPlaying ? 'Audio OK' : 'Esperando'}
              </span>
            </div>
          </div>
        </div>

        {/* Columna Derecha: Métricas de demodulación */}
        {demodType && displayMetrics && (
          <div className="w-full md:w-64 flex-shrink-0">
            {demodType === 'FM' && displayMetrics.excursion_hz !== undefined && (
              <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg p-4 border border-blue-200 h-full shadow-sm">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-blue-100">
                  <Radio className="text-blue-600" size={20} />
                  <h4 className="text-sm font-bold text-blue-900">Análisis FM</h4>
                </div>
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-blue-600 uppercase font-semibold tracking-wider">Excursión</span>
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-mono font-bold text-blue-700">
                        {(displayMetrics.excursion_hz / 1000).toFixed(1)}
                      </span>
                      <span className="text-sm text-blue-600 font-medium">kHz</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {demodType === 'AM' && displayMetrics.depth !== undefined && (
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200 h-full shadow-sm">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-green-100">
                  <Activity className="text-green-600" size={20} />
                  <h4 className="text-sm font-bold text-green-900">Análisis AM</h4>
                </div>
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-green-600 uppercase font-semibold tracking-wider">Profundidad</span>
                    <div className="flex items-baseline gap-1">
                      <span className="text-2xl font-mono font-bold text-green-700">
                        {displayMetrics.depth.toFixed(1)}
                      </span>
                      <span className="text-sm text-green-600 font-medium">%</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Console de logs (colapsado) */}
      {logs.length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">Ver logs ({logs.length})</summary>
          <div className="mt-2 bg-gray-900 rounded p-2 text-xs font-mono text-green-400 max-h-32 overflow-y-auto">
            {logs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
});

WebRTCAudioPlayer.displayName = 'WebRTCAudioPlayer';

export default WebRTCAudioPlayer;
