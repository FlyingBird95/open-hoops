import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { gamesApi, teamsApi } from "../lib/api";
import type { Team, GameStatsResponse, GameEventData, GameFileData } from "../lib/api";
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

  const { data: ownTeams } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const { data: opponents } = useQuery({ queryKey: ["teams", "opponents"], queryFn: () => teamsApi.list(false) });

  const allTeams = [...(ownTeams || []), ...(opponents || [])];
  const teamNameByUid = Object.fromEntries(allTeams.map((t) => [t.uid, t.name]));
  const ownTeamUids = new Set((ownTeams || []).map((t) => t.uid));

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

  const { data: gameFiles } = useQuery({
    queryKey: ["game-files", uid],
    queryFn: () => gamesApi.files(uid!),
  });

  const [seekTarget, setSeekTarget] = useState<number | null>(null);

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

      {gameFiles && gameFiles.length > 0 && <VideoPlayer files={gameFiles} seekTarget={seekTarget} onSeeked={() => setSeekTarget(null)} />}
      {stats && <TeamStatsCards stats={stats} game={game} teamNameByUid={teamNameByUid} ownTeamUids={ownTeamUids} />}
      {stats && <PlayerStatsTable stats={stats} />}
      {events && <EventTimeline events={events} teamNameByUid={teamNameByUid} playerNameByUid={stats ? Object.fromEntries(stats.player_stats.filter(p => p.player_uid).map(p => [p.player_uid!, `#${p.jersey_number}`])) : {}} onEventClick={(ts) => setSeekTarget(ts)} />}
    </div>
  );
}

function TeamStatsCards({ stats, game, teamNameByUid, ownTeamUids }: { stats: GameStatsResponse; game: { own_team_uid: string; own_team_color: string; opponent_team_color: string }; teamNameByUid: Record<string, string>; ownTeamUids: Set<string> }) {
  const sorted = [...stats.team_stats].sort((a, b) => {
    const aOwn = ownTeamUids.has(a.team_uid) ? 0 : 1;
    const bOwn = ownTeamUids.has(b.team_uid) ? 0 : 1;
    return aOwn - bOwn;
  });
  return (
    <div className="grid grid-cols-2 gap-4">
      {sorted.map((ts) => {
        const isOwn = ts.team_uid === game.own_team_uid;
        const color = isOwn ? game.own_team_color : game.opponent_team_color;
        const teamName = teamNameByUid[ts.team_uid] || (isOwn ? "My Team" : "Opponent");
        return (
          <Card key={ts.uid}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className="w-4 h-4 rounded" style={{ backgroundColor: color }} />
                {teamName}
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

function VideoPlayer({ files, seekTarget, onSeeked }: { files: GameFileData[]; seekTarget: number | null; onSeeked: () => void }) {
  const sorted = [...files].sort((a, b) => a.position - b.position);
  const videoRefs = useRef<(HTMLVideoElement | null)[]>([]);
  const [durations, setDurations] = useState<number[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  const handleLoadedMetadata = useCallback((index: number, el: HTMLVideoElement) => {
    setDurations((prev) => {
      const next = [...prev];
      next[index] = el.duration;
      return next;
    });
  }, []);

  useEffect(() => {
    if (seekTarget === null) return;
    let cumulative = 0;
    for (let i = 0; i < sorted.length; i++) {
      const dur = durations[i] || 0;
      if (seekTarget < cumulative + dur || i === sorted.length - 1) {
        setActiveIndex(i);
        const video = videoRefs.current[i];
        if (video) {
          video.currentTime = seekTarget - cumulative;
          video.play();
        }
        break;
      }
      cumulative += dur;
    }
    onSeeked();
  }, [seekTarget]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Video{sorted.length > 1 ? ` (${sorted.length} files)` : ""}</CardTitle>
      </CardHeader>
      <CardContent>
        {sorted.map((f, i) => (
          <div key={f.uid} className={i === activeIndex ? "" : "hidden"}>
            <video
              ref={(el) => { videoRefs.current[i] = el; }}
              controls
              className="w-full rounded"
              src={`http://localhost:8000${f.url}`}
              onLoadedMetadata={(e) => handleLoadedMetadata(i, e.currentTarget)}
              onEnded={() => {
                if (i < sorted.length - 1) {
                  setActiveIndex(i + 1);
                  const next = videoRefs.current[i + 1];
                  if (next) { next.currentTime = 0; next.play(); }
                }
              }}
            />
          </div>
        ))}
        {sorted.length > 1 && (
          <div className="flex gap-1 mt-2">
            {sorted.map((f, i) => (
              <button
                key={f.uid}
                className={`text-xs px-2 py-1 rounded ${i === activeIndex ? "bg-primary text-primary-foreground" : "bg-muted"}`}
                onClick={() => setActiveIndex(i)}
              >
                {f.original_filename}
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EventTimeline({ events, teamNameByUid, playerNameByUid, onEventClick }: { events: GameEventData[]; teamNameByUid: Record<string, string>; playerNameByUid: Record<string, string>; onEventClick: (timestampSec: number) => void }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Events ({events.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-96 overflow-y-auto space-y-1">
          {events.map((e) => (
            <div
              key={e.uid}
              className="flex gap-4 text-sm py-1 border-b cursor-pointer hover:bg-muted/50 rounded px-1"
              onClick={() => onEventClick(e.timestamp_sec)}
            >
              <span className="text-muted-foreground w-16">{e.timestamp_sec.toFixed(1)}s</span>
              <Badge variant="outline">{e.type}</Badge>
              {e.team_uid && <span className="text-xs text-muted-foreground">{teamNameByUid[e.team_uid] || "Unknown"}</span>}
              {e.player_uid && <span className="text-xs font-medium">{playerNameByUid[e.player_uid] || "?"}</span>}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
