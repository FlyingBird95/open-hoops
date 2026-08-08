interface DonutChartProps {
  makes: number;
  misses: number;
  color: string;
  size?: number;
}

export function DonutChart({ makes, misses, color, size = 48 }: DonutChartProps) {
  const total = makes + misses;
  if (total === 0) return <div style={{ width: size, height: size }} />;

  const pct = makes / total;
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const filled = circumference * pct;

  return (
    <svg width={size} height={size} viewBox="0 0 48 48">
      <circle cx="24" cy="24" r={radius} fill="none" stroke="currentColor" strokeWidth="6" className="text-muted" />
      <circle
        cx="24" cy="24" r={radius} fill="none"
        stroke={color} strokeWidth="6"
        strokeDasharray={`${filled} ${circumference - filled}`}
        strokeDashoffset={circumference * 0.25}
        strokeLinecap="round"
      />
      <text x="24" y="24" textAnchor="middle" dominantBaseline="central" className="text-[10px] font-bold fill-foreground">
        {Math.round(pct * 100)}%
      </text>
    </svg>
  );
}
