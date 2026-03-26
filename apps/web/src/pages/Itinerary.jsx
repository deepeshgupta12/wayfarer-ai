import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Share2,
  Sparkles,
  Calendar,
  MapPin,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Heart,
  SkipForward,
  RotateCcw,
  GitBranch,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import LoadingState from '../components/ui/LoadingState';
import ActivityCard from '../components/cards/ActivityCard';
import {
  createTripSignal,
  createTripVersionSnapshot,
  getCurrentTripVersion,
  getSavedTrip,
  listSavedTrips,
  listTripSignals,
  listTripVersions,
  restoreTripVersion,
} from '@/api/wayfarerApi';
import { getOrCreateTravellerId } from '@/lib/travellerProfile';
import {
  cacheSavedTrip,
  cacheSavedTrips,
  getCachedSavedTrip,
  getCachedSavedTrips,
} from '@/lib/tripStorage';

function normalizeDayActivities(day) {
  if (Array.isArray(day.slots) && day.slots.length > 0) {
    return day.slots.map((slot) => {
      const reasonText = slot.rationale || '';
      const loweredReason = reasonText.toLowerCase();

      let replacementStatus = 'original';
      if (loweredReason.includes('now anchors')) {
        replacementStatus = 'replaced';
      } else if (loweredReason.includes('remains in the')) {
        replacementStatus = 'retained_best_fit';
      }

      return {
        time: slot.label,
        name: slot.assigned_place_name || 'Flexible slot',
        description: slot.summary,
        type:
          slot.slot_type === 'lunch'
            ? 'food'
            : slot.slot_type === 'evening'
            ? 'nightlife'
            : slot.slot_type === 'afternoon'
            ? 'nature'
            : 'culture',
        location: slot.assigned_place_name || day.title,
        rating: undefined,
        reason: slot.rationale,
        fallbackNames: slot.fallback_candidate_names || [],
        alternatives: slot.alternatives || [],
        assignedLocationId: slot.assigned_location_id || null,
        slotType: slot.slot_type,
        replacementStatus,
        continuityNote: slot.continuity_note || null,
        movementNote: slot.movement_note || null,
        dayNumber: day.day_number,
      };
    });
  }

  if (Array.isArray(day.activities) && day.activities.length > 0) {
    return day.activities;
  }

  return [];
}

function deriveCanonicalItinerary(trip) {
  if (
    Array.isArray(trip.itinerary_skeleton) &&
    trip.itinerary_skeleton.some((day) => Array.isArray(day?.slots) && day.slots.length > 0)
  ) {
    return trip.itinerary_skeleton;
  }

  if (
    Array.isArray(trip.itinerary) &&
    trip.itinerary.some((day) => Array.isArray(day?.slots) && day.slots.length > 0)
  ) {
    return trip.itinerary;
  }

  return trip.itinerary_skeleton || trip.itinerary || [];
}

function buildSavedPlacesFromSignals(signals) {
  const selectedSignals = (signals || []).filter((signal) => signal.signal_type === 'selected_place');
  const map = new Map();

  selectedSignals.forEach((signal) => {
    const signalKey = signal.location_id || signal.payload?.name;
    if (!signalKey || map.has(signalKey)) return;

    map.set(signalKey, {
      signal_id: signal.signal_id,
      location_id: signal.location_id || null,
      name: signal.payload?.name || 'Saved place',
      city: signal.payload?.city || null,
      category: signal.payload?.category || null,
      created_at: signal.created_at,
    });
  });

  return Array.from(map.values());
}

function buildSkippedPlacesFromSignals(signals) {
  const skippedSignals = (signals || []).filter(
    (signal) => signal.signal_type === 'skipped_recommendation'
  );
  const map = new Map();

  skippedSignals.forEach((signal) => {
    const signalKey = signal.location_id || signal.payload?.name;
    if (!signalKey || map.has(signalKey)) return;

    map.set(signalKey, {
      signal_id: signal.signal_id,
      location_id: signal.location_id || null,
      name: signal.payload?.name || 'Skipped recommendation',
      city: signal.payload?.city || null,
      category: signal.payload?.category || null,
      created_at: signal.created_at,
    });
  });

  return Array.from(map.values());
}

export default function Itinerary() {
  const [expandedDay, setExpandedDay] = useState(0);
  const [searchParams] = useSearchParams();
  const travellerId = getOrCreateTravellerId();
  const tripId = searchParams.get('trip');

  const {
    data: activeTripId,
    isLoading: resolvingTripId,
  } = useQuery({
    queryKey: ['active-trip-id', travellerId, tripId],
    queryFn: async () => {
      if (tripId) return tripId;

      const response = await listSavedTrips(travellerId, 100);
      cacheSavedTrips(travellerId, response.items || []);
      (response.items || []).forEach((trip) => cacheSavedTrip(trip));

      return response.items?.[0]?.trip_id || null;
    },
    initialData: tripId || getCachedSavedTrips(travellerId)?.[0]?.trip_id || null,
  });

  const {
    data: trip,
    isLoading: tripLoading,
    refetch: refetchTrip,
  } = useQuery({
    queryKey: ['saved-trip-detail', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await getSavedTrip(activeTripId);
      cacheSavedTrip(response);
      return response;
    },
    initialData: activeTripId ? getCachedSavedTrip(activeTripId) : null,
  });

  const {
    data: versions = [],
    isLoading: versionsLoading,
    refetch: refetchVersions,
  } = useQuery({
    queryKey: ['trip-versions', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await listTripVersions(activeTripId, 100);
      return response.items || [];
    },
    initialData: [],
  });

  const {
    data: currentVersion = null,
    refetch: refetchCurrentVersion,
  } = useQuery({
    queryKey: ['trip-current-version', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => getCurrentTripVersion(activeTripId),
    initialData: null,
  });

  const {
    data: signals = [],
    isLoading: signalsLoading,
    refetch: refetchSignals,
  } = useQuery({
    queryKey: ['trip-signals', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await listTripSignals(activeTripId, 200);
      return response.items || [];
    },
    initialData: [],
  });

  const savedPlaces = useMemo(() => buildSavedPlacesFromSignals(signals), [signals]);
  const skippedRecommendations = useMemo(() => buildSkippedPlacesFromSignals(signals), [signals]);

  const refreshAll = async () => {
    await Promise.all([
      refetchTrip(),
      refetchVersions(),
      refetchCurrentVersion(),
      refetchSignals(),
    ]);
  };

  const handleSavePlace = async (activity) => {
    if (!trip?.trip_id) return;

    await createTripSignal(trip.trip_id, {
      signal_type: 'selected_place',
      location_id: activity.assignedLocationId || activity.name,
      payload: {
        name: activity.name,
        city: trip.destination,
        category: activity.type,
      },
    });

    await refreshAll();
  };

  const handleSkipAlternative = async (alternative) => {
    if (!trip?.trip_id) return;

    await createTripSignal(trip.trip_id, {
      signal_type: 'skipped_recommendation',
      location_id: alternative.location_id || null,
      payload: {
        name: alternative.name,
        city: alternative.city || null,
        category: alternative.category || null,
      },
    });

    await refreshAll();
  };

  const handleSnapshot = async () => {
    if (!trip?.trip_id) return;

    await createTripVersionSnapshot(trip.trip_id, {
      snapshot_reason: 'manual_workspace_snapshot',
      branch_label: trip.history_branch_label || 'main',
    });

    await refreshAll();
  };

  const handleRestoreVersion = async (versionId) => {
    if (!trip?.trip_id || !versionId) return;

    await restoreTripVersion(trip.trip_id, versionId, {
      snapshot_reason: 'restore_selected_version',
      branch_label: trip.history_branch_label || 'main',
    });

    await refreshAll();
  };

  if (resolvingTripId || tripLoading || versionsLoading || signalsLoading) {
    return <LoadingState message="Loading your itinerary..." />;
  }

  if (!trip) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <h2 className="font-serif text-2xl font-bold mb-3">No itinerary found</h2>
        <p className="text-muted-foreground mb-6">
          Create a trip first to see your itinerary here.
        </p>
        <Link
          to="/plan"
          className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium"
        >
          Go to Planner
        </Link>
      </div>
    );
  }

  const itinerary = deriveCanonicalItinerary(trip);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to="/plan"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to trips
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold mb-1">{trip.title}</h1>
            <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" /> {trip.destination}
              </span>

              {trip.start_date ? (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" /> {trip.start_date}
                </span>
              ) : null}

              <span className="flex items-center gap-1">
                <GitBranch className="w-3.5 h-3.5" />
                Version {trip.current_version_number}
              </span>

              {trip.history_branch_label ? (
                <span>{trip.history_branch_label}</span>
              ) : null}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button className="px-3 py-2 rounded-lg border border-border text-sm hover:bg-secondary transition-colors">
              <Share2 className="w-4 h-4" />
            </button>

            <button
              onClick={handleSnapshot}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Save Version
            </button>
          </div>
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-[1fr_340px] gap-8">
        <div className="space-y-4">
          {itinerary.length > 0 ? (
            itinerary.map((day, i) => {
              const activities = normalizeDayActivities(day);

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="rounded-2xl bg-card border border-border overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedDay(expandedDay === i ? -1 : i)}
                    className="w-full flex items-center justify-between p-4 hover:bg-secondary/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                        D{day.day || day.day_number || i + 1}
                      </div>
                      <div className="text-left">
                        <h3 className="font-semibold text-sm">
                          {day.title || `Day ${day.day || i + 1}`}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          {activities.length} activities
                        </p>
                      </div>
                    </div>

                    {expandedDay === i ? (
                      <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>

                  {expandedDay === i ? (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="px-4 pb-4 space-y-3"
                    >
                      {day.summary ? (
                        <div className="text-sm text-muted-foreground">{day.summary}</div>
                      ) : null}

                      {day.day_rationale ? (
                        <div className="text-xs text-muted-foreground">
                          <span className="font-medium">Day rationale:</span> {day.day_rationale}
                        </div>
                      ) : null}

                      {day.continuity_strategy ? (
                        <div className="text-xs text-muted-foreground">
                          <span className="font-medium">Continuity strategy:</span>{' '}
                          {day.continuity_strategy}
                        </div>
                      ) : null}

                      {day.geo_cluster ? (
                        <div className="text-xs text-muted-foreground">
                          <span className="font-medium">Geo cluster:</span> {day.geo_cluster}
                        </div>
                      ) : null}

                      {activities.map((activity, j) => (
                        <div key={j} className="rounded-xl border border-border/60">
                          <ActivityCard
                            {...activity}
                            index={j}
                            onSwap={() => {}}
                          />

                          <div className="px-4 pb-4 flex flex-wrap gap-2">
                            <button
                              onClick={() => handleSavePlace(activity)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
                            >
                              <Heart className="w-3 h-3" />
                              Save place
                            </button>

                            {(activity.alternatives || []).map((alternative, altIndex) => (
                              <button
                                key={`${alternative.location_id}-${altIndex}`}
                                onClick={() => handleSkipAlternative(alternative)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
                              >
                                <SkipForward className="w-3 h-3" />
                                Skip {alternative.name}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}

                      {day.fallback_candidate_names?.length > 0 ? (
                        <div className="text-xs text-muted-foreground pt-1">
                          <span className="font-medium">Fallback direction:</span>{' '}
                          {day.fallback_candidate_names.join(', ')}
                        </div>
                      ) : null}
                    </motion.div>
                  ) : null}
                </motion.div>
              );
            })
          ) : (
            <div className="p-8 rounded-2xl bg-card border border-border text-center">
              <Sparkles className="w-8 h-8 text-accent mx-auto mb-3" />
              <h3 className="font-semibold mb-1">No itinerary yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Let AI generate a personalized day-by-day plan for this trip.
              </p>
              <button className="px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium">
                Generate Itinerary
              </button>
            </div>
          )}
        </div>

        <div className="hidden lg:block space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border sticky top-6">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" /> Versioning + Memory
            </h3>

            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-accent/5 border border-accent/10">
                <p className="text-xs text-muted-foreground">
                  This saved itinerary now uses the backend trip entity as source of truth.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-sage-light border border-sage/10">
                <p className="text-xs text-muted-foreground">
                  <strong>Current version:</strong>{' '}
                  {currentVersion ? `v${currentVersion.version_number}` : `v${trip.current_version_number}`}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  <strong>Branch:</strong> {trip.history_branch_label || 'main'}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-ocean-light border border-ocean/10">
                <p className="text-xs text-muted-foreground">
                  <strong>Signals:</strong> {signals.length} structured actions stored
                </p>
              </div>

              <div className="p-3 rounded-xl bg-secondary border border-border">
                <p className="text-xs text-muted-foreground">
                  <strong>Saved places:</strong> {savedPlaces.length}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  <strong>Skipped recommendations:</strong> {skippedRecommendations.length}
                </p>
              </div>
            </div>

            {versions.length > 0 ? (
              <div className="mt-5">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Version History
                </div>
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {versions.map((version) => (
                    <div
                      key={version.version_id}
                      className="rounded-xl border border-border bg-background px-3 py-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="text-sm font-medium text-foreground">
                            v{version.version_number}
                            {version.is_current ? ' · current' : ''}
                          </div>
                          <div className="text-[11px] text-muted-foreground mt-1">
                            {version.snapshot_reason}
                          </div>
                          <div className="text-[11px] text-muted-foreground mt-1">
                            {version.branch_label || 'main'}
                            {version.parent_version_number
                              ? ` · parent v${version.parent_version_number}`
                              : ''}
                          </div>
                        </div>

                        {!version.is_current ? (
                          <button
                            onClick={() => handleRestoreVersion(version.version_id)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-border text-[11px] font-medium hover:bg-secondary transition-colors"
                          >
                            <RotateCcw className="w-3 h-3" />
                            Restore
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {savedPlaces.length > 0 ? (
              <div className="mt-4">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Selected Places
                </div>
                <div className="space-y-2">
                  {savedPlaces.slice(0, 5).map((place) => (
                    <div key={place.signal_id} className="text-xs text-muted-foreground">
                      {place.name}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {skippedRecommendations.length > 0 ? (
              <div className="mt-4">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Skipped Signals
                </div>
                <div className="space-y-2">
                  {skippedRecommendations.slice(0, 5).map((place) => (
                    <div key={place.signal_id} className="text-xs text-muted-foreground">
                      {place.name}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}