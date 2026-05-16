import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR } from "@/lib/api";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, AreaChart, Area, Cell } from "recharts";

export default function Reports() {
  const [aging, setAging] = useState([]);
  const [brands, setBrands] = useState([]);
  const [trend, setTrend] = useState([]);
  const [productivity, setProductivity] = useState([]);

  useEffect(() => {
    api.get("/reports/aging").then(({ data }) => setAging(data));
    api.get("/reports/brand-performance").then(({ data }) => setBrands(data));
    api.get("/reports/sales-trend?months=12").then(({ data }) => setTrend(data));
    api.get("/reports/productivity").then(({ data }) => setProductivity(data));
  }, []);

  return (
    <AppLayout title="Reports & Analytics" subtitle="Live business intelligence">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-1">// SALES TREND</div>
          <h3 className="font-display font-bold text-lg mb-4">Last 12 months</h3>
          <div className="h-64" data-testid="report-trend">
            <ResponsiveContainer>
              <AreaChart data={trend}>
                <defs>
                  <linearGradient id="rg1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
                <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="sales" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#rg1)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-1">// AGING</div>
          <h3 className="font-display font-bold text-lg mb-4">Outstanding by bucket</h3>
          <div className="h-64" data-testid="report-aging">
            <ResponsiveContainer>
              <BarChart data={aging}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
                <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {aging.map((_, i) => {
                    const colors = ["hsl(var(--success))", "hsl(var(--warning))", "hsl(var(--chart-1))", "hsl(var(--destructive))"];
                    return <Cell key={i} fill={colors[i]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-1">// BRAND PERFORMANCE</div>
          <h3 className="font-display font-bold text-lg mb-4">All-time billed</h3>
          <table className="w-full text-sm" data-testid="brand-perf-table">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Brand</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Value</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Share</th>
              </tr>
            </thead>
            <tbody>
              {brands.map((b, i) => {
                const total = brands.reduce((s, x) => s + x.value, 0);
                const pct = total ? (b.value / total * 100).toFixed(1) : 0;
                return (
                  <tr key={b.brand} className="border-b border-border last:border-0">
                    <td className="py-3 font-medium">{b.brand}</td>
                    <td className="py-3 text-right font-mono tabular">{formatINR(b.value)}</td>
                    <td className="py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                          <div className="h-full bg-primary" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="font-mono text-xs w-10 text-right">{pct}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-1">// PRODUCTIVITY</div>
          <h3 className="font-display font-bold text-lg mb-4">Sales team</h3>
          <table className="w-full text-sm" data-testid="productivity-table">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Rep</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Visits</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Achievement</th>
              </tr>
            </thead>
            <tbody>
              {productivity.map((p) => (
                <tr key={p.user_id} className="border-b border-border last:border-0">
                  <td className="py-3">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.territory}</div>
                  </td>
                  <td className="py-3 text-right font-mono tabular">{p.visits}</td>
                  <td className="py-3 text-right">
                    <div className="inline-flex items-center gap-2 justify-end">
                      <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div className={`h-full ${p.pct >= 80 ? "bg-success" : p.pct >= 60 ? "bg-warning" : "bg-destructive"}`} style={{ width: `${Math.min(100, p.pct)}%` }} />
                      </div>
                      <span className="font-mono text-xs w-10 text-right">{p.pct}%</span>
                    </div>
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
