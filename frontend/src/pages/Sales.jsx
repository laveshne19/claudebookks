import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINR } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/AuthContext";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, PieChart, Pie } from "recharts";

export default function Sales() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [schemes, setSchemes] = useState([]);
  const [trend, setTrend] = useState([]);
  const [brands, setBrands] = useState([]);

  useEffect(() => {
    api.get("/dashboard/sales").then(({ data }) => setData(data));
    api.get("/schemes?active=true").then(({ data }) => setSchemes(data));
    api.get("/reports/sales-trend").then(({ data }) => setTrend(data));
    api.get("/reports/brand-performance").then(({ data }) => setBrands(data));
  }, []);

  return (
    <AppLayout title="Sales" subtitle="Targets · Schemes · Performance">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-surface border border-border rounded-lg p-5" data-testid="target-card">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// MONTHLY TARGET</div>
          {data && (
            <>
              <div className="flex items-baseline gap-2">
                <div className="font-display font-black text-3xl tabular">{formatINR(data.kpis.achieved)}</div>
                <div className="text-sm text-muted-foreground">/ {formatINR(data.kpis.target)}</div>
              </div>
              <div className="mt-3">
                <Progress value={data.kpis.achievement_pct} className="h-2" />
                <div className="mt-2 flex justify-between text-xs">
                  <span className="text-muted-foreground">Achievement</span>
                  <span className="font-mono font-semibold">{data.kpis.achievement_pct}%</span>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// COLLECTION</div>
          {data && (
            <>
              <div className="flex items-baseline gap-2">
                <div className="font-display font-black text-3xl tabular">{formatINR(data.kpis.collected)}</div>
                <div className="text-sm text-muted-foreground">collected</div>
              </div>
              <div className="mt-3">
                <Progress value={data.kpis.collection_pct} className="h-2" />
                <div className="mt-2 flex justify-between text-xs">
                  <span className="text-muted-foreground">vs target</span>
                  <span className="font-mono font-semibold">{data.kpis.collection_pct}%</span>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// BRAND SPLIT</div>
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={brands.slice(0, 5)} dataKey="value" nameKey="brand" cx="50%" cy="50%" innerRadius={28} outerRadius={56} paddingAngle={2}>
                  {brands.slice(0, 5).map((_, i) => {
                    const colors = ["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--chart-5))"];
                    return <Cell key={i} fill={colors[i]} />;
                  })}
                </Pie>
                <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// SALES vs COLLECTION</div>
            <h3 className="font-display font-bold text-lg mt-0.5">6-month trend</h3>
          </div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={trend}>
              <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
              <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="sales" fill="hsl(var(--primary))" radius={[3, 3, 0, 0]} />
              <Bar dataKey="collected" fill="hsl(var(--chart-2))" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <h3 className="font-display font-bold text-lg mb-3">Live schemes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {schemes.map((s) => (
            <div key={s.id} className="bg-surface border border-border rounded-lg p-5 hover:shadow-sm transition" data-testid={`scheme-card-${s.id}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-mono uppercase tracking-widest bg-muted px-2 py-0.5 rounded">{s.brand}</span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{s.type}</span>
              </div>
              <h4 className="font-display font-bold text-base leading-tight">{s.name}</h4>
              <p className="text-xs text-muted-foreground mt-2">{s.description}</p>
              <div className="mt-4 text-xs">
                <div className="flex justify-between mb-1">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-mono font-semibold">{s.progress}%</span>
                </div>
                <Progress value={s.progress} className="h-1.5" />
              </div>
              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Reward</span>
                <span className="text-xs font-semibold text-primary">{s.reward}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
