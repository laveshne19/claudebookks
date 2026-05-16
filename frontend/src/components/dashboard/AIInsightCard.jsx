import { Sparkles } from "lucide-react";

export default function AIInsightCard({ title, children, badge, testid }) {
  return (
    <div className="relative overflow-hidden bg-ai-surface border border-ai-border rounded-lg p-5 ai-noise" data-testid={testid}>
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles size={14} className="text-ai-text" strokeWidth={2} />
            <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-ai-text">{title}</span>
          </div>
          {badge && (
            <span className="font-mono text-[10px] uppercase tracking-wider text-ai-text border border-ai-border px-1.5 py-0.5 rounded">
              {badge}
            </span>
          )}
        </div>
        <div className="text-sm text-foreground space-y-2">{children}</div>
      </div>
    </div>
  );
}
