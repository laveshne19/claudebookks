import { useState } from "react";
import { motion } from "framer-motion";
import { useMetalRates } from "@/hooks/useMetalRates";
import { inr } from "@/data/catalog";
import { SectionHead } from "@/components/SectionHead";
import { Reveal } from "@/components/Reveal";

export function Metal() {
  const { rates, live, updated } = useMetalRates();
  return (
    <section id="metal" className="bg-emerald-deep py-20 text-white">
      <div className="mx-auto max-w-[1280px] px-6">
        <div className="[&_h2]:text-white [&_p]:text-white/72">
          <SectionHead eyebrow="Precious Metals" title="Live gold & silver coin pricing" sub="Rates auto-update from live market feeds. Coin pricing is calculated in real time across weights, gift-cased and corporate-billed." />
        </div>
        <Reveal>
          <div className="grid gap-5 md:grid-cols-2">
            <Coin metal="Gold" emoji="🪙" purity="24K" rate={rates.gold} weights={[1, 2, 5, 10, 20]} def={2} live={live} updated={updated} />
            <Coin metal="Silver" emoji="🥈" purity="999" rate={rates.silver} weights={[5, 10, 20, 50, 100]} def={10} live={live} updated={updated} />
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Coin({ metal, emoji, purity, rate, weights, def, live, updated }: { metal: string; emoji: string; purity: string; rate: number; weights: number[]; def: number; live: boolean; updated: string }) {
  const [g, setG] = useState(def);
  return (
    <div className="rounded-[20px] border border-gold/30 p-7" style={{ background: "linear-gradient(160deg,#0f5a42,#0a3f2e)" }}>
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-display text-xl">{emoji} {metal} Coin</h3>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/12 px-2.5 py-1 text-[11.5px] text-emerald-200">
          <span className={`h-2 w-2 rounded-full ${live ? "animate-pulseRing bg-emerald-400" : "bg-white/40"}`} />
          {live ? `LIVE · ${updated}` : "LIVE"}
        </span>
      </div>
      <div className="font-display text-[34px] text-gold-soft">
        {inr(rate)}<span className="font-sans text-sm text-white/55"> / g ({purity})</span>
      </div>
      <div className="text-[12.5px] text-white/50">Live market rate · final price incl. GST &amp; making</div>
      <div className="mt-4 flex flex-wrap gap-2">
        {weights.map((w) => (
          <button key={w} onClick={() => setG(w)} className={`rounded-lg border px-3.5 py-2 text-[13px] transition ${g === w ? "border-gold bg-gold text-emerald-deep" : "border-white/16 bg-white/[0.06] text-white hover:border-gold"}`}>
            {w}g
          </button>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-white/12 pt-4">
        <span className="text-[13px] text-white/60">Approx. coin price</span>
        <motion.span key={g * rate} initial={{ opacity: 0.4, y: 4 }} animate={{ opacity: 1, y: 0 }} className="font-display text-2xl">
          {inr(g * rate)}
        </motion.span>
      </div>
    </div>
  );
}
