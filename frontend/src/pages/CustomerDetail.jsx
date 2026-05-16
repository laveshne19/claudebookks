import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import AIInsightCard from "@/components/dashboard/AIInsightCard";
import { api, formatINR, formatINRFull } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Phone, MessageSquare, MapPin, ArrowLeft, Sparkles, RefreshCw } from "lucide-react";

export default function CustomerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [ledger, setLedger] = useState({ invoices: [], payments: [], visits: [] });
  const [insights, setInsights] = useState(null);
  const [loadingInsights, setLoadingInsights] = useState(false);

  useEffect(() => {
    api.get(`/customers/${id}`).then(({ data }) => setC(data));
    api.get(`/customers/${id}/ledger`).then(({ data }) => setLedger(data));
    fetchInsights(false);
    // eslint-disable-next-line
  }, [id]);

  async function fetchInsights(force) {
    setLoadingInsights(true);
    try {
      const { data } = await api.get(`/customers/${id}/insights${force ? "?force=true" : ""}`);
      setInsights(data);
    } finally {
      setLoadingInsights(false);
    }
  }

  if (!c) return <AppLayout title="Customer"><div className="text-sm text-muted-foreground">Loading…</div></AppLayout>;

  return (
    <AppLayout title={c.name} subtitle={c.code}>
      <div className="mb-4">
        <button onClick={() => navigate(-1)} className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1" data-testid="back-btn">
          <ArrowLeft size={12} /> Back
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Profile + AI */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-surface border border-border rounded-lg p-5" data-testid="customer-profile">
            <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground mb-2">// PROFILE</div>
            <div className="flex items-start justify-between gap-2 mb-1">
              <h2 className="font-display font-black text-2xl tracking-tight flex-1 leading-tight">{c.name}</h2>
              {c.tier && <TierBadge tier={c.tier} />}
            </div>
            <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1.5"><MapPin size={11} />{c.area}, {c.city}</div>
            {c.beat_days && <div className="text-xs text-primary mt-1 font-mono uppercase tracking-wider">BEAT · {c.beat_days}</div>}

            <div className="grid grid-cols-2 gap-3 mt-5 pt-5 border-t border-border">
              <Stat label="Outstanding" value={formatINR(c.outstanding)} accent={c.overdue > 0 ? "text-destructive" : ""} />
              <Stat label="Overdue" value={formatINR(c.overdue)} accent="text-destructive" />
              <Stat label="Credit Limit" value={formatINR(c.credit_limit)} />
              <Stat label="Lifetime" value={formatINR(c.total_purchases)} />
            </div>

            <div className="mt-5 pt-5 border-t border-border space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">GSTIN</span><span className="font-mono">{c.gstin || "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Contact</span><span>{c.contact_person || "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Phone</span><span className="font-mono">{c.phone || "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Last visit</span><span className="font-mono">{c.last_visit_date?.slice(0, 10) || "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Last payment</span><span className="font-mono">{c.last_payment_date?.slice(0, 10) || "—"}</span></div>
            </div>

            <div className="flex gap-2 mt-5">
              <Button size="sm" className="flex-1" onClick={() => c.phone && window.open(`tel:${c.phone}`)} data-testid="call-customer-btn">
                <Phone size={13} className="mr-1.5" /> Call
              </Button>
              <Button size="sm" variant="outline" className="flex-1" onClick={() => c.phone && window.open(`sms:${c.phone}`)} data-testid="sms-customer-btn">
                <MessageSquare size={13} className="mr-1.5" /> SMS
              </Button>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground flex items-center gap-1.5">
                <Sparkles size={11} /> AI INTELLIGENCE
              </div>
              <button onClick={() => fetchInsights(true)} disabled={loadingInsights} className="text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground inline-flex items-center gap-1 font-mono" data-testid="regenerate-insights-btn">
                <RefreshCw size={10} className={loadingInsights ? "animate-spin" : ""} /> {loadingInsights ? "Generating" : "Refresh"}
              </button>
            </div>

            {insights ? (
              <>
                <AIInsightCard title="Executive Summary" testid="ai-summary">
                  <p>{insights.summary}</p>
                </AIInsightCard>

                <div className="grid grid-cols-2 gap-3">
                  <ScoreCard label="Credit Risk" score={100 - insights.credit_risk_score} inverse />
                  <ScoreCard label="Pay Behavior" score={insights.payment_behaviour_score} />
                </div>

                <AIInsightCard title="Next Order Prediction" badge="FORECAST" testid="ai-prediction">
                  <p className="font-mono text-sm">{insights.predicted_next_order}</p>
                </AIInsightCard>

                <AIInsightCard title="Recovery Approach" badge="ACTION" testid="ai-recovery">
                  <p>{insights.recovery_approach}</p>
                </AIInsightCard>

                <AIInsightCard title="Pitch Points" testid="ai-pitch">
                  <ul className="space-y-1.5 list-disc list-inside">
                    {insights.pitch_points?.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </AIInsightCard>

                <AIInsightCard title="Upsell Suggestions" testid="ai-upsell">
                  <ul className="space-y-1.5">
                    {insights.upsell_suggestions?.map((p, i) => <li key={i} className="font-mono text-xs">→ {p}</li>)}
                  </ul>
                </AIInsightCard>

                <AIInsightCard title="Best Visit Time" testid="ai-visit-time">
                  <p>{insights.best_visit_time}</p>
                </AIInsightCard>
              </>
            ) : (
              <div className="bg-ai-surface border border-ai-border rounded-lg p-5 ai-noise relative">
                <div className="relative z-10 text-xs text-ai-text font-mono">Generating insights…</div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Tabs */}
        <div className="lg:col-span-8">
          <div className="bg-surface border border-border rounded-lg">
            <Tabs defaultValue="invoices" className="w-full">
              <TabsList className="rounded-none border-b border-border bg-transparent w-full justify-start h-12 p-0 px-3">
                <TabsTrigger value="invoices" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-4" data-testid="tab-invoices">Invoices ({ledger.invoices.length})</TabsTrigger>
                <TabsTrigger value="payments" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-4" data-testid="tab-payments">Payments ({ledger.payments.length})</TabsTrigger>
                <TabsTrigger value="visits" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-4" data-testid="tab-visits">Visits ({ledger.visits.length})</TabsTrigger>
                <TabsTrigger value="ledger" className="data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none h-12 px-4" data-testid="tab-ledger">Statement</TabsTrigger>
              </TabsList>

              <TabsContent value="invoices" className="p-0 m-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/30">
                      <tr className="border-b border-border">
                        <Th>Invoice</Th><Th>Date</Th><Th>Brand</Th><Th right>Amount</Th><Th right>Paid</Th><Th right>Status</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.invoices.map((i) => (
                        <tr key={i.id} className="border-b border-border hover:bg-surface-hover">
                          <td className="px-4 py-2.5 font-mono text-xs">{i.invoice_no}</td>
                          <td className="px-4 py-2.5 text-xs text-muted-foreground">{i.date?.slice(0, 10)}</td>
                          <td className="px-4 py-2.5 text-xs">{i.brand}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-xs">{formatINRFull(i.amount)}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-xs text-muted-foreground">{formatINRFull(i.paid_amount)}</td>
                          <td className="px-4 py-2.5 text-right"><StatusPill status={i.status} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </TabsContent>

              <TabsContent value="payments" className="p-0 m-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/30">
                      <tr className="border-b border-border">
                        <Th>Date</Th><Th>Method</Th><Th>Reference</Th><Th right>Amount</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {ledger.payments.map((p) => (
                        <tr key={p.id} className="border-b border-border hover:bg-surface-hover">
                          <td className="px-4 py-2.5 text-xs">{p.date?.slice(0, 10)}</td>
                          <td className="px-4 py-2.5 text-xs uppercase font-mono">{p.method}</td>
                          <td className="px-4 py-2.5 text-xs font-mono text-muted-foreground">{p.reference || "—"}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-xs text-success">{formatINRFull(p.amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </TabsContent>

              <TabsContent value="visits" className="p-0 m-0">
                <div className="divide-y divide-border">
                  {ledger.visits.length === 0 && <div className="px-5 py-12 text-center text-sm text-muted-foreground">No visits recorded</div>}
                  {ledger.visits.map((v) => (
                    <div key={v.id} className="px-5 py-4">
                      <div className="flex items-center justify-between mb-1">
                        <div className="text-sm font-medium">{v.date?.slice(0, 10)} · {v.duration_minutes} min</div>
                        <span className="text-[10px] uppercase tracking-wider font-mono px-2 py-0.5 rounded bg-muted">{v.outcome}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{v.notes || "—"}</p>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="ledger" className="p-5 m-0">
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <Stat label="Total Billed" value={formatINR(c.total_purchases)} />
                  <Stat label="Outstanding" value={formatINR(c.outstanding)} accent="text-destructive" />
                  <Stat label="Overdue" value={formatINR(c.overdue)} accent="text-destructive" />
                </div>
                <p className="text-xs text-muted-foreground">Live ledger pulled from Zoho Books. Sync runs every 30 minutes when credentials are configured.</p>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

function Stat({ label, value, accent = "" }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono mb-0.5">{label}</div>
      <div className={`font-display font-black text-lg tabular ${accent}`}>{value}</div>
    </div>
  );
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

function ScoreCard({ label, score, inverse }) {
  const value = Math.max(0, Math.min(100, score));
  let color = "bg-success";
  if (value < 40) color = "bg-destructive";
  else if (value < 65) color = "bg-warning";
  return (
    <div className="bg-ai-surface border border-ai-border rounded-lg p-4 ai-noise relative">
      <div className="relative z-10">
        <div className="text-[10px] uppercase tracking-widest text-ai-text font-mono">{label}</div>
        <div className="mt-1.5 flex items-end gap-2">
          <div className="font-display font-black text-2xl text-foreground tabular">{value}</div>
          <div className="text-[10px] font-mono text-muted-foreground pb-1">/100</div>
        </div>
        <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
          <div className={`h-full ${color} transition-all duration-500`} style={{ width: `${value}%` }} />
        </div>
      </div>
    </div>
  );
}

function Th({ children, right }) {
  return <th className={`px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold ${right ? "text-right" : "text-left"}`}>{children}</th>;
}

function StatusPill({ status }) {
  const map = {
    paid: { cls: "bg-success/10 text-success", label: "PAID" },
    partial: { cls: "bg-warning/10 text-warning", label: "PARTIAL" },
    unpaid: { cls: "bg-muted text-muted-foreground", label: "UNPAID" },
    overdue: { cls: "bg-destructive/10 text-destructive", label: "OVERDUE" },
  };
  const m = map[status] || map.unpaid;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider ${m.cls}`}>{m.label}</span>;
}
