import { Toaster } from "@/components/ui/toaster";
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider } from '@/lib/AuthContext';

import Landing from './pages/Landing';
import Onboarding from './pages/Onboarding';
import Discover from './pages/Discover';
import Assistant from './pages/Assistant';
import Plan from './pages/Plan';
import Itinerary from './pages/Itinerary';
import Trips from './pages/Trips';
import Nearby from './pages/Nearby';
import Compare from './pages/Compare';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';
import AppLayout from './components/layout/AppLayout';

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/onboarding" element={<Onboarding />} />
            <Route element={<AppLayout />}>
              <Route path="/discover" element={<Discover />} />
              <Route path="/assistant" element={<Assistant />} />
              <Route path="/plan" element={<Plan />} />
              <Route path="/itinerary" element={<Itinerary />} />
              <Route path="/trips" element={<Trips />} />
              <Route path="/nearby" element={<Nearby />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/profile" element={<Profile />} />
            </Route>
            <Route path="*" element={<PageNotFound />} />
          </Routes>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  );
}

export default App;