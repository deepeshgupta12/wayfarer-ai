const SAVED_TRIPS_CACHE_KEY = 'wayfarer_backend_saved_trips_cache_v2_5';
const SAVED_TRIP_DETAIL_CACHE_KEY = 'wayfarer_backend_saved_trip_detail_cache_v2_5';
const TRIP_PLAN_CACHE_KEY = 'wayfarer_backend_trip_plan_cache_v2_5';

function isBrowser() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function readJson(key, fallbackValue) {
  if (!isBrowser()) return fallbackValue;

  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallbackValue;

    const parsed = JSON.parse(raw);
    return parsed ?? fallbackValue;
  } catch {
    return fallbackValue;
  }
}

function writeJson(key, value) {
  if (!isBrowser()) return;

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore cache-only failures
  }
}

function mergeUniqueById(items, idField) {
  const map = new Map();

  for (const item of items || []) {
    const id = item?.[idField];
    if (!id) continue;
    map.set(id, item);
  }

  return Array.from(map.values());
}

export function getCachedSavedTrips(travellerId) {
  const cache = readJson(SAVED_TRIPS_CACHE_KEY, {});
  return Array.isArray(cache?.[travellerId]) ? cache[travellerId] : [];
}

export function cacheSavedTrips(travellerId, trips) {
  const cache = readJson(SAVED_TRIPS_CACHE_KEY, {});
  cache[travellerId] = Array.isArray(trips) ? trips : [];
  writeJson(SAVED_TRIPS_CACHE_KEY, cache);
}

export function getCachedSavedTrip(tripId) {
  const cache = readJson(SAVED_TRIP_DETAIL_CACHE_KEY, {});
  return cache?.[tripId] || null;
}

export function cacheSavedTrip(trip) {
  if (!trip?.trip_id) return;

  const detailCache = readJson(SAVED_TRIP_DETAIL_CACHE_KEY, {});
  detailCache[trip.trip_id] = trip;
  writeJson(SAVED_TRIP_DETAIL_CACHE_KEY, detailCache);

  if (trip.traveller_id) {
    const listCache = readJson(SAVED_TRIPS_CACHE_KEY, {});
    const existing = Array.isArray(listCache?.[trip.traveller_id]) ? listCache[trip.traveller_id] : [];
    const merged = mergeUniqueById([trip, ...existing], 'trip_id').sort((a, b) => {
      const aTime = new Date(a?.updated_at || a?.created_at || 0).getTime();
      const bTime = new Date(b?.updated_at || b?.created_at || 0).getTime();
      return bTime - aTime;
    });
    listCache[trip.traveller_id] = merged;
    writeJson(SAVED_TRIPS_CACHE_KEY, listCache);
  }
}

export function getCachedTripPlan(planningSessionId) {
  const cache = readJson(TRIP_PLAN_CACHE_KEY, {});
  return cache?.[planningSessionId] || null;
}

export function cacheTripPlan(plan) {
  if (!plan?.planning_session_id) return;

  const cache = readJson(TRIP_PLAN_CACHE_KEY, {});
  cache[plan.planning_session_id] = plan;
  writeJson(TRIP_PLAN_CACHE_KEY, cache);
}

export function clearCachedSavedTrip(tripId) {
  const detailCache = readJson(SAVED_TRIP_DETAIL_CACHE_KEY, {});
  if (!detailCache?.[tripId]) return;

  delete detailCache[tripId];
  writeJson(SAVED_TRIP_DETAIL_CACHE_KEY, detailCache);
}