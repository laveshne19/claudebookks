import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Search, MapPin, Phone } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function Customers() {
  const [list, setList] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    const q = search ? `?search=${encodeURIComponent(search)}` : "";
    api.get(`/customers${q}`).then(({ data }) => setList(data)).finally(() => setLoading(false));
  }, [search]);

  return (
    <AppLayout title="Customers" subtitle={`${list.length} dealers`}>
      <div className="mb-4 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative max-w-md w-full">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name, code, area…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-10"
            data-testid="customer-search-input"
          />
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="customers-table">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Customer</th>
                <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Tier</th>
                <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Beat</th>
                <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Brands</th>
                <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Outstanding</th>
                <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Credit Limit</th>
                <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Risk</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-muted-foreground text-sm">Loading…</td></tr>
              ) : list.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-muted-foreground text-sm">No customers</td></tr>
              ) : list.map((c) => (
                <tr key={c.id} onClick={() => navigate(`/customers/${c.id}`)} className="border-b border-border hover:bg-surface-hover cursor-pointer transition" data-testid={`customer-row-${c.id}`}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{c.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{c.code}</div>
                  </td>
                  <td className="px-4 py-3">{c.tier ? <TierBadge tier={c.tier} /> : <span className="text-xs text-muted-foreground">—</span>}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground font-mono">{c.beat_days || "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {c.brand_preferences?.slice(0, 3).map((b) => (
                        <span key={b} className="text-[10px] font-mono uppercase px-1.5 py-0.5 bg-muted rounded">{b}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular">
                    {formatINR(c.outstanding)}
                    {c.overdue > 0 && <div className="text-[10px] uppercase text-destructive">+{formatINR(c.overdue)} overdue</div>}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular text-muted-foreground">{formatINR(c.credit_limit)}</td>
                  <td className="px-4 py-3 text-right">
                    <RiskBadge score={c.credit_risk_score} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppLayout>
  );
}

function RiskBadge({ score }) {
  let label = "LOW", cls = "bg-success/10 text-success";
  if (score < 40) { label = "HIGH"; cls = "bg-destructive/10 text-destructive"; }
  else if (score < 65) { label = "MED"; cls = "bg-warning/10 text-warning"; }
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${cls}`}>{label} · {score}</span>;
}

function TierBadge({ tier }) {
  const map = {
    PLATINUM: "bg-zinc-200 text-zinc-900 dark:bg-zinc-300 dark:text-zinc-900",
    DIAMOND:  "bg-sky-100 text-sky-900 dark:bg-sky-300 dark:text-sky-950",
    GOLD:     "bg-amber-100 text-amber-900 dark:bg-amber-300 dark:text-amber-950",
    SILVER:   "bg-zinc-100 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-100",
  };
  const cls = map[tier] || "bg-muted text-muted-foreground";
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${cls}`}>{tier}</span>;
}
