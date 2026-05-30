import { motion } from "framer-motion";
import { SectionHead } from "@/components/SectionHead";
import { Handshake, Lock, Calculator, Bot, MessageCircle, Backpack, PartyPopper, Wrench, LayoutDashboard } from "lucide-react";

const mods = [
  { icon: Handshake, t: "Vendor Portal", d: "Suppliers manage catalogue, pricing, stock & dispatch with role-based access.", tag: "New" },
  { icon: Lock, t: "Corporate Account Login", d: "Per-company logins with negotiated price lists, GST & order history.", tag: "New" },
  { icon: Calculator, t: "Bulk Quotation Engine", d: "Auto tiered quotes by quantity, branding & budget — PDF in one click.", tag: "New" },
  { icon: Bot, t: "AI Gift Recommender", d: "Suggests gifts by occasion, seniority & budget from live catalogue.", tag: "New" },
  { icon: MessageCircle, t: "WhatsApp Ordering", d: "Browse, quote & order over WhatsApp via Interakt.", tag: "New" },
  { icon: Backpack, t: "Onboarding Kit Builder", d: "HR builds new-hire kits; reorder per headcount instantly.", tag: "New" },
  { icon: PartyPopper, t: "Festival Campaign Manager", d: "Schedule Diwali/New-Year drives, recipient lists & dispatch tracking.", tag: "New" },
  { icon: Wrench, t: "Customization Studio", d: "Laser engraving, logo & UV printing, embroidery, premium packaging.", tag: "Service" },
  { icon: LayoutDashboard, t: "Admin Dashboard", d: "Revenue, orders, leads, RFQs, inventory & metal-rate controls.", tag: "Core" },
];

export function Modules() {
  return (
    <section id="modules" className="bg-cream py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead eyebrow="Enterprise Solutions" title="Built for how large teams actually buy" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {mods.map((m, i) => (
            <motion.div
              key={m.t}
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: (i % 3) * 0.08 }}
              whileHover={{ y: -5 }}
              className="rounded-2xl border border-border bg-card p-6 transition hover:border-gold-soft hover:shadow-[0_20px_50px_-28px_rgba(14,92,67,.45)]"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald text-gold-soft">
                <m.icon className="h-5 w-5" />
              </div>
              <h3 className="font-display text-lg text-emerald-deep">{m.t}</h3>
              <p className="mt-1.5 text-[13.5px] text-muted-foreground">{m.d}</p>
              <span className="mt-3 inline-block text-[10.5px] font-semibold uppercase tracking-[0.12em] text-terra">{m.tag}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
