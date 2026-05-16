import { useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Upload, Download, FileSpreadsheet, Loader2, MapPin } from "lucide-react";
import { toast } from "sonner";

const UPLOAD_KINDS = [
  {
    key: "customers",
    label: "Customers",
    description: "Add or update customer records. Fuzzy name-matched against existing.",
    endpoint: "/admin/upload/customers",
    template: "customers",
  },
  {
    key: "beat-plans",
    label: "Beat Plans",
    description: "Assign weekly beat days (e.g. 'Mon, Thu' or 'Sat (weekly)') per customer.",
    endpoint: "/admin/upload/beat-plans",
    template: "beat_plans",
  },
  {
    key: "salesperson-mapping",
    label: "Salesperson Mapping",
    description: "Map customers to salespersons; optionally set tier, beat_days, monthly_target.",
    endpoint: "/admin/upload/salesperson-mapping",
    template: "salesperson_mapping",
  },
];

function UploadRow({ kind }) {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  async function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setResult(null);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const { data } = await api.post(kind.endpoint, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      toast.success(`${kind.label} uploaded`, {
        description: `${data.created || data.updated || 0} processed · ${data.errors?.length || 0} errors`,
      });
    } catch (e2) {
      toast.error(e2?.response?.data?.detail || `Failed to upload ${kind.label}`);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function downloadTemplate() {
    try {
      const { data } = await api.get(`/admin/upload-template/${kind.template}`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${kind.template}_template.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Could not download template");
    }
  }

  return (
    <div className="border border-border rounded-md p-4" data-testid={`upload-row-${kind.key}`}>
      <div className="flex items-start gap-3 mb-3">
        <FileSpreadsheet size={18} className="text-primary mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="font-display font-bold text-sm">{kind.label}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{kind.description}</div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={onFile} data-testid={`upload-input-${kind.key}`} />
        <Button size="sm" onClick={() => fileRef.current?.click()} disabled={busy} className="flex-1" data-testid={`upload-btn-${kind.key}`}>
          {busy ? <Loader2 size={13} className="mr-1.5 animate-spin" /> : <Upload size={13} className="mr-1.5" />}
          {busy ? "Uploading…" : "Upload file"}
        </Button>
        <Button size="sm" variant="outline" onClick={downloadTemplate} data-testid={`template-btn-${kind.key}`}>
          <Download size={13} className="mr-1.5" /> Template
        </Button>
      </div>
      {result && (
        <div className="mt-3 text-xs space-y-1 bg-muted/40 rounded p-2 font-mono">
          {Object.entries(result).filter(([k]) => k !== "errors").map(([k, v]) => (
            <div key={k} className="flex justify-between"><span className="text-muted-foreground">{k}</span><span>{typeof v === "object" ? JSON.stringify(v) : String(v)}</span></div>
          ))}
          {result.errors?.length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-destructive">{result.errors.length} error(s)</summary>
              <ul className="mt-1 space-y-0.5 max-h-32 overflow-y-auto">
                {result.errors.slice(0, 25).map((e, i) => <li key={i} className="text-[10px] text-destructive">{e}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}

export default function DataUploadCenter() {
  const [backfillBusy, setBackfillBusy] = useState(false);
  const [backfillResult, setBackfillResult] = useState(null);

  async function backfillAddresses() {
    setBackfillBusy(true);
    setBackfillResult(null);
    try {
      const { data } = await api.post("/admin/backfill-addresses", null, { timeout: 600000 });
      setBackfillResult(data);
      toast.success(`Backfill complete — ${data.updated} addresses updated`, {
        description: `Failed: ${data.failed} · Time: ${data.duration_seconds}s`,
      });
    } catch (e) {
      toast.error("Backfill failed", { description: e?.response?.data?.detail || String(e) });
    } finally {
      setBackfillBusy(false);
    }
  }

  return (
    <div className="bg-surface border border-border rounded-lg p-5" data-testid="data-upload-center">
      <div className="text-[11px] uppercase tracking-widest text-muted-foreground font-mono mb-1">// DATA UPLOAD CENTER</div>
      <h3 className="font-display font-bold text-lg mb-1">Bulk import / sync</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Upload Excel or CSV files to refresh the entire app. Existing records are matched by name (fuzzy) and updated in place.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
        {UPLOAD_KINDS.map((k) => <UploadRow key={k.key} kind={k} />)}
      </div>

      <div className="border border-dashed border-border rounded-md p-4 bg-muted/20" data-testid="address-backfill-card">
        <div className="flex items-start gap-3">
          <MapPin size={18} className="text-primary mt-0.5" />
          <div className="flex-1">
            <div className="font-display font-bold text-sm">Address backfill (Zoho)</div>
            <div className="text-xs text-muted-foreground mt-0.5 mb-2">
              Re-fetch full billing addresses (sector, city, state) from Zoho for every customer.
              Use this once after major Zoho address changes. Takes 2-5 minutes.
            </div>
            <Button size="sm" onClick={backfillAddresses} disabled={backfillBusy} data-testid="backfill-addresses-btn">
              {backfillBusy ? <Loader2 size={13} className="mr-1.5 animate-spin" /> : <MapPin size={13} className="mr-1.5" />}
              {backfillBusy ? "Backfilling…" : "Backfill addresses"}
            </Button>
            {backfillResult && (
              <div className="mt-3 text-xs font-mono bg-muted/40 rounded p-2 space-y-0.5">
                <div className="flex justify-between"><span className="text-muted-foreground">Updated</span><span className="text-success">{backfillResult.updated}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Failed</span><span className="text-destructive">{backfillResult.failed}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Total</span><span>{backfillResult.total}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Duration</span><span>{backfillResult.duration_seconds}s</span></div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
