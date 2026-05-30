import { motion } from "framer-motion";
import { SectionHead } from "@/components/SectionHead";

const posts = [
  { e: "🎁", g: "linear-gradient(160deg,#15795a,#0a3f2e)", m: "Trends · 28 May 2026", t: "Corporate Gifting Trends to Watch in FY26", d: "From sustainable hampers to gadget bundles — what Indian enterprises are gifting this year." },
  { e: "🪙", g: "linear-gradient(160deg,#c9a227,#7a5f12)", m: "Guide · 20 May 2026", t: "Why Gold & Silver Coins Make Smart Corporate Gifts", d: "Purity, hallmarking, GST and how to price coin gifting transparently for bulk orders." },
  { e: "🤝", g: "linear-gradient(160deg,#c06b4a,#6e351f)", m: "Employee · 12 May 2026", t: "Building Onboarding Kits That New Hires Love", d: "A practical checklist for HR teams designing welcome kits that boost day-one engagement." },
];

export function Blog() {
  return (
    <section id="insights" className="py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead eyebrow="Insights" title="Corporate gifting, decoded" />
        <div className="grid gap-5 md:grid-cols-3">
          {posts.map((p, i) => (
            <motion.article key={p.t} initial={{ opacity: 0, y: 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }} whileHover={{ y: -6 }} className="cursor-pointer overflow-hidden rounded-2xl border border-border bg-card transition hover:border-gold-soft hover:shadow-lg">
              <div className="flex h-36 items-end p-4 text-4xl" style={{ background: p.g }}>{p.e}</div>
              <div className="p-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-gold">{p.m}</div>
                <h3 className="mt-2 font-display text-lg leading-tight text-emerald-deep">{p.t}</h3>
                <p className="mt-2 text-[13.5px] text-muted-foreground">{p.d}</p>
                <div className="mt-3 text-[13px] font-semibold text-emerald">Read more →</div>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
