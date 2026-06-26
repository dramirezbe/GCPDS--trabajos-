import { WebSocketServer, WebSocket } from 'ws';
import { IncomingMessage } from 'http';
import { Server } from 'http';
import OpusScript from 'opusscript';

interface OpusFrameHeader {
  magic: number;      // 0x4F505530 ('OPU0')
  seq: number;
  sampleRate: number;
  channels: number;
  payloadLen: number;
}

interface PCMFrameHeader {
  magic: number;      // 0x41554430 ('AUD0')
  seq: number;
  sampleRate: number;
  channels: number;
  samples: number;
}

interface SensorMetrics {
  in: number;
  inB: number;
  out: number;
  outB: number;
  t0: number;
}

const OPUS_MAGIC = 0x4F505530;  // 'OPU0'
const PCM_MAGIC = 0x41554430;   // 'AUD0'
const SAMPLE_RATE = 48000;
const CHANNELS = 1;
const FRAME_SAMPLES = 960;      // 20 ms @ 48k

// Estado global
const listeners: Map<string, Set<WebSocket>> = new Map();
const lastConfig: Map<string, string> = new Map();
const decoders: Map<string, OpusScript> = new Map();
const metrics: Map<string, SensorMetrics> = new Map();

function getMetrics(sensorId: string): SensorMetrics {
  if (!metrics.has(sensorId)) {
    metrics.set(sensorId, { in: 0, inB: 0, out: 0, outB: 0, t0: Date.now() });
  }
  return metrics.get(sensorId)!;
}

function maybeLogMetrics(sensorId: string) {
  const m = getMetrics(sensorId);
  const now = Date.now();
  const dt = (now - m.t0) / 1000;
  
  if (dt >= 1.0) {
    const li = listeners.get(sensorId)?.size || 0;
    console.log(
      `[AUDIO][${sensorId}] IN ${m.in}/s ${(m.inB / 1024).toFixed(1)} KiB/s | ` +
      `OUT ${m.out}/s ${(m.outB / 1024).toFixed(1)} KiB/s | listeners=${li}`
    );
    m.in = m.inB = m.out = m.outB = 0;
    m.t0 = now;
  }
}

function parseOpusHeader(buffer: Buffer): OpusFrameHeader | null {
  if (buffer.length < 16) return null;
  
  return {
    magic: buffer.readUInt32BE(0),
    seq: buffer.readUInt32BE(4),
    sampleRate: buffer.readUInt32BE(8),
    channels: buffer.readUInt16BE(12),
    payloadLen: buffer.readUInt16BE(14)
  };
}

function buildPCMFrame(seq: number, pcmData: Buffer): Buffer {
  // Header: 16 bytes
  const header = Buffer.allocUnsafe(16);
  header.writeUInt32BE(PCM_MAGIC, 0);       // magic
  header.writeUInt32BE(seq, 4);              // seq
  header.writeUInt32BE(SAMPLE_RATE, 8);     // sample_rate
  header.writeUInt16BE(CHANNELS, 12);       // channels
  header.writeUInt16BE(FRAME_SAMPLES, 14);  // samples
  
  return Buffer.concat([header, pcmData]);
}

function handleSensorConnection(ws: WebSocket, sensorId: string) {
  console.log(`[AUDIO] Sensor conectado: ${sensorId}`);
  
  // 🎯 Inicializar decoder con configuración por defecto automáticamente
  const defaultConfig = JSON.stringify({
    codec: 'opus',
    sample_rate: SAMPLE_RATE,
    channels: CHANNELS
  });
  
  let decoder = new OpusScript(SAMPLE_RATE, CHANNELS);
  decoders.set(sensorId, decoder);
  lastConfig.set(sensorId, defaultConfig);
  
  console.log(`[AUDIO] Decoder inicializado con config por defecto: ${defaultConfig}`);
  
  // Enviar config PCM a listeners existentes
  const pcmConfig = defaultConfig.replace('"codec":"opus"', '"codec":"pcm_s16le"');
  const sensorListeners = listeners.get(sensorId);
  if (sensorListeners) {
    sensorListeners.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(pcmConfig);
      }
    });
  }

  ws.on('message', (data: Buffer | string) => {
    // Mensaje opcional: config JSON (sobrescribe defaults)
    if (typeof data === 'string') {
      try {
        const config = data.toString();
        const parsed = JSON.parse(config);
        
        // Si viene nueva config, recrear decoder
        if (parsed.sample_rate || parsed.channels || parsed.codec) {
          const newSampleRate = parsed.sample_rate || SAMPLE_RATE;
          const newChannels = parsed.channels || CHANNELS;
          
          decoder = new OpusScript(newSampleRate, newChannels);
          decoders.set(sensorId, decoder);
          lastConfig.set(sensorId, config);
          
          console.log(`[AUDIO] Config actualizada ${sensorId}: ${config}`);
          
          // Reenviar a listeners
          const pcmCfg = config.replace('"codec":"opus"', '"codec":"pcm_s16le"');
          const listeners = sensorListeners;
          if (listeners) {
            listeners.forEach(client => {
              if (client.readyState === WebSocket.OPEN) {
                client.send(pcmCfg);
              }
            });
          }
        }
      } catch (err) {
        console.error(`[AUDIO] Error parseando config JSON: ${err}`);
      }
      return;
    }

    // Mensajes siguientes: frames Opus binarios
    if (!(data instanceof Buffer)) return;
    
    const m = getMetrics(sensorId);
    m.in += 1;
    m.inB += data.length;

    // Parsear header Opus
    const header = parseOpusHeader(data);
    if (!header || header.magic !== OPUS_MAGIC) return;

    // Extraer payload Opus
    const opusPayload = data.subarray(16, 16 + header.payloadLen);
    if (opusPayload.length !== header.payloadLen) return;

    // Decodificar Opus → PCM
    if (!decoder) return;
    
    try {
      const pcmData = decoder.decode(opusPayload);
      
      // Construir frame PCM con header
      const pcmFrame = buildPCMFrame(header.seq, Buffer.from(pcmData.buffer));

      // Broadcast a todos los listeners
      const sensorListeners = listeners.get(sensorId);
      if (sensorListeners) {
        const dead: WebSocket[] = [];
        
        sensorListeners.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            try {
              client.send(pcmFrame);
              m.out += 1;
              m.outB += pcmFrame.length;
            } catch (err) {
              dead.push(client);
            }
          } else {
            dead.push(client);
          }
        });

        // Limpiar listeners muertos
        dead.forEach(client => sensorListeners.delete(client));
      }

      maybeLogMetrics(sensorId);
    } catch (err) {
      console.error(`[AUDIO] Error decodificando Opus:`, err);
    }
  });

  ws.on('close', () => {
    console.log(`[AUDIO] Sensor desconectado: ${sensorId}`);
    decoders.delete(sensorId);
  });

  ws.on('error', (err) => {
    console.error(`[AUDIO] Error en sensor ${sensorId}:`, err);
  });
}

function handleListenerConnection(ws: WebSocket, sensorId: string) {
  // Registrar listener
  if (!listeners.has(sensorId)) {
    listeners.set(sensorId, new Set());
  }
  listeners.get(sensorId)!.add(ws);
  
  console.log(
    `[AUDIO] Listener conectado a ${sensorId}. Total=${listeners.get(sensorId)!.size}`
  );

  // Enviar config guardada (si existe)
  const config = lastConfig.get(sensorId);
  if (config) {
    const pcmConfig = config.replace('"codec":"opus"', '"codec":"pcm_s16le"');
    ws.send(pcmConfig);
  }

  // Mantener conexión viva (ping/pong)
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping();
    }
  }, 30000); // 30 segundos

  ws.on('message', (data) => {
    // Los listeners pueden enviar ping/pong
    if (data.toString() === 'ping') {
      ws.send('pong');
    }
  });

  ws.on('close', () => {
    clearInterval(pingInterval);
    listeners.get(sensorId)?.delete(ws);
    console.log(
      `[AUDIO] Listener salió de ${sensorId}. Total=${listeners.get(sensorId)?.size || 0}`
    );
  });

  ws.on('error', (err) => {
    console.error(`[AUDIO] Error en listener ${sensorId}:`, err);
  });
}

export function setupAudioWebSocket(server: Server) {
  const wss = new WebSocketServer({ noServer: true });

  // Manejar upgrade de HTTP a WebSocket
  server.on('upgrade', (request: IncomingMessage, socket, head) => {
    const url = new URL(request.url!, `http://${request.headers.host}`);
    
    // Rutas WebSocket para audio
    if (url.pathname.startsWith('/ws/audio/sensor/')) {
      const sensorId = url.pathname.split('/').pop()!;
      
      wss.handleUpgrade(request, socket, head, (ws) => {
        handleSensorConnection(ws, sensorId);
      });
    } else if (url.pathname.startsWith('/ws/audio/listen/')) {
      const sensorId = url.pathname.split('/').pop()!;
      
      wss.handleUpgrade(request, socket, head, (ws) => {
        handleListenerConnection(ws, sensorId);
      });
    }
  });

  console.log('🎵 Audio WebSocket server initialized');
  console.log('   Sensor ingest: ws://host/ws/audio/sensor/{sensor_id}');
  console.log('   Listen stream: ws://host/ws/audio/listen/{sensor_id}');
}

// Health check para verificar estado
export function getAudioServerStatus() {
  const sensorsConnected = decoders.size;
  const totalListeners = Array.from(listeners.values())
    .reduce((sum, set) => sum + set.size, 0);
  
  return {
    ok: true,
    sensorsConnected,
    totalListeners,
    sensors: Array.from(listeners.keys()).map(id => ({
      id,
      listeners: listeners.get(id)?.size || 0,
      hasConfig: lastConfig.has(id),
      hasDecoder: decoders.has(id)
    }))
  };
}
