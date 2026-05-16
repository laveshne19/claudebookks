import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard, Users, ShoppingBag, Wallet, Tag, BarChart3,
  Bell, Settings, LogOut, Building2, Map, Sparkles, Clock
} from "lucide-react";

const NAV = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, module: "dashboard" },
  { label: "Customers", to: "/customers", icon: Users, module: "customers" },
  { label: "Sales", to: "/sales", icon: ShoppingBag, module: "sales" },
  { label: "Accounts", to: "/accounts", icon: Wallet, module: "accounts" },
  { label: "Schemes", to: "/schemes", icon: Tag, module: "schemes" },
  { label: "AI Route", to: "/route", icon: Sparkles, module: "route" },
  { label: "Map View", to: "/map", icon: Map, module: "route" },
  { label: "Attendance", to: "/attendance", icon: Clock, module: "attendance" },
  { label: "Reports", to: "/reports", icon: BarChart3, module: "reports" },
  { label: "Notifications", to: "/notifications", icon: Bell, module: "notifications" },
  { label: "Admin", to: "/admin", icon: Settings, module: "admin" },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const allowed = new Set(user?.effective_permissions?.modules || ["dashboard"]);
  const items = NAV.filter((n) => allowed.has(n.module));

  return (
    <aside
      className="hidden md:flex w-64 shrink-0 flex-col bg-zinc-950 text-zinc-200 border-r border-zinc-800 sidebar-scroll"
      data-testid="sidebar"
    >
      <div className="h-14 flex items-center gap-2 px-5 border-b border-zinc-800/80">
        <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
          <Building2 size={18} className="text-white" strokeWidth={2} />
        </div>
        <div className="leading-tight">
          <div className="font-display font-black text-white text-sm tracking-tight">NALANDA</div>
          <div className="text-[10px] uppercase tracking-widest text-zinc-500">Enterprises</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        <div className="text-[10px] uppercase tracking-widest text-zinc-600 px-3 mb-2">Workspace</div>
        {items.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            data-testid={`nav-${it.label.toLowerCase().replace(/\s+/g, "-")}`}
            className={({ isActive }) =>
              `group flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`
            }
          >
            <it.icon size={17} strokeWidth={1.75} />
            <span>{it.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-3 border-t border-zinc-800/80">
        <div className="flex items-center gap-3 px-2 py-2 rounded-md">
          <div className="h-8 w-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-bold text-zinc-200">
            {(user?.name || "U").slice(0, 2).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">{user?.name}</div>
            <div className="text-[10px] uppercase tracking-widest text-zinc-500">{user?.role?.replace("_", " ")}</div>
          </div>
          <button
            onClick={async () => { await logout(); navigate("/login"); }}
            data-testid="logout-btn"
            className="p-1.5 rounded text-zinc-400 hover:text-white hover:bg-zinc-900 transition"
            title="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
