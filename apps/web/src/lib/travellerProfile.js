const TRAVELLER_ID_KEY = 'wayfarer_traveller_id';
const TRAVELLER_PERSONA_KEY = 'wayfarer_persona';
const PERSONA_UPDATED_EVENT = 'wayfarer-persona-updated';

function emitPersonaUpdated() {
  window.dispatchEvent(new CustomEvent(PERSONA_UPDATED_EVENT));
}

export function getOrCreateTravellerId() {
  const existing = window.localStorage.getItem(TRAVELLER_ID_KEY);
  if (existing) return existing;

  const generated = `traveller_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(TRAVELLER_ID_KEY, generated);
  return generated;
}

export function getTravellerId() {
  return window.localStorage.getItem(TRAVELLER_ID_KEY);
}

export function getPersonaUpdatedEventName() {
  return PERSONA_UPDATED_EVENT;
}

function normalizePersona(persona) {
  if (!persona || typeof persona !== 'object') return null;

  return {
    traveller_id: persona.traveller_id || null,
    archetype: persona.archetype || 'comfort-seeking explorer',
    summary: persona.summary || '',
    signals: {
      travel_style: persona?.signals?.travel_style || 'midrange',
      pace_preference: persona?.signals?.pace_preference || 'balanced',
      group_type: persona?.signals?.group_type || 'solo',
      interests: Array.isArray(persona?.signals?.interests) ? persona.signals.interests : [],
      memory_events_used:
        typeof persona?.signals?.memory_events_used === 'number'
          ? persona.signals.memory_events_used
          : 0,
      updated_from_memory: Boolean(persona?.signals?.updated_from_memory),
    },
    saved_at: new Date().toISOString(),
  };
}

export function saveTravellerPersona(persona) {
  const normalized = normalizePersona(persona);
  if (!normalized) return;

  window.localStorage.setItem(TRAVELLER_PERSONA_KEY, JSON.stringify(normalized));
  emitPersonaUpdated();
}

export function getTravellerPersona() {
  const raw = window.localStorage.getItem(TRAVELLER_PERSONA_KEY);
  if (!raw) return null;

  try {
    return normalizePersona(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function clearTravellerPersona() {
  window.localStorage.removeItem(TRAVELLER_PERSONA_KEY);
  emitPersonaUpdated();
}

export function replaceTravellerPersona(persona) {
  const normalized = normalizePersona(persona);
  if (!normalized) return;

  window.localStorage.setItem(TRAVELLER_PERSONA_KEY, JSON.stringify(normalized));
  emitPersonaUpdated();
}