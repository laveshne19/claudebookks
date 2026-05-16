import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KPICard from "@/components/dashboard/KPICard";
import { api, formatINR } from "@/lib/api";
import { Users, Building2, Tag, Wallet, FileText, Plus, RefreshCw, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

export default function Admin() {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "sales", phone: "", territory: "" });

  useEffect(() => {
    refresh();
  }, []);

  function refresh() {
    api.get("/dashboard/admin").then(({ data }) => setData(data));
    api.get("/users").then(({ data }) => setUsers(data));
  }

  async function addUser() {
    try {
      await api.post("/auth/register", form);
      toast.success("User created successfully");
      setOpen(false);
      setForm({ name: "", email: "", password: "", role: "sales", phone: "", territory: "" });
      refresh();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to create user");
    }
  }

  async function triggerSync() {
    setSyncing(true);
    try {
      const { data } = await api.post("/sync/zoho");
      toast.success(`Sync ${data.status}`, { description: data.message });
    } catch (e) {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  if (!data) return <AppLayout title="Admin"><div className="text-sm text-muted-foreground">Loading…</div></AppLayout>;

  const k = data.kpis;

  return (
    <AppLayout title="Admin Control" subtitle="Master operations panel">
      <div className="mb-6 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <KPICard testid="kpi-admin-users" title="Users" value={k.total_users} icon={Users} />
        <KPICard testid="kpi-admin-sales-team" title="Sales Team" value={k.sales_users} icon={Activity} />
        <KPICard testid="kpi-admin-customers" title="Customers" value={k.total_customers} icon={Building2} />
        <KPICard testid="kpi-admin-schemes" title="Schemes" value={k.active_schemes} icon={Tag} />
        <KPICard testid="kpi-admin-invoices" title="Invoices" value={k.total_invoices} icon={FileText} />
        <KPICard testid="kpi-admin-mtd" title="MTD" value={formatINR(k.mtd_sales)} icon={Activity} accent="bg-primary/10 text-primary" />
        <KPICard testid="kpi-admin-overdue" title="Overdue" value={formatINR(k.total_overdue)} icon={Wallet} accent="bg-destructive/10 text-destructive" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 bg-surface border border-border rounded-lg p-5" data-testid="leaderboard">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// LEADERBOARD</div>
              <h3 className="font-display font-bold text-lg mt-0.5">Top performers this month</h3>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">#</th>
                <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Salesperson</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Target</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Achieved</th>
                <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">%</th>
              </tr>
            </thead>
            <tbody>
              {data.leaderboard.map((p, i) => (
                <tr key={p.user_id} className="border-b border-border last:border-0">
                  <td className="py-3 font-mono text-xs text-muted-foreground">{i + 1}</td>
                  <td className="py-3">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.territory}</div>
                  </td>
                  <td className="py-3 text-right font-mono tabular">{formatINR(p.target)}</td>
                  <td className="py-3 text-right font-mono tabular">{formatINR(p.achieved)}</td>
                  <td className="py-3 text-right">
                    <span className={`font-mono font-bold ${p.pct >= 80 ? "text-success" : p.pct >= 60 ? "text-warning" : "text-destructive"}`}>{p.pct}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// ZOHO BOOKS SYNC</div>
          <p className="text-xs text-muted-foreground mb-3">
            Auto-sync every 30 min. Connects ledgers, invoices, payments &amp; outstanding from Zoho Books.
          </p>
          <Button onClick={triggerSync} disabled={syncing} className="w-full" data-testid="trigger-sync-btn">
            <RefreshCw size={14} className={`mr-1.5 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing…" : "Trigger sync now"}
          </Button>
          <div className="mt-4 pt-4 border-t border-border space-y-2 text-xs">
            <div className="flex justify-between"><span className="text-muted-foreground">Status</span><span className="font-mono text-warning">CREDENTIALS PENDING</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Interval</span><span className="font-mono">30 min</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Mode</span><span className="font-mono">Seeded data</span></div>
          </div>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg" data-testid="users-section">
        <div className="flex items-center justify-between p-5 pb-3">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono">// USERS</div>
            <h3 className="font-display font-bold text-lg mt-0.5">Workforce ({users.length})</h3>
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" data-testid="add-user-btn"><Plus size={14} className="mr-1.5" /> Add user</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Create new user</DialogTitle></DialogHeader>
              <div className="space-y-3 mt-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Name</Label><Input data-testid="new-user-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                  <div><Label>Email</Label><Input data-testid="new-user-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                </div>
                <div><Label>Password</Label><Input data-testid="new-user-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Role</Label>
                    <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                      <SelectTrigger data-testid="new-user-role"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Admin</SelectItem>
                        <SelectItem value="manager">Manager</SelectItem>
                        <SelectItem value="sales">Sales</SelectItem>
                        <SelectItem value="accounts">Accounts</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div><Label>Territory</Label><Input value={form.territory} onChange={(e) => setForm({ ...form, territory: e.target.value })} /></div>
                </div>
                <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              </div>
              <DialogFooter className="mt-4">
                <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
                <Button onClick={addUser} data-testid="save-user-btn">Create</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/30">
              <tr className="border-y border-border">
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Name</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Email</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Role</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Territory</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-border last:border-0 hover:bg-surface-hover" data-testid={`user-row-${u.id}`}>
                  <td className="px-5 py-3 font-medium">{u.name}</td>
                  <td className="px-5 py-3 text-xs font-mono text-muted-foreground">{u.email}</td>
                  <td className="px-5 py-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-muted">{u.role}</span>
                  </td>
                  <td className="px-5 py-3 text-xs">{u.territory || "—"}</td>
                  <td className="px-5 py-3">
                    <span className={`text-[10px] font-mono uppercase tracking-wider ${u.active !== false ? "text-success" : "text-muted-foreground"}`}>
                      {u.active !== false ? "● ACTIVE" : "○ DEACTIVATED"}
                    </span>
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
