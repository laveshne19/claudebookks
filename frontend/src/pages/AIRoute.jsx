import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR } from "@/lib/api";
import { Sparkles, MapPin, RefreshCw, ArrowDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

export default function AIRoute() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    try {
      const { data } = await api.get("/ai/route-plan?max_stops=10");
      setData(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const stops = data?.plan || [];
  const lats = stops.map((s) => s.customer?.lat).filter(Boolean);
  const lngs = stops.map((s) => s.customer?.lng).filter(Boolean);
  const bbox = lats.length
    ? `${Math.min(...lngs) - 0.04},${Math.min(...lats) - 0.04},${Math.max(...lngs) + 0.04},${Math.max(...lats) + 0.04}`
    : "72.7,18.9,73.0,19.3";
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik`;

  return (
    <AppLayout title="Route Planner" subtitle="AI · LIVE data">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-mono text-ai-text">
          <Sparkles size={13} /> {data ? `GENERATED ${new Date(data.generated_at).toLocaleTimeString("en-IN")}` : "GENERATING…"}
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading} data-testid="regenerate-route-btn">
          <RefreshCw size={13} className={`mr-1.5 ${loading ? "animate-spin" : ""}`} /> Regenerate
        </Button>
      </div>

      {data?.summary && (
        <div className="bg-ai-surface border border-ai-border rounded-lg p-5 ai-noise relative mb-6">
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={14} className="text-ai-text" />
              <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-ai-text">CLAUDE ROUTE STRATEGY</span>
            </div>
            <p className="text-sm">{data.summary}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-surface border border-border rounded-lg overflow-hidden">
          <iframe title="Route map" src={mapUrl} className="w-full h-[600px] border-0" data-testid="ai-route-map" />
        </div>

        <div className="lg:col-span-2 bg-surface border border-border rounded-lg p-5 max-h-[600px] overflow-y-auto" data-testid="ai-route-stops">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// PRIORITISED STOPS</div>
          <ol className="space-y-3">
            {stops.map((s, i) => (
              <li
                key={s.customer_id}
                onClick={() => navigate(`/customers/${s.customer_id}`)}
                className="p-3 rounded-md border border-border hover:bg-surface-hover cursor-pointer transition"
                data-testid={`ai-stop-${s.customer_id}`}
              >
                <div className="flex items-start gap-3">
                  <div className="h-7 w-7 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[11px] font-bold font-mono shrink-0">
                    {s.order || i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{s.customer?.name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                      <MapPin size={11} />{s.customer?.area}
                    </div>
                    <div className="mt-2 text-xs text-foreground">{s.reason}</div>
                    <div className="mt-2 flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider">
                      <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary">{s.objective}</span>
                      {s.suggested_time && <span className="text-muted-foreground">@ {s.suggested_time}</span>}
                    </div>
                    <div className="mt-2 flex gap-3 text-[10px] font-mono">
                      <span className="text-muted-foreground">Out:</span><span className="tabular">{formatINR(s.customer?.outstanding)}</span>
                      {s.customer?.overdue > 0 && <><span className="text-destructive">Overdue:</span><span className="tabular text-destructive">{formatINR(s.customer.overdue)}</span></>}
                    </div>
                  </div>
                </div>
                {i < stops.length - 1 && (
                  <div className="flex justify-center mt-2 mb-[-4px] text-muted-foreground"><ArrowDown size={12} /></div>
                )}
              </li>
            ))}
            {stops.length === 0 && !loading && <div className="text-xs text-muted-foreground py-4">No mappable customers</div>}
          </ol>
        </div>
      </div>
    </AppLayout>
  );
}
