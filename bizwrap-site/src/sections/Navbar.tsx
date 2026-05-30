import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Menu, X } from "lucide-react";
import { InstallButton } from "@/components/InstallButton";

const links = [
  { href: "#shop", label: "Shop by Budget" },
  { href: "#collections", label: "Collections" },
  { href: "#metal", label: "Gold & Silver" },
  { href: "#story", label: "Our Story" },
  { href: "#insights", label: "Insights" },
  { href: "#rfq", label: "Contact" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 30);
    window.addEventListener("scroll", on);
    return () => window.removeEventListener("scroll", on);
  }, []);

  return (
    <motion.header
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ delay: 2.6, duration: 0.6, ease: "easeOut" }}
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 [.has-topbar_&]:top-[38px] ${
        scrolled ? "bg-ivory/90 shadow-[0_1px_0_hsl(var(--border))] backdrop-blur-md" : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-[72px] max-w-[1280px] items-center justify-between px-6">
        <a href="#top"><Logo light={!scrolled} /></a>
        <nav className="hidden items-center gap-7 lg:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className={`group relative text-sm font-medium transition-colors ${
                scrolled ? "text-ink hover:text-gold" : "text-white/90 hover:text-gold-soft"
              }`}
            >
              {l.label}
              <span className="absolute -bottom-1.5 left-0 h-0.5 w-0 bg-gold transition-all duration-300 group-hover:w-full" />
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <InstallButton scrolled={scrolled} />
          <a href="#login" className={`rounded-full border px-4 py-2.5 text-sm font-semibold transition ${scrolled ? "border-border text-emerald hover:border-gold hover:text-gold" : "border-white/35 text-white hover:border-gold-soft hover:text-gold-soft"}`}>
            Corporate Login
          </a>
          <Button asChild className="rounded-full bg-gold font-semibold text-emerald-deep hover:bg-gold-soft">
            <a href="#rfq">Get Quote</a>
          </Button>
        </div>
        <button className="lg:hidden" onClick={() => setOpen(!open)}>
          {open ? <X className={scrolled ? "text-ink" : "text-white"} /> : <Menu className={scrolled ? "text-ink" : "text-white"} />}
        </button>
      </div>
      {open && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="border-t border-border bg-ivory px-6 py-4 lg:hidden">
          {links.map((l) => (
            <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="block py-2.5 font-medium text-ink">
              {l.label}
            </a>
          ))}
          <a href="#rfq" onClick={() => setOpen(false)} className="mt-2 block rounded-full bg-gold py-3 text-center font-semibold text-emerald-deep">Get Quote</a>
        </motion.div>
      )}
    </motion.header>
  );
}
