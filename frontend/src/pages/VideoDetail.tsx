import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { videosApi } from "../lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface PlayerStat {
  player_id: number | null;
  team_id: string;
  distance_covered_m: number;
  shot_attempts: number;
  shot_makes: number;
  passes_made: number;
  passes_received: number;
  possession_frames: number;
}

interface TeamStat {
  team_id: string;
  color: string;
  score: number;
  possession_pct: number;
  players: PlayerStat[];
}

interface GameEvent {
  type: string;
  frame: number;
  timestamp_sec: number;
  player_id: number | null;
  team_id: string | null;
}

interface GameStats {
  duration_seconds: number;
  fps: number;
  teams: TeamStat[];
  events: GameEvent[];
}

export default function VideoDetail() {
  const { uid } = useParams<{ uid: string }>();
  const { data: video } = useQuery({
    queryKey: ["video", uid],
    queryFn: () => videosApi.get(uid!),
    refetchInterval: (query) => query.state.data?.status === "done" ? false : 3000,
  });

  if (!video) return <p>Loading...</p>;

  if (video.status !== "done") {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{video.name}</h1>
        <Badge>{video.status}</Badge>
        {video.status === "processing" && <p className="text-muted-foreground">Analysis in progress...</p>}
        {video.status === "failed" && <p className="text-red-500">Analysis failed.</p>}
      </div>
    );
  }

  const stats = video.stats_json as unknown as GameStats;

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">{video.name}</h1>
      <p className="text-muted-foreground">
        Duration: {(stats.duration_seconds / 60).toFixed(1)} min | FPS: {stats.fps}
      </p>

      <div className="grid grid-cols-2 gap-4">
        {stats.teams.map((team) => (
          <Card key={team.team_id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: team.color }} />
                {team.team_id}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{team.score}</p>
              <p className="text-sm text-muted-foreground">Possession: {(team.possession_pct * 100).toFixed(0)}%</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Player Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Jersey</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Shots</TableHead>
                <TableHead>Makes</TableHead>
                <TableHead>FG%</TableHead>
                <TableHead>Passes</TableHead>
                <TableHead>Distance (m)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.teams.flatMap((t) =>
                t.players.map((p) => (
                  <TableRow key={`${t.team_id}-${p.player_id}`}>
                    <TableCell>{p.player_id ?? "?"}</TableCell>
                    <TableCell>{t.team_id}</TableCell>
                    <TableCell>{p.shot_attempts}</TableCell>
                    <TableCell>{p.shot_makes}</TableCell>
                    <TableCell>{p.shot_attempts > 0 ? ((p.shot_makes / p.shot_attempts) * 100).toFixed(0) + "%" : "—"}</TableCell>
                    <TableCell>{p.passes_made}</TableCell>
                    <TableCell>{p.distance_covered_m.toFixed(0)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Events</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-y-auto space-y-1">
            {stats.events.map((e, i) => (
              <div key={i} className="flex gap-4 text-sm py-1 border-b">
                <span className="text-muted-foreground w-16">{e.timestamp_sec.toFixed(1)}s</span>
                <Badge variant="outline">{e.type}</Badge>
                <span>{e.team_id}</span>
                <span>#{e.player_id ?? "?"}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
