import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { gamesApi, eventsApi, teamsApi, playersApi } from "../lib/api";
import type { Game, GameStatsResponse, GameEventData, GameFileData } from "../lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Archive, ArchiveRestore, Eye, Pencil, PencilOff, Trash2 } from "lucide-react";
import { ScoreCard } from "@/components/viz/score-card";
import { StatBar } from "@/components/viz/stat-bar";
import { DonutChart } from "@/components/viz/donut-chart";

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

  const { data: stats } = useQuery({
    queryKey: ["game-stats", uid],
    queryFn: () => gamesApi.stats(uid!),
    enabled: game?.status === "done",
  });

  const { data: events } = useQuery({
    queryKey: ["game-events", uid],
    queryFn: () => eventsApi.list(uid!),
    enabled: game?.status === "done",
  });

  const { data: gameFiles } = useQuery({
    queryKey: ["game-files", uid],
    queryFn: () => gamesApi.files(uid!),
  });

  const [seekTarget, setSeekTarget] = useState<number | null>(null);
  const currentTimeRef = useRef<() => number>(() => 0);
  const isPlayingRef = useRef(false);
  const [editMode, setEditMode] = useState(false);

  const queryClient = useQueryClient();

  const archiveMutation = useMutation({
    mutationFn: (archived: boolean) => gamesApi.update(uid!, { is_archived: archived }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["game", uid] });
      queryClient.invalidateQueries({ queryKey: ["games"] });
      toast(updated.is_archived ? "Game archived" : "Game restored");
    },
  });

  if (!game) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-48" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-32 rounded-xl" />
        </div>
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

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
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h1 className="text-2xl font-bold">{game.name}</h1>
        {game.status === "done" && (
          <>
            <Button
              variant={editMode ? "default" : "outline"}
              size="sm"
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? (
                <><PencilOff className="h-4 w-4 mr-1" /> Exit Edit</>
              ) : (
                <><Pencil className="h-4 w-4 mr-1" /> Edit Events</>
              )}
            </Button>
            <Button
              variant={game.is_archived ? "outline" : "ghost"}
              size="sm"
              onClick={() => archiveMutation.mutate(!game.is_archived)}
              disabled={archiveMutation.isPending}
            >
              {game.is_archived ? (
                <><ArchiveRestore className="h-4 w-4 mr-1" /> Unarchive</>
              ) : (
                <><Archive className="h-4 w-4 mr-1" /> Archive</>
              )}
            </Button>
          </>
        )}
      </div>
      <p className="text-muted-foreground">
        Duration: {(game.duration_seconds / 60).toFixed(1)} min | FPS: {game.fps.toFixed(0)}
      </p>

      {gameFiles && gameFiles.length > 0 && (
        <div className={editMode ? "flex gap-4" : ""}>
          <div className={editMode ? "w-2/3" : "w-full"}>
            <VideoPlayer files={gameFiles} seekTarget={seekTarget} onSeeked={() => setSeekTarget(null)} onTimeRef={currentTimeRef} isPlayingRef={isPlayingRef} />
          </div>
          {editMode && events && (
            <div className="w-1/3">
              <EventEditorPanel events={events} game={game} teamNameByUid={teamNameByUid} playerNameByUid={stats ? Object.fromEntries(stats.player_stats.filter(p => p.player_uid).map(p => [p.player_uid!, `#${p.jersey_number}`])) : {}} getCurrentTime={() => currentTimeRef.current()} isPlayingRef={isPlayingRef} onEventClick={(ts) => setSeekTarget(ts)} />
            </div>
          )}
        </div>
      )}
      {stats && (() => {
        const ownStats = stats.team_stats.find(ts => ts.team_uid === game.own_team_uid);
        const oppStats = stats.team_stats.find(ts => ts.team_uid !== game.own_team_uid);
        const ownName = teamNameByUid[game.own_team_uid] || "My Team";
        const oppName = teamNameByUid[stats.team_stats.find(ts => ts.team_uid !== game.own_team_uid)?.team_uid || ""] || "Opponent";
        return (
          <ScoreCard
            homeTeam={ownName}
            awayTeam={oppName}
            homeScore={ownStats?.score ?? 0}
            awayScore={oppStats?.score ?? 0}
            homeColor={game.own_team_color}
            awayColor={game.opponent_team_color}
            homePossession={ownStats?.possession_pct ?? 0}
            awayPossession={oppStats?.possession_pct ?? 0}
          />
        );
      })()}
      {stats && <PlayerStatsTable stats={stats} game={game} teamNameByUid={teamNameByUid} />}
      {!editMode && events && <EventTimeline events={events} game={game} teamNameByUid={teamNameByUid} playerNameByUid={stats ? Object.fromEntries(stats.player_stats.filter(p => p.player_uid).map(p => [p.player_uid!, `#${p.jersey_number}`])) : {}} onEventClick={(ts) => setSeekTarget(ts)} />}
    </div>
  );
}

function PlayerStatsTable({ stats, game, teamNameByUid }: { stats: GameStatsResponse; game: Game; teamNameByUid: Record<string, string> }) {
  const teams = [...new Set(stats.player_stats.map(p => p.team_uid))];
  const maxDistance = Math.max(...stats.player_stats.map(p => p.distance_covered_m), 1);

  return (
    <div className="space-y-4">
      {teams.map(teamUid => {
        const players = stats.player_stats.filter(p => p.team_uid === teamUid);
        const isOwn = teamUid === game.own_team_uid;
        const color = isOwn ? game.own_team_color : game.opponent_team_color;
        const teamName = teamNameByUid[teamUid] || (isOwn ? "My Team" : "Opponent");
        const totalShots = players.reduce((s, p) => s + p.shot_attempts, 0);
        const totalMakes = players.reduce((s, p) => s + p.shot_makes, 0);

        return (
          <Card key={teamUid}>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <span className="w-3 h-3 rounded" style={{ backgroundColor: color }} />
                {teamName}
                <DonutChart makes={totalMakes} misses={totalShots - totalMakes} color={color} size={36} />
              </CardTitle>
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
                    <TableHead>Distance</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {players.map((p, i) => {
                    const fgPct = p.shot_attempts > 0 ? p.shot_makes / p.shot_attempts : 0;
                    return (
                      <TableRow key={`${p.team_uid}-${p.jersey_number ?? i}`}>
                        <TableCell className="font-medium">{p.jersey_number ?? "?"}</TableCell>
                        <TableCell>{p.shot_attempts}</TableCell>
                        <TableCell>{p.shot_makes}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <StatBar value={fgPct} max={1} color={color} className="w-16" />
                            <span className="text-xs">{p.shot_attempts > 0 ? `${Math.round(fgPct * 100)}%` : "—"}</span>
                          </div>
                        </TableCell>
                        <TableCell>{p.passes_made}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <StatBar value={p.distance_covered_m} max={maxDistance} color={color} className="w-12" />
                            <span className="text-xs">{p.distance_covered_m.toFixed(0)}m</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

function VideoPlayer({ files, seekTarget, onSeeked, onTimeRef, isPlayingRef }: { files: GameFileData[]; seekTarget: number | null; onSeeked: () => void; onTimeRef: React.MutableRefObject<() => number>; isPlayingRef: React.MutableRefObject<boolean> }) {
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

  onTimeRef.current = () => {
    const video = videoRefs.current[activeIndex];
    if (!video) return 0;
    let cumulative = 0;
    for (let i = 0; i < activeIndex; i++) cumulative += durations[i] || 0;
    return cumulative + video.currentTime;
  };

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
              onPlay={() => { isPlayingRef.current = true; }}
              onPause={() => { isPlayingRef.current = false; }}
              onEnded={() => {
                isPlayingRef.current = false;
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

const EDITOR_EVENT_TYPES = [
  { type: "make", label: "Made Shot" },
  { type: "miss", label: "Missed Shot" },
  { type: "pass", label: "Pass" },
  { type: "rebound", label: "Rebound" },
  { type: "turnover", label: "Turnover" },
  { type: "steal", label: "Steal" },
  { type: "block", label: "Block" },
  { type: "foul", label: "Foul" },
  { type: "assist", label: "Assist" },
  { type: "substitution", label: "Sub" },
  { type: "possession_change", label: "Poss Change" },
] as const;

function EventEditorPanel({ events, game, teamNameByUid, playerNameByUid, getCurrentTime, isPlayingRef, onEventClick }: { events: GameEventData[]; game: Game; teamNameByUid: Record<string, string>; playerNameByUid: Record<string, string>; getCurrentTime: () => number; isPlayingRef: React.MutableRefObject<boolean>; onEventClick: (timestampSec: number) => void }) {
  const [selectedTeamUid, setSelectedTeamUid] = useState<string>(game.own_team_uid);
  const [selectedPlayerUid, setSelectedPlayerUid] = useState<string>("");
  const [selectedPlayer2Uid, setSelectedPlayer2Uid] = useState<string>("");
  const [selectedEventUid, setSelectedEventUid] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: ownPlayers } = useQuery({
    queryKey: ["players", game.own_team_uid],
    queryFn: () => playersApi.list(game.own_team_uid),
  });
  const { data: oppPlayers } = useQuery({
    queryKey: ["players", game.opponent_team_uid],
    queryFn: () => playersApi.list(game.opponent_team_uid),
  });

  const activePlayers = selectedTeamUid === game.own_team_uid ? (ownPlayers || []) : (oppPlayers || []);

  const createMutation = useMutation({
    mutationFn: (attrs: { type: string; timestamp_sec: number; frame: number; team_uid?: string; player_uid?: string; player2_uid?: string }) =>
      eventsApi.create(game.uid, attrs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["game-events", game.uid] });
      toast("Event added");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ eventId, attrs }: { eventId: string; attrs: { type?: string; team_uid?: string | null; player_uid?: string | null; player2_uid?: string | null } }) =>
      eventsApi.update(eventId, attrs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["game-events", game.uid] });
      toast("Event updated");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (eventId: string) => eventsApi.delete(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["game-events", game.uid] });
      setSelectedEventUid(null);
      toast("Event removed");
    },
  });

  const hasSecondPlayer = (type: string) => type === "pass" || type === "assist";

  const handleQuickAdd = (type: string) => {
    const t = getCurrentTime();
    const frame = Math.round(t * (game.fps || 30));
    createMutation.mutate({
      type,
      timestamp_sec: t,
      frame,
      team_uid: selectedTeamUid,
      ...(selectedPlayerUid ? { player_uid: selectedPlayerUid } : {}),
      ...(hasSecondPlayer(type) && selectedPlayer2Uid ? { player2_uid: selectedPlayer2Uid } : {}),
    });
  };

  const handleUpdateType = (type: string) => {
    if (!selectedEventUid) return;
    updateMutation.mutate({ eventId: selectedEventUid, attrs: { type } });
  };

  const handleUpdateTeam = (teamUid: string) => {
    if (!selectedEventUid) return;
    setSelectedTeamUid(teamUid);
    setSelectedPlayerUid("");
    updateMutation.mutate({ eventId: selectedEventUid, attrs: { team_uid: teamUid, player_uid: null } });
  };

  const handleUpdatePlayer = (playerUid: string) => {
    if (!selectedEventUid) return;
    setSelectedPlayerUid(playerUid);
    updateMutation.mutate({ eventId: selectedEventUid, attrs: { player_uid: playerUid || null } });
  };

  const handleUpdatePlayer2 = (playerUid: string) => {
    if (!selectedEventUid) return;
    setSelectedPlayer2Uid(playerUid);
    updateMutation.mutate({ eventId: selectedEventUid, attrs: { player2_uid: playerUid || null } });
  };

  const handleSelectEvent = (e: GameEventData) => {
    if (selectedEventUid === e.uid) {
      setSelectedEventUid(null);
    } else {
      setSelectedEventUid(e.uid);
      setSelectedTeamUid(e.team_uid || game.own_team_uid);
      setSelectedPlayerUid(e.player_uid || "");
      setSelectedPlayer2Uid(e.player2_uid || "");
      onEventClick(e.timestamp_sec);
    }
  };

  const ownName = teamNameByUid[game.own_team_uid] || "Own";
  const oppName = teamNameByUid[game.opponent_team_uid] || "Opp";
  const sortedEvents = [...events].sort((a, b) => b.timestamp_sec - a.timestamp_sec);
  const selectedEvent = events.find(e => e.uid === selectedEventUid);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">{selectedEvent ? "Edit Event" : "Event Editor"}</CardTitle>
        <div className="flex gap-1 mt-2">
          <Button
            size="sm"
            variant={selectedTeamUid === game.own_team_uid ? "default" : "outline"}
            onClick={() => { if (selectedEvent) { handleUpdateTeam(game.own_team_uid); } else { setSelectedTeamUid(game.own_team_uid); setSelectedPlayerUid(""); } }}
            className="flex-1 text-xs"
          >
            {ownName}
          </Button>
          <Button
            size="sm"
            variant={selectedTeamUid === game.opponent_team_uid ? "default" : "outline"}
            onClick={() => { if (selectedEvent) { handleUpdateTeam(game.opponent_team_uid); } else { setSelectedTeamUid(game.opponent_team_uid); setSelectedPlayerUid(""); } }}
            className="flex-1 text-xs"
          >
            {oppName}
          </Button>
        </div>
        {activePlayers.length > 0 && (
          <>
            <span className="text-[10px] text-muted-foreground mt-2">Player</span>
            <div className="flex flex-wrap gap-1">
              <Button
                size="sm"
                variant={selectedPlayerUid === "" ? "default" : "outline"}
                onClick={() => { if (selectedEvent) { handleUpdatePlayer(""); } else { setSelectedPlayerUid(""); } }}
                className="text-xs px-2 h-6"
              >
                Unknown
              </Button>
              {activePlayers.map(p => (
                <Button
                  key={p.uid}
                  size="sm"
                  variant={selectedPlayerUid === p.uid ? "default" : "outline"}
                  onClick={() => { if (selectedEvent) { handleUpdatePlayer(p.uid); } else { setSelectedPlayerUid(p.uid); } }}
                  className="text-xs px-2 h-6"
                >
                  #{p.jersey_number}
                </Button>
              ))}
            </div>
          </>
        )}
      </CardHeader>
      <CardContent className="flex flex-col flex-1 min-h-0 gap-3">
        <div className="grid grid-cols-2 gap-1">
          {EDITOR_EVENT_TYPES.map(({ type, label }) => (
            <Button
              key={type}
              size="sm"
              variant={selectedEvent?.type === type ? "default" : "secondary"}
              className="text-xs"
              disabled={createMutation.isPending || updateMutation.isPending}
              onClick={() => {
                if (!isPlayingRef.current && selectedEvent) {
                  handleUpdateType(type);
                } else {
                  handleQuickAdd(type);
                }
              }}
            >
              {!isPlayingRef.current && selectedEvent ? "" : "+ "}{label}
            </Button>
          ))}
        </div>
        {selectedEvent && hasSecondPlayer(selectedEvent.type) && activePlayers.length > 0 && (
          <>
            <span className="text-[10px] text-muted-foreground">Receiver</span>
            <div className="flex flex-wrap gap-1">
              <Button
                size="sm"
                variant={selectedPlayer2Uid === "" ? "default" : "outline"}
                onClick={() => handleUpdatePlayer2("")}
                className="text-xs px-2 h-6"
              >
                None
              </Button>
              {activePlayers.map(p => (
                <Button
                  key={p.uid}
                  size="sm"
                  variant={selectedPlayer2Uid === p.uid ? "default" : "outline"}
                  onClick={() => handleUpdatePlayer2(p.uid)}
                  className="text-xs px-2 h-6"
                >
                  #{p.jersey_number}
                </Button>
              ))}
            </div>
          </>
        )}
        {selectedEvent && (
          <Button
            size="sm"
            variant="ghost"
            className="text-xs"
            onClick={() => setSelectedEventUid(null)}
          >
            Deselect
          </Button>
        )}
        <div className="flex-1 overflow-y-auto min-h-0 space-y-0.5">
          {sortedEvents.map((e) => (
            <div
              key={e.uid}
              className={`flex items-center gap-2 text-xs py-1 px-1 rounded cursor-pointer border-l-2 ${e.uid === selectedEventUid ? "bg-accent" : "hover:bg-muted/50"}`}
              style={{ borderLeftColor: e.team_uid === game.own_team_uid ? game.own_team_color : game.opponent_team_color }}
              onClick={() => handleSelectEvent(e)}
            >
              <span className="text-muted-foreground w-12 shrink-0">{e.timestamp_sec.toFixed(1)}s</span>
              <Badge variant="outline" className="text-[10px] px-1 py-0">{e.type}</Badge>
              {e.player_uid && <span className="text-muted-foreground">{playerNameByUid[e.player_uid] || "?"}</span>}
              {e.source === "manual" && <span className="text-[9px] text-muted-foreground">M</span>}
              <button
                className="ml-auto p-0.5 rounded hover:bg-destructive/10 shrink-0"
                onClick={(ev) => { ev.stopPropagation(); deleteMutation.mutate(e.uid); }}
              >
                <Trash2 className="h-3 w-3 text-destructive" />
              </button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function EventTimeline({ events, game, teamNameByUid, playerNameByUid, onEventClick }: { events: GameEventData[]; game: Game; teamNameByUid: Record<string, string>; playerNameByUid: Record<string, string>; onEventClick: (timestampSec: number) => void }) {
  const [frameEvent, setFrameEvent] = useState<GameEventData | null>(null);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Events ({events.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="max-h-96 overflow-y-auto space-y-1">
            {events.map((e) => (
              <div
                key={e.uid}
                className="group flex items-center gap-4 text-sm py-1 border-b cursor-pointer hover:bg-muted/50 rounded px-1 border-l-2"
                style={{ borderLeftColor: e.team_uid === game.own_team_uid ? game.own_team_color : game.opponent_team_color }}
                onClick={() => onEventClick(e.timestamp_sec)}
              >
                <span className="text-muted-foreground w-16">{e.timestamp_sec.toFixed(1)}s</span>
                <Badge variant="outline">{e.type}</Badge>
                {e.team_uid && <span className="text-xs text-muted-foreground">{teamNameByUid[e.team_uid] || "Unknown"}</span>}
                {e.player_uid && <span className="text-xs font-medium">{playerNameByUid[e.player_uid] || "?"}</span>}
                {e.source === "manual" && <Badge variant="secondary" className="text-[10px] px-1 py-0">manual</Badge>}
                {e.bbox && (
                  <button
                    className="ml-auto p-1 rounded hover:bg-muted"
                    title="View detection frame"
                    onClick={(ev) => { ev.stopPropagation(); setFrameEvent(e); }}
                  >
                    <Eye className="h-3.5 w-3.5 text-muted-foreground" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog open={!!frameEvent} onOpenChange={(open) => { if (!open) setFrameEvent(null); }}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>
              {frameEvent && `${frameEvent.type} @ ${frameEvent.timestamp_sec.toFixed(1)}s`}
            </DialogTitle>
          </DialogHeader>
          {frameEvent && (
            <img
              src={`/api/games/${game.uid}/events/${frameEvent.uid}/frame`}
              alt="Annotated detection frame"
              className="w-full rounded"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
