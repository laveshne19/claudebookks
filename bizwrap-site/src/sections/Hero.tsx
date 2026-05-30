import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles } from "lucide-react";
import { useMetalRates } from "@/hooks/useMetalRates";
import { inr } from "@/data/catalog";

const stat = (n: string, l: string) => ({ n, l });
const stats = [stat("500+", "Corporate Clients"), stat("50,000+", "Gifts Delivered"), stat("100+", "Brands")];

const container = { hidden: {}, show: { transition: { staggerChildren: 0.12, delayChildren: 2.7 } } };
const item = { hidden: { opacity: 0, y: 24 }, show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.2, 0.7, 0.2, 1] as const } } };

export function Hero() {
  const { rates, live, updated } = useMetalRates();
  return (
    <section id="top" className="relative overflow-hidden pt-[118px] pb-20 text-white" style={{ background: "linear-gradient(160deg,#0f6b4e,#0E5C43 55%,#0A3F2E)" }}>
      <div className="dotgrid absolute inset-0 opacity-60" />
      <motion.div className="absolute -right-16 -top-28 h-[380px] w-[380px] rounded-full blur-[64px]" style={{ background: "radial-gradient(circle,rgba(228,201,122,.5),transparent 70%)" }} animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 8, repeat: Infinity }} />
      <motion.div className="absolute -bottom-28 -left-20 h-[300px] w-[300px] rounded-full blur-[64px]" style={{ background: "radial-gradient(circle,rgba(21,121,90,.6),transparent 70%)" }} animate={{ scale: [1, 1.15, 1] }} transition={{ duration: 9, repeat: Infinity }} />

      <div className="relative z-10 mx-auto grid max-w-[1280px] grid-cols-1 items-center gap-12 px-6 md:grid-cols-[1.1fr_0.9fr]">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.span variants={item} className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-gold">
            <Sparkles className="h-3.5 w-3.5" /> Pan-India · 7 years of trusted gifting
          </motion.span>
          <motion.h1 variants={item} className="mt-4 font-display text-[clamp(32px,4.6vw,56px)] font-medium leading-[1.05] text-balance">
            India's Trusted <br /> <span className="gold-text italic">Corporate Gifting</span> Partner
          </motion.h1>
          <motion.p variants={item} className="mt-5 max-w-lg text-[16.5px] font-light leading-relaxed text-white/80">
            Premium gifts, lifestyle gadgets, audio, wearables, gold &amp; silver coins and vouchers — curated for businesses across India.
          </motion.p>
          <motion.div variants={item} className="mt-7 flex flex-wrap gap-3">
            <Button asChild size="lg" className="rounded-full bg-gold font-semibold text-emerald-deep hover:bg-gold-soft">
              <a href="#shop">Shop by Budget <ArrowRight className="ml-1 h-4 w-4" /></a>
            </Button>
            <Button asChild size="lg" variant="outline" className="rounded-full border-white/30 bg-transparent text-white hover:border-gold-soft hover:bg-white/5 hover:text-gold-soft">
              <a href="#rfq">Request a Quote</a>
            </Button>
          </motion.div>
          <motion.div variants={item} className="mt-9 flex flex-wrap gap-8">
            {stats.map((s) => (
              <div key={s.l}>
                <div className="font-display text-2xl font-semibold text-gold-soft">{s.n}</div>
                <div className="text-[12.5px] text-white/60">{s.l}</div>
              </div>
            ))}
          </motion.div>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 3, duration: 0.7 }} className="relative">
          <motion.span className="absolute -top-7 left-0 text-3xl" animate={{ y: [0, -12, 0] }} transition={{ duration: 5, repeat: Infinity }}>🎁</motion.span>
          <motion.span className="absolute -bottom-5 right-2 text-3xl" animate={{ y: [0, -12, 0] }} transition={{ duration: 5, delay: 1.5, repeat: Infinity }}>🪙</motion.span>
          <div className="rounded-[22px] border border-gold/30 bg-white/[0.07] p-6 shadow-2xl backdrop-blur-md">
            <h4 className="font-display text-lg text-gold-soft">Live precious-metal pricing</h4>
            <div className="mt-3 space-y-0.5">
              <Rate label="Gold · 24K" value={`${inr(rates.gold)} / g`} />
              <Rate label="Silver · 999" value={`${inr(rates.silver)} / g`} last />
            </div>
            <p className="mt-3 flex items-center gap-2 text-[12px] text-white/50">
              <span className={`inline-block h-2 w-2 rounded-full ${live ? "animate-pulseRing bg-emerald-400" : "bg-white/40"}`} />
              {live ? `Live market rate · updated ${updated}` : "Live rate · auto-updates"} · incl. GST &amp; making on invoice.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Rate({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <div className={`flex items-center justify-between py-2.5 text-sm ${last ? "" : "border-b border-dashed border-white/15"}`}>
      <span className="text-white/80">{label}</span>
      <b className="font-display text-gold-soft">{value}</b>
    </div>
  );
}
