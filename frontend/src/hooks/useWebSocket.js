import { useEffect, useRef, useCallback, useState } from 'react';

// 后端地址：本地开发留空（同源走 vite proxy），生产由 VITE_API_BASE_URL 指向腾讯云后端
const _RAW_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

function wsUrl(path) {
  if (!_RAW_BASE) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${path}`;
  }
  try {
    const url = new URL(_RAW_BASE);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}${path}`;
  } catch {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${path}`;
  }
}

export function useTaskWebSocket(taskId) {
  const wsRef = useRef(null);
  const [status, setStatus] = useState(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    if (!taskId) return;
    const ws = new WebSocket(wsUrl(`/ws/task/${taskId}`));
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
    const ws = new WebSocket(wsUrl('/ws/all'));
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
