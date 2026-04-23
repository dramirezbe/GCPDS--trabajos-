import { WebSocketServer, WebSocket } from 'ws';
import { Server } from 'http';

let wss: WebSocketServer;
const clients = new Set<WebSocket>();
const audioSubscribers = new Map<WebSocket, { demodType: 'AM' | 'FM' }>();

export function initWebSocket(server: Server) {
  wss = new WebSocketServer({ server, path: '/ws' });

  wss.on('connection', (ws: WebSocket) => {
    clients.add(ws);
    console.log('✅ New WebSocket client connected. Total clients:', clients.size);

    ws.on('message', (message: string) => {
      try {
        const data = JSON.parse(message.toString());
        console.log('Received message from client:', data);
        
        // Manejar suscripción a audio streaming
        if (data.type === 'subscribe_audio') {
          audioSubscribers.set(ws, { demodType: data.demodType });
          console.log(`🎵 Client subscribed to ${data.demodType} audio streaming`);
        } else if (data.type === 'unsubscribe_audio') {
          audioSubscribers.delete(ws);
          console.log('🎵 Client unsubscribed from audio streaming');
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    });

    ws.on('close', () => {
      clients.delete(ws);
      audioSubscribers.delete(ws);
      console.log('❌ WebSocket client disconnected. Total clients:', clients.size);
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
      clients.delete(ws);
      audioSubscribers.delete(ws);
    });

    // Enviar mensaje de bienvenida
    ws.send(JSON.stringify({
      type: 'connected',
      message: 'Connected to ANE WebSocket server'
    }));
  });

  console.log('🔌 WebSocket server initialized on /ws');
}

export function broadcastToClients(data: any) {
  const message = JSON.stringify(data);
  
  clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

export function sendToClient(client: WebSocket, data: any) {
  if (client.readyState === WebSocket.OPEN) {
    client.send(JSON.stringify(data));
  }
}

export function broadcastAudioData(audioData: string, demodType: 'AM' | 'FM') {
  audioSubscribers.forEach((subscription, client) => {
    if (subscription.demodType === demodType && client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({
        type: 'audio_data',
        audio: audioData,
        demodType: demodType,
        timestamp: Date.now()
      }));
    }
  });
}

export function getAudioSubscribers() {
  return audioSubscribers;
}
