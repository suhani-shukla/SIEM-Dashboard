// FILE LOCATION: frontend/src/hooks/useSSE.js
import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "../api/client";

/**
 * Subscribes to the /alerts/stream SSE endpoint (Phase 4).
 * Returns { connected, alerts, lastAlertAt } and auto-reconnects with
 * backoff if the connection drops.
 */
export function useAlertStream({ maxBuffered = 50 } = {}) {
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [lastAlertAt, setLastAlertAt] = useState(null);
  const sourceRef = useRef(null);
  const retryRef = useRef(1000);

  const connect = useCallback(() => {
    const es = new EventSource(api.alertsStreamUrl());
    sourceRef.current = es;

    es.onopen = () => {
      setConnected(true);
      retryRef.current = 1000;
    };

    es.addEventListener("new_alert", (e) => {
      try {
        const alert = JSON.parse(e.data);
        setAlerts((prev) => [alert, ...prev].slice(0, maxBuffered));
        setLastAlertAt(Date.now());
      } catch {
        // ignore malformed payloads
      }
    });

    es.onerror = () => {
      setConnected(false);
      es.close();
      const delay = Math.min(retryRef.current, 15000);
      retryRef.current = delay * 1.5;
      setTimeout(connect, delay);
    };
  }, [maxBuffered]);

  useEffect(() => {
    connect();
    return () => sourceRef.current?.close();
  }, [connect]);

  return { connected, alerts, lastAlertAt };
}
