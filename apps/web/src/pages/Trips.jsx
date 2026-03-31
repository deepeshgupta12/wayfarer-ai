import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Briefcase, Heart, Clock, Star, Camera, GitBranch, Route } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { listSavedTrips, listTripSignals } from '@/api/wayfarerApi';
import EmptyState from '../components/ui/EmptyState';
import LoadingState from '../components/ui/LoadingState';
import TripPlanCard from '../components/cards/TripPlanCard';
import SavedPlacesList from '../components/trips/SavedPlacesList';
import { getOrCreateTravellerId } from '@/lib/travellerProfile';
import { cacheSavedTrip, cacheSavedTrips, getCachedSavedTrips } from '@/lib/tripStorage';

const tabs = [
  { id: 'trips', label: 'My Trips', icon: Briefcase },
  { id: 'saved', label: 'Saved Places', icon: Heart },
  { id: 'history', label: 'Past Trips', icon: Clock },
];

function deriveSavedPlaces(trips, signalsByTrip) {
  const savedMap = new Map();

  (trips || []).forEach((trip) => {
    const tripSignals = signalsByTrip[trip.trip_id] || [];

    tripSignals
      .filter((signal) => signal.signal_type === 'selected_place')
      .forEach((signal) => {
        const key = signal.location_id || `${trip.trip_id}_${signal.payload?.name || signal.signal_id}`;
        if (savedMap.has(key)) return;

        const candidate = (trip.candidate_places || []).find(
          (item) => item.location_id === signal.location_id
        );

        const slotPhoto =
          (trip.itinerary_skeleton || [])
            .flatMap((day) => day?.slots || [])
            .find((slot) => slot?.assigned_location_id === signal.location_id)
            ?.assigned_place_photos?.[0]?.image_url || null;

        savedMap.set(key, {
          id: signal.signal_id,
          location_id: signal.location_id || null,
          name: signal.payload?.name || candidate?.name || 'Saved place',
          image_url: slotPhoto || candidate?.photos?.[0]?.image_url || null,
          photos: candidate?.photos || [],
          category: signal.payload?.category || candidate?.category || null,
          rating: candidate?.rating || null,
          description: trip.destination
            ? `Saved from ${trip.destination}`
            : 'Saved from your itinerary',
          reason_saved: trip.title,
          is_hidden_gem: false,
          city: signal.payload?.city || candidate?.city || null,
          tags: candidate?.photos?.[0]?.tags || [],
          saved_at: signal.created_at,
          trip_status: trip.status,
        });
      });
  });

  return Array.from(savedMap.values()).sort((a, b) => {
    const aTime = new Date(a?.saved_at || 0).getTime();
    const bTime = new Date(b?.saved_at || 0).getTime();
    return bTime - aTime;
  });
}

function buildTripsMemoryStats(trips, savedPlaces) {
  const completedTrips = trips.filter((trip) => trip.status === 'completed').length;
  const versionCount = trips.reduce((sum, trip) => sum + (trip.current_version_number || 0), 0);
  const savedCount = trips.reduce((sum, trip) => sum + (trip.selected_places_count || 0), 0);
  const routeAdjustments = trips.reduce((sum, trip) => sum + (trip.replaced_slots_count || 0), 0);

  return [
    {
      label: 'Completed memories',
      value: completedTrips,
      icon: Star,
    },
    {
      label: 'Trip versions',
      value: versionCount,
      icon: GitBranch,
    },
    {
      label: 'Saved places',
      value: savedPlaces.length || savedCount,
      icon: Heart,
    },
    {
      label: 'Route changes',
      value: routeAdjustments,
      icon: Route,
    },
  ];
}

export default function Trips() {
  const [activeTab, setActiveTab] = useState('trips');
  const travellerId = getOrCreateTravellerId();

  const { data: trips = [], isLoading: tripsLoading } = useQuery({
    queryKey: ['trips-page-saved-trips', travellerId],
    queryFn: async () => {
      const response = await listSavedTrips(travellerId, 100);
      cacheSavedTrips(travellerId, response.items || []);
      (response.items || []).forEach((trip) => cacheSavedTrip(trip));
      return response.items || [];
    },
    initialData: () => getCachedSavedTrips(travellerId),
  });

  const { data: signalsByTrip = {}, isLoading: signalsLoading } = useQuery({
    queryKey: ['trips-page-signals', trips.map((trip) => trip.trip_id).join(',')],
    enabled: trips.length > 0,
    queryFn: async () => {
      const entries = await Promise.all(
        trips.map(async (trip) => {
          const response = await listTripSignals(trip.trip_id, 200);
          return [trip.trip_id, response.items || []];
        })
      );
      return Object.fromEntries(entries);
    },
    initialData: {},
  });

  const activeTripsList = trips.filter((trip) => ['planning', 'upcoming', 'active'].includes(trip.status));
  const pastTripsList = trips.filter((trip) => trip.status === 'completed');
  const savedPlaces = useMemo(() => deriveSavedPlaces(trips, signalsByTrip), [trips, signalsByTrip]);
  const memoryStats = useMemo(() => buildTripsMemoryStats(trips, savedPlaces), [trips, savedPlaces]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 overflow-hidden rounded-3xl border border-sage/15 bg-gradient-to-br from-sage/6 via-card to-lavender-light/35"
      >
        <div className="px-6 py-6 lg:px-8 lg:py-8">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-sage/10 px-3 py-1 text-xs font-medium text-sage">
            <Camera className="h-3.5 w-3.5" />
            Trip memory and travel history
          </div>
          <h1 className="font-serif text-3xl font-bold sm:text-4xl">Your Trips</h1>
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground sm:text-base">
            This is your travel memory layer. Revisit completed trips, inspect versions,
            browse saved places, and keep the history of what you actually chose.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {memoryStats.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="rounded-2xl border border-border bg-card/70 p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-muted-foreground">{item.label}</div>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="mt-2 text-2xl font-semibold">{item.value}</div>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>

      <div className="mb-8 flex w-fit gap-1 rounded-xl bg-secondary/60 p-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === 'trips' &&
        (tripsLoading ? (
          <LoadingState message="Loading saved trips..." />
        ) : activeTripsList.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No active trips"
            description="Your upcoming and in-progress trips will appear here."
          />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {activeTripsList.map((trip, index) => (
              <motion.div
                key={trip.trip_id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <TripPlanCard trip={trip} variant="memory" />
              </motion.div>
            ))}
          </div>
        ))}

      {activeTab === 'saved' &&
        (signalsLoading ? (
          <LoadingState message="Loading saved places..." />
        ) : !savedPlaces.length ? (
          <EmptyState
            icon={Heart}
            title="No saved places yet"
            description="Places saved through itinerary and runtime signals will appear here."
          />
        ) : (
          <SavedPlacesList places={savedPlaces} />
        ))}

      {activeTab === 'history' &&
        (tripsLoading ? (
          <LoadingState message="Loading trip history..." />
        ) : pastTripsList.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No past trips"
            description="Completed trips and your travel memory will live here."
          />
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {pastTripsList.map((trip, index) => (
              <motion.div
                key={trip.trip_id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <TripPlanCard trip={trip} variant="history" />
              </motion.div>
            ))}
          </div>
        ))}

      {activeTab === 'history' && pastTripsList.length > 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-10 rounded-2xl border border-lavender/10 bg-gradient-to-r from-lavender-light to-sage-light p-5"
        >
          <div className="flex items-start gap-3">
            <Star className="mt-0.5 h-5 w-5 flex-shrink-0 text-lavender" />
            <div>
              <h3 className="mb-1 text-sm font-semibold">Your travel intelligence is compounding</h3>
              <p className="text-xs text-muted-foreground">
                With {pastTripsList.length} completed {pastTripsList.length === 1 ? 'trip' : 'trips'},
                Wayfarer has stronger memory across destinations, versions, and choices.
              </p>
            </div>
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}