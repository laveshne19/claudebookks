import { Reveal } from "./Reveal";

export function SectionHead({ eyebrow, title, sub, center }: { eyebrow: string; title: string; sub?: string; center?: boolean }) {
  return (
    <Reveal className={`mb-12 max-w-2xl ${center ? "mx-auto text-center" : ""}`}>
      <span className="text-xs font-semibold uppercase tracking-[0.22em] text-gold">{eyebrow}</span>
      <h2 className="mt-3 font-display text-[clamp(28px,3.4vw,42px)] font-medium text-emerald-deep text-balance">{title}</h2>
      {sub && <p className="mt-4 text-[16px] font-light text-muted-foreground">{sub}</p>}
    </Reveal>
  );
}
