const TRIPS_STORAGE_KEY = 'wayfarer_saved_trips_v2';

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

function createVersionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `version_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeArray(value) {
  return Array.isArray(value) ? value : [];
}

function buildVersionSnapshot(trip, reason = 'manual_snapshot') {
  const now = new Date().toISOString();
  const currentVersions = normalizeArray(trip.itinerary_versions);

  return {
    version_id: createVersionId(),
    version_number: currentVersions.length + 1,
    created_at: now,
    reason,
    itinerary: normalizeArray(trip.itinerary),
    itinerary_skeleton: normalizeArray(trip.itinerary_skeleton),
    planning_session_id: trip.planning_session_id || null,
    selected_places: normalizeArray(trip.selected_places),
    skipped_recommendations: normalizeArray(trip.skipped_recommendations),
  };
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

  const baseTrip = {
    id: createTripId(),
    title: payload.title,
    destination: payload.destination,
    start_date: payload.start_date || null,
    end_date: payload.end_date || null,
    companions: payload.companions || null,
    status: payload.status || 'planning',
    itinerary: normalizeArray(payload.itinerary),
    itinerary_skeleton: normalizeArray(payload.itinerary_skeleton),
    planning_session_id: payload.planning_session_id || null,
    traveller_id: payload.traveller_id || null,
    source_surface: payload.source_surface || 'planner_modal',
    selected_places: normalizeArray(payload.selected_places),
    skipped_recommendations: normalizeArray(payload.skipped_recommendations),
    itinerary_versions: [],
    created_date: now,
    updated_date: now,
  };

  const initialVersion = buildVersionSnapshot(baseTrip, 'initial_save');
  const trip = {
    ...baseTrip,
    itinerary_versions: [initialVersion],
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

export function appendTripVersion(tripId, reason = 'manual_snapshot') {
  const trips = safeReadTrips();
  const index = trips.findIndex((trip) => trip.id === tripId);

  if (index === -1) {
    return null;
  }

  const currentTrip = trips[index];
  const nextVersion = buildVersionSnapshot(currentTrip, reason);

  const updatedTrip = {
    ...currentTrip,
    itinerary_versions: [...normalizeArray(currentTrip.itinerary_versions), nextVersion],
    updated_date: new Date().toISOString(),
  };

  trips[index] = updatedTrip;
  safeWriteTrips(trips);

  return updatedTrip;
}

export function recordSelectedPlace(tripId, place) {
  const trips = safeReadTrips();
  const index = trips.findIndex((trip) => trip.id === tripId);

  if (index === -1) {
    return null;
  }

  const trip = trips[index];
  const selectedPlaces = normalizeArray(trip.selected_places);
  const alreadyExists = selectedPlaces.some(
    (item) => item.location_id && item.location_id === place.location_id
  );

  if (alreadyExists) {
    return trip;
  }

  const updatedTrip = {
    ...trip,
    selected_places: [
      ...selectedPlaces,
      {
        ...place,
        saved_at: new Date().toISOString(),
      },
    ],
    updated_date: new Date().toISOString(),
  };

  trips[index] = updatedTrip;
  safeWriteTrips(trips);

  return updatedTrip;
}

export function recordSkippedRecommendation(tripId, recommendation) {
  const trips = safeReadTrips();
  const index = trips.findIndex((trip) => trip.id === tripId);

  if (index === -1) {
    return null;
  }

  const trip = trips[index];
  const skippedRecommendations = normalizeArray(trip.skipped_recommendations);

  const updatedTrip = {
    ...trip,
    skipped_recommendations: [
      ...skippedRecommendations,
      {
        ...recommendation,
        skipped_at: new Date().toISOString(),
      },
    ],
    updated_date: new Date().toISOString(),
  };

  trips[index] = updatedTrip;
  safeWriteTrips(trips);

  return updatedTrip;
}