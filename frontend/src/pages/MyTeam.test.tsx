import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  teamsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn() },
  playersApi: { list: vi.fn(), create: vi.fn(), delete: vi.fn() },
}));

vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));

import MyTeam from "./MyTeam";
import { teamsApi, playersApi } from "../lib/api";

const mockTeam = {
  uid: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
  name: "Lakers",
  is_own: true,
  home_color: "#552583",
  away_color: "#fdb927",
};

const mockPlayers = [
  { uid: "p1p1p1p1p1p1p1p1p1p1p1p1p1p1p1p1", jersey_number: 23, name: "LeBron", team_uid: mockTeam.uid },
  { uid: "p2p2p2p2p2p2p2p2p2p2p2p2p2p2p2p2", jersey_number: 3, name: "AD", team_uid: mockTeam.uid },
];

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  vi.resetAllMocks();
});

describe("MyTeam", () => {
  it("shows loading skeleton while fetching", () => {
    vi.mocked(teamsApi.list).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<MyTeam />);
    const skeletons = document.querySelectorAll(".animate-pulse, [data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows CreateTeamForm when no team exists", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByText("Create Your Team")).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText("e.g. Lakers")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Team" })).toBeInTheDocument();
  });

  it("CreateTeamForm: button disabled without name", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([]);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Create Team" })).toBeDisabled();
    });
  });

  it("shows team name and colors when team exists", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([mockTeam]);
    vi.mocked(playersApi.list).mockResolvedValue(mockPlayers);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByText(/My Team — Lakers/)).toBeInTheDocument();
    });
    const colorInputs = document.querySelectorAll("input[type='color']");
    expect(colorInputs.length).toBeGreaterThanOrEqual(2);
    expect((colorInputs[0] as HTMLInputElement).value).toBe("#552583");
    expect((colorInputs[1] as HTMLInputElement).value).toBe("#fdb927");
  });

  it("shows player roster", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([mockTeam]);
    vi.mocked(playersApi.list).mockResolvedValue(mockPlayers);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByText("23")).toBeInTheDocument();
    });
    expect(screen.getByText("LeBron")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("AD")).toBeInTheDocument();
  });

  it("shows empty roster message when no players", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([mockTeam]);
    vi.mocked(playersApi.list).mockResolvedValue([]);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByText(/No players yet/)).toBeInTheDocument();
    });
  });

  it("Add Player button disabled without jersey number", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([mockTeam]);
    vi.mocked(playersApi.list).mockResolvedValue([]);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Add Player" })).toBeDisabled();
    });
  });

  it("Remove button visible for each player", async () => {
    vi.mocked(teamsApi.list).mockResolvedValue([mockTeam]);
    vi.mocked(playersApi.list).mockResolvedValue(mockPlayers);
    renderWithProviders(<MyTeam />);
    await waitFor(() => {
      const removeButtons = screen.getAllByRole("button", { name: "Remove" });
      expect(removeButtons).toHaveLength(2);
    });
  });
});
