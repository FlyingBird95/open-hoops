import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  gamesApi: { list: vi.fn() },
  teamsApi: { list: vi.fn() },
}));

import { gamesApi, teamsApi } from "../lib/api";
import type { Game, Team } from "../lib/api";
import Dashboard from "./Dashboard";

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

function makeGame(overrides: Partial<Game> = {}): Game {
  return {
    uid: "abc00000000000000000000000000001",
    name: "Game 1",
    date: "2026-08-01",
    status: "done",
    own_team_uid: "team1uid00000000000000000000000",
    opponent_team_uid: "opp1uid000000000000000000000000",
    own_team_color: "#FF0000",
    opponent_team_color: "#0000FF",
    duration_seconds: 120,
    fps: 30,
    file_count: 1,
    is_archived: false,
    ...overrides,
  };
}

function makeTeam(overrides: Partial<Team> = {}): Team {
  return {
    uid: "opp1uid000000000000000000000000",
    name: "Opponents FC",
    is_own: false,
    home_color: "#0000FF",
    away_color: "#FFFFFF",
    ...overrides,
  };
}

afterEach(cleanup);

beforeEach(() => {
  vi.mocked(gamesApi.list).mockReset();
  vi.mocked(teamsApi.list).mockReset();
  vi.mocked(teamsApi.list).mockResolvedValue([]);
});

describe("Dashboard", () => {
  it("shows loading skeleton initially", () => {
    vi.mocked(gamesApi.list).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<Dashboard />);
    // Skeleton renders animated placeholder blocks, not the main content
    expect(screen.queryByText("Dashboard")).not.toBeInTheDocument();
    expect(screen.queryByText("No games yet")).not.toBeInTheDocument();
  });

  it("shows empty state when games list is empty", async () => {
    vi.mocked(gamesApi.list).mockResolvedValue([]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("No games yet")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /upload game/i });
    expect(link).toHaveAttribute("href", "/games");
  });

  it("shows stats cards with correct counts", async () => {
    const games: Game[] = [
      makeGame({ uid: "g1", status: "done", duration_seconds: 600 }),
      makeGame({ uid: "g2", status: "done", duration_seconds: 300 }),
      makeGame({ uid: "g3", status: "done", duration_seconds: 300 }),
      makeGame({ uid: "g4", status: "processing", duration_seconds: 0 }),
    ];
    vi.mocked(gamesApi.list).mockResolvedValue(games);
    renderWithProviders(<Dashboard />);

    // Games Processed = done count = 3
    expect(await screen.findByText("Games Processed")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    // Processing = active count = 1
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    // Footage Analyzed = 1200s = 20m
    expect(screen.getByText("20m")).toBeInTheDocument();
  });

  describe("duration formatting", () => {
    it("formats seconds", async () => {
      vi.mocked(gamesApi.list).mockResolvedValue([
        makeGame({ status: "done", duration_seconds: 45 }),
      ]);
      renderWithProviders(<Dashboard />);
      expect(await screen.findByText("45s")).toBeInTheDocument();
    });

    it("formats minutes", async () => {
      vi.mocked(gamesApi.list).mockResolvedValue([
        makeGame({ status: "done", duration_seconds: 180 }),
      ]);
      renderWithProviders(<Dashboard />);
      expect(await screen.findByText("3m")).toBeInTheDocument();
    });

    it("formats hours", async () => {
      vi.mocked(gamesApi.list).mockResolvedValue([
        makeGame({ status: "done", duration_seconds: 5400 }),
      ]);
      renderWithProviders(<Dashboard />);
      expect(await screen.findByText("1.5h")).toBeInTheDocument();
    });
  });

  it("shows active jobs for processing/pending games", async () => {
    const games: Game[] = [
      makeGame({ uid: "g1", name: "Quarterfinal", status: "processing" }),
      makeGame({ uid: "g2", name: "Semifinal", status: "pending" }),
      makeGame({ uid: "g3", name: "Final", status: "done", duration_seconds: 60 }),
    ];
    vi.mocked(gamesApi.list).mockResolvedValue(games);
    renderWithProviders(<Dashboard />);

    expect(await screen.findByText("Active Jobs")).toBeInTheDocument();
    expect(screen.getByText("Quarterfinal")).toBeInTheDocument();
    expect(screen.getByText("Semifinal")).toBeInTheDocument();
  });

  it("shows recent completions limited to 5", async () => {
    const games: Game[] = Array.from({ length: 7 }, (_, i) =>
      makeGame({
        uid: `done${i}`,
        name: `Completed Game ${i + 1}`,
        status: "done",
        duration_seconds: 60,
      })
    );
    vi.mocked(gamesApi.list).mockResolvedValue(games);
    renderWithProviders(<Dashboard />);

    expect(await screen.findByText("Recent Completions")).toBeInTheDocument();
    // First 5 should appear
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByText(`Completed Game ${i}`)).toBeInTheDocument();
    }
    // 6th and 7th should not
    expect(screen.queryByText("Completed Game 6")).not.toBeInTheDocument();
    expect(screen.queryByText("Completed Game 7")).not.toBeInTheDocument();
  });

  it("links to game detail pages", async () => {
    const games: Game[] = [
      makeGame({ uid: "abc123", name: "Linked Game", status: "done", duration_seconds: 60 }),
    ];
    vi.mocked(gamesApi.list).mockResolvedValue(games);
    renderWithProviders(<Dashboard />);

    await screen.findByText("Linked Game");
    const link = screen.getByRole("link", { name: /linked game/i });
    expect(link).toHaveAttribute("href", "/games/abc123");
  });
});
