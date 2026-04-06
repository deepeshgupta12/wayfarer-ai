import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Navigation,
  MapPin,
  Coffee,
  Utensils,
  TreePine,
  Gem,
  Zap,
  Users,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import PlaceCard from '../components/cards/PlaceCard';
import LoadingState from '../components/ui/LoadingState';
import {
  listSavedTrips,
  orchestrateLiveRuntime,
  refreshTravellerPersonaFromMemory,
  upsertLiveRuntimeContext,
  writeLiveRuntimeAction,
} from '@/api/wayfarerApi';
import { getOrCreateTravellerId, getTravellerPersona, replaceTravellerPersona } from '@/lib/travellerProfile';
import { cacheSavedTrip, cacheSavedTrips, getCachedSavedTrips } from '@/lib/tripStorage';

const quickModes = [
  {
    id: 'food',
    label: 'Food Now',
    icon: Utensils,
    emoji: '🍽️',
    intent_hint: 'food',
    slot_type: 'lunch',
    message: 'Show me something great nearby right now for lunch',
  },
  {
    id: 'coffee',
    label: 'Quick Coffee',
    icon: Coffee,
    emoji: '☕',
    intent_hint: 'coffee',
    slot_type: 'morning',
    message: 'Find a good coffee spot near me right now',
  },
  {
    id: 'walk',
    label: 'Relaxed Walk',
    icon: TreePine,
    emoji: '🚶',
    intent_hint: 'nature',
    slot_type: 'afternoon',
    message: 'Find something calm and walkable nearby right now',
  },
  {
    id: 'hidden',
    label: 'Something Underrated',
    icon: Gem,
    emoji: '💎',
    intent_hint: 'culture',
    slot_type: 'afternoon',
    message: 'What underrated place in this area fits my vibe?',
  },
  {
    id: 'quick',
    label: 'Quick Stop',
    icon: Zap,
    emoji: '⚡',
    intent_hint: 'quick',
    slot_type: 'afternoon',
    message: 'Find a quick stop near me right now',
  },
  {
    id: 'family',
    label: 'Family-Safe',
    icon: Users,
    emoji: '👨‍👩‍👧',
    intent_hint: 'family',
    slot_type: 'afternoon',
    message: 'Show me a family-friendly nearby option right now',
  },
];

function getActiveTrip(trips = []) {
  return trips.find((trip) => ['active', 'upcoming', 'planning'].includes(trip.status)) || trips[0] || null;
}

function getGeoLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported in this browser.'));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => resolve(position),
      (error) => reject(error),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
}

// Reverse geocode GPS coordinates to a city name using the free Nominatim API.
// Falls back to null on failure so callers can use the trip destination instead.
async function resolveGpsCity(lat, lon) {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
      { headers: { 'Accept-Language': 'en' } }
    );
    if (!response.ok) return null;
    const data = await response.json();
    const address = data?.address || {};
    // Prefer city, then town, then village, then county
    return address.city || address.town || address.village || address.county || null;
  } catch {
    return null;
  }
}

function buildContext(mode, position, trip, persona, resolvedCity = null) {
  const itineraryFirstDay = trip?.itinerary_skeleton?.[0];
  const firstSlot = itineraryFirstDay?.slots?.find((slot) => slot?.slot_type === mode.slot_type) || itineraryFirstDay?.slots?.[0];
  // Use GPS-resolved city when available so recommendations match the user's
  // physical location rather than the trip's stored destination.
  const currentCity = resolvedCity || trip?.destination || null;

  return {
    traveller_id: trip.traveller_id,
    trip_id: trip.trip_id,
    planning_session_id: trip.planning_session_id,
    source_surface: 'live_runtime',
    trip_status: 'active',
    intent_hint: mode.intent_hint,
    transport_mode: 'walk',
    available_minutes: 75,
    current_day_number: itineraryFirstDay?.day_number || 1,
    current_slot_type: firstSlot?.slot_type || mode.slot_type || 'afternoon',
    gps: {
      latitude: Number(position.coords.latitude.toFixed(6)),
      longitude: Number(position.coords.longitude.toFixed(6)),
      accuracy_meters: Math.round(position.coords.accuracy || 50),
    },
    local_time_iso: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    current_place_name: currentCity || 'Current location',
    current_city: currentCity,
    current_country: null,
    context_payload: {
      traveller_style: persona?.signals?.travel_style || 'midrange',
      traveller_interests: persona?.signals?.interests || [],
    },
  };
}

export default function Nearby() {
  const travellerId = getOrCreateTravellerId();
  const persona = getTravellerPersona();
  const [activeMode, setActiveMode] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [locationGranted, setLocationGranted] = useState(null);

  const { data: trips = [] } = useQuery({
    queryKey: ['nearby-saved-trips', travellerId],
    queryFn: async () => {
      const response = await listSavedTrips(travellerId, 50);
      cacheSavedTrips(travellerId, response.items || []);
      (response.items || []).forEach((trip) => cacheSavedTrip(trip));
      return response.items || [];
    },
    initialData: getCachedSavedTrips(travellerId),
  });

  const activeTrip = useMemo(() => getActiveTrip(trips), [trips]);

  const handleModeSelect = async (mode) => {
    if (!activeTrip?.trip_id) {
      setErrorMessage('Create or promote a saved trip first so Nearby can use your active trip context.');
      return;
    }

    setActiveMode(mode.id);
    setLoading(true);
    setErrorMessage('');

    try {
      const position = await getGeoLocation();
      setLocationGranted(true);

      // Resolve GPS to a city name so recommendations match the user's physical
      // location, not the trip's stored destination.
      const resolvedCity = await resolveGpsCity(
        position.coords.latitude,
        position.coords.longitude
      );

      const contextPayload = buildContext(mode, position, activeTrip, persona, resolvedCity);
      await upsertLiveRuntimeContext(contextPayload);

      const response = await orchestrateLiveRuntime({
        traveller_id: activeTrip.traveller_id,
        trip_id: activeTrip.trip_id,
        planning_session_id: activeTrip.planning_session_id,
        source_surface: 'live_runtime',
        message: mode.message,
      });

      setResult(response.run?.final_output || null);
    } catch (error) {
      setLocationGranted(false);
      setErrorMessage(error?.message || 'Unable to fetch nearby recommendations right now.');
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (actionType, place, payload = {}) => {
    if (!activeTrip?.trip_id || !place?.location_id) return;

    await writeLiveRuntimeAction({
      traveller_id: activeTrip.traveller_id,
      trip_id: activeTrip.trip_id,
      planning_session_id: activeTrip.planning_session_id,
      action_type: actionType,
      location_id: place.location_id,
      day_number: result?.current_day_number || 1,
      slot_type: activeMode === 'food' ? 'lunch' : activeMode === 'coffee' ? 'morning' : 'afternoon',
      source_surface: 'live_runtime',
      payload: {
        name: place.name,
        category: place.category,
        city: place.city,
        ...payload,
      },
    });

    // Fire-and-forget persona refresh so taste signals are captured in memory.
    refreshTravellerPersonaFromMemory(travellerId)
      .then((updated) => { if (updated) replaceTravellerPersona(updated); })
      .catch(() => {});
  };

  const recommendations = result?.recommendations || result?.alternatives || result?.gems || [];
  const walkingAlternatives = result?.walking_alternatives || [];
  const fallbacks = result?.fallbacks || [];
  const hasRenderableResults =
    recommendations.length > 0 || walkingAlternatives.length > 0 || fallbacks.length > 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent/20 to-sunset/20 flex items-center justify-center">
            <Navigation className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold">Nearby</h1>
            <p className="text-sm text-muted-foreground">Real live-runtime routing on top of your active saved trip</p>
          </div>
        </div>

        <div className="text-xs text-muted-foreground">
          Active trip: <span className="font-medium">{activeTrip?.title || 'No saved trip found'}</span>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-8">
        <h3 className="text-sm font-medium text-muted-foreground mb-3">What are you looking for?</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {quickModes.map((mode) => {
            const Icon = mode.icon;
            return (
              <motion.button
                key={mode.id}
                whileTap={{ scale: 0.97 }}
                onClick={() => handleModeSelect(mode)}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all ${
                  activeMode === mode.id ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/30 bg-card'
                }`}
              >
                <span className="text-2xl">{mode.emoji}</span>
                <div>
                  <div className="font-medium text-sm">{mode.label}</div>
                  <div className="text-[11px] text-muted-foreground mt-1 flex items-center gap-1">
                    <Icon className="w-3 h-3" />
                    {mode.intent_hint}
                  </div>
                </div>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {loading ? <LoadingState message="Finding the best spots nearby..." /> : null}

      {errorMessage ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive mb-6">
          {errorMessage}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-8">
          <div className="rounded-2xl border border-border bg-card p-4">
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="inline-flex items-center gap-2 font-medium">
                <Sparkles className="w-4 h-4 text-accent" />
                {result.title || 'Live recommendations'}
              </span>
              {typeof result.radius_used_meters === 'number' ? (
                <span className="text-muted-foreground">Radius used: {result.radius_used_meters}m</span>
              ) : null}
              {locationGranted === true ? (
                <span className="inline-flex items-center gap-1 text-muted-foreground"><MapPin className="w-3 h-3" /> GPS active</span>
              ) : null}
            </div>
            {result.message ? <p className="text-sm text-muted-foreground mt-2">{result.message}</p> : null}
          </div>

          {!hasRenderableResults ? (
            <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
              No live recommendations were returned for this mode right now. Try another mode, move a bit, or run the same request again.
            </div>
          ) : null}

          {recommendations.length ? (
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-accent" />
                <h3 className="font-semibold text-sm">Top recommendations</h3>
                <span className="text-xs text-muted-foreground">({recommendations.length})</span>
              </div>
              <div className="space-y-3">
                {recommendations.map((place, index) => (
                  <PlaceCard
                    key={place.location_id || index}
                    name={place.name}
                    category={place.category}
                    rating={place.rating}
                    description={place.why_recommended || place.why_hidden_gem || place.description}
                    distance={place.distance_meters ? `${place.distance_meters} m` : undefined}
                    reason={(place.fit_reasons || []).slice(0, 2).join(' • ') || place.gem_reason}
                    photos={place.photos || []}
                    tags={place.tags || place.fit_reasons || []}
                    isGem={Boolean(place.underrated_signal || activeMode === 'hidden')}
                    trailing={
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleAction(activeMode === 'hidden' ? 'gem_saved' : 'nearby_selected', place)}
                          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium bg-accent/10 text-accent hover:bg-accent/15"
                        >
                          <CheckCircle2 className="w-3 h-3" /> Save
                        </button>
                        <button
                          onClick={() => handleAction(activeMode === 'hidden' ? 'gem_skipped' : 'nearby_rejected', place)}
                          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium bg-secondary text-muted-foreground hover:text-foreground"
                        >
                          <XCircle className="w-3 h-3" /> Skip
                        </button>
                        <button
                          onClick={() => handleAction('place_closed', place, { reason: 'reported_from_nearby_ui' })}
                          className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium bg-destructive/10 text-destructive hover:bg-destructive/15"
                        >
                          <AlertTriangle className="w-3 h-3" /> Closed
                        </button>
                      </div>
                    }
                  />
                ))}
              </div>
            </section>
          ) : null}

          {walkingAlternatives.length ? (
            <section>
              <h3 className="font-semibold text-sm mb-3">Walking alternatives</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {walkingAlternatives.map((place) => (
                  <PlaceCard
                    key={place.location_id}
                    name={place.name}
                    category={place.category}
                    rating={place.rating}
                    description={place.why_recommended}
                    distance={place.distance_meters ? `${place.distance_meters} m` : undefined}
                    photos={place.photos || []}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {fallbacks.length ? (
            <section>
              <h3 className="font-semibold text-sm mb-3">Fallbacks</h3>
              <div className="grid gap-3 md:grid-cols-2">
                {fallbacks.map((place) => (
                  <PlaceCard
                    key={place.location_id}
                    name={place.name}
                    category={place.category}
                    rating={place.rating}
                    description={place.why_recommended}
                    photos={place.photos || []}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      ) : !activeMode && !loading ? (
        <div className="text-center py-16">
          <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 3, repeat: Infinity }} className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
            <MapPin className="w-7 h-7 text-muted-foreground" />
          </motion.div>
          <h3 className="font-semibold mb-2">Your live travel companion</h3>
          <p className="text-sm text-muted-foreground max-w-md mx-auto">
            Nearby now uses the real V3 live-runtime backend. Pick a mode and Wayfarer will upsert live context, route to the correct specialist agent, and return context-aware results.
          </p>
        </div>
      ) : null}
    </div>
  );
}
