import { motion } from "framer-motion";
import { SectionHead } from "@/components/SectionHead";

const vals = ["₹500","₹1,000","₹2,000","₹5,000"];
const tags = ["Bulk pricing","Bulk pricing","Best value","Enterprise deal"];
const brands = ["Amazon","Flipkart","Myntra","Ajio","Nykaa","Swiggy","Zomato","Croma","Reliance Digital"];

export function Vouchers() {
  return (
    <section id="vouchers" className="py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead eyebrow="Gift Vouchers" title="Multi-brand vouchers at corporate rates" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {vals.map((v, i) => (
            <motion.div key={v} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.06 }} whileHover={{ y: -5 }} className="rounded-2xl border border-border bg-card p-6 text-center transition hover:border-gold hover:shadow-lg">
              <div className="font-display text-[32px] text-emerald">{v}</div>
              <div className="mt-2 inline-block rounded-full bg-emerald/10 px-3 py-1 text-[12.5px] font-semibold text-emerald-light">{tags[i]}</div>
            </motion.div>
          ))}
        </div>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          {brands.map((b) => <span key={b} className="rounded-full border border-border bg-card px-4 py-1.5 text-[13.5px] font-semibold text-muted-foreground">{b}</span>)}
        </div>
      </div>
    </section>
  );
}
