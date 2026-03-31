import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Plus,
  Sparkles,
  Calendar,
  MapPin,
  Layers,
  Route,
  GitBranch,
  Heart,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import EmptyState from '../components/ui/EmptyState';
import LoadingState from '../components/ui/LoadingState';
import TripPlanCard from '../components/cards/TripPlanCard';
import NewTripModal from '../components/plan/NewTripModal';
import { listSavedTrips } from '@/api/wayfarerApi';
import { getOrCreateTravellerId } from '@/lib/travellerProfile';
import { cacheSavedTrip, cacheSavedTrips, getCachedSavedTrips } from '@/lib/tripStorage';

function buildWorkspaceStats(trips) {
  const totalTrips = trips.length;
  const totalVersions = trips.reduce((sum, trip) => sum + (trip.current_version_number || 0), 0);
  const totalSaved = trips.reduce((sum, trip) => sum + (trip.selected_places_count || 0), 0);
  const totalReplacements = trips.reduce((sum, trip) => sum + (trip.replaced_slots_count || 0), 0);

  return [
    {
      label: 'Active workspaces',
      value: totalTrips,
      icon: Layers,
      tone: 'from-accent/10 to-accent/5 border-accent/15',
    },
    {
      label: 'Tracked versions',
      value: totalVersions,
      icon: GitBranch,
      tone: 'from-ocean/10 to-ocean/5 border-ocean/15',
    },
    {
      label: 'Saved decisions',
      value: totalSaved,
      icon: Heart,
      tone: 'from-sage/10 to-sage/5 border-sage/15',
    },
    {
      label: 'Route refinements',
      value: totalReplacements,
      icon: Route,
      tone: 'from-lavender/10 to-lavender/5 border-lavender/15',
    },
  ];
}

export default function Plan() {
  const [showNewTrip, setShowNewTrip] = useState(false);
  const travellerId = getOrCreateTravellerId();

  const {
    data: trips = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['backend-saved-trips', travellerId],
    queryFn: async () => {
      const response = await listSavedTrips(travellerId, 100);
      cacheSavedTrips(travellerId, response.items || []);
      (response.items || []).forEach((trip) => cacheSavedTrip(trip));
      return response.items || [];
    },
    initialData: () => getCachedSavedTrips(travellerId),
  });

  const planningTrips = useMemo(
    () => (trips || []).filter((trip) => ['planning', 'upcoming', 'active'].includes(trip.status)),
    [trips]
  );

  const stats = useMemo(() => buildWorkspaceStats(planningTrips), [planningTrips]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 overflow-hidden rounded-3xl border border-accent/15 bg-gradient-to-br from-accent/5 via-card to-sunset-light/40"
      >
        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.3fr_0.7fr] lg:px-8 lg:py-8">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
              <Sparkles className="h-3.5 w-3.5" />
              Planning workspace
            </div>
            <h1 className="font-serif text-3xl font-bold sm:text-4xl">Plan</h1>
            <p className="mt-3 max-w-2xl text-sm text-muted-foreground sm:text-base">
              This is your itinerary workspace. Build routes, compare versions, refine slots,
              and move from rough plan to a structured trip you can actually use.
            </p>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => setShowNewTrip(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
              >
                <Plus className="h-4 w-4" />
                New trip
              </button>

              <Link
                to="/assistant"
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2.5 text-sm font-medium hover:border-accent/30"
              >
                <Sparkles className="h-4 w-4 text-accent" />
                Start with AI
              </Link>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <Link
              to="/compare"
              className="group rounded-2xl border border-ocean/15 bg-gradient-to-br from-ocean/10 to-card p-4 transition-all hover:border-ocean/25"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ocean/15">
                  <MapPin className="h-5 w-5 text-ocean" />
                </div>
                <div>
                  <div className="text-sm font-medium">Compare before planning</div>
                  <div className="text-xs text-muted-foreground">Start from a stronger destination call</div>
                </div>
              </div>
            </Link>

            <Link
              to="/discover"
              className="group rounded-2xl border border-sage/15 bg-gradient-to-br from-sage/10 to-card p-4 transition-all hover:border-sage/25"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sage/15">
                  <Calendar className="h-5 w-5 text-sage" />
                </div>
                <div>
                  <div className="text-sm font-medium">Discover candidates</div>
                  <div className="text-xs text-muted-foreground">Feed better places into your workspace</div>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="mb-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
      >
        {stats.map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className={`rounded-2xl border bg-gradient-to-br p-4 ${item.tone}`}
            >
              <div className="flex items-center justify-between">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="mt-2 text-2xl font-semibold">{item.value}</div>
            </div>
          );
        })}
      </motion.div>

      {isLoading ? (
        <LoadingState message="Loading your planning workspace..." />
      ) : !planningTrips.length ? (
        <EmptyState
          icon={MapPin}
          title="No planning workspaces yet"
          description="Create a new trip and start shaping the route, versions, and itinerary slots."
          action={() => setShowNewTrip(true)}
          actionLabel="Create trip workspace"
        />
      ) : (
        <div>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Live workspaces</h2>
              <p className="text-sm text-muted-foreground">
                Resume the trip plans you are still shaping.
              </p>
            </div>
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {planningTrips.map((trip, index) => (
              <motion.div
                key={trip.trip_id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <TripPlanCard trip={trip} variant="workspace" />
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {!isLoading && planningTrips.length > 0 ? (
        <div className="mt-8 rounded-2xl border border-border bg-card p-4">
          <div className="mb-2 flex items-center gap-2">
            <Layers className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-medium">Workspace mode is backend-first</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            Versions, saved trip entities, slot refinements, and signal counts are being pulled
            from backend state. Local storage is used only as a lightweight cache for faster UI recovery.
          </p>
        </div>
      ) : null}

      {showNewTrip ? (
        <NewTripModal
          onClose={() => setShowNewTrip(false)}
          onCreated={() => {
            refetch();
          }}
        />
      ) : null}
    </div>
  );
}