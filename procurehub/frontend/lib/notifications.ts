import { notification as toast } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, apiFetch, AppNotification, ensureAccessToken, streamNotifications } from "@/lib/api";

const RECONNECT_DELAY_MS = 3000;

type Inbox = { count: number; unread_count: number; results: AppNotification[] };

function sleep(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve) => {
    const timer = window.setTimeout(resolve, ms);
    signal.addEventListener("abort", () => { window.clearTimeout(timer); resolve(); }, { once: true });
  });
}

/** Hộp thư thông báo: tải qua REST, nhận mới qua SSE; mất kết nối thì nối lại với id cuối (NFR-REL-05). */
export function useNotifications(enabled: boolean) {
  const [items, setItems] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [live, setLive] = useState(false);
  const lastIdRef = useRef(0);

  const reload = useCallback(async () => {
    const inbox = await apiFetch<Inbox>("/notifications?limit=20");
    setItems(inbox.results);
    setUnread(inbox.unread_count);
    lastIdRef.current = Math.max(lastIdRef.current, ...inbox.results.map((item) => item.id), 0);
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    const controller = new AbortController();
    const onNotification = (item: AppNotification) => {
      lastIdRef.current = Math.max(lastIdRef.current, item.id);
      setItems((current) => [item, ...current.filter((existing) => existing.id !== item.id)].slice(0, 20));
      setUnread((count) => count + 1);
      toast.info({ message: item.title, placement: "bottomRight", duration: 4 });
    };
    async function run() {
      try { await reload(); } catch { /* vẫn thử mở stream */ }
      while (!controller.signal.aborted) {
        try {
          setLive(true);
          lastIdRef.current = await streamNotifications(lastIdRef.current, onNotification, controller.signal);
        } catch (err) {
          setLive(false);
          if (controller.signal.aborted) break;
          if (err instanceof ApiError && err.status === 401) {
            try { await ensureAccessToken(true); } catch { break; }
          }
          await sleep(RECONNECT_DELAY_MS, controller.signal);
        }
      }
      setLive(false);
    }
    void run();
    return () => controller.abort();
  }, [enabled, reload]);

  const markRead = useCallback(async (item: AppNotification) => {
    if (item.read_at) return;
    await apiFetch(`/notifications/${item.id}/read`, { method: "POST", body: JSON.stringify({}) });
    setItems((current) => current.map((existing) => existing.id === item.id ? { ...existing, read_at: new Date().toISOString() } : existing));
    setUnread((count) => Math.max(count - 1, 0));
  }, []);

  const markAllRead = useCallback(async () => {
    await apiFetch("/notifications/read-all", { method: "POST", body: JSON.stringify({}) });
    setItems((current) => current.map((existing) => ({ ...existing, read_at: existing.read_at ?? new Date().toISOString() })));
    setUnread(0);
  }, []);

  return { items, unread, live, reload, markRead, markAllRead };
}
