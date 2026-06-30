"use client";

import { getToken } from "./auth";
import type { LiveDetection } from "./types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/events";

export interface LiveClientHandlers {
  onMessage: (msg: LiveDetection) => void;
  onStatus?: (status: "connecting" | "open" | "closed") => void;
}

/** Authenticated WebSocket client with automatic reconnection and backoff. */
export function createLiveClient(handlers: LiveClientHandlers) {
  let socket: WebSocket | null = null;
  let closedByUser = false;
  let backoff = 1000;

  const connect = () => {
    const token = getToken();
    if (!token) return;
    handlers.onStatus?.("connecting");
    const url = `${WS_URL}${WS_URL.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`;
    socket = new WebSocket(url);

    socket.onopen = () => {
      backoff = 1000;
      handlers.onStatus?.("open");
    };
    socket.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as LiveDetection;
        if (data.type === "detection") handlers.onMessage(data);
      } catch {
        /* ignore malformed frames */
      }
    };
    socket.onclose = () => {
      handlers.onStatus?.("closed");
      if (!closedByUser) {
        setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, 15000);
      }
    };
    socket.onerror = () => socket?.close();
  };

  connect();

  return {
    close() {
      closedByUser = true;
      socket?.close();
    },
  };
}
