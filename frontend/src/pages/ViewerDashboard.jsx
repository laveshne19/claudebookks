import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR, formatINRFull } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Cell } from "recharts";
import { Activity, TrendingUp, Calendar, Package } from "lucide-react";
import KPICard from "@/components/dashboard/KPICard";

export default function ViewerDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/dashboard/viewer").then(({ data }) => setData(data));
  }, []);

  if (!data) return <AppLayout title="Brand Dashboard"><div className="text-sm text-muted-foreground">Loading…</div></AppLayout>;

  const brandLabel = data.scope.brands.join(", ");

  return (
    <AppLayout title={`${brandLabel} · Partner View`} subtitle={`Read-only · Daily totals · Last ${data.scope.days} days`}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <KPICard testid="viewer-grand-total" title={`${brandLabel} · Total Sale`} value={formatINR(data.totals.grand_total)} icon={Activity} accent="bg-primary/10 text-primary" />
        <KPICard testid="viewer-days" title="Active Days" value={data.totals.day_count} icon={Calendar} />
        <KPICard testid="viewer-avg" title="Avg Daily" value={formatINR(data.totals.avg_daily)} icon={TrendingUp} />
        <KPICard testid="viewer-brands" title="Brands in View" value={data.scope.brands.length} icon={Package} />
      </div>

      <div className="bg-surface border border-border rounded-lg p-5 mb-6" data-testid="viewer-daily-chart">
        <div className="mb-4">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// DAILY SALES</div>
          <h3 className="font-display font-bold text-lg mt-0.5">{brandLabel} — total per day</h3>
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.daily}>
              <defs>
                <linearGradient id="vg1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(d) => d.slice(5)} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="total" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#vg1)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden" data-testid="viewer-daily-table">
        <div className="px-5 py-4 border-b border-border">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// DAY-WISE BREAKDOWN</div>
          <h3 className="font-display font-bold text-lg mt-0.5">Daily totals · {brandLabel}</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30">
              <tr className="border-b border-border">
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Date</th>
                <th className="text-right px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Total Sale</th>
              </tr>
            </thead>
            <tbody>
              {data.daily.slice().reverse().map((d) => (
                <tr key={d.date} className="border-b border-border last:border-0">
                  <td className="px-5 py-3 text-sm">{new Date(d.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</td>
                  <td className="px-5 py-3 text-right font-mono tabular text-sm font-semibold">{formatINRFull(d.total)}</td>
                </tr>
              ))}
              {data.daily.length === 0 && <tr><td colSpan={2} className="px-5 py-12 text-center text-muted-foreground text-sm">No sales in selected window</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6 text-[10px] uppercase tracking-widest text-muted-foreground font-mono">
        // READ-ONLY VIEW · NO CUSTOMER DETAILS · TOTALS_ONLY SCOPE
      </div>
    </AppLayout>
  );
}
