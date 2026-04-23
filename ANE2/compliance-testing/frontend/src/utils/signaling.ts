
export interface SignalingClient {
  connect: () => void;
  close: () => void;
  send: (obj: any) => void;
  isOpen: () => boolean;
}

export interface SignalingClientOptions {
  sensorId: string;
  wsUrlBase: string; // The base URL (e.g. wss://host:port)
  onMessage: (msg: any) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  log?: (msg: string) => void;
}

export function createSignalingClient({
  sensorId,
  wsUrlBase,
  onMessage,
  onConnected,
  onDisconnected,
  log = console.log,
}: SignalingClientOptions): SignalingClient {
  const WS_PING_MS = 15000;
  const RECONNECT_BASE_MS = 500;
  const RECONNECT_MAX_MS = 8000;

  // Ensure wsUrlBase doesn't have a trailing slash
  const baseUrl = wsUrlBase.endsWith('/') ? wsUrlBase.slice(0, -1) : wsUrlBase;
  const fullWsUrl = `${baseUrl}/ws/signal/${encodeURIComponent(sensorId)}`;

  let ws: WebSocket | null = null;
  let pingTimer: any = null;
  let reconnectTimer: any = null;
  let reconnectAttempt = 0;

  const outbox: string[] = []; // queued JSON strings

  function isOpen() {
    return ws !== null && ws.readyState === WebSocket.OPEN;
  }

  function send(obj: any) {
    const s = JSON.stringify(obj);
    if (isOpen() && ws) {
      try {
        ws.send(s);
      } catch (e) {
        log(`[ws] send failed: ${e}`);
      }
    } else {
      outbox.push(s);
    }
  }

  function flushOutbox() {
    if (!isOpen() || outbox.length === 0 || !ws) return;
    log(`[ws] flushing ${outbox.length} queued messages`);
    while (outbox.length) {
      const msg = outbox.shift();
      if (msg) {
        try {
          ws.send(msg);
        } catch {
          outbox.unshift(msg); // Put back if failed
          break;
        }
      }
    }
  }

  function startPing() {
    stopPing();
    pingTimer = setInterval(() => {
      if (isOpen() && ws) {
        try {
          ws.send(JSON.stringify({ type: "ping", t: Date.now() }));
        } catch {}
      }
    }, WS_PING_MS);
  }

  function stopPing() {
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    const delay = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * (2 ** reconnectAttempt));
    reconnectAttempt += 1;
    log(`[ws] reconnect in ${delay} ms (attempt ${reconnectAttempt})`);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    log(`[ws] connect: ${fullWsUrl}`);
    try {
        ws = new WebSocket(fullWsUrl);
    } catch(e) {
        log(`[ws] creation failed: ${e}`);
        scheduleReconnect();
        return;
    }

    ws.onopen = () => {
      reconnectAttempt = 0;
      log("[ws] open");
      if (onConnected) onConnected();

      // REQUIRED: declare role
      send({ role: "client" });

      flushOutbox();
      startPing();
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        onMessage(msg);
      } catch (e) {
        log(`[ws] bad json: ${e}`);
      }
    };

    ws.onerror = () => {
      log("[ws] error");
      // onclose will trigger reconnect
    };

    ws.onclose = (ev) => {
      log(`[ws] close code=${ev.code} reason=${ev.reason || ""}`);
      if (onDisconnected) onDisconnected();
      stopPing();
      ws = null; 
      scheduleReconnect();
    };
  }

  function close() {
    stopPing();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws) {
      // Prevent onclose triggering reconnect during intentional close
      ws.onclose = null;
      ws.onerror = null;
      try {
        ws.close(1000, "client close");
      } catch {}
      ws = null;
      if (onDisconnected) onDisconnected();
    }
  }

  return { connect, close, send, isOpen };
}
