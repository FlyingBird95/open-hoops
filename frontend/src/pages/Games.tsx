import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { teamsApi, gamesApi } from "../lib/api";
import type { Team, Game } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ArrowDown, ArrowUp, ArrowUpDown, Upload } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DropZone } from "@/components/drop-zone";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

type SortKey = "name" | "date" | "file_count" | "status";
type SortDir = "asc" | "desc";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500",
  processing: "bg-blue-500",
  done: "bg-green-500",
  failed: "bg-red-500",
};

export default function Games() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [awayUid, setAwayUid] = useState("");
  const [homeColor, setHomeColor] = useState("");
  const [awayColor, setAwayColor] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const { data: ownTeams } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const { data: opponents } = useQuery({ queryKey: ["teams", "opponents"], queryFn: () => teamsApi.list(false) });
  const { data: games } = useQuery({ queryKey: ["games"], queryFn: gamesApi.list, refetchInterval: 5000 });

  const sortedGames = useMemo(() => {
    if (!games) return [];
    return [...games].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "name") cmp = a.name.localeCompare(b.name);
      else if (sortKey === "date") cmp = a.date.localeCompare(b.date);
      else if (sortKey === "file_count") cmp = a.file_count - b.file_count;
      else if (sortKey === "status") cmp = a.status.localeCompare(b.status);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [games, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "date" ? "desc" : "asc");
    }
  }

  function SortIcon({ column }: { column: SortKey }) {
    if (sortKey !== column) return <ArrowUpDown className="inline ml-1 h-3 w-3 opacity-40" />;
    return sortDir === "asc"
      ? <ArrowUp className="inline ml-1 h-3 w-3" />
      : <ArrowDown className="inline ml-1 h-3 w-3" />;
  }

  const myTeam = ownTeams?.[0];
  const opponentTeam = opponents?.find((t) => t.uid === awayUid);

  const upload = useMutation({
    mutationFn: () => {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("date", date);
      formData.append("own_team_uid", myTeam!.uid);
      formData.append("opponent_team_uid", awayUid);
      formData.append("own_team_color", homeColor || myTeam!.home_color);
      formData.append("opponent_team_color", awayColor || opponentTeam!.home_color);
      files.forEach((f) => formData.append("files", f));
      setUploadProgress(0);
      return gamesApi.upload(formData, (pct) => setUploadProgress(pct));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["games"] });
      setName("");
      setDate(new Date().toISOString().slice(0, 10));
      setAwayUid("");
      setHomeColor("");
      setAwayColor("");
      setFiles([]);
      setUploadProgress(null);
      toast("Game uploaded — analysis started");
    },
    onError: (err: Error) => {
      setUploadProgress(null);
      toast.error(`Upload failed — ${err.message}`);
    },
  });

  return (
    <div className="space-y-6 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle>Upload Game</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Section 1: Game Info */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Game Info</p>
            <div className="grid grid-cols-2 gap-4">
              <Input placeholder="Game name" value={name} onChange={(e) => setName(e.target.value)} disabled={upload.isPending} />
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} disabled={upload.isPending} />
            </div>
          </div>

          <Separator />

          {/* Section 2: Teams */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Teams</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">My Team</label>
                <p className="font-medium">{myTeam?.name || "No team set"}</p>
                {myTeam && (
                  <div className="flex gap-2 items-center">
                    <label className="text-xs text-muted-foreground">Jersey color:</label>
                    <button
                      type="button"
                      className={`w-6 h-6 rounded border-2 ${(!homeColor || homeColor === myTeam.home_color) ? "border-foreground" : "border-transparent"}`}
                      style={{ backgroundColor: myTeam.home_color }}
                      onClick={() => setHomeColor(myTeam.home_color)}
                      title="Home"
                      disabled={upload.isPending}
                    />
                    <button
                      type="button"
                      className={`w-6 h-6 rounded border-2 ${homeColor === myTeam.away_color ? "border-foreground" : "border-transparent"}`}
                      style={{ backgroundColor: myTeam.away_color }}
                      onClick={() => setHomeColor(myTeam.away_color)}
                      title="Away"
                      disabled={upload.isPending}
                    />
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">Opponent</label>
                <select
                  className="w-full border rounded px-3 py-2"
                  value={awayUid}
                  onChange={(e) => {
                    setAwayUid(e.target.value);
                    setAwayColor("");
                  }}
                  disabled={upload.isPending}
                >
                  <option value="">Select opponent...</option>
                  {opponents?.map((t: Team) => (
                    <option key={t.uid} value={t.uid}>{t.name}</option>
                  ))}
                </select>
                {opponentTeam && (
                  <div className="flex gap-2 items-center">
                    <label className="text-xs text-muted-foreground">Jersey color:</label>
                    <button
                      type="button"
                      className={`w-6 h-6 rounded border-2 ${(!awayColor || awayColor === opponentTeam.home_color) ? "border-foreground" : "border-transparent"}`}
                      style={{ backgroundColor: opponentTeam.home_color }}
                      onClick={() => setAwayColor(opponentTeam.home_color)}
                      title="Home"
                      disabled={upload.isPending}
                    />
                    <button
                      type="button"
                      className={`w-6 h-6 rounded border-2 ${awayColor === opponentTeam.away_color ? "border-foreground" : "border-transparent"}`}
                      style={{ backgroundColor: opponentTeam.away_color }}
                      onClick={() => setAwayColor(opponentTeam.away_color)}
                      title="Away"
                      disabled={upload.isPending}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>

          <Separator />

          {/* Section 3: Files */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Video Files</p>
            <DropZone files={files} onChange={setFiles} disabled={upload.isPending} />
          </div>

          {uploadProgress !== null && (
            <Progress value={uploadProgress} className="h-2" />
          )}

          <Button onClick={() => upload.mutate()} disabled={!name || !date || !awayUid || files.length === 0 || upload.isPending}>
            {upload.isPending ? "Uploading..." : "Upload & Analyze"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Games</CardTitle>
        </CardHeader>
        <CardContent>
          {!games ? (
            <div className="space-y-3">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
          ) : sortedGames.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <Upload className="h-10 w-10 text-muted-foreground/40 mb-2" />
              <p className="text-sm text-muted-foreground">No games yet — upload one above</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("name")}>Name<SortIcon column="name" /></TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("date")}>Date<SortIcon column="date" /></TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("file_count")}>Files<SortIcon column="file_count" /></TableHead>
                  <TableHead className="cursor-pointer select-none" onClick={() => toggleSort("status")}>Status<SortIcon column="status" /></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedGames.map((v: Game) => (
                  <TableRow key={v.uid}>
                    <TableCell>
                      <Link to={`/games/${v.uid}`} className="text-blue-600 underline">{v.name}</Link>
                    </TableCell>
                    <TableCell>{v.date}</TableCell>
                    <TableCell>{v.file_count}</TableCell>
                    <TableCell>
                      <Badge className={STATUS_COLORS[v.status]}>{v.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
