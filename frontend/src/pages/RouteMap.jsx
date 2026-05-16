import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR } from "@/lib/api";
import { MapPin } from "lucide-react";

export default function RouteMap() {
  const [customers, setCustomers] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    api.get("/customers").then(({ data }) => setCustomers(data));
  }, []);

  // Priority: sort by overdue desc + outstanding desc
  const sorted = [...customers]
    .filter((c) => c.lat && c.lng)
    .sort((a, b) => (b.overdue - a.overdue) || (b.outstanding - a.outstanding))
    .slice(0, 15);

  // Build OpenStreetMap embed URL covering Mumbai
  const lats = sorted.map(c => c.lat);
  const lngs = sorted.map(c => c.lng);
  const bbox = sorted.length
    ? `${Math.min(...lngs) - 0.05},${Math.min(...lats) - 0.05},${Math.max(...lngs) + 0.05},${Math.max(...lats) + 0.05}`
    : "72.7,18.9,73.0,19.3";
  const markerParam = selected ? `&marker=${selected.lat},${selected.lng}` : "";
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik${markerParam}`;

  return (
    <AppLayout title="Route Planner" subtitle="AI-prioritised daily plan">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-surface border border-border rounded-lg overflow-hidden">
          <iframe
            title="Customer map"
            src={mapUrl}
            className="w-full h-[600px] border-0"
            data-testid="route-map-iframe"
          />
        </div>
        <div className="bg-surface border border-border rounded-lg p-5 max-h-[600px] overflow-y-auto" data-testid="route-list">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// TODAY'S ROUTE · AI OPTIMISED</div>
          <p className="text-xs text-muted-foreground mb-4">Customers ranked by recovery urgency × visit potential. Click to focus on map.</p>
          <ol className="space-y-2">
            {sorted.map((c, i) => (
              <li
                key={c.id}
                onClick={() => setSelected(c)}
                className={`p-3 rounded-md border cursor-pointer transition ${selected?.id === c.id ? "border-primary bg-primary/5" : "border-border hover:bg-surface-hover"}`}
                data-testid={`route-stop-${c.id}`}
              >
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-[11px] font-bold font-mono shrink-0">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{c.name}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5"><MapPin size={11} />{c.area}</div>
                    <div className="mt-1.5 text-[10px] font-mono uppercase tracking-wider flex gap-2">
                      <span className="text-muted-foreground">Out:</span><span className="tabular">{formatINR(c.outstanding)}</span>
                      {c.overdue > 0 && <><span className="text-destructive">Overdue:</span><span className="tabular text-destructive">{formatINR(c.overdue)}</span></>}
                    </div>
                  </div>
                </div>
              </li>
            ))}
            {sorted.length === 0 && <div className="text-xs text-muted-foreground py-4">No locations available</div>}
          </ol>
        </div>
      </div>
    </AppLayout>
  );
}
