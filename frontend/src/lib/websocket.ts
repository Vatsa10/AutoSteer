const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

export type WSEvent =
  | { type: "routing"; stage: string; department?: string; agent?: string }
  | { type: "token"; content: string }
  | { type: "metadata"; conversation_id: string; agent?: string; department?: string; model?: string }
  | { type: "error"; message: string }
  | { type: "done" };

interface WSCallbacks {
  onEvent: (event: WSEvent) => void;
  onOpen?: () => void;
  onError?: (error: Event) => void;
  onClose?: (error: boolean) => void;
}

export function createChatWebSocket(callbacks: WSCallbacks): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/chat`);
  let doneReceived = false;
  let pingInterval: ReturnType<typeof setInterval> | null = null;

  function stopPing() {
    if (pingInterval) { clearInterval(pingInterval); pingInterval = null; }
  }

  ws.onopen = () => {
    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25_000);
    callbacks.onOpen?.();
  };

  ws.onmessage = (msg: MessageEvent) => {
    try {
      const data = JSON.parse(msg.data);
      if (data.type === "pong") return;
      if (data.type === "done") doneReceived = true;
      callbacks.onEvent(data as WSEvent);
    } catch {
      callbacks.onEvent({ type: "token", content: msg.data });
    }
  };

  ws.onerror = (err) => {
    stopPing();
    callbacks.onError?.(err);
  };

  ws.onclose = () => {
    stopPing();
    callbacks.onClose?.(!doneReceived);
  };

  return ws;
}

export function sendWSMessage(
  ws: WebSocket | null,
  message: string,
  conversationId?: string,
  targetAgent?: string,
  fileIds?: string[],
  files?: { filename: string; content: string; mime_type: string }[],
) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  const prefs = (() => { try { const s = localStorage.getItem("autosteer_preferences"); return s ? JSON.parse(s) : null; } catch { return null; } })();
  ws.send(
    JSON.stringify({
      message,
      conversation_id: conversationId,
      target_agent: targetAgent || null,
      file_ids: fileIds || null,
      files: files || null,
      preferences: prefs,
    }),
  );
}
