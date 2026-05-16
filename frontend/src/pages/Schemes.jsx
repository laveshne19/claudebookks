import { useEffect, useState } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { api } from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function Schemes() {
  const [list, setList] = useState([]);

  useEffect(() => {
    api.get("/schemes").then(({ data }) => setList(data));
  }, []);

  return (
    <AppLayout title="Schemes" subtitle={`${list.length} active programs`}>
      <div className="mb-4 flex justify-end">
        <Button size="sm" data-testid="new-scheme-btn"><Plus size={14} className="mr-1.5" /> New scheme</Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {list.map((s) => (
          <div key={s.id} className="bg-surface border border-border rounded-lg p-5 hover:shadow-sm transition" data-testid={`scheme-${s.id}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-widest bg-muted px-2 py-0.5 rounded">{s.brand}</span>
              <span className={`text-[10px] font-mono uppercase tracking-wider ${s.active ? "text-success" : "text-muted-foreground"}`}>
                {s.active ? "● LIVE" : "○ ENDED"}
              </span>
            </div>
            <h4 className="font-display font-bold text-base leading-tight">{s.name}</h4>
            <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{s.description}</p>
            <div className="mt-4 text-xs">
              <div className="flex justify-between mb-1">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-mono font-semibold">{s.progress}%</span>
              </div>
              <Progress value={s.progress} className="h-1.5" />
            </div>
            <div className="mt-4 pt-3 border-t border-border space-y-1.5 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">Reward</span><span className="font-semibold text-primary">{s.reward}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Ends</span><span className="font-mono">{s.end_date?.slice(0, 10)}</span></div>
            </div>
          </div>
        ))}
      </div>
    </AppLayout>
  );
}
