import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import { Bell, AlertTriangle, Tag, Megaphone, Calendar, CheckCircle2 } from "lucide-react";

const ICON = {
  overdue: AlertTriangle,
  scheme: Tag,
  announcement: Megaphone,
  followup: Calendar,
  task: CheckCircle2,
  system: Bell,
};

export default function Notifications() {
  const [list, setList] = useState([]);

  useEffect(() => {
    api.get("/notifications").then(({ data }) => setList(data));
  }, []);

  async function markRead(n) {
    if (n.read) return;
    await api.patch(`/notifications/${n.id}/read`);
    setList((l) => l.map((x) => x.id === n.id ? { ...x, read: true } : x));
  }

  return (
    <AppLayout title="Notifications" subtitle={`${list.filter(n => !n.read).length} unread`}>
      <div className="bg-surface border border-border rounded-lg divide-y divide-border" data-testid="notifications-list">
        {list.length === 0 && <div className="p-12 text-center text-sm text-muted-foreground">No notifications</div>}
        {list.map((n) => {
          const Icon = ICON[n.type] || Bell;
          return (
            <div
              key={n.id}
              onClick={() => markRead(n)}
              className={`px-5 py-4 flex items-start gap-4 cursor-pointer hover:bg-surface-hover transition ${!n.read ? "bg-primary/[0.02]" : ""}`}
              data-testid={`notif-${n.id}`}
            >
              <div className={`h-9 w-9 rounded-md flex items-center justify-center shrink-0 ${
                n.type === "overdue" ? "bg-destructive/10 text-destructive" :
                n.type === "scheme" ? "bg-primary/10 text-primary" :
                n.type === "announcement" ? "bg-warning/10 text-warning" :
                "bg-muted text-muted-foreground"
              }`}>
                <Icon size={16} strokeWidth={1.75} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-display font-bold text-sm">{n.title}</h4>
                  {!n.read && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
                </div>
                <p className="text-xs text-muted-foreground">{n.body}</p>
                <div className="mt-1 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">{new Date(n.created_at).toLocaleString("en-IN")}</div>
              </div>
            </div>
          );
        })}
      </div>
    </AppLayout>
  );
}
