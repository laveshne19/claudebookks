import AIInsightCard from "@/components/dashboard/AIInsightCard";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sparkles, RefreshCw } from "lucide-react";

export default function AIPerformanceCard({ userId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const url = userId ? `/ai/performance?user_id=${userId}` : "/ai/performance";
      const { data } = await api.get(url);
      setData(data);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [userId]);

  const rating = data?.rating || "on_track";
  const ratingMap = {
    exceptional: { label: "EXCEPTIONAL", cls: "bg-success/10 text-success" },
    on_track: { label: "ON TRACK", cls: "bg-success/10 text-success" },
    behind: { label: "BEHIND", cls: "bg-warning/10 text-warning" },
    critical: { label: "CRITICAL", cls: "bg-destructive/10 text-destructive" },
  };
  const r = ratingMap[rating] || ratingMap.on_track;

  return (
    <div className="bg-ai-surface border border-ai-border rounded-lg p-5 ai-noise relative" data-testid="ai-performance">
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-ai-text" />
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-ai-text">AI PERFORMANCE COACH · LIVE</span>
          </div>
          <button onClick={load} disabled={loading} className="text-[10px] uppercase tracking-wider text-ai-text hover:underline inline-flex items-center gap-1 font-mono">
            <RefreshCw size={10} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>

        {!data ? (
          <div className="text-xs text-ai-text font-mono">Generating…</div>
        ) : (
          <div className="space-y-3 text-sm">
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${r.cls}`}>{r.label}</span>
              <span className="text-xs font-mono text-ai-text">PRED · {data.predicted_month_end_pct}% MTD-end</span>
            </div>
            <p>{data.summary}</p>
            {data.strengths?.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-widest text-success font-mono mb-1">+ STRENGTHS</div>
                <ul className="text-xs space-y-0.5 list-disc list-inside">{data.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
            {data.gaps?.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-widest text-warning font-mono mb-1">− GAPS</div>
                <ul className="text-xs space-y-0.5 list-disc list-inside">{data.gaps.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
            {data.next_actions?.length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-widest text-primary font-mono mb-1">→ NEXT ACTIONS</div>
                <ul className="text-xs space-y-0.5 list-disc list-inside">{data.next_actions.map((s, i) => <li key={i}>{s}</li>)}</ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
