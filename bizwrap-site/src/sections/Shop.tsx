import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, SlidersHorizontal } from "lucide-react";
import { PRODUCTS, BANDS, CATEGORIES, BRANDS, catIcon } from "@/data/catalog";
import { ProductCard } from "@/components/ProductCard";
import { SectionHead } from "@/components/SectionHead";
import { Reveal } from "@/components/Reveal";

export function Shop() {
  const [band, setBand] = useState("all");
  const [cat, setCat] = useState("all");
  const [brand, setBrand] = useState("all");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("disc");
  const [shown, setShown] = useState(20);

  const list = useMemo(() => {
    let l = PRODUCTS.filter(
      (p) =>
        (band === "all" || p.band === band) &&
        (cat === "all" || p.cat === cat) &&
        (brand === "all" || p.brand === brand) &&
        (!q || (p.title + " " + p.brand).toLowerCase().includes(q.toLowerCase()))
    );
    if (sort === "disc") l = [...l].sort((a, b) => b.mrp - b.price - (a.mrp - a.price));
    if (sort === "plow") l = [...l].sort((a, b) => a.price - b.price);
    if (sort === "phigh") l = [...l].sort((a, b) => b.price - a.price);
    return l;
  }, [band, cat, brand, q, sort]);

  const reset = (fn: (v: string) => void) => (v: string) => { fn(v); setShown(20); };

  return (
    <section id="shop" className="bg-ivory py-20">
      <div className="mx-auto max-w-[1280px] px-6">
        <SectionHead
          eyebrow="Shop by Budget"
          title="Find the perfect gift in your price range"
          sub={`Filter by budget, category or brand across ${PRODUCTS.length}+ curated products. Every price shows the MRP and your corporate rate.`}
        />

        {/* budget chips */}
        <Reveal>
          <div className="no-scrollbar -mx-1 mb-5 flex gap-2.5 overflow-x-auto px-1 pb-1">
            {BANDS.map((b) => (
              <button
                key={b.key}
                onClick={() => reset(setBand)(b.key)}
                className={`shrink-0 rounded-full border px-5 py-2.5 text-sm font-semibold transition ${
                  band === b.key ? "border-emerald bg-emerald text-white" : "border-border bg-card text-ink hover:border-gold"
                }`}
              >
                {b.label}
              </button>
            ))}
          </div>
        </Reveal>

        {/* category + brand + search + sort bar */}
        <Reveal className="mb-7">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap gap-2">
              <Pill active={cat === "all"} onClick={() => reset(setCat)("all")}>All categories</Pill>
              {CATEGORIES.map((c) => (
                <Pill key={c} active={cat === c} onClick={() => reset(setCat)(c)}>
                  <span className="mr-1">{catIcon[c] ?? "🎁"}</span>{c}
                </Pill>
              ))}
            </div>
            <div className="ml-auto flex items-center gap-2.5">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={q}
                  onChange={(e) => { setQ(e.target.value); setShown(20); }}
                  placeholder="Search products, brands…"
                  className="w-52 rounded-full border border-border bg-card py-2.5 pl-9 pr-3 text-sm outline-none focus:border-gold"
                />
              </div>
              <select value={sort} onChange={(e) => setSort(e.target.value)} className="rounded-full border border-border bg-card px-3 py-2.5 text-sm outline-none focus:border-gold">
                <option value="disc">Biggest discount</option>
                <option value="plow">Price: low → high</option>
                <option value="phigh">Price: high → low</option>
              </select>
            </div>
          </div>
          {/* brand row */}
          <div className="no-scrollbar mt-3 flex items-center gap-2 overflow-x-auto pb-1 text-sm">
            <SlidersHorizontal className="h-4 w-4 shrink-0 text-muted-foreground" />
            <button onClick={() => reset(setBrand)("all")} className={`shrink-0 rounded-full px-3 py-1.5 ${brand === "all" ? "bg-gold/20 font-semibold text-emerald-deep" : "text-muted-foreground hover:text-emerald"}`}>All brands</button>
            {BRANDS.slice(0, 10).map((b) => (
              <button key={b} onClick={() => reset(setBrand)(b)} className={`shrink-0 rounded-full px-3 py-1.5 ${brand === b ? "bg-gold/20 font-semibold text-emerald-deep" : "text-muted-foreground hover:text-emerald"}`}>{b}</button>
            ))}
          </div>
        </Reveal>

        <div className="mb-5 text-sm text-muted-foreground">{list.length} products</div>

        <motion.div layout className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          <AnimatePresence mode="popLayout">
            {list.slice(0, shown).map((p, i) => <ProductCard key={p.id} p={p} index={i} />)}
          </AnimatePresence>
        </motion.div>

        {list.length === 0 && <div className="py-16 text-center text-muted-foreground">No products match these filters. Try widening the budget or clearing the search.</div>}

        {list.length > shown && (
          <div className="mt-9 text-center">
            <button onClick={() => setShown((s) => s + 20)} className="rounded-full bg-emerald px-9 py-3.5 text-sm font-semibold text-white transition hover:bg-emerald-light">
              Load more ({list.length - shown} more)
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function Pill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick} className={`rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition ${active ? "border-emerald bg-emerald text-white" : "border-border bg-card text-ink hover:border-gold"}`}>
      {children}
    </button>
  );
}
