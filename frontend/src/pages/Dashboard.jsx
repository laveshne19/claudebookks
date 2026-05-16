import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KPICard from "@/components/dashboard/KPICard";
import AIInsightCard from "@/components/dashboard/AIInsightCard";
import AIPerformanceCard from "@/components/dashboard/AIPerformanceCard";
import { api, formatINR } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import {
  Activity, Target, TrendingDown, Wallet, AlertTriangle, CircleDollarSign, Users, FileText, ArrowUpRight
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, BarChart, Bar, Cell
} from "recharts";
import { Progress } from "@/components/ui/progress";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/dashboard/sales").then(({ data }) => setData(data));
  }, []);

  if (!data) {
    return <AppLayout title="Dashboard" subtitle="Loading…"><DashboardSkeleton /></AppLayout>;
  }

  const k = data.kpis;
  const greeting = user?.role === "sales" ? "Mission brief" : "Operations overview";

  return (
    <AppLayout title={`Welcome, ${user?.name?.split(" ")[0]}`} subtitle={greeting}>
      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <KPICard testid="kpi-mtd-sales" title="MTD Sales" value={formatINR(k.mtd_sales)} icon={Activity} delta={12.4} deltaLabel="vs last mo" accent="bg-primary/10 text-primary" />
        <KPICard testid="kpi-target" title="Target" value={formatINR(k.target)} icon={Target} />
        <KPICard testid="kpi-achievement" title="Achievement" value={`${k.achievement_pct}%`} icon={TrendingDown} delta={k.achievement_pct > 80 ? 8.1 : -3.2} accent="bg-success/10 text-success" />
        <KPICard testid="kpi-collection" title="Collection" value={`${k.collection_pct}%`} icon={CircleDollarSign} delta={k.collection_pct > 70 ? 5.0 : -2.4} />
        <KPICard testid="kpi-overdue" title="Overdue" value={formatINR(k.overdue)} icon={AlertTriangle} delta={-6.2} accent="bg-destructive/10 text-destructive" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 bg-surface border border-border rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// SALES TREND</div>
              <h3 className="font-display font-bold text-lg mt-0.5">Last 6 months</h3>
            </div>
            <div className="text-xs text-muted-foreground font-mono">₹ in lakhs</div>
          </div>
          <div className="h-64" data-testid="sales-trend-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.sales_trend}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  formatter={(v) => formatINR(v)}
                />
                <Area type="monotone" dataKey="sales" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#g1)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="mb-4">
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// AGING</div>
            <h3 className="font-display font-bold text-lg mt-0.5">Outstanding</h3>
          </div>
          <div className="h-64" data-testid="aging-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.aging} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 100000).toFixed(0)}L`} />
                <YAxis type="category" dataKey="bucket" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={50} />
                <Tooltip contentStyle={{ background: "hsl(var(--surface))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} formatter={(v) => formatINR(v)} />
                <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
                  {data.aging.map((entry, i) => {
                    const colors = ["hsl(var(--success))", "hsl(var(--warning))", "hsl(var(--chart-1))", "hsl(var(--destructive))"];
                    return <Cell key={i} fill={colors[i]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Priority customers + Tasks + AI */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 bg-surface border border-border rounded-lg p-5" data-testid="priority-customers">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// PRIORITY LIST</div>
              <h3 className="font-display font-bold text-lg mt-0.5">Customers requiring attention</h3>
            </div>
            <button onClick={() => navigate("/customers")} className="text-xs font-medium text-primary hover:underline">View all <ArrowUpRight size={12} className="inline" /></button>
          </div>
          <div className="divide-y divide-border">
            {data.priority_customers.map((c) => (
              <div key={c.id} onClick={() => navigate(`/customers/${c.id}`)} className="flex items-center justify-between py-3 cursor-pointer hover:bg-surface-hover px-2 -mx-2 rounded transition" data-testid={`priority-cust-${c.id}`}>
                <div>
                  <div className="font-medium text-sm">{c.name}</div>
                  <div className="text-xs text-muted-foreground">{c.area} · {c.code}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-sm tabular">{formatINR(c.outstanding)}</div>
                  {c.overdue > 0 && <div className="text-[10px] uppercase font-mono text-destructive">OVERDUE · {formatINR(c.overdue)}</div>}
                </div>
              </div>
            ))}
            {data.priority_customers.length === 0 && (
              <div className="py-12 text-center text-sm text-muted-foreground">No priority customers</div>
            )}
          </div>
        </div>

        <div className="space-y-4">
          <AIPerformanceCard />

          <AIInsightCard title="AI Recommendation" badge="LIVE">
            <p>
              <span className="font-semibold">{data.priority_customers[0]?.name || "Top customer"}</span> hasn't ordered in 18+ days but has high outstanding.
              Visit Tue 11AM with Boat Q1 Volume Booster scheme.
            </p>
            <p className="text-xs text-muted-foreground font-mono">Confidence · 84%</p>
          </AIInsightCard>

          <div className="bg-surface border border-border rounded-lg p-5" data-testid="open-tasks">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// OPEN TASKS</div>
              <span className="text-xs font-mono tabular text-muted-foreground">{data.open_tasks.length}</span>
            </div>
            <ul className="space-y-2">
              {data.open_tasks.slice(0, 6).map((t) => (
                <li key={t.id} className="text-xs flex items-start gap-2">
                  <div className={`mt-1 h-1.5 w-1.5 rounded-full shrink-0 ${t.priority === "urgent" ? "bg-destructive" : t.priority === "high" ? "bg-warning" : "bg-muted-foreground"}`} />
                  <span className="flex-1">{t.title}</span>
                </li>
              ))}
              {data.open_tasks.length === 0 && <div className="text-xs text-muted-foreground py-2">No open tasks</div>}
            </ul>
          </div>
        </div>
      </div>

      {/* Bottom stats strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard testid="kpi-customers" title="Customers" value={k.customer_count} icon={Users} />
        <KPICard testid="kpi-invoices" title="Active Invoices" value={k.active_invoices} icon={FileText} />
        <KPICard testid="kpi-outstanding" title="Outstanding" value={formatINR(k.outstanding)} icon={Wallet} />
        <KPICard testid="kpi-collected" title="Collected MTD" value={formatINR(k.collected)} icon={CircleDollarSign} accent="bg-success/10 text-success" />
      </div>
    </AppLayout>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-28 bg-muted rounded-lg" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 h-72 bg-muted rounded-lg" />
        <div className="h-72 bg-muted rounded-lg" />
      </div>
    </div>
  );
}
