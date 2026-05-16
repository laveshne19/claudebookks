import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { toast } from "sonner";

export default function PermissionsDialog({ user, open, onClose, onSaved }) {
  const [options, setOptions] = useState(null);
  const [perms, setPerms] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.get("/permissions/options").then(({ data }) => setOptions(data));
    const ep = user?.effective_permissions || {};
    setPerms({
      modules: ep.modules || [],
      brands: ep.brands || [],
      view_scope: ep.view_scope || "full",
      customer_visibility: ep.customer_visibility || "assigned",
      can_edit: !!ep.can_edit,
      can_create: !!ep.can_create,
      can_export: !!ep.can_export,
      can_manage_users: !!ep.can_manage_users,
    });
  }, [open, user]);

  if (!options || !perms) return null;

  const toggleArray = (key, value) => {
    setPerms((p) => {
      const set = new Set(p[key]);
      if (set.has(value)) set.delete(value); else set.add(value);
      return { ...p, [key]: Array.from(set) };
    });
  };

  async function save() {
    setSaving(true);
    try {
      await api.patch(`/users/${user.id}/permissions`, perms);
      toast.success("Permissions updated");
      onSaved?.();
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to update");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="permissions-dialog">
        <DialogHeader>
          <DialogTitle>Permissions · {user?.name}</DialogTitle>
          <p className="text-xs text-muted-foreground mt-1">Role: <span className="font-mono">{user?.role}</span> · Override what this user can see and do</p>
        </DialogHeader>

        <div className="space-y-5 mt-3 max-h-[60vh] overflow-y-auto pr-2">
          <section>
            <Label className="text-xs uppercase tracking-wider font-semibold">Allowed modules</Label>
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {options.modules.map((m) => (
                <label key={m} className="flex items-center gap-2 text-sm cursor-pointer" data-testid={`perm-module-${m}`}>
                  <Checkbox checked={perms.modules.includes(m)} onCheckedChange={() => toggleArray("modules", m)} />
                  <span className="capitalize">{m}</span>
                </label>
              ))}
            </div>
          </section>

          <section>
            <Label className="text-xs uppercase tracking-wider font-semibold">Brand filter (empty = all brands)</Label>
            <div className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
              {options.brands.map((b) => (
                <label key={b} className="flex items-center gap-2 text-sm cursor-pointer" data-testid={`perm-brand-${b}`}>
                  <Checkbox checked={perms.brands.includes(b)} onCheckedChange={() => toggleArray("brands", b)} />
                  <span>{b}</span>
                </label>
              ))}
            </div>
          </section>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <section>
              <Label className="text-xs uppercase tracking-wider font-semibold">View scope</Label>
              <Select value={perms.view_scope} onValueChange={(v) => setPerms({ ...perms, view_scope: v })}>
                <SelectTrigger className="mt-2" data-testid="perm-view-scope"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {options.view_scopes.map((v) => <SelectItem key={v} value={v}>{v.replace("_", " ")}</SelectItem>)}
                </SelectContent>
              </Select>
              <p className="text-[10px] text-muted-foreground mt-1 font-mono">FULL = customer-level · AGGREGATE = no names · TOTALS = day totals</p>
            </section>

            <section>
              <Label className="text-xs uppercase tracking-wider font-semibold">Customer visibility</Label>
              <Select value={perms.customer_visibility} onValueChange={(v) => setPerms({ ...perms, customer_visibility: v })}>
                <SelectTrigger className="mt-2" data-testid="perm-cust-vis"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {options.customer_visibility.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </section>
          </div>

          <section className="space-y-3">
            <Label className="text-xs uppercase tracking-wider font-semibold">Action permissions</Label>
            {[
              { k: "can_edit", label: "Can edit records" },
              { k: "can_create", label: "Can create records" },
              { k: "can_export", label: "Can export reports (Excel/PDF)" },
              { k: "can_manage_users", label: "Can manage users" },
            ].map((it) => (
              <div key={it.k} className="flex items-center justify-between border border-border rounded-md px-3 py-2">
                <span className="text-sm">{it.label}</span>
                <Switch checked={perms[it.k]} onCheckedChange={(v) => setPerms({ ...perms, [it.k]: v })} data-testid={`perm-${it.k}`} />
              </div>
            ))}
          </section>
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} data-testid="save-permissions-btn">{saving ? "Saving…" : "Save permissions"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
