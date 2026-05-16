import { useEffect, useRef, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api, formatINRFull } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Plus, Upload, RefreshCw, Cloud, Trash2, BarChart3, Trophy, X,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

const TIER_COLORS = {
  PLATINUM: "bg-zinc-300 text-zinc-900",
  DIAMOND:  "bg-sky-200 text-sky-950",
  GOLD:     "bg-amber-200 text-amber-950",
  SILVER:   "bg-zinc-200 text-zinc-700",
};

function emptyForm() {
  return {
    name: "", brand: "", type: "value", description: "",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
    target_amount: 0, reward: "", active: true,
  };
}

export default function Schemes() {
  const { user } = useAuth();
  const isAdmin = user && ["super_admin", "admin"].includes(user.role);
  const canManage = user && ["super_admin", "admin", "manager"].includes(user.role);

  const [list, setList] = useState([]);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(false);
  const [openNew, setOpenNew] = useState(false);
  const [openLb, setOpenLb] = useState(null); // scheme id
  const [lbData, setLbData] = useState(null);
  const [form, setForm] = useState(emptyForm());
  const fileRef = useRef(null);

  async function load() {
    setLoading(true);
    try {
      const [{ data }, br] = await Promise.all([
        api.get("/schemes"),
        api.get("/schemes/brands").catch(() => ({ data: { brands: [] } })),
      ]);
      setList(data);
      setBrands(br?.data?.brands || []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function createScheme() {
    if (!form.name || !form.brand) { toast.error("Name & Brand required"); return; }
    try {
      await api.post("/schemes", { ...form, target_amount: Number(form.target_amount) || 0 });
      toast.success("Scheme created");
      setOpenNew(false);
      setForm(emptyForm());
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create");
    }
  }

  async function deleteScheme(id, name) {
    if (!window.confirm(`Delete scheme "${name}"?`)) return;
    await api.delete(`/schemes/${id}`);
    toast.success("Scheme deleted");
    load();
  }

  async function recompute(id) {
    toast.loading("Recomputing…", { id: "rec" + id });
    try {
      const { data } = await api.post(`/schemes/${id}/recompute`);
      toast.success(`Progress: ${data?.scheme?.progress ?? 0}%`, { id: "rec" + id });
      load();
    } catch {
      toast.error("Failed", { id: "rec" + id });
    }
  }

  async function recomputeAll() {
    toast.loading("Recomputing all…", { id: "ra" });
    try {
      const { data } = await api.post("/schemes/recompute-all");
      toast.success(`Recomputed ${data.updated} schemes`, { id: "ra" });
      load();
    } catch {
      toast.error("Failed", { id: "ra" });
    }
  }

  async function syncZohoBrands() {
    toast.loading("Pulling brands from Zoho…", { id: "zb" });
    try {
      const { data } = await api.post("/schemes/sync-zoho-brands");
      if (data?.ok) {
        toast.success(`Got ${data.brand_count} brands from ${data.items_pulled} items`, { id: "zb" });
        setBrands(data.brands || []);
      } else {
        toast.error(data?.error || "Zoho brand sync failed", { id: "zb" });
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed", { id: "zb" });
    }
  }

  async function uploadFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f);
    toast.loading("Uploading…", { id: "up" });
    try {
      const { data } = await api.post("/schemes/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(
        `Created ${data.created} · Updated ${data.updated} · Skipped ${data.skipped}`,
        { id: "up" },
      );
      if (data.errors?.length) toast.warning(`${data.errors.length} row error(s) — check console`);
      console.log("Scheme upload errors:", data.errors);
      load();
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || "Upload failed", { id: "up" });
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function openLeaderboard(id) {
    setOpenLb(id);
    setLbData(null);
    try {
      const { data } = await api.get(`/schemes/${id}/leaderboard`);
      setLbData(data);
    } catch {
      toast.error("Failed to load leaderboard");
    }
  }

  return (
    <AppLayout title="Schemes" subtitle={`${list.length} programs · ${list.filter(s => s.active).length} live`}>
      <div className="mb-5 flex flex-wrap items-center justify-end gap-2">
        {canManage && (
          <Button size="sm" variant="outline" onClick={recomputeAll} disabled={loading} data-testid="recompute-all-btn">
            <RefreshCw size={13} className={`mr-1.5 ${loading ? "animate-spin" : ""}`} /> Recompute all
          </Button>
        )}
        {isAdmin && (
          <>
            <Button size="sm" variant="outline" onClick={syncZohoBrands} data-testid="sync-zoho-brands-btn">
              <Cloud size={13} className="mr-1.5" /> Sync Zoho brands
            </Button>
            <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} data-testid="upload-schemes-btn">
              <Upload size={13} className="mr-1.5" /> Upload Excel/CSV
            </Button>
            <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={uploadFile} data-testid="scheme-file-input" />
            <Dialog open={openNew} onOpenChange={setOpenNew}>
              <DialogTrigger asChild>
                <Button size="sm" data-testid="new-scheme-btn"><Plus size={14} className="mr-1.5" /> New scheme</Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader><DialogTitle>Create scheme</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-3 py-2">
                  <div className="col-span-2 space-y-1.5">
                    <Label>Name *</Label>
                    <Input value={form.name} onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))} data-testid="scheme-name" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Brand *</Label>
                    {brands.length ? (
                      <Select value={form.brand} onValueChange={(v) => setForm(f => ({ ...f, brand: v }))}>
                        <SelectTrigger data-testid="scheme-brand"><SelectValue placeholder="Select" /></SelectTrigger>
                        <SelectContent>
                          {brands.map(b => <SelectItem key={b} value={b}>{b}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input value={form.brand} onChange={(e) => setForm(f => ({ ...f, brand: e.target.value }))} placeholder="e.g. Boat" data-testid="scheme-brand" />
                    )}
                  </div>
                  <div className="space-y-1.5">
                    <Label>Type</Label>
                    <Select value={form.type} onValueChange={(v) => setForm(f => ({ ...f, type: v }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="value">Value (₹)</SelectItem>
                        <SelectItem value="volume">Volume</SelectItem>
                        <SelectItem value="product">Product</SelectItem>
                        <SelectItem value="incentive">Incentive</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <Label>Start</Label>
                    <Input type="date" value={form.start_date} onChange={(e) => setForm(f => ({ ...f, start_date: e.target.value }))} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>End</Label>
                    <Input type="date" value={form.end_date} onChange={(e) => setForm(f => ({ ...f, end_date: e.target.value }))} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Target amount (₹)</Label>
                    <Input type="number" value={form.target_amount} onChange={(e) => setForm(f => ({ ...f, target_amount: e.target.value }))} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Reward</Label>
                    <Input value={form.reward} onChange={(e) => setForm(f => ({ ...f, reward: e.target.value }))} placeholder="e.g. 2% extra credit" />
                  </div>
                  <div className="col-span-2 space-y-1.5">
                    <Label>Description</Label>
                    <Textarea rows={2} value={form.description} onChange={(e) => setForm(f => ({ ...f, description: e.target.value }))} />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setOpenNew(false)}>Cancel</Button>
                  <Button onClick={createScheme} data-testid="create-scheme-submit">Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        )}
      </div>

      {/* Help-strip on how to upload */}
      {isAdmin && (
        <div className="mb-4 text-xs text-muted-foreground border border-dashed border-border rounded-md p-3 bg-surface">
          <span className="font-mono uppercase tracking-widest text-[10px] text-ai-text mr-2">UPLOAD FORMAT</span>
          Columns: <span className="font-mono">name, brand, start_date, end_date</span> (required) · <span className="font-mono">type, description, target_amount, reward, active</span> (optional). Dates in YYYY-MM-DD.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="scheme-grid">
        {list.map((s) => (
          <div key={s.id} className="bg-surface border border-border rounded-lg p-5 hover:shadow-sm transition flex flex-col" data-testid={`scheme-${s.id}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-widest bg-muted px-2 py-0.5 rounded">{s.brand}</span>
              <span className={`text-[10px] font-mono uppercase tracking-wider ${s.active ? "text-success" : "text-muted-foreground"}`}>
                {s.active ? "● LIVE" : "○ ENDED"}
              </span>
            </div>
            <h4 className="font-display font-bold text-base leading-tight">{s.name}</h4>
            <p className="text-xs text-muted-foreground mt-2 line-clamp-2 min-h-[2rem]">{s.description || "—"}</p>
            <div className="mt-4 text-xs">
              <div className="flex justify-between mb-1">
                <span className="text-muted-foreground">Achieved</span>
                <span className="font-mono font-semibold tabular">{formatINRFull(s.achieved_amount || 0)} / {formatINRFull(s.target_amount || 0)}</span>
              </div>
              <Progress value={Math.min(100, s.progress || 0)} className="h-1.5" />
              <div className="text-right text-[10px] font-mono mt-1 text-muted-foreground">{Math.round(s.progress || 0)}%</div>
            </div>
            <div className="mt-3 pt-3 border-t border-border space-y-1.5 text-xs flex-1">
              <div className="flex justify-between"><span className="text-muted-foreground">Reward</span><span className="font-semibold text-primary text-right">{s.reward || "—"}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Window</span><span className="font-mono">{(s.start_date || "").slice(0, 10)} → {(s.end_date || "").slice(0, 10)}</span></div>
            </div>
            <div className="mt-3 pt-3 border-t border-border flex items-center gap-1.5">
              <Button size="sm" variant="outline" className="h-7 text-xs flex-1" onClick={() => openLeaderboard(s.id)} data-testid={`leaderboard-${s.id}`}>
                <Trophy size={11} className="mr-1" /> Leaderboard
              </Button>
              {canManage && (
                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => recompute(s.id)} data-testid={`recompute-${s.id}`}>
                  <BarChart3 size={11} className="mr-1" /> Recompute
                </Button>
              )}
              {isAdmin && (
                <Button size="sm" variant="outline" className="h-7 text-xs text-destructive" onClick={() => deleteScheme(s.id, s.name)} data-testid={`delete-${s.id}`}>
                  <Trash2 size={11} />
                </Button>
              )}
            </div>
          </div>
        ))}
        {list.length === 0 && !loading && (
          <div className="col-span-full text-center py-12 text-sm text-muted-foreground">
            No schemes yet. {isAdmin ? "Click 'New scheme' or 'Upload Excel/CSV' to begin." : "Ask an admin to create some."}
          </div>
        )}
      </div>

      {/* Leaderboard dialog */}
      <Dialog open={!!openLb} onOpenChange={(o) => { if (!o) { setOpenLb(null); setLbData(null); } }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Trophy size={16} /> Leaderboard</DialogTitle>
          </DialogHeader>
          {!lbData ? (
            <div className="py-12 text-center text-sm text-muted-foreground">Computing…</div>
          ) : (
            <div>
              <div className="mb-3 grid grid-cols-3 gap-2 text-xs">
                <div className="bg-muted/30 rounded p-2"><div className="text-[10px] uppercase tracking-widest text-muted-foreground">Target</div><div className="font-mono tabular font-bold">{formatINRFull(lbData.scheme?.target_amount || 0)}</div></div>
                <div className="bg-muted/30 rounded p-2"><div className="text-[10px] uppercase tracking-widest text-muted-foreground">Achieved</div><div className="font-mono tabular font-bold">{formatINRFull(lbData.total || 0)}</div></div>
                <div className="bg-muted/30 rounded p-2"><div className="text-[10px] uppercase tracking-widest text-muted-foreground">Progress</div><div className="font-mono tabular font-bold">{Math.round(lbData.scheme?.progress || 0)}%</div></div>
              </div>
              <div className="max-h-[420px] overflow-y-auto border border-border rounded">
                <table className="w-full text-sm">
                  <thead className="bg-muted/30 sticky top-0">
                    <tr className="border-b border-border">
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">#</th>
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">Customer</th>
                      <th className="text-left px-3 py-2 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">Tier</th>
                      <th className="text-right px-3 py-2 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">Amount</th>
                      <th className="text-right px-3 py-2 text-[10px] uppercase tracking-widest font-semibold text-muted-foreground">% Target</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(lbData.leaderboard || []).map((row, i) => (
                      <tr key={row.customer_id} className="border-b border-border">
                        <td className="px-3 py-2 font-mono text-xs text-muted-foreground">{i + 1}</td>
                        <td className="px-3 py-2">{row.name}</td>
                        <td className="px-3 py-2">
                          {row.tier && (
                            <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${TIER_COLORS[row.tier] || "bg-muted"}`}>{row.tier}</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono tabular">{formatINRFull(row.amount)}</td>
                        <td className="px-3 py-2 text-right font-mono tabular text-primary">{row.pct_of_target}%</td>
                      </tr>
                    ))}
                    {(lbData.leaderboard || []).length === 0 && (
                      <tr><td colSpan={5} className="px-3 py-8 text-center text-sm text-muted-foreground">No matching invoices in this window.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
