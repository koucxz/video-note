import { useEffect, useRef, useCallback, useState } from 'react';
import { API_BASE, getToken } from '../api/client';

// Same-origin builds leave API_BASE empty and keep using window.location.host.
// A cross-origin build injects https://106.55.19.23, which becomes wss://.
const WS_BASE = API_BASE
  ? API_BASE.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

const buildWsUrl = (path) => {
  const token = getToken();
  return `${WS_BASE}${path}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
};

export function useTaskWebSocket(taskId) {
  const wsRef = useRef(null);
  const [status, setStatus] = useState(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (!taskId) return;
    const ws = new WebSocket(buildWsUrl(`/ws/task/${taskId}`));
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setStatus(data);
      } catch {}
    };

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [taskId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return status;
}

export function useGlobalWebSocket() {
  const wsRef = useRef(null);
  const [updates, setUpdates] = useState([]);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(buildWsUrl('/ws/all'));
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        setUpdates(prev => [...prev.slice(-50), data]);
      } catch {}
    };

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return updates;
}
