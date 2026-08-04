import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MyTeam from "./pages/MyTeam";
import Opponents from "./pages/Opponents";
import Videos from "./pages/Videos";
import VideoDetail from "./pages/VideoDetail";

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
            <NavLink to="/videos" className={({ isActive }) => isActive ? "font-bold" : ""}>
              Videos
            </NavLink>
          </nav>
          <main className="p-6">
            <Routes>
              <Route path="/" element={<MyTeam />} />
              <Route path="/opponents" element={<Opponents />} />
              <Route path="/videos" element={<Videos />} />
              <Route path="/videos/:uid" element={<VideoDetail />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
