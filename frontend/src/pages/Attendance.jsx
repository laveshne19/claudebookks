import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Clock } from "lucide-react";

export default function Attendance() {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);

  useEffect(() => {
    api.get("/attendance").then(({ data }) => setRecords(data));
  }, []);

  return (
    <AppLayout title="Attendance" subtitle={user?.role === "sales" ? "My attendance log" : "Team attendance"}>
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="attendance-table">
            <thead className="bg-muted/30">
              <tr className="border-b border-border">
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Date</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Check-in</th>
                <th className="text-left px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Last Activity</th>
                <th className="text-right px-5 py-2.5 text-[10px] uppercase tracking-widest text-muted-foreground font-semibold">Pings</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0 hover:bg-surface-hover" data-testid={`attendance-row-${r.date}`}>
                  <td className="px-5 py-3 text-sm font-medium">{new Date(r.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</td>
                  <td className="px-5 py-3 text-xs font-mono">{r.check_in ? new Date(r.check_in).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                  <td className="px-5 py-3 text-xs font-mono">{r.check_out ? new Date(r.check_out).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
                  <td className="px-5 py-3 text-right font-mono tabular text-xs">{r.ping_count || 0}</td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr><td colSpan={4} className="px-5 py-12 text-center text-sm text-muted-foreground">
                  <Clock size={20} className="mx-auto mb-2 text-muted-foreground" />
                  No attendance recorded yet. Open the app on your phone to start auto-attendance.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <p className="mt-4 text-[10px] uppercase tracking-widest text-muted-foreground font-mono">
        // ATTENDANCE IS CAPTURED AUTOMATICALLY WHEN THE APP IS OPEN
      </p>
    </AppLayout>
  );
}
