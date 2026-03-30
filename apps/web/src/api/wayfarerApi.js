const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function parseJsonResponse(response) {
  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('application/json')) {
    const text = await response.text();
    throw new Error(text || 'Expected JSON response from Wayfarer API.');
  }

  const payload = await response.json();

  if (!response.ok) {
    const detail =
      typeof payload?.detail === 'string'
        ? payload.detail
        : payload?.message || 'Wayfarer API request failed.';
    throw new Error(detail);
  }

  return payload;
}

async function parseTextError(response) {
  const text = await response.text();
  throw new Error(text || 'Wayfarer API request failed.');
}

async function parseNdjsonStream(response, onEvent) {
  if (!response.ok) {
    await parseTextError(response);
  }

  if (!response.body) {
    throw new Error('Streaming response body is unavailable.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalPayload = null;

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const rawLine of lines) {
      const line = rawLine.trim();
      if (!line) continue;

      let parsed;
      try {
        parsed = JSON.parse(line);
      } catch {
        continue;
      }

      if (typeof onEvent === 'function') {
        onEvent(parsed);
      }

      if (parsed?.type === 'final' && parsed?.payload) {
        finalPayload = parsed.payload;
      } else if (parsed?.payload && !parsed?.type) {
        finalPayload = parsed.payload;
      } else if (parsed?.result) {
        finalPayload = parsed.result;
      }
    }
  }

  if (buffer.trim()) {
    try {
      const parsed = JSON.parse(buffer.trim());

      if (typeof onEvent === 'function') {
        onEvent(parsed);
      }

      if (parsed?.type === 'final' && parsed?.payload) {
        finalPayload = parsed.payload;
      } else if (parsed?.payload && !parsed?.type) {
        finalPayload = parsed.payload;
      } else if (parsed?.result) {
        finalPayload = parsed.result;
      }
    } catch {
      // ignore trailing partial line
    }
  }

  return finalPayload;
}

async function sendJson(path, payload, method = 'POST') {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });

  return parseJsonResponse(response);
}

async function sendGet(path) {
  const response = await fetch(`${API_BASE_URL}${path}`);
  return parseJsonResponse(response);
}

export async function initializeAndSavePersona(payload) {
  return sendJson('/persona/initialize-and-save', payload);
}

export async function refreshTravellerPersonaFromMemory(travellerId) {
  const response = await fetch(
    `${API_BASE_URL}/persona/refresh-from-memory/${encodeURIComponent(travellerId)}`,
    { method: 'POST' }
  );

  return parseJsonResponse(response);
}

export async function searchDestinations(payload) {
  return sendJson('/destinations/search', payload);
}

export async function generateDestinationGuide(payload) {
  return sendJson('/destinations/guide', payload);
}

export async function generateDestinationGuideStream(payload, options = {}) {
  const response = await fetch(`${API_BASE_URL}/destinations/guide/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseNdjsonStream(response, options.onEvent);
}

export async function compareDestinations(payload) {
  return sendJson('/destinations/compare', payload);
}

export async function indexDestinationPlaces(payload) {
  return sendJson('/destinations/places/index', payload);
}

export async function getSimilarPlaces(payload) {
  return sendJson('/destinations/places/similar', payload);
}

export async function discoverNearbyPlaces(payload) {
  return sendJson('/destinations/nearby', payload);
}

export async function discoverHiddenGems(payload) {
  return sendJson('/destinations/gems', payload);
}

export async function orchestrateAssistant(payload) {
  return sendJson('/assistant/orchestrate', payload);
}

export async function streamAssistantOrchestration(payload, options = {}) {
  const response = await fetch(`${API_BASE_URL}/assistant/orchestrate/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseNdjsonStream(response, options.onEvent);
}

export async function parseAndSaveTripBrief(payload) {
  return sendJson('/trip-plans/parse-and-save', payload);
}

export async function createTripPlanFromComparison(payload) {
  return sendJson('/trip-plans/from-comparison', payload);
}

export async function updateTripPlan(planningSessionId, payload) {
  const response = await fetch(
    `${API_BASE_URL}/trip-plans/${encodeURIComponent(planningSessionId)}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  );

  return parseJsonResponse(response);
}

export async function replaceTripPlanSlot(planningSessionId, payload) {
  return sendJson(`/trip-plans/${encodeURIComponent(planningSessionId)}/replace-slot`, payload);
}

export async function enrichTripPlan(planningSessionId) {
  const response = await fetch(
    `${API_BASE_URL}/trip-plans/${encodeURIComponent(planningSessionId)}/enrich`,
    {
      method: 'POST',
    }
  );

  return parseJsonResponse(response);
}

export async function streamTripPlanEnrichment(planningSessionId, options = {}) {
  const response = await fetch(
    `${API_BASE_URL}/trip-plans/${encodeURIComponent(planningSessionId)}/enrich/stream`,
    {
      method: 'POST',
    }
  );

  return parseNdjsonStream(response, options.onEvent);
}

export async function getTripPlan(planningSessionId) {
  return sendGet(`/trip-plans/${encodeURIComponent(planningSessionId)}`);
}

export async function promoteTripPlanToSavedTrip(planningSessionId, payload) {
  return sendJson(`/trips/from-plan/${encodeURIComponent(planningSessionId)}`, payload);
}

export async function listSavedTrips(travellerId, limit = 50) {
  const params = new URLSearchParams({
    traveller_id: travellerId,
    limit: String(limit),
  });

  return sendGet(`/trips?${params.toString()}`);
}

export async function getSavedTrip(tripId) {
  return sendGet(`/trips/${encodeURIComponent(tripId)}`);
}

export async function listTripVersions(tripId, limit = 50) {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  return sendGet(`/trips/${encodeURIComponent(tripId)}/versions?${params.toString()}`);
}

export async function createTripVersionSnapshot(tripId, payload) {
  return sendJson(`/trips/${encodeURIComponent(tripId)}/versions`, payload);
}

export async function getCurrentTripVersion(tripId) {
  return sendGet(`/trips/${encodeURIComponent(tripId)}/versions/current`);
}

export async function restoreTripVersion(tripId, versionId, payload) {
  return sendJson(
    `/trips/${encodeURIComponent(tripId)}/versions/${encodeURIComponent(versionId)}/restore`,
    payload
  );
}

export async function listTripSignals(tripId, limit = 100) {
  const params = new URLSearchParams({
    limit: String(limit),
  });

  return sendGet(`/trips/${encodeURIComponent(tripId)}/signals?${params.toString()}`);
}

export async function createTripSignal(tripId, payload) {
  return sendJson(`/trips/${encodeURIComponent(tripId)}/signals`, payload);
}

export async function createTravellerMemory(payload) {
  return sendJson('/traveller-memory', payload);
}

export async function getTravellerMemory(travellerId, limit = 20, filters = {}) {
  const params = new URLSearchParams({ limit: String(limit) });

  if (filters.event_type) {
    params.set('event_type', filters.event_type);
  }

  if (filters.planning_session_id) {
    params.set('planning_session_id', filters.planning_session_id);
  }

  return sendGet(
    `/traveller-memory/${encodeURIComponent(travellerId)}?${params.toString()}`
  );
}

export async function upsertLiveRuntimeContext(payload) {
  return sendJson('/live-runtime/context', payload);
}

export async function getLiveRuntimeContext(tripId) {
  return sendGet(`/live-runtime/context/${encodeURIComponent(tripId)}`);
}

export async function writeLiveRuntimeAction(payload) {
  return sendJson('/live-runtime/actions', payload);
}

export async function orchestrateLiveRuntime(payload) {
  return sendJson('/live-runtime/orchestrate', payload);
}

export async function streamLiveRuntime(payload, options = {}) {
  const response = await fetch(`${API_BASE_URL}/live-runtime/orchestrate/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseNdjsonStream(response, options.onEvent);
}

export async function inspectProactiveAlerts(payload) {
  return sendJson('/live-runtime/monitor/inspect', payload);
}

export async function listProactiveAlerts(tripId, { status, limit = 100 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set('status', status);
  return sendGet(`/live-runtime/alerts/${encodeURIComponent(tripId)}?${params.toString()}`);
}

export async function resolveProactiveAlert(alertId, payload) {
  return sendJson(`/live-runtime/alerts/${encodeURIComponent(alertId)}/resolve`, payload);
}

export async function getLiveRuntimeRun(runId) {
  return sendGet(`/live-runtime/runs/${encodeURIComponent(runId)}`);
}

export async function getLiveRuntimeEvents(runId, limit = 200) {
  return sendGet(`/live-runtime/runs/${encodeURIComponent(runId)}/events?limit=${limit}`);
}

export async function getBackendHealth() {
  return sendGet('/health');
}
