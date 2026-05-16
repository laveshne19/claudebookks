import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KPICard from "@/components/dashboard/KPICard";
import { api, formatINR, formatINRFull } from "@/lib/api";
import { Wallet, AlertTriangle, FileWarning, Receipt, CheckCircle2 } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { useState as useStateReact } from "react";

export default function Accounts() {
  const [data, setData] = useState(null);
  const [checks, setChecks] = useState({});

  useEffect(() => {
    api.get("/dashboard/accounts").then(({ data }) => {
      setData(data);
      const c = {};
      data.checklist.forEach((it) => c[it.id] = it.done);
      setChecks(c);
    });
  }, []);

  if (!data) return <AppLayout title="Accounts"><div className="text-sm text-muted-foreground">Loading…</div></AppLayout>;

  const k = data.kpis;

  return (
    <AppLayout title="Accounts" subtitle="Recovery · GST · Reconciliation">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KPICard testid="kpi-acc-outstanding" title="Outstanding" value={formatINR(k.total_outstanding)} icon={Wallet} delta={-4.2} />
        <KPICard testid="kpi-acc-overdue" title="Overdue" value={formatINR(k.total_overdue)} icon={AlertTriangle} delta={-2.1} accent="bg-destructive/10 text-destructive" />
        <KPICard testid="kpi-acc-overdue-count" title="Overdue Inv." value={k.overdue_count} icon={FileWarning} />
        <KPICard testid="kpi-acc-mtd-inv" title="MTD Invoices" value={k.mtd_invoice_count} icon={Receipt} delta={6.8} />
        <KPICard testid="kpi-acc-gst" title="GST (MTD)" value={formatINR(k.gst_collected_mtd)} icon={CheckCircle2} accent="bg-success/10 text-success" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 bg-surface border border-border rounded-lg overflow-hidden">
          <Tabs defaultValue="overdue">
            <TabsList className="rounded-none border-b border-border bg-transparent w-full justify-start h-12 px-3">
              <TabsTrigger value="overdue" className="h-12 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none" data-testid="acc-tab-overdue">Overdue ({data.overdue_invoices.length})</TabsTrigger>
              <TabsTrigger value="partial" className="h-12 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none" data-testid="acc-tab-partial">Partial ({data.partial_invoices.length})</TabsTrigger>
              <TabsTrigger value="unpaid" className="h-12 data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none" data-testid="acc-tab-unpaid">Unpaid ({data.unpaid_invoices.length})</TabsTrigger>
            </TabsList>
            {[
              { key: "overdue", list: data.overdue_invoices },
              { key: "partial", list: data.partial_invoices },
              { key: "unpaid", list: data.unpaid_invoices },
            ].map(({ key, list }) => (
              <TabsContent key={key} value={key} className="p-0 m-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" data-testid={`acc-table-${key}`}>
                    <thead className="bg-muted/30">
                      <tr className="border-b border-border">
                        <Th>Invoice</Th><Th>Date</Th><Th>Due</Th><Th>Brand</Th><Th right>Amount</Th><Th right>Pending</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.slice(0, 25).map((inv) => (
                        <tr key={inv.id} className="border-b border-border hover:bg-surface-hover">
                          <td className="px-4 py-2.5 font-mono text-xs">{inv.invoice_no}</td>
                          <td className="px-4 py-2.5 text-xs text-muted-foreground">{inv.date?.slice(0, 10)}</td>
                          <td className="px-4 py-2.5 text-xs">{inv.due_date?.slice(0, 10)}</td>
                          <td className="px-4 py-2.5 text-xs">{inv.brand}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-xs">{formatINRFull(inv.amount)}</td>
                          <td className="px-4 py-2.5 text-right font-mono tabular text-xs text-destructive">{formatINRFull(inv.amount - (inv.paid_amount || 0))}</td>
                        </tr>
                      ))}
                      {list.length === 0 && <tr><td colSpan={6} className="px-4 py-12 text-center text-sm text-muted-foreground">No items</td></tr>}
                    </tbody>
                  </table>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5" data-testid="daily-checklist">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// DAILY CHECKLIST</div>
          <ul className="space-y-3">
            {data.checklist.map((it) => (
              <li key={it.id} className="flex items-start gap-3">
                <Checkbox
                  id={`chk-${it.id}`}
                  checked={!!checks[it.id]}
                  onCheckedChange={(v) => setChecks((c) => ({ ...c, [it.id]: !!v }))}
                  data-testid={`checklist-item-${it.id}`}
                />
                <label htmlFor={`chk-${it.id}`} className={`text-xs cursor-pointer ${checks[it.id] ? "line-through text-muted-foreground" : ""}`}>{it.title}</label>
              </li>
            ))}
          </ul>
          <div className="mt-5 pt-5 border-t border-border">
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-2">// GST SNAPSHOT</div>
            <div className="text-xs text-muted-foreground">Output GST collected this month</div>
            <div className="font-display font-black text-2xl tabular text-success mt-1">{formatINR(k.gst_collected_mtd)}</div>
            <div className="text-[10px] text-muted-foreground mt-1 font-mono">Across {k.mtd_invoice_count} invoices</div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

function Th({ children, right }) {
  return <th className={`px-4 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold ${right ? "text-right" : "text-left"}`}>{children}</th>;
}
