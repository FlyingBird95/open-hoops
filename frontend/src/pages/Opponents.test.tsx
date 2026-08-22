import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  teamsApi: { list: vi.fn(), create: vi.fn(), delete: vi.fn() },
  playersApi: { list: vi.fn(), create: vi.fn(), delete: vi.fn() },
}));

vi.mock("sonner", () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }));

import { teamsApi, playersApi } from "../lib/api";
import Opponents from "./Opponents";

const mockTeamsApi = teamsApi as { list: ReturnType<typeof vi.fn>; create: ReturnType<typeof vi.fn>; delete: ReturnType<typeof vi.fn> };
const mockPlayersApi = playersApi as { list: ReturnType<typeof vi.fn>; create: ReturnType<typeof vi.fn>; delete: ReturnType<typeof vi.fn> };

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

const opponent1 = { uid: "aaa111", name: "Lakers", is_own: false, home_color: "#552583", away_color: "#FDB927" };
const opponent2 = { uid: "bbb222", name: "Celtics", is_own: false, home_color: "#007A33", away_color: "#FFFFFF" };

describe("Opponents", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows loading skeletons", () => {
    mockTeamsApi.list.mockReturnValue(new Promise(() => {}));
    renderWithProviders(<Opponents />);
    const skeletons = document.querySelectorAll(".h-10, .h-14");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows empty state when no opponents", async () => {
    mockTeamsApi.list.mockResolvedValue([]);
    renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("No opponents added yet")).toBeInTheDocument();
    });
  });

  it("shows Add button disabled without name", async () => {
    mockTeamsApi.list.mockResolvedValue([]);
    renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("No opponents added yet")).toBeInTheDocument();
    });
    const addButton = screen.getByRole("button", { name: "Add" });
    expect(addButton).toBeDisabled();
  });

  it("renders opponent cards with team name", async () => {
    mockTeamsApi.list.mockResolvedValue([opponent1, opponent2]);
    renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("Lakers")).toBeInTheDocument();
    });
    expect(screen.getByText("Celtics")).toBeInTheDocument();
  });

  it("shows Delete button per team", async () => {
    mockTeamsApi.list.mockResolvedValue([opponent1, opponent2]);
    renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("Lakers")).toBeInTheDocument();
    });
    const deleteButtons = screen.getAllByRole("button", { name: "Delete" });
    expect(deleteButtons).toHaveLength(2);
  });

  it("toggles roster expand/collapse", async () => {
    const user = userEvent.setup();
    mockTeamsApi.list.mockResolvedValue([opponent1]);
    mockPlayersApi.list.mockResolvedValue([]);
    renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("Lakers")).toBeInTheDocument();
    });

    const rosterButton = screen.getByRole("button", { name: "Roster" });
    await user.click(rosterButton);
    expect(screen.getByRole("button", { name: "Hide" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Hide" }));
    expect(screen.getByRole("button", { name: "Roster" })).toBeInTheDocument();
  });

  it("add opponent form has color pickers", async () => {
    mockTeamsApi.list.mockResolvedValue([]);
    const { container } = renderWithProviders(<Opponents />);
    await waitFor(() => {
      expect(screen.getByText("No opponents added yet")).toBeInTheDocument();
    });
    const colorInputs = container.querySelectorAll("input[type='color']");
    expect(colorInputs).toHaveLength(2);
  });
});
