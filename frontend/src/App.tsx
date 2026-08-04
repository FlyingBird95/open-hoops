import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MyTeam from "./pages/MyTeam";
import Opponents from "./pages/Opponents";
import Games from "./pages/Games";
import GameDetail from "./pages/GameDetail";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <nav className="border-b px-6 py-3 flex gap-6">
            <NavLink to="/" className={({ isActive }) => isActive ? "font-bold" : ""}>
              My Team
            </NavLink>
            <NavLink to="/opponents" className={({ isActive }) => isActive ? "font-bold" : ""}>
              Opponents
            </NavLink>
            <NavLink to="/games" className={({ isActive }) => isActive ? "font-bold" : ""}>
              Games
            </NavLink>
          </nav>
          <main className="p-6">
            <Routes>
              <Route path="/" element={<MyTeam />} />
              <Route path="/opponents" element={<Opponents />} />
              <Route path="/games" element={<Games />} />
              <Route path="/games/:uid" element={<GameDetail />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
