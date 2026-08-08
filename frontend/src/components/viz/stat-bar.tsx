import { cn } from "@/lib/utils";

interface StatBarProps {
  value: number;
  max: number;
  color?: string;
  className?: string;
}

export function StatBar({ value, max, color, className }: StatBarProps) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className={cn("h-2 w-full rounded-full bg-muted", className)}>
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${pct}%`, backgroundColor: color || "currentColor" }}
      />
    </div>
  );
}
