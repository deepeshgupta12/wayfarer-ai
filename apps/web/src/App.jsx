import { Toaster } from "@/components/ui/toaster"
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClientInstance } from '@/lib/query-client'
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import PageNotFound from './lib/PageNotFound';
import { AuthProvider, useAuth } from '@/lib/AuthContext';
import UserNotRegisteredError from '@/components/UserNotRegisteredError';

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

const AuthenticatedApp = () => {
  const { isLoadingAuth, isLoadingPublicSettings, authError, navigateToLogin } = useAuth();

  if (isLoadingPublicSettings || isLoadingAuth) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-border border-t-accent rounded-full animate-spin"></div>
          <span className="text-sm text-muted-foreground">Loading Wayfarer...</span>
        </div>
      </div>
    );
  }

  if (authError) {
    if (authError.type === 'user_not_registered') {
      return <UserNotRegisteredError />;
    } else if (authError.type === 'auth_required') {
      navigateToLogin();
      return null;
    }
  }

  return (
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
  );
};

function App() {
  return (
    <AuthProvider>
      <QueryClientProvider client={queryClientInstance}>
        <Router>
          <AuthenticatedApp />
        </Router>
        <Toaster />
      </QueryClientProvider>
    </AuthProvider>
  )
}

export default App