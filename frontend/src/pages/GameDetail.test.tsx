import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("../lib/api", () => ({
  gamesApi: {
    get: vi.fn(),
    list: vi.fn(),
    upload: vi.fn(),
    update: vi.fn(),
    stats: vi.fn(),
    events: vi.fn(),
    files: vi.fn(),
    createEvent: vi.fn(),
    updateEvent: vi.fn(),
    deleteEvent: vi.fn(),
  },
  teamsApi: { list: vi.fn() },
  playersApi: { list: vi.fn() },
}));

vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));

import { gamesApi, teamsApi, playersApi } from "../lib/api";
import type { Game, GameStatsResponse, GameEventData, Team, Player } from "../lib/api";
import GameDetail from "./GameDetail";

function renderWithProviders(uid: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/games/${uid}`]}>
        <Routes>
          <Route path="/games/:uid" element={<GameDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockOwnTeam: Team = {
  uid: "ownteam0000000000000000000000001",
  name: "My Squad",
  is_own: true,
  home_color: "#FF0000",
  away_color: "#FFFFFF",
};

const mockOpponent: Team = {
  uid: "opponent000000000000000000000001",
  name: "Rival Team",
  is_own: false,
  home_color: "#0000FF",
  away_color: "#000000",
};

const mockGame: Game = {
  uid: "game00000000000000000000000000a1",
  name: "Season Opener",
  date: "2026-08-01",
  status: "done",
  own_team_uid: mockOwnTeam.uid,
  opponent_team_uid: mockOpponent.uid,
  own_team_color: "#FF0000",
  opponent_team_color: "#0000FF",
  duration_seconds: 3600,
  fps: 30,
  file_count: 2,
  is_archived: false,
};

const mockProcessingGame: Game = {
  ...mockGame,
  uid: "game00000000000000000000000000b2",
  name: "Playoff Game",
  status: "processing",
};

const mockPendingGame: Game = {
  ...mockGame,
  uid: "game00000000000000000000000000c3",
  name: "Upcoming Match",
  status: "pending",
};

const mockArchivedGame: Game = {
  ...mockGame,
  uid: "game00000000000000000000000000d4",
  name: "Old Game",
  is_archived: true,
};

const mockStats: GameStatsResponse = {
  team_stats: [
    { uid: "ts1", score: 78, possession_pct: 0.55, team_uid: mockOwnTeam.uid },
    { uid: "ts2", score: 72, possession_pct: 0.45, team_uid: mockOpponent.uid },
  ],
  player_stats: [
    {
      uid: "ps1",
      jersey_number: 23,
      distance_covered_m: 1200,
      shot_attempts: 15,
      shot_makes: 8,
      passes_made: 5,
      passes_received: 3,
      possession_frames: 100,
      team_uid: mockOwnTeam.uid,
      player_uid: "player001",
    },
    {
      uid: "ps2",
      jersey_number: 11,
      distance_covered_m: 900,
      shot_attempts: 10,
      shot_makes: 4,
      passes_made: 8,
      passes_received: 6,
      possession_frames: 80,
      team_uid: mockOpponent.uid,
      player_uid: "player002",
    },
  ],
};

const mockEvents: GameEventData[] = [
  {
    uid: "evt001",
    type: "make",
    frame: 900,
    timestamp_sec: 30.0,
    team_uid: mockOwnTeam.uid,
    player_uid: "player001",
    source: "analysis",
  },
  {
    uid: "evt002",
    type: "pass",
    frame: 1500,
    timestamp_sec: 50.0,
    team_uid: mockOpponent.uid,
    player_uid: "player002",
    player2_uid: "player003",
    source: "manual",
  },
];

const mockPlayers: Player[] = [
  { uid: "player001", jersey_number: 23, name: "Jordan", team_uid: mockOwnTeam.uid },
];

const mockOppPlayers: Player[] = [
  { uid: "player002", jersey_number: 11, name: "Irving", team_uid: mockOpponent.uid },
];

function setupDefaultMocks() {
  vi.mocked(teamsApi.list).mockImplementation(async (isOwn: boolean) =>
    isOwn ? [mockOwnTeam] : [mockOpponent]
  );
  vi.mocked(playersApi.list).mockImplementation(async (teamUid: string) => {
    if (teamUid === mockOwnTeam.uid) return mockPlayers;
    if (teamUid === mockOpponent.uid) return mockOppPlayers;
    return [];
  });
  vi.mocked(gamesApi.files).mockResolvedValue([]);
}

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("GameDetail", () => {
  it("shows loading skeleton when game not loaded", () => {
    vi.mocked(gamesApi.get).mockReturnValue(new Promise(() => {}));
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    vi.mocked(playersApi.list).mockResolvedValue([]);
    vi.mocked(gamesApi.files).mockReturnValue(new Promise(() => {}));

    renderWithProviders(mockGame.uid);

    const skeletons = document.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows processing status with message for processing game", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockProcessingGame);

    renderWithProviders(mockProcessingGame.uid);

    await waitFor(() => {
      expect(screen.getByText("Playoff Game")).toBeInTheDocument();
    });
    expect(screen.getByText("processing")).toBeInTheDocument();
    expect(screen.getByText("Analysis in progress...")).toBeInTheDocument();
  });

  it("shows pending status badge for pending game", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockPendingGame);

    renderWithProviders(mockPendingGame.uid);

    await waitFor(() => {
      expect(screen.getByText("Upcoming Match")).toBeInTheDocument();
    });
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  it("shows game name as heading when loaded", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Season Opener" })).toBeInTheDocument();
    });
  });

  it("shows ScoreCard with team stats when done", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    await waitFor(() => {
      expect(screen.getByText("78")).toBeInTheDocument();
    });
    expect(screen.getByText("72")).toBeInTheDocument();
    // Team names appear in ScoreCard and PlayerStatsTable
    expect(screen.getAllByText("My Squad").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Rival Team").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Possession")).toBeInTheDocument();
  });

  it("shows player stats table when done", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    // Wait for stats table to render - headers appear once per team
    await waitFor(() => {
      expect(screen.getAllByText("Shots").length).toBe(2);
    });
    // Table headers (one per team table)
    expect(screen.getAllByText("Makes").length).toBe(2);
    expect(screen.getAllByText("FG%").length).toBe(2);
    expect(screen.getAllByText("Passes").length).toBe(2);
    expect(screen.getAllByText("Distance").length).toBe(2);
    // Player distance values (unique per player)
    expect(screen.getByText("1200m")).toBeInTheDocument();
    expect(screen.getByText("900m")).toBeInTheDocument();
  });

  it("shows Archive button for non-archived game", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^\s*archive\s*$/i })).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /unarchive/i })).not.toBeInTheDocument();
  });

  it("shows Unarchive button for archived game", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockArchivedGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockArchivedGame.uid);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /unarchive/i })).toBeInTheDocument();
    });
  });

  it("edit mode toggle button exists for done game", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /edit events/i })).toBeInTheDocument();
    });
  });

  it("shows events timeline when not in edit mode", async () => {
    setupDefaultMocks();
    vi.mocked(gamesApi.get).mockResolvedValue(mockGame);
    vi.mocked(gamesApi.stats).mockResolvedValue(mockStats);
    vi.mocked(gamesApi.events).mockResolvedValue(mockEvents);

    renderWithProviders(mockGame.uid);

    await waitFor(() => {
      expect(screen.getByText(/Events \(2\)/)).toBeInTheDocument();
    });
    expect(screen.getByText("30.0s")).toBeInTheDocument();
    expect(screen.getByText("50.0s")).toBeInTheDocument();
    expect(screen.getByText("make")).toBeInTheDocument();
    expect(screen.getByText("pass")).toBeInTheDocument();
  });
});
