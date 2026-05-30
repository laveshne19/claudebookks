import { useEffect, useState } from "react";

const OZ = 31.1035;
// Indian retail = global spot + import duty (6%) + GST (3%) + dealer premium.
const INDIA_FACTOR = 1.14;
// 30-May-2026 market fallbacks if APIs are blocked (e.g. CORS in some sandboxes).
const FALLBACK = { gold: 15950, silver: 280 };

export function useMetalRates() {
  const [rates, setRates] = useState(FALLBACK);
  const [live, setLive] = useState(false);
  const [updated, setUpdated] = useState<string>("");

  async function fetchRates() {
    try {
      const [g, s, fx] = await Promise.all([
        fetch("https://api.gold-api.com/price/XAU").then((r) => r.json()),
        fetch("https://api.gold-api.com/price/XAG").then((r) => r.json()),
        fetch("https://api.exchangerate-api.com/v4/latest/USD").then((r) => r.json()),
      ]);
      const usdinr = fx?.rates?.INR;
      if (g?.price && s?.price && usdinr) {
        setRates({
          gold: Math.round((g.price * usdinr * INDIA_FACTOR) / OZ),
          silver: Math.round((s.price * usdinr * INDIA_FACTOR) / OZ),
        });
        setLive(true);
        setUpdated(new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }));
      }
    } catch {
      /* keep fallback */
    }
  }

  useEffect(() => {
    fetchRates();
    const id = setInterval(fetchRates, 3600000); // hourly
    return () => clearInterval(id);
  }, []);

  return { rates, live, updated };
}
