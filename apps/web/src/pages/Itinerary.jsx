import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Calendar,
  MapPin,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  GitBranch,
  Bell,
  RefreshCw,
  Heart,
  Layers,
  Route,
  Camera,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import LoadingState from '../components/ui/LoadingState';
import ActivityCard from '../components/cards/ActivityCard';
import {
  createTripSignal,
  getCurrentTripVersion,
  getSavedTrip,
  inspectProactiveAlerts,
  listProactiveAlerts,
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

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function findCandidateByLocation(trip, locationId) {
  if (!locationId) return null;
  return safeArray(trip?.candidate_places).find((item) => item.location_id === locationId) || null;
}

function buildSlotImage(trip, day, slot) {
  const slotPhoto = safeArray(slot?.assigned_place_photos)[0]?.image_url;
  if (slotPhoto) return slotPhoto;

  const candidate = findCandidateByLocation(trip, slot?.assigned_location_id);
  const candidatePhoto = safeArray(candidate?.photos)[0]?.image_url;
  if (candidatePhoto) return candidatePhoto;

  const sameDaySlotPhoto = safeArray(day?.slots)
    .flatMap((item) => safeArray(item?.assigned_place_photos))
    .find((photo) => photo?.image_url)?.image_url;
  if (sameDaySlotPhoto) return sameDaySlotPhoto;

  const anyCandidatePhoto = safeArray(trip?.candidate_places)
    .flatMap((item) => safeArray(item?.photos))
    .find((photo) => photo?.image_url)?.image_url;
  if (anyCandidatePhoto) return anyCandidatePhoto;

  return null;
}

function normalizeDayActivities(trip, day) {
  if (!Array.isArray(day?.slots) || !day.slots.length) return [];

  return day.slots.map((slot) => {
    const candidate = findCandidateByLocation(trip, slot?.assigned_location_id);

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
      reason: slot.rationale,
      fallbackNames: slot.fallback_candidate_names || [],
      alternatives: slot.alternatives || [],
      assignedLocationId: slot.assigned_location_id || null,
      slotType: slot.slot_type,
      continuityNote: slot.continuity_note || null,
      movementNote: slot.movement_note || null,
      dayNumber: day.day_number,
      image: buildSlotImage(trip, day, slot),
      replacementStatus: candidate?.review_authenticity || null,
    };
  });
}

function deriveCanonicalItinerary(trip) {
  if (Array.isArray(trip?.itinerary_skeleton) && trip.itinerary_skeleton.length > 0) {
    return trip.itinerary_skeleton;
  }
  if (Array.isArray(trip?.itinerary) && trip.itinerary.length > 0) {
    return trip.itinerary;
  }
  return [];
}

function buildSavedPlacesFromSignals(signals) {
  const selectedSignals = safeArray(signals).filter((signal) => signal.signal_type === 'selected_place');
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

function buildSignalStats(trip, signals) {
  const selectedSignals = safeArray(signals).filter((item) => item.signal_type === 'selected_place').length;
  const replacedSignals = safeArray(signals).filter((item) => item.signal_type === 'replaced_slot').length;
  const skippedSignals = safeArray(signals).filter((item) => item.signal_type === 'skipped_recommendation').length;
  const photoCount =
    safeArray(trip?.candidate_places).reduce((sum, item) => sum + safeArray(item?.photos).length, 0) || 0;

  return [
    { label: 'Versions', value: trip?.current_version_number || 0, icon: GitBranch },
    { label: 'Saved places', value: selectedSignals || trip?.selected_places_count || 0, icon: Heart },
    { label: 'Route changes', value: replacedSignals || trip?.replaced_slots_count || 0, icon: Route },
    { label: 'Photos', value: photoCount, icon: Camera },
    { label: 'Skipped', value: skippedSignals || trip?.skipped_recommendations_count || 0, icon: Layers },
  ];
}

export default function Itinerary() {
  const [expandedDay, setExpandedDay] = useState(0);
  const [alertsRunning, setAlertsRunning] = useState(false);
  const [searchParams] = useSearchParams();
  const travellerId = getOrCreateTravellerId();
  const tripId = searchParams.get('trip');

  const { data: activeTripId, isLoading: resolvingTripId } = useQuery({
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

  const { data: trip, isLoading: tripLoading, refetch: refetchTrip } = useQuery({
    queryKey: ['saved-trip-detail', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await getSavedTrip(activeTripId);
      cacheSavedTrip(response);
      return response;
    },
    initialData: activeTripId ? getCachedSavedTrip(activeTripId) : null,
  });

  const { data: versions = [], refetch: refetchVersions } = useQuery({
    queryKey: ['trip-versions', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await listTripVersions(activeTripId, 100);
      return response.items || [];
    },
    initialData: [],
  });

  const { data: currentVersion = null, refetch: refetchCurrentVersion } = useQuery({
    queryKey: ['trip-current-version', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => getCurrentTripVersion(activeTripId),
    initialData: null,
  });

  const { data: signals = [], refetch: refetchSignals } = useQuery({
    queryKey: ['trip-signals', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => {
      const response = await listTripSignals(activeTripId, 200);
      return response.items || [];
    },
    initialData: [],
  });

  const { data: proactiveAlertResponse, refetch: refetchAlerts } = useQuery({
    queryKey: ['trip-proactive-alerts', activeTripId],
    enabled: Boolean(activeTripId),
    queryFn: async () => listProactiveAlerts(activeTripId, { limit: 100 }),
    initialData: { items: [] },
  });

  const itinerary = useMemo(() => (trip ? deriveCanonicalItinerary(trip) : []), [trip]);
  const savedPlaces = useMemo(() => buildSavedPlacesFromSignals(signals), [signals]);
  const signalStats = useMemo(() => buildSignalStats(trip, signals), [trip, signals]);
  const openAlerts = proactiveAlertResponse?.items?.filter((item) => item.status === 'generated') || [];

  const runInspection = async () => {
    if (!trip?.trip_id) return;
    setAlertsRunning(true);
    try {
      await inspectProactiveAlerts({
        traveller_id: trip.traveller_id,
        trip_id: trip.trip_id,
        planning_session_id: trip.planning_session_id,
        source_surface: 'itinerary_page',
        current_day_only: false,
        max_days_to_check: 4,
      });
      await refetchAlerts();
    } finally {
      setAlertsRunning(false);
    }
  };

  const saveSlot = async (activity) => {
    if (!trip?.trip_id || !activity?.assignedLocationId) return;

    await createTripSignal(trip.trip_id, {
      signal_type: 'selected_place',
      location_id: activity.assignedLocationId,
      day_number: activity.dayNumber,
      slot_type: activity.slotType,
      payload: {
        name: activity.name,
        city: trip.destination,
        category: activity.type,
      },
    });

    await refetchSignals();
  };

  const restoreVersion = async (versionId) => {
    if (!trip?.trip_id) return;

    await restoreTripVersion(trip.trip_id, versionId, {
      snapshot_reason: 'restore_selected_version',
      branch_label: 'main',
    });

    await Promise.all([refetchTrip(), refetchVersions(), refetchCurrentVersion()]);
  };

  if (resolvingTripId || tripLoading) {
    return <LoadingState message="Loading itinerary..." />;
  }

  if (!trip) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
          No saved trip found. Create or promote a trip first.
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            to="/trips"
            className="mb-3 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Trips
          </Link>
          <h1 className="font-serif text-3xl font-bold sm:text-4xl">{trip.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-4 w-4" />
            {trip.destination || 'Destination pending'}
            {trip.start_date ? (
              <>
                <span>•</span>
                <Calendar className="h-4 w-4" />
                {trip.start_date}
                {trip.end_date ? ` → ${trip.end_date}` : ''}
              </>
            ) : null}
            {currentVersion ? (
              <>
                <span>•</span>
                <GitBranch className="h-4 w-4" />
                Version {currentVersion.version_number}
              </>
            ) : null}
          </div>
        </div>

        <button
          onClick={runInspection}
          disabled={alertsRunning}
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium hover:border-accent/30 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${alertsRunning ? 'animate-spin' : ''}`} />
          Run proactive check
        </button>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {signalStats.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="rounded-2xl border border-border bg-card p-4">
              <div className="flex items-center justify-between">
                <div className="text-xs text-muted-foreground">{item.label}</div>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="mt-2 text-2xl font-semibold">{item.value}</div>
            </div>
          );
        })}
      </div>

      {openAlerts.length > 0 ? (
        <div className="mb-6 rounded-2xl border border-accent/20 bg-accent/5 p-4">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Bell className="h-4 w-4 text-accent" />
            {openAlerts.length} active alert{openAlerts.length === 1 ? '' : 's'}
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {openAlerts.slice(0, 4).map((alert) => (
              <div key={alert.alert_id} className="rounded-xl border border-border bg-card p-3">
                <div className="text-sm font-medium">{alert.title}</div>
                <div className="mt-1 text-xs text-muted-foreground">{alert.message}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          {itinerary.map((day, index) => {
            const activities = normalizeDayActivities(trip, day);
            const isOpen = expandedDay === index;

            return (
              <motion.div
                key={day.day_number || index}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="overflow-hidden rounded-2xl border border-border bg-card"
              >
                <button
                  onClick={() => setExpandedDay(isOpen ? -1 : index)}
                  className="w-full p-4 text-left"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-muted-foreground">
                        Day {day.day_number}
                      </div>
                      <div className="mt-1 font-semibold">{day.title}</div>
                      <div className="mt-1 text-sm text-muted-foreground">{day.summary}</div>
                    </div>
                    {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </div>

                  {day.continuity_strategy ? (
                    <div className="mt-3 inline-flex rounded-full bg-secondary px-3 py-1 text-[11px] text-muted-foreground">
                      {day.continuity_strategy}
                    </div>
                  ) : null}
                </button>

                {isOpen ? (
                  <div className="border-t border-border px-4 pb-4">
                    {activities.map((activity, activityIndex) => (
                      <ActivityCard
                        key={`${day.day_number}-${activity.slotType}-${activityIndex}`}
                        time={activity.time}
                        name={activity.name}
                        description={activity.description}
                        type={activity.type}
                        location={activity.location}
                        reason={activity.reason}
                        image={activity.image}
                        index={activityIndex}
                        fallbackNames={activity.fallbackNames}
                        replacementStatus={activity.replacementStatus}
                        slotType={activity.slotType}
                        continuityNote={activity.continuityNote}
                        movementNote={activity.movementNote}
                        onSwap={() => saveSlot(activity)}
                        onExpand={() => {}}
                      />
                    ))}
                  </div>
                ) : null}
              </motion.div>
            );
          })}
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <GitBranch className="h-4 w-4 text-accent" />
              Versions
            </div>

            <div className="space-y-2">
              {versions.slice(0, 8).map((version) => (
                <div key={version.version_id} className="rounded-xl border border-border p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium">Version {version.version_number}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{version.snapshot_reason}</div>
                    </div>

                    {!version.is_current ? (
                      <button
                        onClick={() => restoreVersion(version.version_id)}
                        className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                      >
                        <RotateCcw className="h-3 w-3" /> Restore
                      </button>
                    ) : (
                      <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                        Current
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <Heart className="h-4 w-4 text-accent" />
              Saved from itinerary
            </div>

            <div className="space-y-2">
              {savedPlaces.length ? (
                savedPlaces.slice(0, 8).map((item) => (
                  <div key={item.signal_id} className="rounded-xl border border-border p-3">
                    <div className="text-sm font-medium">{item.name}</div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {item.category || 'place'}
                      {item.city ? ` • ${item.city}` : ''}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-muted-foreground">No selected-place signals yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}