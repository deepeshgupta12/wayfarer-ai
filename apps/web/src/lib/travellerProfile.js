const TRAVELLER_ID_KEY = 'wayfarer_traveller_id';
const TRAVELLER_PERSONA_KEY = 'wayfarer_persona';

export function getOrCreateTravellerId() {
  const existing = window.localStorage.getItem(TRAVELLER_ID_KEY);
  if (existing) return existing;

  const generated = `traveller_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  window.localStorage.setItem(TRAVELLER_ID_KEY, generated);
  return generated;
}

export function saveTravellerPersona(persona) {
  window.localStorage.setItem(TRAVELLER_PERSONA_KEY, JSON.stringify(persona));
}

export function getTravellerPersona() {
  const raw = window.localStorage.getItem(TRAVELLER_PERSONA_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}