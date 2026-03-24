const TRAVELLER_ID_KEY = 'wayfarer_traveller_id';
const TRAVELLER_PERSONA_KEY = 'wayfarer_persona';

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
    },
    saved_at: new Date().toISOString(),
  };
}

export function saveTravellerPersona(persona) {
  const normalized = normalizePersona(persona);
  if (!normalized) return;

  window.localStorage.setItem(TRAVELLER_PERSONA_KEY, JSON.stringify(normalized));
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
}

export function replaceTravellerPersona(persona) {
  clearTravellerPersona();
  saveTravellerPersona(persona);
}