import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/components/theme-provider";
import { AppLayout } from "@/components/app-layout";
import { Toaster } from "@/components/ui/sonner";
import Dashboard from "./pages/Dashboard";
import MyTeam from "./pages/MyTeam";
import Opponents from "./pages/Opponents";
import Games from "./pages/Games";
import GameDetail from "./pages/GameDetail";

const queryClient = new QueryClient();

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppLayout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/my-team" element={<MyTeam />} />
              <Route path="/opponents" element={<Opponents />} />
              <Route path="/games" element={<Games />} />
              <Route path="/games/:uid" element={<GameDetail />} />
            </Routes>
          </AppLayout>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
