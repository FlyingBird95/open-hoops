import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { teamsApi, playersApi } from "../lib/api";
import type { Team, Player } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldPlus } from "lucide-react";

function OpponentRoster({ team }: { team: Team }) {
  const queryClient = useQueryClient();
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");

  const { data: players } = useQuery({
    queryKey: ["players", team.uid],
    queryFn: () => playersApi.list(team.uid),
  });

  const addPlayer = useMutation({
    mutationFn: () =>
      playersApi.create({ team_uid: team.uid, jersey_number: parseInt(newNumber), name: newName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["players", team.uid] });
      setNewNumber("");
      setNewName("");
    },
  });

  const deletePlayer = useMutation({
    mutationFn: (uid: string) => playersApi.delete(uid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["players", team.uid] }),
  });

  return (
    <div className="mt-2">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>#</TableHead>
            <TableHead>Name</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {players?.map((p: Player) => (
            <TableRow key={p.uid}>
              <TableCell>{p.jersey_number}</TableCell>
              <TableCell>{p.name || "—"}</TableCell>
              <TableCell>
                <Button variant="destructive" size="sm" onClick={() => deletePlayer.mutate(p.uid)}>
                  Remove
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex gap-2 mt-2">
        <Input placeholder="#" value={newNumber} onChange={(e) => setNewNumber(e.target.value)} className="w-20" />
        <Input placeholder="Name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <Button onClick={() => addPlayer.mutate()} disabled={!newNumber} size="sm">
          Add
        </Button>
      </div>
    </div>
  );
}

export default function Opponents() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [homeColor, setHomeColor] = useState("#000000");
  const [awayColor, setAwayColor] = useState("#ffffff");
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: teams, isLoading } = useQuery({
    queryKey: ["teams", "opponents"],
    queryFn: () => teamsApi.list(false),
  });

  const createTeam = useMutation({
    mutationFn: () => teamsApi.create({ name, is_own: false, home_color: homeColor, away_color: awayColor }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      toast("Opponent added");
      setName("");
    },
  });

  const deleteTeam = useMutation({
    mutationFn: (uid: string) => teamsApi.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      toast("Opponent removed");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-2xl">
        <Card><CardContent className="pt-6"><Skeleton className="h-10 w-full" /></CardContent></Card>
        <Card><CardContent className="pt-6 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-14 w-full rounded" />)}</CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Add Opponent</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 items-center">
            <Input placeholder="Team name" value={name} onChange={(e) => setName(e.target.value)} />
            <label className="text-sm">Home</label>
            <input type="color" value={homeColor} onChange={(e) => setHomeColor(e.target.value)} />
            <label className="text-sm">Away</label>
            <input type="color" value={awayColor} onChange={(e) => setAwayColor(e.target.value)} />
            <Button onClick={() => createTeam.mutate()} disabled={!name}>
              Add
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Opponents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {teams && teams.length === 0 && (
            <div className="flex flex-col items-center py-8 text-center">
              <ShieldPlus className="h-10 w-10 text-muted-foreground/40 mb-2" />
              <p className="text-sm text-muted-foreground">No opponents added yet</p>
            </div>
          )}
          {teams?.map((t: Team) => (
            <div key={t.uid} className="border rounded p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{t.name}</span>
                  <Badge style={{ backgroundColor: t.home_color }} className="w-6 h-6" />
                  <Badge style={{ backgroundColor: t.away_color }} className="w-6 h-6" />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpanded(expanded === t.uid ? null : t.uid)}
                  >
                    {expanded === t.uid ? "Hide" : "Roster"}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => deleteTeam.mutate(t.uid)}>
                    Delete
                  </Button>
                </div>
              </div>
              {expanded === t.uid && <OpponentRoster team={t} />}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
