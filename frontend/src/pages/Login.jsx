import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building2, ArrowRight } from "lucide-react";

const HERO = "https://static.prod-images.emergentagent.com/jobs/af0ab025-89aa-4751-8d30-d70381712cf4/images/772d819f53612412f6ea67fa029fec16f1631fb7f40a278d6f66157b58110865.png";

const QUICK = [
  { label: "Super Admin", email: "admin@nalanda.com", password: "Admin@123" },
  { label: "Sales (Andheri)", email: "sales1@nalanda.com", password: "Sales@123" },
  { label: "Accounts", email: "accounts@nalanda.com", password: "Accounts@123" },
];

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("admin@nalanda.com");
  const [password, setPassword] = useState("Admin@123");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  if (user) return <Navigate to="/dashboard" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    const res = await login(email, password);
    setLoading(false);
    if (res.ok) navigate("/dashboard");
    else setErr(res.error || "Login failed");
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background" data-testid="login-page">
      {/* Form */}
      <div className="flex-1 flex flex-col justify-center px-6 md:px-16 lg:px-24 py-12">
        <div className="max-w-md w-full mx-auto md:mx-0">
          <div className="flex items-center gap-2 mb-12">
            <div className="h-9 w-9 rounded-md bg-primary flex items-center justify-center">
              <Building2 size={20} className="text-white" />
            </div>
            <div className="leading-tight">
              <div className="font-display font-black tracking-tight">NALANDA</div>
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Enterprises ERP</div>
            </div>
          </div>

          <div className="mb-8">
            <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-primary mb-3">// Operator Access</div>
            <h1 className="font-display text-3xl md:text-4xl font-black tracking-tight mb-3">Sign in to your workspace</h1>
            <p className="text-sm text-muted-foreground">Internal Operating System for the sales, accounts &amp; admin teams.</p>
          </div>

          <form onSubmit={submit} className="space-y-4" data-testid="login-form">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-xs uppercase tracking-wider font-semibold">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@nalanda.com"
                required
                data-testid="login-email-input"
                className="h-11"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs uppercase tracking-wider font-semibold">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                data-testid="login-password-input"
                className="h-11"
              />
            </div>
            {err && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2" data-testid="login-error">
                {err}
              </div>
            )}
            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 text-sm font-semibold bg-primary hover:bg-primary/90"
              data-testid="login-submit-btn"
            >
              {loading ? "Authenticating…" : "Sign in"}
              {!loading && <ArrowRight size={15} className="ml-2" />}
            </Button>
          </form>

          <div className="mt-10 pt-6 border-t border-border">
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-3">Quick demo access</div>
            <div className="flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <button
                  key={q.email}
                  onClick={() => { setEmail(q.email); setPassword(q.password); }}
                  className="px-3 py-1.5 text-xs rounded-md border border-border bg-surface hover:bg-surface-hover transition font-medium"
                  data-testid={`quick-login-${q.label.toLowerCase().replace(/\s+/g, "-")}`}
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Hero */}
      <div className="hidden md:block flex-1 relative bg-zinc-950 overflow-hidden">
        <img src={HERO} alt="" className="absolute inset-0 w-full h-full object-cover opacity-70" />
        <div className="absolute inset-0 bg-gradient-to-tr from-zinc-950 via-zinc-950/40 to-transparent" />
        <div className="relative h-full flex flex-col justify-end p-10 lg:p-16 text-white z-10">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-primary mb-4">// Operating System</div>
          <h2 className="font-display text-3xl lg:text-5xl font-black tracking-tight max-w-md leading-[1.05]">
            Run the distribution business from one console.
          </h2>
          <p className="mt-4 text-sm text-zinc-300 max-w-md">
            Sales force automation · Customer 360 · AI insights · Accounts recovery · Live schemes · Reporting.
          </p>
          <div className="mt-8 flex items-center gap-6 text-xs font-mono uppercase tracking-widest text-zinc-400">
            <span>Boat</span><span>Fireboltt</span><span>Noise</span><span>Logitech</span><span>Mivi</span>
          </div>
        </div>
      </div>
    </div>
  );
}
