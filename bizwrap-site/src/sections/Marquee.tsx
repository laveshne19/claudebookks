const brands = ["Philips","Wonderchef","Borosil","Prestige","Milton","Havells","boAt","Noise","JBL","Sony","Marshall","Mivi","Fire-Boltt","Portronics","Swiss Military"];
export function Marquee() {
  return (
    <div className="overflow-hidden border-b border-border bg-cream py-5">
      <p className="mb-3.5 text-center text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Brands we curate · authorised product feeds</p>
      <div className="flex w-max animate-marquee gap-12">
        {[...brands, ...brands].map((b, i) => (
          <span key={i} className="font-display text-lg font-bold text-emerald opacity-60">{b}</span>
        ))}
      </div>
    </div>
  );
}
