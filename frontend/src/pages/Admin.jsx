import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import KPICard from "@/components/dashboard/KPICard";
import { api, formatINR } from "@/lib/api";
import { Users, Building2, Tag, Wallet, FileText, Plus, RefreshCw, Activity, Shield, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import PermissionsDialog from "@/components/admin/PermissionsDialog";

export default function Admin() {
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "sales", phone: "", territory: "" });
  const [permsTarget, setPermsTarget] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [locations, setLocations] = useState([]);
  const [zohoStatus, setZohoStatus] = useState(null);
  const [zohoLogs, setZohoLogs] = useState([]);

  useEffect(() => {
    refresh();
  }, []);

  function refresh() {
    api.get("/dashboard/admin").then(({ data }) => setData(data));
    api.get("/users").then(({ data }) => setUsers(data));
    api.get("/attendance/today").then(({ data }) => setAttendance(data)).catch(() => {});
    api.get("/location/latest").then(({ data }) => setLocations(data)).catch(() => {});
    api.get("/sync/zoho/status").then(({ data }) => setZohoStatus(data)).catch(() => {});
    api.get("/sync/logs").then(({ data }) => setZohoLogs(data.slice(0, 5))).catch(() => {});
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
      if (data.status === "completed") {
        const s = data.synced || {};
        toast.success("Zoho sync complete", { description: `Customers: ${s.customers || 0} · Invoices: ${s.invoices || 0} · Payments: ${s.payments || 0}` });
      } else {
        toast.error(`Sync ${data.status}`, { description: data.message });
      }
      refresh();
    } catch (e) {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  async function detectZoho() {
    setSyncing(true);
    try {
      const { data } = await api.post("/sync/zoho/detect");
      if (data.ok) {
        toast.success("Zoho connected", { description: `${data.organization_name} · region ${data.region}` });
      } else {
        toast.error("Detect failed", { description: data.error });
      }
      refresh();
    } finally { setSyncing(false); }
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

        <div className="bg-surface border border-border rounded-lg p-5" data-testid="zoho-sync-card">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// ZOHO BOOKS SYNC</div>
          <p className="text-xs text-muted-foreground mb-3">
            Live 30-min auto-sync from Zoho Books — customers, invoices, payments, credit notes.
          </p>
          <div className="flex gap-2">
            <Button onClick={triggerSync} disabled={syncing} className="flex-1" data-testid="trigger-sync-btn">
              <RefreshCw size={14} className={`mr-1.5 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Syncing…" : "Sync now"}
            </Button>
            <Button onClick={detectZoho} disabled={syncing} variant="outline" data-testid="detect-zoho-btn">Detect</Button>
          </div>
          <div className="mt-4 pt-4 border-t border-border space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Credentials</span>
              <span className={`font-mono ${zohoStatus?.credentials_present ? "text-success" : "text-warning"}`}>
                {zohoStatus?.credentials_present ? "● PRESENT" : "○ MISSING"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Region</span>
              <span className="font-mono">{zohoStatus?.region || "—"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Organization</span>
              <span className="font-mono truncate max-w-[140px]" title={zohoStatus?.organization_name}>{zohoStatus?.organization_name || "Not detected"}</span>
            </div>
            <div className="flex justify-between"><span className="text-muted-foreground">Schedule</span><span className="font-mono">30 min</span></div>
          </div>
          {zohoLogs.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground font-mono mb-2">// LAST RUNS</div>
              <ul className="space-y-1.5">
                {zohoLogs.map((l) => (
                  <li key={l.id} className="text-[11px] flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1 shrink-0 ${l.status === "completed" ? "text-success" : l.status === "failed" ? "text-destructive" : "text-muted-foreground"}`}>
                      <span className="h-1.5 w-1.5 rounded-full bg-current" /> {l.status}
                    </span>
                    <span className="text-muted-foreground font-mono truncate flex-1">{l.message || ""}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
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
                <th className="text-right px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Actions</th>
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
                  <td className="px-5 py-3 text-right">
                    <Button size="sm" variant="outline" onClick={() => setPermsTarget(u)} data-testid={`perm-btn-${u.id}`}>
                      <Shield size={12} className="mr-1.5" /> Permissions
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Attendance + Live locations */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-surface border border-border rounded-lg p-5" data-testid="attendance-today">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// ATTENDANCE TODAY</div>
          <table className="w-full text-sm">
            <thead><tr className="border-b border-border">
              <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Rep</th>
              <th className="text-left py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Check-in</th>
              <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Pings</th>
              <th className="text-right py-2 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Status</th>
            </tr></thead>
            <tbody>
              {attendance.map((a) => (
                <tr key={a.user_id} className="border-b border-border last:border-0">
                  <td className="py-2.5">
                    <div className="font-medium text-sm">{a.name}</div>
                    <div className="text-xs text-muted-foreground">{a.territory}</div>
                  </td>
                  <td className="py-2.5 text-xs font-mono">{a.check_in ? new Date(a.check_in).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                  <td className="py-2.5 text-right font-mono tabular text-xs">{a.ping_count}</td>
                  <td className="py-2.5 text-right">
                    <span className={`text-[10px] font-mono uppercase tracking-wider ${a.checked_in ? "text-success" : "text-muted-foreground"}`}>
                      {a.checked_in ? "● ACTIVE" : "○ ABSENT"}
                    </span>
                  </td>
                </tr>
              ))}
              {attendance.length === 0 && <tr><td colSpan={4} className="py-6 text-center text-xs text-muted-foreground">No attendance data yet · staff must open app on phone for silent location capture</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="bg-surface border border-border rounded-lg p-5" data-testid="live-locations">
          <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-3">// LIVE LOCATIONS</div>
          <ul className="space-y-2">
            {locations.map((l) => (
              <li key={l.id} className="p-3 rounded border border-border flex items-center justify-between">
                <div>
                  <div className="font-medium text-sm">{l.name}</div>
                  <div className="text-xs text-muted-foreground">{l.territory}</div>
                </div>
                <div className="text-right">
                  {l.lat ? (
                    <>
                      <div className="font-mono text-xs flex items-center gap-1"><MapPin size={11} className="text-primary" /> {l.lat.toFixed(3)}, {l.lng.toFixed(3)}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{l.timestamp ? new Date(l.timestamp).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : ""}</div>
                    </>
                  ) : (
                    <div className="text-[10px] text-muted-foreground font-mono">NO PING YET</div>
                  )}
                </div>
              </li>
            ))}
            {locations.length === 0 && <div className="text-xs text-muted-foreground py-4">No location data yet</div>}
          </ul>
        </div>
      </div>

      <PermissionsDialog
        user={permsTarget}
        open={!!permsTarget}
        onClose={() => setPermsTarget(null)}
        onSaved={refresh}
      />
    </AppLayout>
  );
}
