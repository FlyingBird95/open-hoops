import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { gamesApi } from "../lib/api";
import type { GameStatsResponse, GameEventData } from "../lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function GameDetail() {
  const { uid } = useParams<{ uid: string }>();

  const { data: game } = useQuery({
    queryKey: ["game", uid],
    queryFn: () => gamesApi.get(uid!),
    refetchInterval: (query) => query.state.data?.status === "done" ? false : 3000,
  });

  const { data: stats } = useQuery({
    queryKey: ["game-stats", uid],
    queryFn: () => gamesApi.stats(uid!),
    enabled: game?.status === "done",
  });

  const { data: events } = useQuery({
    queryKey: ["game-events", uid],
    queryFn: () => gamesApi.events(uid!),
    enabled: game?.status === "done",
  });

  if (!game) return <p>Loading...</p>;

  if (game.status !== "done") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{game.name}</h1>
        <Badge>{game.status}</Badge>
        {game.status === "processing" && <p className="text-muted-foreground">Analysis in progress...</p>}
        {game.status === "failed" && <p className="text-red-500">Analysis failed.</p>}
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">{game.name}</h1>
      <p className="text-muted-foreground">
        Duration: {(game.duration_seconds / 60).toFixed(1)} min | FPS: {game.fps.toFixed(0)}
      </p>

      {stats && <TeamStatsCards stats={stats} game={game} />}
      {stats && <PlayerStatsTable stats={stats} />}
      {events && <EventTimeline events={events} />}
    </div>
  );
}

function TeamStatsCards({ stats, game }: { stats: GameStatsResponse; game: { home_team_uid: string; home_team_color: string; away_team_color: string } }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {stats.team_stats.map((ts) => {
        const isHome = ts.team_uid === game.home_team_uid;
        const color = isHome ? game.home_team_color : game.away_team_color;
        return (
          <Card key={ts.uid}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: color }} />
                {isHome ? "Home" : "Away"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{ts.score}</p>
              <p className="text-sm text-muted-foreground">
                Possession: {(ts.possession_pct * 100).toFixed(0)}%
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function PlayerStatsTable({ stats }: { stats: GameStatsResponse }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Player Stats</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>#</TableHead>
              <TableHead>Shots</TableHead>
              <TableHead>Makes</TableHead>
              <TableHead>FG%</TableHead>
              <TableHead>Passes</TableHead>
              <TableHead>Distance (m)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stats.player_stats.map((p) => (
              <TableRow key={p.uid}>
                <TableCell>{p.jersey_number ?? "?"}</TableCell>
                <TableCell>{p.shot_attempts}</TableCell>
                <TableCell>{p.shot_makes}</TableCell>
                <TableCell>
                  {p.shot_attempts > 0
                    ? ((p.shot_makes / p.shot_attempts) * 100).toFixed(0) + "%"
                    : "—"}
                </TableCell>
                <TableCell>{p.passes_made}</TableCell>
                <TableCell>{p.distance_covered_m.toFixed(0)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function EventTimeline({ events }: { events: GameEventData[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Events ({events.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-96 overflow-y-auto space-y-1">
          {events.map((e) => (
            <div key={e.uid} className="flex gap-4 text-sm py-1 border-b">
              <span className="text-muted-foreground w-16">{e.timestamp_sec.toFixed(1)}s</span>
              <Badge variant="outline">{e.type}</Badge>
              {e.team_uid && <span className="text-xs text-muted-foreground">{e.team_uid.slice(0, 8)}</span>}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
