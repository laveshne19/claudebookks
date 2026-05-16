import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

export default function KPICard({ title, value, delta, deltaLabel, icon: Icon, accent, testid }) {
  const trendIcon = delta > 0 ? ArrowUpRight : delta < 0 ? ArrowDownRight : Minus;
  const TrendIcon = trendIcon;
  const trendColor = delta > 0 ? "text-success" : delta < 0 ? "text-destructive" : "text-muted-foreground";

  return (
    <div
      className="bg-surface border border-border rounded-lg p-5 flex flex-col justify-between h-full transition-all duration-200 hover:shadow-sm hover:-translate-y-[1px]"
      data-testid={testid}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{title}</h4>
        {Icon && (
          <div className={`h-7 w-7 rounded flex items-center justify-center ${accent || "bg-muted text-muted-foreground"}`}>
            <Icon size={14} strokeWidth={1.75} />
          </div>
        )}
      </div>
      <div className="mt-4">
        <div className="text-3xl font-display font-black tracking-tight tabular">{value}</div>
        {(delta !== undefined && delta !== null) && (
          <div className={`mt-1.5 inline-flex items-center gap-1 text-xs font-medium ${trendColor}`}>
            <TrendIcon size={12} />
            <span className="tabular">{delta > 0 ? "+" : ""}{delta}%</span>
            {deltaLabel && <span className="text-muted-foreground">· {deltaLabel}</span>}
          </div>
        )}
      </div>
    </div>
  );
}
