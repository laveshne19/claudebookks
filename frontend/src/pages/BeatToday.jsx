import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR, formatINRFull } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Calendar, MapPin, CheckCircle2, Phone, MessageSquare, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

function TierBadge({ tier }) {
  const map = {
    PLATINUM: "bg-zinc-200 text-zinc-900 dark:bg-zinc-300 dark:text-zinc-900",
    DIAMOND:  "bg-sky-100 text-sky-900 dark:bg-sky-300 dark:text-sky-950",
    GOLD:     "bg-amber-100 text-amber-900 dark:bg-amber-300 dark:text-amber-950",
    SILVER:   "bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-100",
  };
  const cls = map[tier] || "bg-muted text-muted-foreground";
  return <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${cls}`}>{tier || "—"}</span>;
}

export default function BeatToday() {
  const [data, setData] = useState(null);
  const [visited, setVisited] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    api.get("/beat/today", { signal: controller.signal })
      .then(({ data }) => setData(data))
      .catch((err) => {
        if (err.code === "ERR_CANCELED" || err.name === "CanceledError") return;
      });
    return () => controller.abort();
  }, []);

  async function markVisited(c) {
    if (visited[c.id]) return;
    setVisited((v) => ({ ...v, [c.id]: "saving" }));
    try {
      await api.post("/beat/visit", {
        customer_id: c.id,
        notes: "Beat visit",
        outcome: "followup",
      });
      setVisited((v) => ({ ...v, [c.id]: "done" }));
      toast.success(`Marked visit for ${c.name}`);
    } catch (e) {
      setVisited((v) => { const n = { ...v }; delete n[c.id]; return n; });
      toast.error("Failed to save visit");
    }
  }

  if (!data) return <AppLayout title="Today's Beat" subtitle="Loading…"><div className="text-sm text-muted-foreground">Loading beat plan…</div></AppLayout>;

  const s = data.summary;

  return (
    <AppLayout title={`Today's Beat — ${s.weekday}`} subtitle={`${s.count} stops scheduled · ${s.date}`}>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Total Stops</div>
          <div className="font-display font-black text-2xl tabular mt-1">{s.count}</div>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Platinum</div>
          <div className="font-display font-black text-2xl tabular mt-1">{s.platinum}</div>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Diamond</div>
          <div className="font-display font-black text-2xl tabular mt-1">{s.diamond}</div>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Gold</div>
          <div className="font-display font-black text-2xl tabular mt-1">{s.gold}</div>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">To Recover</div>
          <div className="font-display font-black text-xl tabular mt-1 text-primary">{formatINR(s.total_outstanding)}</div>
        </div>
        <div className="bg-surface border border-border rounded-lg p-4">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono">Overdue</div>
          <div className="font-display font-black text-xl tabular mt-1 text-destructive">{formatINR(s.total_overdue)}</div>
        </div>
      </div>

      <div className="bg-ai-surface border border-ai-border rounded-lg p-5 ai-noise relative mb-6">
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={14} className="text-ai-text" />
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-ai-text">AI · BEAT STRATEGY</span>
          </div>
          <p className="text-sm">
            Visit your <strong>{s.platinum + s.diamond} highest-tier outlets first</strong> — they account for the bulk of recoverable outstanding (₹{(s.total_outstanding / 100000).toFixed(1)}L).
            Cluster nearby stops, prioritise dealers with overdue ledger, and use call-ahead for any far-flung accounts.
          </p>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden" data-testid="beat-list">
        <table className="w-full text-sm">
          <thead className="bg-muted/30">
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">#</th>
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Customer</th>
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Tier</th>
              <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Beat</th>
              <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Outstanding</th>
              <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Last Visit</th>
              <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Action</th>
            </tr>
          </thead>
          <tbody>
            {data.stops.map((c, i) => (
              <tr key={c.id} className={`border-b border-border hover:bg-surface-hover ${visited[c.id] === "done" ? "opacity-50" : ""}`} data-testid={`beat-row-${c.id}`}>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{i + 1}</td>
                <td className="px-4 py-3 cursor-pointer" onClick={() => navigate(`/customers/${c.id}`)}>
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5"><MapPin size={11} />{c.area}</div>
                </td>
                <td className="px-4 py-3"><TierBadge tier={c.tier} /></td>
                <td className="px-4 py-3 text-xs font-mono text-muted-foreground">{c.beat_days || "—"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="font-mono tabular text-sm">{formatINRFull(c.outstanding || 0)}</div>
                  {c.overdue > 0 && <div className="text-[10px] uppercase text-destructive font-mono">+{formatINRFull(c.overdue)} OVD</div>}
                </td>
                <td className="px-4 py-3 text-right text-xs text-muted-foreground font-mono">{c.last_visit_date ? c.last_visit_date.slice(0, 10) : "—"}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end items-center gap-1">
                    {c.phone && (
                      <a href={`tel:${c.phone}`} className="h-7 w-7 rounded border border-border hover:bg-muted flex items-center justify-center" title="Call"><Phone size={12} /></a>
                    )}
                    {c.phone && (
                      <a href={`sms:${c.phone}`} className="h-7 w-7 rounded border border-border hover:bg-muted flex items-center justify-center" title="SMS"><MessageSquare size={12} /></a>
                    )}
                    <Button
                      size="sm"
                      variant={visited[c.id] === "done" ? "outline" : "default"}
                      onClick={() => markVisited(c)}
                      disabled={!!visited[c.id]}
                      className="h-7 text-xs"
                      data-testid={`mark-visit-${c.id}`}
                    >
                      <CheckCircle2 size={12} className="mr-1" />
                      {visited[c.id] === "done" ? "Done" : visited[c.id] === "saving" ? "…" : "Visited"}
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {data.stops.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-12 text-center text-sm text-muted-foreground">
                <Calendar size={24} className="mx-auto mb-2 text-muted-foreground" />
                No customers scheduled for {s.weekday}. Take a well-deserved break or follow up on pending orders.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </AppLayout>
  );
}
