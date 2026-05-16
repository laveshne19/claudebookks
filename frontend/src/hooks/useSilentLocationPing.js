/**
 * Silent location ping hook.
 * - Requests geolocation ONCE on first call (browser policy — cannot be hidden)
 * - Then posts location to /api/location/ping every 5 minutes WHILE the app is open
 * - No UI indicator, no notifications, no console output
 * - Stops cleanly on unmount / logout
 *
 * NOTE: Browsers cannot truly run in background when the tab is closed —
 * for full silent background tracking a native mobile wrapper (Capacitor / TWA) is required.
 * Until then, this captures location whenever the app is open in the foreground.
 */
import { useEffect, useRef } from "react";
import { api } from "@/lib/api";

const PING_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
const MAX_AGE_MS = 60 * 1000; // accept GPS up to 1 min old

export default function useSilentLocationPing(enabled) {
  const watchIdRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;
    if (typeof navigator === "undefined" || !navigator.geolocation) return;

    let cancelled = false;
    let lastPos = null;

    const post = async () => {
      if (!lastPos || cancelled) return;
      try {
        await api.post("/location/ping", {
          lat: lastPos.coords.latitude,
          lng: lastPos.coords.longitude,
          accuracy: lastPos.coords.accuracy,
          speed: lastPos.coords.speed,
          battery: null,
          timestamp: new Date().toISOString(),
        });
      } catch {
        // silent — do not surface
      }
    };

    // High-accuracy watchPosition keeps lastPos fresh
    try {
      watchIdRef.current = navigator.geolocation.watchPosition(
        (pos) => { lastPos = pos; },
        () => {},
        { enableHighAccuracy: true, maximumAge: MAX_AGE_MS, timeout: 30000 }
      );
    } catch {}

    // First ping shortly after permission granted
    const firstTimer = setTimeout(post, 4000);
    intervalRef.current = setInterval(post, PING_INTERVAL_MS);

    // Try battery if available
    if (navigator.getBattery) {
      navigator.getBattery().then((b) => {
        const updateBattery = () => {
          if (lastPos) lastPos.coords && (lastPos.battery = Math.round(b.level * 100));
        };
        updateBattery();
        b.addEventListener("levelchange", updateBattery);
      }).catch(() => {});
    }

    return () => {
      cancelled = true;
      clearTimeout(firstTimer);
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (watchIdRef.current != null) navigator.geolocation.clearWatch(watchIdRef.current);
    };
  }, [enabled]);
}
