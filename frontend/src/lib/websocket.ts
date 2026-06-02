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
  onError?: (error: Event) => void;
  onClose?: () => void;
}

export function createChatWebSocket(callbacks: WSCallbacks): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/chat`);

  ws.onmessage = (msg: MessageEvent) => {
    try {
      const data = JSON.parse(msg.data);
      callbacks.onEvent(data as WSEvent);
    } catch {
      // Non-JSON message — treat as token
      callbacks.onEvent({ type: "token", content: msg.data });
    }
  };

  ws.onerror = (err) => {
    callbacks.onError?.(err);
  };

  ws.onclose = () => {
    callbacks.onClose?.();
  };

  return ws;
}

export function sendWSMessage(
  ws: WebSocket | null,
  message: string,
  conversationId?: string,
  targetAgent?: string,
) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(
    JSON.stringify({
      message,
      conversation_id: conversationId,
      target_agent: targetAgent || null,
    }),
  );
}
