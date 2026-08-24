import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  gamesApi: { list: vi.fn(), upload: vi.fn() },
  teamsApi: { list: vi.fn() },
}));

vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));

import { gamesApi, teamsApi } from "../lib/api";
import type { Game, Team } from "../lib/api";
import Games from "./Games";

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
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

const mockGames: Game[] = [
  {
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
  },
  {
    uid: "game00000000000000000000000000b2",
    name: "Playoff Game",
    date: "2026-08-15",
    status: "processing",
    own_team_uid: mockOwnTeam.uid,
    opponent_team_uid: mockOpponent.uid,
    own_team_color: "#FF0000",
    opponent_team_color: "#0000FF",
    duration_seconds: 4200,
    fps: 30,
    file_count: 4,
    is_archived: false,
  },
];

beforeEach(() => {
  vi.resetAllMocks();
});

afterEach(() => {
  cleanup();
});

describe("Games", () => {
  it("shows loading skeletons initially", () => {
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    vi.mocked(gamesApi.list).mockReturnValue(new Promise(() => {}));

    renderWithProviders(<Games />);

    const skeletons = document.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders empty state when no games", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    vi.mocked(gamesApi.list).mockResolvedValue([]);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText(/no games yet/i)).toBeInTheDocument();
    });
  });

  it("renders games table with data", async () => {
    vi.mocked(teamsApi.list).mockImplementation(async (isOwn: boolean) =>
      isOwn ? [mockOwnTeam] : [mockOpponent]
    );
    vi.mocked(gamesApi.list).mockResolvedValue(mockGames);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText("Season Opener")).toBeInTheDocument();
    });
    expect(screen.getByText("Playoff Game")).toBeInTheDocument();
    expect(screen.getByText("2026-08-01")).toBeInTheDocument();
    expect(screen.getByText("2026-08-15")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
  });

  it("upload button disabled when form incomplete", async () => {
    vi.mocked(teamsApi.list).mockImplementation(async (isOwn: boolean) =>
      isOwn ? [mockOwnTeam] : [mockOpponent]
    );
    vi.mocked(gamesApi.list).mockResolvedValue([]);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText(/no games yet/i)).toBeInTheDocument();
    });

    const uploadButton = screen.getByRole("button", { name: /upload & analyze/i });
    expect(uploadButton).toBeDisabled();
  });

  it("sort toggling changes direction on click", async () => {
    const user = userEvent.setup();
    vi.mocked(teamsApi.list).mockImplementation(async (isOwn: boolean) =>
      isOwn ? [mockOwnTeam] : [mockOpponent]
    );
    vi.mocked(gamesApi.list).mockResolvedValue(mockGames);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText("Season Opener")).toBeInTheDocument();
    });

    // Default sort is date desc, so Playoff Game (Aug 15) comes first
    const rows = document.querySelectorAll("tbody tr");
    expect(rows[0]).toHaveTextContent("Playoff Game");
    expect(rows[1]).toHaveTextContent("Season Opener");

    // Click date header to toggle to asc
    const dateHeader = screen.getByText("Date");
    await user.click(dateHeader);

    const rowsAfter = document.querySelectorAll("tbody tr");
    expect(rowsAfter[0]).toHaveTextContent("Season Opener");
    expect(rowsAfter[1]).toHaveTextContent("Playoff Game");
  });

  it("archive toggle button renders", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    vi.mocked(gamesApi.list).mockResolvedValue([]);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText(/no games yet/i)).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /show archived/i })).toBeInTheDocument();
  });

  it("games link to detail page", async () => {
    vi.mocked(teamsApi.list).mockImplementation(async (isOwn: boolean) =>
      isOwn ? [mockOwnTeam] : [mockOpponent]
    );
    vi.mocked(gamesApi.list).mockResolvedValue(mockGames);

    renderWithProviders(<Games />);

    await waitFor(() => {
      expect(screen.getByText("Season Opener")).toBeInTheDocument();
    });

    const link = screen.getByRole("link", { name: "Season Opener" });
    expect(link).toHaveAttribute("href", "/games/game00000000000000000000000000a1");

    const link2 = screen.getByRole("link", { name: "Playoff Game" });
    expect(link2).toHaveAttribute("href", "/games/game00000000000000000000000000b2");
  });
});
