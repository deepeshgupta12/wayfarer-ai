const TRIPS_STORAGE_KEY = 'wayfarer_saved_trips_v1';

function isBrowser() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function safeReadTrips() {
  if (!isBrowser()) return [];

  try {
    const raw = window.localStorage.getItem(TRIPS_STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function safeWriteTrips(trips) {
  if (!isBrowser()) return;
  window.localStorage.setItem(TRIPS_STORAGE_KEY, JSON.stringify(trips));
}

function createTripId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `trip_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function listStoredTrips() {
  return safeReadTrips()
    .slice()
    .sort((a, b) => {
      const aTime = new Date(a.created_date || 0).getTime();
      const bTime = new Date(b.created_date || 0).getTime();
      return bTime - aTime;
    });
}

export function getStoredTripById(tripId) {
  if (!tripId) return null;
  return listStoredTrips().find((trip) => trip.id === tripId) || null;
}

export function saveStoredTrip(payload) {
  const trips = safeReadTrips();
  const now = new Date().toISOString();

  const trip = {
    id: createTripId(),
    title: payload.title,
    destination: payload.destination,
    start_date: payload.start_date || null,
    end_date: payload.end_date || null,
    companions: payload.companions || null,
    status: payload.status || 'planning',
    itinerary: Array.isArray(payload.itinerary) ? payload.itinerary : [],
    itinerary_skeleton: Array.isArray(payload.itinerary_skeleton) ? payload.itinerary_skeleton : [],
    planning_session_id: payload.planning_session_id || null,
    traveller_id: payload.traveller_id || null,
    source_surface: payload.source_surface || 'planner_modal',
    created_date: now,
    updated_date: now,
  };

  trips.push(trip);
  safeWriteTrips(trips);

  return trip;
}

export function updateStoredTrip(tripId, updates) {
  const trips = safeReadTrips();
  const index = trips.findIndex((trip) => trip.id === tripId);

  if (index === -1) {
    return null;
  }

  const updatedTrip = {
    ...trips[index],
    ...updates,
    updated_date: new Date().toISOString(),
  };

  trips[index] = updatedTrip;
  safeWriteTrips(trips);

  return updatedTrip;
}