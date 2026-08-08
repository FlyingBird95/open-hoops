import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { teamsApi, playersApi } from "../lib/api";
import type { Team, Player } from "../lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UserPlus } from "lucide-react";

function CreateTeamForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [homeColor, setHomeColor] = useState("#000000");
  const [awayColor, setAwayColor] = useState("#ffffff");

  const createTeam = useMutation({
    mutationFn: () => teamsApi.create({ name, is_own: true, home_color: homeColor, away_color: awayColor }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      toast("Team created");
    },
  });

  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>Create Your Team</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <label className="text-sm text-muted-foreground">Team Name</label>
          <Input placeholder="e.g. Lakers" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex gap-4 items-center">
          <label className="text-sm">Home Color</label>
          <input type="color" value={homeColor} onChange={(e) => setHomeColor(e.target.value)} />
          <label className="text-sm">Away Color</label>
          <input type="color" value={awayColor} onChange={(e) => setAwayColor(e.target.value)} />
        </div>
        <Button onClick={() => createTeam.mutate()} disabled={!name}>
          Create Team
        </Button>
      </CardContent>
    </Card>
  );
}

export default function MyTeam() {
  const queryClient = useQueryClient();
  const [newNumber, setNewNumber] = useState("");
  const [newName, setNewName] = useState("");

  const { data: teams, isLoading } = useQuery({ queryKey: ["teams", "own"], queryFn: () => teamsApi.list(true) });
  const team = teams?.[0];

  const { data: players } = useQuery({
    queryKey: ["players", team?.uid],
    queryFn: () => playersApi.list(team!.uid),
    enabled: !!team,
  });

  const updateTeam = useMutation({
    mutationFn: (data: Partial<Team>) => teamsApi.update(team!.uid, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      toast("Colors updated");
    },
  });

  const addPlayer = useMutation({
    mutationFn: () => playersApi.create({ team_uid: team!.uid, jersey_number: parseInt(newNumber), name: newName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["players"] });
      toast(`Player #${newNumber} added`);
      setNewNumber("");
      setNewName("");
    },
  });

  const deletePlayer = useMutation({
    mutationFn: (uid: string) => playersApi.delete(uid),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["players"] });
      toast("Player removed");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Card><CardContent className="pt-6"><Skeleton className="h-6 w-40 mb-4" /><Skeleton className="h-8 w-full" /></CardContent></Card>
        <Card><CardContent className="pt-6 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</CardContent></Card>
      </div>
    );
  }
  if (!team) return <CreateTeamForm />;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>My Team — {team.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4 items-center">
            <label className="text-sm">Home Color</label>
            <input
              type="color"
              value={team.home_color}
              onChange={(e) => updateTeam.mutate({ home_color: e.target.value })}
            />
            <label className="text-sm">Away Color</label>
            <input
              type="color"
              value={team.away_color}
              onChange={(e) => updateTeam.mutate({ away_color: e.target.value })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Roster</CardTitle>
        </CardHeader>
        <CardContent>
          {players && players.length === 0 && (
            <div className="flex flex-col items-center py-8 text-center">
              <UserPlus className="h-10 w-10 text-muted-foreground/40 mb-2" />
              <p className="text-sm text-muted-foreground">No players yet — add your roster below</p>
            </div>
          )}
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

          <div className="flex gap-2 mt-4">
            <Input placeholder="#" value={newNumber} onChange={(e) => setNewNumber(e.target.value)} className="w-20" />
            <Input placeholder="Name (optional)" value={newName} onChange={(e) => setNewName(e.target.value)} />
            <Button onClick={() => addPlayer.mutate()} disabled={!newNumber}>
              Add Player
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
