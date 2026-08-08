import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { gamesApi, teamsApi } from "@/lib/api";
import type { Game } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PlayCircle, Loader2 } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function Dashboard() {
  const { data: games, isLoading } = useQuery({
    queryKey: ["games"],
    queryFn: gamesApi.list,
    refetchInterval: 5000,
  });
  const { data: opponents } = useQuery({
    queryKey: ["teams", "opponents"],
    queryFn: () => teamsApi.list(false),
  });

  if (isLoading) return <DashboardSkeleton />;

  if (!games || games.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <PlayCircle className="h-16 w-16 text-muted-foreground/40 mb-4" />
        <h2 className="text-xl font-semibold mb-2">No games yet</h2>
        <p className="text-muted-foreground mb-4">Upload game footage to start analyzing</p>
        <Link to="/games" className={cn(buttonVariants())}>
          Upload Game
        </Link>
      </div>
    );
  }

  const opponentNameByUid = Object.fromEntries((opponents || []).map(t => [t.uid, t.name]));
  const done = games.filter((g: Game) => g.status === "done");
  const active = games.filter((g: Game) => g.status === "processing" || g.status === "pending");
  const totalHours = done.reduce((sum: number, g: Game) => sum + g.duration_seconds, 0) / 3600;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Games Processed</p>
            <p className="text-3xl font-bold">{done.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Processing</p>
            <p className="text-3xl font-bold flex items-center gap-2">
              {active.length}
              {active.length > 0 && <Loader2 className="h-5 w-5 animate-spin text-blue-500" />}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Footage Analyzed</p>
            <p className="text-3xl font-bold">{totalHours.toFixed(1)}h</p>
          </CardContent>
        </Card>
      </div>

      {active.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Active Jobs</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {active.map((g: Game) => (
              <Link key={g.uid} to={`/games/${g.uid}`}>
                <Card className="hover:ring-2 hover:ring-primary/20 transition-shadow">
                  <CardContent className="pt-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium">{g.name}</p>
                      <p className="text-sm text-muted-foreground">
                        vs {opponentNameByUid[g.opponent_team_uid] || "Unknown"}
                      </p>
                    </div>
                    <Badge className="bg-blue-500 animate-pulse">{g.status}</Badge>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-lg font-semibold mb-3">Recent Completions</h2>
        <div className="space-y-2">
          {done.slice(0, 5).map((g: Game) => (
            <Link key={g.uid} to={`/games/${g.uid}`}>
              <Card className="hover:ring-2 hover:ring-primary/20 transition-shadow">
                <CardContent className="pt-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{g.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {g.date} · vs {opponentNameByUid[g.opponent_team_uid] || "Unknown"}
                    </p>
                  </div>
                  <Badge className="bg-green-500">done</Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-40" />
      <div className="grid grid-cols-3 gap-4">
        {[1, 2, 3].map(i => (
          <Card key={i}><CardContent className="pt-6"><Skeleton className="h-6 w-20 mb-2" /><Skeleton className="h-10 w-16" /></CardContent></Card>
        ))}
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map(i => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
      </div>
    </div>
  );
}
