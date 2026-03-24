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

export async function streamDestinationGuide(payload, handlers = {}) {
  const response = await fetch(`${API_BASE_URL}/destinations/guide/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = 'Wayfarer API request failed.';
    try {
      const payload = await response.json();
      message =
        typeof payload?.detail === 'string'
          ? payload.detail
          : payload?.message || message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  if (!response.body) {
    throw new Error('Streaming response body is unavailable.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const event = JSON.parse(trimmed);

      if (event.type === 'meta' && handlers.onMeta) {
        handlers.onMeta(event);
      }

      if (event.type === 'content_delta' && handlers.onContentDelta) {
        handlers.onContentDelta(event.content);
      }

      if (event.type === 'final' && handlers.onFinal) {
        handlers.onFinal(event.payload);
      }
    }
  }

  if (buffer.trim()) {
    const event = JSON.parse(buffer.trim());
    if (event.type === 'final' && handlers.onFinal) {
      handlers.onFinal(event.payload);
    }
  }
}

export async function getBackendHealth() {
  const response = await fetch(`${API_BASE_URL}/health`);
  return parseJsonResponse(response);
}