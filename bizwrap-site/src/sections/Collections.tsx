import { motion } from "framer-motion";
import { CATEGORIES, PRODUCTS, catIcon } from "@/data/catalog";
import { SectionHead } from "@/components/SectionHead";

const grad: Record<string, string> = {
  "Audio & Earbuds": "linear-gradient(160deg,#15795a,#0a3f2e)",
  "Smartwatches & Wearables": "linear-gradient(160deg,#3f7a52,#1d3f28)",
  "Speakers": "linear-gradient(160deg,#c9a227,#7a5f12)",
  "Home & Party Audio": "linear-gradient(160deg,#c06b4a,#6e351f)",
  "Mobile Accessories": "linear-gradient(160deg,#177a5a,#0c4734)",
  "Smart Home & Security": "linear-gradient(160deg,#2c5d49,#133024)",
  "Lifestyle Gadgets": "linear-gradient(160deg,#b8902a,#5c4410)",
};

export function Collections() {
  const go = () => document.getElementById("shop")?.scrollIntoView({ behavior: "smooth" });
  return (
    <section id="collections" className="py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead eyebrow="Curated Collections" title="Gifting for every occasion" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {CATEGORIES.map((c, i) => (
            <motion.button
              key={c}
              onClick={go}
              initial={{ opacity: 0, y: 22 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              whileHover={{ y: -6 }}
              className="relative flex min-h-[168px] flex-col justify-end overflow-hidden rounded-2xl p-5 text-left text-white shadow-lg"
              style={{ background: grad[c] ?? "linear-gradient(160deg,#15795a,#0a3f2e)" }}
            >
              <span className="absolute right-4 top-4 text-3xl opacity-90">{catIcon[c]}</span>
              <h3 className="font-display text-lg leading-tight">{c}</h3>
              <p className="mt-1 text-[12.5px] text-white/80">{PRODUCTS.filter((p) => p.cat === c).length} products</p>
            </motion.button>
          ))}
          <motion.button onClick={go} whileHover={{ y: -6 }} className="flex min-h-[168px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gold/40 p-5 text-center transition hover:border-gold">
            <span className="text-3xl">→</span>
            <h3 className="mt-2 font-display text-lg text-emerald-deep">Browse all</h3>
          </motion.button>
        </div>
      </div>
    </section>
  );
}
