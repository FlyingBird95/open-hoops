import { Card, CardContent } from "@/components/ui/card";

interface ScoreCardProps {
  homeTeam: string;
  awayTeam: string;
  homeScore: number;
  awayScore: number;
  homeColor: string;
  awayColor: string;
  homePossession: number;
  awayPossession: number;
}

export function ScoreCard({ homeTeam, awayTeam, homeScore, awayScore, homeColor, awayColor, homePossession, awayPossession }: ScoreCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-center gap-6">
          <div className="flex flex-col items-center gap-1">
            <span className="w-4 h-4 rounded-full" style={{ backgroundColor: homeColor }} />
            <span className="text-sm font-medium">{homeTeam}</span>
            <span className="text-4xl font-bold">{homeScore}</span>
          </div>
          <span className="text-2xl text-muted-foreground">—</span>
          <div className="flex flex-col items-center gap-1">
            <span className="w-4 h-4 rounded-full" style={{ backgroundColor: awayColor }} />
            <span className="text-sm font-medium">{awayTeam}</span>
            <span className="text-4xl font-bold">{awayScore}</span>
          </div>
        </div>

        {/* Possession bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>{Math.round(homePossession * 100)}%</span>
            <span className="text-muted-foreground">Possession</span>
            <span>{Math.round(awayPossession * 100)}%</span>
          </div>
          <div className="h-2 w-full rounded-full overflow-hidden flex">
            <div style={{ width: `${homePossession * 100}%`, backgroundColor: homeColor }} className="h-full" />
            <div style={{ width: `${awayPossession * 100}%`, backgroundColor: awayColor }} className="h-full" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
