import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { teamsApi, videosApi } from "../lib/api";
import type { Team, Video } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-500",
  processing: "bg-blue-500",
  done: "bg-green-500",
  failed: "bg-red-500",
};

export default function Videos() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [awayUid, setAwayUid] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const { data: ownTeams } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const { data: opponents } = useQuery({ queryKey: ["teams", "opponents"], queryFn: () => teamsApi.list(false) });
  const { data: videos } = useQuery({ queryKey: ["videos"], queryFn: videosApi.list, refetchInterval: 5000 });

  const homeTeam = ownTeams?.[0];

  const upload = useMutation({
    mutationFn: () => {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("date", date);
      formData.append("home_team_uid", homeTeam!.uid);
      formData.append("away_team_uid", awayUid);
      formData.append("file", file!);
      return videosApi.upload(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      setName("");
      setDate("");
      setAwayUid("");
      setFile(null);
    },
  });

  return (
    <div className="space-y-6 max-w-3xl">
      <Card>
        <CardHeader>
          <CardTitle>Upload Video</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input placeholder="Video name" value={name} onChange={(e) => setName(e.target.value)} />
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-muted-foreground">Home Team</label>
              <p className="font-medium">{homeTeam?.name || "No team set"}</p>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Away Team</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={awayUid}
                onChange={(e) => setAwayUid(e.target.value)}
              >
                <option value="">Select opponent...</option>
                {opponents?.map((t: Team) => (
                  <option key={t.uid} value={t.uid}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>
          <Input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <Button onClick={() => upload.mutate()} disabled={!name || !date || !awayUid || !file}>
            Upload & Analyze
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Videos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {videos?.map((v: Video) => (
                <TableRow key={v.uid}>
                  <TableCell>
                    <Link to={`/videos/${v.uid}`} className="text-blue-600 underline">{v.name}</Link>
                  </TableCell>
                  <TableCell>{v.date}</TableCell>
                  <TableCell>
                    <Badge className={STATUS_COLORS[v.status]}>{v.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
