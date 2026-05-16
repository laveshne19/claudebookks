import { Bell, Moon, Sun, Search } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { MobileSidebar } from "./Sidebar";

export default function Topbar({ title, subtitle }) {
  const { theme, toggle } = useTheme();
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/notifications").then(({ data }) => {
      setUnread(data.filter((n) => !n.read).length);
    }).catch(() => {});
  }, []);

  return (
    <header className="h-14 flex items-center justify-between border-b border-border bg-surface/60 backdrop-blur px-4 md:px-6 sticky top-0 z-30" data-testid="topbar">
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <MobileSidebar />
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-lg md:text-xl font-bold tracking-tight truncate" data-testid="page-title">{title}</h1>
            {subtitle && <span className="hidden sm:inline text-xs text-muted-foreground font-mono uppercase tracking-wider">// {subtitle}</span>}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 md:gap-3">
        <div className="hidden md:flex items-center gap-2 h-9 px-3 rounded-md border border-border bg-background text-sm text-muted-foreground w-64">
          <Search size={15} strokeWidth={1.75} />
          <span className="text-xs">Search customers, invoices…</span>
          <kbd className="ml-auto px-1.5 py-0.5 rounded bg-muted text-[10px] font-mono">⌘K</kbd>
        </div>
        <button
          onClick={() => navigate("/notifications")}
          className="relative h-9 w-9 rounded-md border border-border hover:bg-surface-hover flex items-center justify-center transition"
          data-testid="notifications-bell"
        >
          <Bell size={16} strokeWidth={1.75} />
          {unread > 0 && (
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-primary" />
          )}
        </button>
        <button
          onClick={toggle}
          className="h-9 w-9 rounded-md border border-border hover:bg-surface-hover flex items-center justify-center transition"
          data-testid="theme-toggle"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <div className="hidden md:flex items-center gap-2 pl-3 ml-1 border-l border-border">
          <div className="text-right">
            <div className="text-xs font-medium truncate max-w-[120px]">{user?.name}</div>
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{user?.role?.replace("_", " ")}</div>
          </div>
        </div>
      </div>
    </header>
  );
}
