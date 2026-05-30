import { motion, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { SectionHead } from "@/components/SectionHead";
import { Reveal } from "@/components/Reveal";

const milestones = [
  ["2019", "Founded in Gurugram as a boutique corporate gifting studio."],
  ["2021", "Crossed 100 corporate clients; launched festive hamper programs."],
  ["2023", "Added gold/silver coin gifting & a multi-brand voucher desk."],
  ["2025", "Pan-India delivery network; 50,000+ gifts delivered."],
  ["2026", "Launched vendor portal, AI gift recommender & WhatsApp ordering."],
];

function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let cur = 0;
    const step = to / 60;
    const id = setInterval(() => { cur += step; if (cur >= to) { setN(to); clearInterval(id); } else setN(Math.floor(cur)); }, 16);
    return () => clearInterval(id);
  }, [inView, to]);
  return <span ref={ref}>{n.toLocaleString("en-IN")}{suffix}</span>;
}

export function Story() {
  return (
    <>
      <section className="bg-cream py-16">
        <div className="mx-auto grid max-w-[1280px] grid-cols-2 gap-5 px-6 md:grid-cols-4">
          {[
            { v: 500, s: "+", l: "Corporate Clients" },
            { v: 50000, s: "+", l: "Gifts Delivered" },
            { v: 100, s: "+", l: "Brands Available" },
            { v: 0, s: "", l: "Client Rating", custom: "4.9/5" },
          ].map((c) => (
            <Reveal key={c.l} className="rounded-2xl border border-border bg-card p-7 text-center transition hover:-translate-y-1.5 hover:shadow-lg">
              <div className="font-display text-[42px] font-semibold text-emerald">
                {c.custom ?? <Counter to={c.v} suffix={c.s} />}
              </div>
              <div className="mt-1 text-[13.5px] text-muted-foreground">{c.l}</div>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="story" className="bg-ivory py-20">
        <div className="mx-auto grid max-w-[1280px] grid-cols-1 items-center gap-12 px-6 md:grid-cols-[0.9fr_1.1fr]">
          <Reveal>
            <span className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">Our Story</span>
            <h2 className="mt-3 font-display text-[clamp(28px,3.4vw,40px)] font-medium text-emerald-deep text-balance">Seven years of gifting that builds relationships</h2>
            <p className="mt-4 font-light leading-relaxed text-muted-foreground">Since 2019, BizWrap India has grown from a small Gurugram gifting studio into a pan-India corporate gifting partner — serving HR, procurement and admin teams with curated gifts, transparent pricing and on-time nationwide delivery.</p>
            <p className="mt-4 font-light leading-relaxed text-muted-foreground">Today we manage festive campaigns, employee onboarding kits and executive gifting for enterprises across the country, backed by authorised brand feeds and a dedicated account-management team.</p>
          </Reveal>
          <div className="relative pl-8">
            <div className="absolute bottom-1.5 left-[7px] top-1.5 w-0.5" style={{ background: "linear-gradient(#C9A227,#0E5C43)" }} />
            {milestones.map(([yr, txt], i) => (
              <motion.div
                key={yr}
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.1 }}
                className="relative pb-7 pl-4"
              >
                <span className="absolute -left-8 top-1 h-4 w-4 rounded-full border-[3px] border-cream bg-gold shadow-[0_0_0_2px_#C9A227]" />
                <div className="font-display text-xl font-semibold text-emerald">{yr}</div>
                <p className="mt-1 text-sm text-muted-foreground">{txt}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
