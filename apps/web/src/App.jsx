import { Toaster } from "@/components/ui/toaster";
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClientInstance } from '@/lib/query-client';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider } from '@/lib/AuthContext';
import ErrorBoundary from '@/components/ui/ErrorBoundary';

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
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route element={<AppLayout />}>
                <Route path="/discover" element={<ErrorBoundary><Discover /></ErrorBoundary>} />
                <Route path="/assistant" element={<ErrorBoundary><Assistant /></ErrorBoundary>} />
                <Route path="/plan" element={<ErrorBoundary><Plan /></ErrorBoundary>} />
                <Route path="/itinerary" element={<ErrorBoundary><Itinerary /></ErrorBoundary>} />
                <Route path="/trips" element={<ErrorBoundary><Trips /></ErrorBoundary>} />
                <Route path="/nearby" element={<ErrorBoundary><Nearby /></ErrorBoundary>} />
                <Route path="/compare" element={<ErrorBoundary><Compare /></ErrorBoundary>} />
                <Route path="/notifications" element={<ErrorBoundary><Notifications /></ErrorBoundary>} />
                <Route path="/profile" element={<ErrorBoundary><Profile /></ErrorBoundary>} />
              </Route>
              <Route path="*" element={<PageNotFound />} />
            </Routes>
          </ErrorBoundary>
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  );
}

export default App;