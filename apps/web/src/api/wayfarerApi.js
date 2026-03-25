const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function parseJsonResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    throw new Error('Expected JSON response from Wayfarer API.');
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

export async function initializeAndSavePersona(payload) {
  const response = await fetch(`${API_BASE_URL}/persona/initialize-and-save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function refreshTravellerPersonaFromMemory(travellerId) {
  const response = await fetch(
    `${API_BASE_URL}/persona/refresh-from-memory/${encodeURIComponent(travellerId)}`,
    {
      method: 'POST',
    }
  );

  return parseJsonResponse(response);
}

export async function searchDestinations(payload) {
  const response = await fetch(`${API_BASE_URL}/destinations/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function generateDestinationGuide(payload) {
  const response = await fetch(`${API_BASE_URL}/destinations/guide`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function compareDestinations(payload) {
  const response = await fetch(`${API_BASE_URL}/destinations/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function indexDestinationPlaces(payload) {
  const response = await fetch(`${API_BASE_URL}/destinations/places/index`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function getSimilarPlaces(payload) {
  const response = await fetch(`${API_BASE_URL}/destinations/places/similar`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function parseAndSaveTripBrief(payload) {
  const response = await fetch(`${API_BASE_URL}/trip-plans/parse-and-save`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
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
  const response = await fetch(
    `${API_BASE_URL}/trip-plans/${encodeURIComponent(planningSessionId)}/replace-slot`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    }
  );

  return parseJsonResponse(response);
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

export async function getTripPlan(planningSessionId) {
  const response = await fetch(
    `${API_BASE_URL}/trip-plans/${encodeURIComponent(planningSessionId)}`
  );

  return parseJsonResponse(response);
}

export async function createTravellerMemory(payload) {
  const response = await fetch(`${API_BASE_URL}/traveller-memory`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  return parseJsonResponse(response);
}

export async function getTravellerMemory(travellerId, limit = 20, filters = {}) {
  const params = new URLSearchParams({ limit: String(limit) });

  if (filters.event_type) {
    params.set('event_type', filters.event_type);
  }

  if (filters.planning_session_id) {
    params.set('planning_session_id', filters.planning_session_id);
  }

  const response = await fetch(
    `${API_BASE_URL}/traveller-memory/${encodeURIComponent(travellerId)}?${params.toString()}`
  );

  return parseJsonResponse(response);
}

export async function getBackendHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return parseJsonResponse(response);
}