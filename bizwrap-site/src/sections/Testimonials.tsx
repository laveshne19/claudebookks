import { motion } from "framer-motion";
import { Star } from "lucide-react";
import { SectionHead } from "@/components/SectionHead";

const t = [
  { q: "BizWrap handled our 1,200-employee Diwali rollout end-to-end — branding, dispatch tracking, one GST invoice. Flawless.", n: "Ritika Malhotra", r: "Head of HR · IT Services", i: "RM" },
  { q: "The bulk quotation engine cut our procurement cycle from days to hours. Tiered pricing in one click.", n: "Amit Sharma", r: "Procurement Lead · Manufacturing", i: "AS" },
  { q: "Executive client gifts always look premium. Gold-coin pricing was transparent and delivery on time, pan-India.", n: "Neha Kapoor", r: "VP Admin · BFSI", i: "NK" },
];

export function Testimonials() {
  return (
    <section className="bg-cream py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead eyebrow="Client Voices" title="What procurement & HR teams say" />
        <div className="grid gap-5 md:grid-cols-3">
          {t.map((c, i) => (
            <motion.div key={c.n} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} className="rounded-2xl border border-border bg-card p-7">
              <div className="flex gap-0.5 text-gold">{Array.from({ length: 5 }).map((_, k) => <Star key={k} className="h-4 w-4 fill-gold" />)}</div>
              <p className="my-4 font-display text-[15px] italic leading-relaxed text-ink/85">"{c.q}"</p>
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-full font-display font-semibold text-white" style={{ background: "linear-gradient(135deg,#0E5C43,#C9A227)" }}>{c.i}</div>
                <div>
                  <b className="block text-[13.5px] text-emerald-deep">{c.n}</b>
                  <small className="text-[12px] text-muted-foreground">{c.r}</small>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
