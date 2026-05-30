import { motion } from "framer-motion";
import { type Product, inr, discount } from "@/data/catalog";

export function ProductCard({ p, index = 0 }: { p: Product; index?: number }) {
  const off = discount(p);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.03, 0.3) }}
      className="group flex flex-col overflow-hidden rounded-2xl border border-border bg-card transition-all duration-300 hover:-translate-y-1.5 hover:border-gold-soft hover:shadow-[0_20px_50px_-28px_rgba(14,92,67,.45)]"
    >
      <div className="relative aspect-square overflow-hidden border-b border-border bg-white">
        {off > 0 && <span className="absolute left-2.5 top-2.5 z-10 rounded-md bg-terra px-2 py-1 text-[11px] font-bold text-white">{off}% OFF</span>}
        <span className="absolute right-2.5 top-2.5 z-10 rounded-md bg-emerald/90 px-2 py-1 text-[10px] font-semibold tracking-wide text-white">{p.brand}</span>
        <img
          loading="lazy"
          src={p.img}
          alt={p.title}
          className="h-full w-full object-contain p-3.5 transition-transform duration-500 group-hover:scale-[1.06]"
          onError={(e) => { (e.currentTarget.style.opacity = "0.25"); }}
        />
      </div>
      <div className="flex flex-1 flex-col p-3.5">
        <h3 className="line-clamp-2 min-h-[38px] text-[13.3px] font-semibold leading-snug text-ink">{p.title}</h3>
        <div className="mt-2 flex flex-wrap items-baseline gap-2">
          <span className="font-display text-[19px] font-semibold text-emerald">{inr(p.price)}</span>
          {p.mrp > p.price && <span className="text-[12.5px] text-muted-foreground line-through">{inr(p.mrp)}</span>}
        </div>
        <button className="mt-3 rounded-lg border border-emerald py-2 text-[12.5px] font-semibold text-emerald transition-colors hover:bg-emerald hover:text-white">
          Add to Quote
        </button>
      </div>
    </motion.div>
  );
}
