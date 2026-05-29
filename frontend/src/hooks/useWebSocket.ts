import { useEffect, useRef, useState, useCallback } from "react";

const WS_BASE = import.meta.env.VITE_API_URL?.replace("http", "ws") || "ws://localhost:8000";

export function useTicketWebSocket(ticketId: string | null) {
  const ws = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!ticketId) return;

    const socket = new WebSocket(`${WS_BASE}/tickets/${ticketId}/ws`);
    ws.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    return () => {
      socket.close();
    };
  }, [ticketId]);

  const sendAgentMessage = useCallback((content: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ content }));
    }
  }, []);

  return { messages, connected, sendAgentMessage };
}