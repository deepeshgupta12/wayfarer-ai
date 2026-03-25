import { useRef, useState, useEffect } from 'react';
// @ts-ignore
import { motion } from 'framer-motion';
// @ts-ignore
import { Send, Sparkles, Plus } from 'lucide-react';
import LoadingState from '../components/ui/LoadingState';
import PlaceCard from '../components/cards/PlaceCard';
import {
  createTravellerMemory,
  enrichTripPlan,
  generateDestinationGuide,
  parseAndSaveTripBrief,
  refreshTravellerPersonaFromMemory,
  updateTripPlan,
} from '@/api/wayfarerApi';
import {
  getOrCreateTravellerId,
  getTravellerPersona,
  getPersonaUpdatedEventName,
  replaceTravellerPersona,
} from '@/lib/travellerProfile';

const suggestedChips = [
  '3 days in Kyoto for food and culture',
  'Couple-friendly Lisbon guide',
  'I have 4 days in Tokyo, mid-budget, love food and calm neighborhoods',
  'Compare Prague and Budapest for a couple trip',
  'Replace Day 2 with something less hectic',
];

const KNOWN_DESTINATIONS = ['Tokyo', 'Kyoto', 'Lisbon', 'Prague', 'Budapest'];

function deriveGuidePayload(rawInput, persona) {
  const normalized = rawInput.toLowerCase();

  let destination = 'Kyoto';
  if (normalized.includes('lisbon')) destination = 'Lisbon';
  else if (normalized.includes('prague')) destination = 'Prague';
  else if (normalized.includes('kyoto')) destination = 'Kyoto';
  else if (normalized.includes('tokyo')) destination = 'Tokyo';
  else if (normalized.includes('budapest')) destination = 'Budapest';

  const durationMatch = normalized.match(/(\d+)\s*days?/);
  const durationDays = durationMatch ? Number(durationMatch[1]) : 3;

  return {
    destination,
    duration_days: durationDays,
    traveller_type: persona?.signals?.group_type || 'solo',
    interests: persona?.signals?.interests || ['culture'],
    pace_preference: persona?.signals?.pace_preference || 'balanced',
    budget: persona?.signals?.travel_style || 'midrange',
  };
}

function isPlanningBrief(rawInput) {
  const lowered = rawInput.toLowerCase().trim();

  const explicitPlanningStarts = [
    'i have ',
    'plan ',
    'build ',
    'create ',
    'make ',
    'help me plan',
    'itinerary',
    'replace day',
    'replan',
    'compare ',
  ];

  if (explicitPlanningStarts.some((term) => lowered.startsWith(term) || lowered.includes(term))) {
    return true;
  }

  const strongPlanningPatterns = [
    /i have\s+\d+\s*days?\s+in\s+/,
    /plan\s+(me\s+)?a\s+trip/,
    /build\s+(me\s+)?an?\s+itinerary/,
    /create\s+(me\s+)?an?\s+itinerary/,
    /replace\s+day\s+\d+/,
    /compare\s+[a-z\s]+\s+and\s+[a-z\s]+/,
  ];

  if (strongPlanningPatterns.some((pattern) => pattern.test(lowered))) {
    return true;
  }

  return false;
}

function getLatestPlanningSessionMessage(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.planningSession?.planning_session_id) {
      return message;
    }
  }

  return null;
}

function isRefinementFollowUp(rawInput, currentPlanningSession) {
  if (!currentPlanningSession?.planning_session_id) return false;

  const lowered = rawInput.toLowerCase().trim();

  const followupTerms = [
    'make it more relaxed',
    'make it relaxed',
    'more relaxed',
    'swap candidates',
    'make it food + culture',
    'make it food and culture',
    'food + culture',
    'food and culture',
    'change to couple trip',
    'change to solo trip',
    'change to family trip',
    'change to friends trip',
    'couple trip',
    'solo trip',
    'family trip',
    'friends trip',
    'change to',
    'refine pace',
  ];

  if (followupTerms.some((term) => lowered.includes(term))) {
    return true;
  }

  if (/(\d+)\s*days?/.test(lowered)) return true;
  if (KNOWN_DESTINATIONS.some((destination) => lowered.includes(destination.toLowerCase()))) return true;
  if (
    ['budget', 'mid-budget', 'mid budget', 'midrange', 'luxury', 'balanced', 'fast'].some((term) =>
      lowered.includes(term)
    )
  ) {
    return true;
  }

  return false;
}

function buildTripPlanUpdatePayload(rawInput) {
  const lowered = rawInput.toLowerCase().trim();
  const updatePayload = {};

  const destination = KNOWN_DESTINATIONS.find((item) => lowered.includes(item.toLowerCase()));
  if (destination) {
    updatePayload.destination = destination;
  }

  const durationMatch = lowered.match(/(\d+)\s*days?/);
  if (durationMatch) {
    updatePayload.duration_days = Number(durationMatch[1]);
  }

  if (lowered.includes('couple')) updatePayload.group_type = 'couple';
  else if (lowered.includes('family')) updatePayload.group_type = 'family';
  else if (lowered.includes('friends')) updatePayload.group_type = 'friends';
  else if (lowered.includes('solo')) updatePayload.group_type = 'solo';

  const interests = [];
  if (lowered.includes('food')) interests.push('food');
  if (lowered.includes('culture')) interests.push('culture');
  if (lowered.includes('adventure')) interests.push('adventure');
  if (lowered.includes('nature')) interests.push('nature');
  if (lowered.includes('luxury')) interests.push('luxury');
  if (lowered.includes('nightlife')) interests.push('nightlife');
  if (lowered.includes('wellness')) interests.push('wellness');
  if (interests.length > 0) {
    updatePayload.interests = interests.slice(0, 3);
  }

  if (
    lowered.includes('more relaxed') ||
    lowered.includes('make it relaxed') ||
    lowered.includes('refine pace') ||
    lowered.includes('less hectic') ||
    lowered.includes('calm')
  ) {
    updatePayload.pace_preference = 'relaxed';
  } else if (lowered.includes('balanced')) {
    updatePayload.pace_preference = 'balanced';
  } else if (lowered.includes('fast') || lowered.includes('hectic') || lowered.includes('packed')) {
    updatePayload.pace_preference = 'fast';
  }

  if (lowered.includes('mid-budget') || lowered.includes('mid budget') || lowered.includes('midrange')) {
    updatePayload.budget = 'midrange';
  } else if (lowered.includes('luxury') || lowered.includes('premium') || lowered.includes('upscale')) {
    updatePayload.budget = 'luxury';
  } else if (lowered.includes('budget')) {
    updatePayload.budget = 'budget';
  }

  return updatePayload;
}

function buildAssistantMessageFromGuide(result) {
  return {
    role: 'assistant',
    type: 'destination_guide',
    content: result.overview,
    places:
      result.area_cards?.map((area) => ({
        name: area.name,
        category: area.category || 'area',
        rating: area.rating,
        description: area.summary,
        why_recommended: area.why_it_fits,
      })) || [],
    chips: result.highlights || [],
    reviewSummary: result.review_summary || null,
    reviewInsight: result.review_insight || null,
    reviewSignals: result.review_signals || {},
    reviewAuthenticity: result.review_authenticity || null,
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromTripPlan(result) {
  const constraints = result.parsed_constraints || {};

  const summaryParts = [
    constraints.destination ? `destination: ${constraints.destination}` : null,
    constraints.duration_days ? `duration: ${constraints.duration_days} days` : null,
    constraints.group_type ? `group: ${constraints.group_type}` : null,
    constraints.budget ? `budget: ${constraints.budget}` : null,
    constraints.pace_preference ? `pace: ${constraints.pace_preference}` : null,
  ].filter(Boolean);

  const content =
    summaryParts.length > 0
      ? `I parsed your planning brief and created a draft planning session with ${summaryParts.join(', ')}.`
      : 'I created a draft planning session, but I still need a few core details before generating a full itinerary.';

  return {
    role: 'assistant',
    type: 'trip_plan',
    content,
    planningSession: result,
    chips:
      (result.missing_fields || []).map((field) => {
        if (field === 'destination') return 'Add destination';
        if (field === 'duration_days') return 'Add duration';
        if (field === 'group_type') return 'Add group type';
        if (field === 'budget') return 'Add budget';
        if (field === 'pace_preference') return 'Add pace';
        if (field === 'interests') return 'Add interests';
        return `Add ${field}`;
      }) || [],
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromUpdatedTripPlan(result, followupText) {
  return {
    role: 'assistant',
    type: 'trip_plan',
    content: `I updated your existing planning session based on: "${followupText}".`,
    planningSession: result,
    chips:
      (result.missing_fields || []).map((field) => {
        if (field === 'destination') return 'Add destination';
        if (field === 'duration_days') return 'Add duration';
        if (field === 'group_type') return 'Add group type';
        if (field === 'budget') return 'Add budget';
        if (field === 'pace_preference') return 'Add pace';
        if (field === 'interests') return 'Add interests';
        return `Add ${field}`;
      }) || [],
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromEnrichedTripPlan(result, followupText = null) {
  const dayCount = result.itinerary_skeleton?.length || 0;
  const candidateCount = result.candidate_places?.length || 0;
  const content = followupText
    ? `I regenerated your itinerary after "${followupText}" and now have ${candidateCount} candidate places across ${dayCount} days.`
    : `I enriched your planning session into a first draft slot-based itinerary with ${candidateCount} candidate places across ${dayCount} days.`;

  return {
    role: 'assistant',
    type: 'trip_plan_enriched',
    content,
    planningSession: result,
    chips: ['Make it more relaxed', 'Make it food + culture', 'Change to couple trip', 'Swap candidates'],
    timestamp: new Date().toISOString(),
  };
}

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [persona, setPersona] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const travellerId = getOrCreateTravellerId();

  useEffect(() => {
    const refreshPersona = () => {
      setPersona(getTravellerPersona());
    };

    refreshPersona();

    const personaEventName = getPersonaUpdatedEventName();
    window.addEventListener('storage', refreshPersona);
    window.addEventListener('focus', refreshPersona);
    window.addEventListener(personaEventName, refreshPersona);

    return () => {
      window.removeEventListener('storage', refreshPersona);
      window.removeEventListener('focus', refreshPersona);
      window.removeEventListener(personaEventName, refreshPersona);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;

    setInput('');
    setErrorMessage('');

    const payload = deriveGuidePayload(msg, persona);
    const currentPlanningSessionMessage = getLatestPlanningSessionMessage(messages);
    const currentPlanningSession = currentPlanningSessionMessage?.planningSession || null;

    const userMsg = { role: 'user', content: msg, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      if (currentPlanningSession && isRefinementFollowUp(msg, currentPlanningSession)) {
        const planningSessionId = currentPlanningSession.planning_session_id;
        const updatePayload = buildTripPlanUpdatePayload(msg);

        let updatedPlan = currentPlanningSession;

        if (Object.keys(updatePayload).length > 0) {
          updatedPlan = await updateTripPlan(planningSessionId, updatePayload);

          await createTravellerMemory({
            traveller_id: travellerId,
            event_type: 'trip_plan_updated',
            source_surface: 'assistant',
            payload: {
              planning_session_id: planningSessionId,
              update_payload: updatePayload,
              missing_fields: updatedPlan.missing_fields || [],
            },
          });

          const updatedMsg = buildAssistantMessageFromUpdatedTripPlan(updatedPlan, msg);
          setMessages((prev) => [...prev, updatedMsg]);
        }

        if ((updatedPlan.missing_fields || []).length === 0) {
          const enrichedResult = await enrichTripPlan(planningSessionId);

          await createTravellerMemory({
            traveller_id: travellerId,
            event_type: 'trip_plan_regenerated',
            source_surface: 'assistant',
            payload: {
              planning_session_id: enrichedResult.planning_session_id,
              candidate_count: (enrichedResult.candidate_places || []).length,
              day_count: (enrichedResult.itinerary_skeleton || []).length,
              destination: enrichedResult.parsed_constraints?.destination || null,
              followup_text: msg,
            },
          });

          const enrichedMsg = buildAssistantMessageFromEnrichedTripPlan(enrichedResult, msg);
          setMessages((prev) => [...prev, enrichedMsg]);
        }

        return;
      }

      if (isPlanningBrief(msg)) {
        const planResult = await parseAndSaveTripBrief({
          traveller_id: travellerId,
          brief: msg,
          source_surface: 'assistant',
        });

        const assistantMsg = buildAssistantMessageFromTripPlan(planResult);
        setMessages((prev) => [...prev, assistantMsg]);

        await createTravellerMemory({
          traveller_id: travellerId,
          event_type: 'trip_plan_brief_parsed',
          source_surface: 'assistant',
          payload: {
            planning_session_id: planResult.planning_session_id,
            brief: msg,
            parsed_constraints: planResult.parsed_constraints,
            missing_fields: planResult.missing_fields,
          },
        });

        if ((planResult.missing_fields || []).length === 0) {
          const enrichedResult = await enrichTripPlan(planResult.planning_session_id);

          await createTravellerMemory({
            traveller_id: travellerId,
            event_type: 'trip_plan_enriched',
            source_surface: 'assistant',
            payload: {
              planning_session_id: enrichedResult.planning_session_id,
              candidate_count: (enrichedResult.candidate_places || []).length,
              day_count: (enrichedResult.itinerary_skeleton || []).length,
              destination: enrichedResult.parsed_constraints?.destination || null,
            },
          });

          const enrichedMsg = buildAssistantMessageFromEnrichedTripPlan(enrichedResult);
          setMessages((prev) => [...prev, enrichedMsg]);
        }

        return;
      }

      await createTravellerMemory({
        traveller_id: travellerId,
        event_type: 'destination_guide_requested',
        source_surface: 'assistant',
        payload: {
          query: msg,
          destination: payload.destination,
          duration_days: payload.duration_days,
          traveller_type: payload.traveller_type,
          interests: payload.interests,
          budget: payload.budget,
        },
      });

      const result = await generateDestinationGuide(payload);
      const assistantMsg = buildAssistantMessageFromGuide(result);

      setMessages((prev) => [...prev, assistantMsg]);

      await createTravellerMemory({
        traveller_id: travellerId,
        event_type: 'destination_guide_generated',
        source_surface: 'assistant',
        payload: {
          query: msg,
          destination: result.destination,
          duration_days: result.duration_days,
          suggested_areas: result.suggested_areas || [],
          highlights_count: (result.highlights || []).length,
          review_authenticity: result.review_authenticity || null,
          review_summary: result.review_summary || null,
          traveller_type: payload.traveller_type,
          interests: payload.interests,
          budget: payload.budget,
        },
      });

      try {
        const refreshedPersona = await refreshTravellerPersonaFromMemory(travellerId);
        replaceTravellerPersona(refreshedPersona);
        setPersona(refreshedPersona);
      } catch {
        // Non-blocking
      }
    } catch (error) {
      setErrorMessage(error.message || 'Unable to process your request right now.');
    } finally {
      setIsLoading(false);
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="h-screen flex flex-col max-w-4xl mx-auto">
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-sunset flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-sm">Wayfarer Assistant</h1>
            <p className="text-xs text-muted-foreground">
              Destination intelligence + trip planning foundation
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setMessages([]);
            setErrorMessage('');
          }}
          className="p-2 rounded-lg hover:bg-secondary transition-colors text-muted-foreground"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {isEmpty ? (
          <EmptyChat onSuggestionClick={handleSend} persona={persona} />
        ) : (
          <div className="space-y-6">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} onChipClick={handleSend} />
            ))}

            {isLoading ? (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-sunset flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-white" />
                </div>
                <LoadingState compact message="Processing your travel request..." />
              </div>
            ) : null}

            {errorMessage ? (
              <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {errorMessage}
              </div>
            ) : null}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="px-4 sm:px-6 py-4 border-t border-border">
        <div className="relative max-w-3xl mx-auto">
          <input
            ref={inputRef}
            type="text"
            placeholder="Try: I have 4 days in Tokyo, mid-budget, love food and calm neighborhoods..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            className="w-full pl-4 pr-12 py-3.5 rounded-xl bg-secondary/60 border border-border text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent/30 transition-all"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:opacity-90 transition-opacity disabled:opacity-30"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function EmptyChat({ onSuggestionClick, persona }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full text-center"
    >
      <motion.div
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 3, repeat: Infinity }}
        className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center mb-6"
      >
        <Sparkles className="w-7 h-7 text-accent" />
      </motion.div>
      <h2 className="font-serif text-2xl font-bold mb-2">Where to next?</h2>
      <p className="text-muted-foreground text-sm max-w-sm mb-4">
        Ask for destination guidance or start a planning brief for your next trip.
      </p>
      <p className="text-xs text-muted-foreground max-w-md mb-8">
        {persona?.summary
          ? persona.summary
          : 'Complete onboarding first to make planning and destination guidance more personalized.'}
      </p>
      <div className="flex flex-wrap justify-center gap-2 max-w-md">
        {suggestedChips.map((chip) => (
          <button
            key={chip}
            onClick={() => onSuggestionClick(chip)}
            className="px-3 py-2 rounded-full bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors border border-border"
          >
            {chip}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

function InsightSection({ reviewInsight, chips, onChipClick }) {
  const hasInsight = Boolean(reviewInsight) || (chips?.length || 0) > 0;
  if (!hasInsight) return null;

  return (
    <div className="mt-4 space-y-3">
      {reviewInsight ? (
        <div className="rounded-xl border border-border bg-secondary/40 px-4 py-3">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
            Review insight
          </div>
          <div className="text-sm text-foreground">{reviewInsight.overall_vibe}</div>

          {reviewInsight.standout_themes?.length > 0 ? (
            <div className="mt-2 text-xs text-muted-foreground">
              Stands out for:{' '}
              <span className="font-medium">{reviewInsight.standout_themes.join(', ')}</span>
            </div>
          ) : null}

          <div className="mt-2 text-xs text-muted-foreground">
            Confidence: <span className="font-medium">{reviewInsight.confidence}</span>
          </div>
        </div>
      ) : null}

      {chips?.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {chips.map((chip, i) => (
            <button
              key={i}
              onClick={() => onChipClick(chip)}
              className="px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors border border-border"
            >
              {chip}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function PlanningSessionCard({ planningSession, onChipClick, chips }) {
  const constraints = planningSession?.parsed_constraints || {};

  return (
    <div className="mt-4 rounded-2xl border border-border bg-card p-4 space-y-3">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
          Planning session
        </div>
        <div className="text-sm font-medium text-foreground">
          {planningSession.planning_session_id}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3 text-sm">
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Destination</div>
          <div>{constraints.destination || 'Missing'}</div>
        </div>
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Duration</div>
          <div>{constraints.duration_days ? `${constraints.duration_days} days` : 'Missing'}</div>
        </div>
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Group</div>
          <div>{constraints.group_type || 'Missing'}</div>
        </div>
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Budget</div>
          <div>{constraints.budget || 'Missing'}</div>
        </div>
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Pace</div>
          <div>{constraints.pace_preference || 'Missing'}</div>
        </div>
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Interests</div>
          <div>{constraints.interests?.length ? constraints.interests.join(', ') : 'Missing'}</div>
        </div>
      </div>

      {planningSession.missing_fields?.length > 0 ? (
        <div className="text-xs text-muted-foreground">
          Missing before itinerary generation:{' '}
          <span className="font-medium">{planningSession.missing_fields.join(', ')}</span>
        </div>
      ) : null}

      {chips?.length > 0 ? (
        <div className="flex flex-wrap gap-2 pt-1">
          {chips.map((chip, i) => (
            <button
              key={i}
              onClick={() => onChipClick(chip)}
              className="px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors border border-border"
            >
              {chip}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function SlotCard({ slot }) {
  return (
    <div className="rounded-xl bg-secondary/40 px-4 py-3 space-y-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-medium text-foreground">{slot.label}</div>
          <div className="text-xs text-muted-foreground">{slot.summary}</div>
        </div>
        {slot.assigned_place_name ? (
          <div className="text-xs font-medium text-foreground">{slot.assigned_place_name}</div>
        ) : (
          <div className="text-xs text-muted-foreground">Flexible</div>
        )}
      </div>

      <div className="text-xs text-muted-foreground">{slot.rationale}</div>

      {slot.fallback_candidate_names?.length > 0 ? (
        <div className="text-[11px] text-muted-foreground">
          Fallback options:{' '}
          <span className="font-medium">{slot.fallback_candidate_names.join(', ')}</span>
        </div>
      ) : null}
    </div>
  );
}

function ItinerarySkeletonCard({ planningSession }) {
  const itinerary = planningSession?.itinerary_skeleton || [];
  const candidates = planningSession?.candidate_places || [];

  if (!itinerary.length) return null;

  return (
    <div className="mt-4 rounded-2xl border border-border bg-card p-4 space-y-4">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
          Slot-based itinerary workspace
        </div>
        <div className="text-sm text-foreground">
          {candidates.length} candidate places currently support this draft.
        </div>
      </div>

      <div className="space-y-4">
        {itinerary.map((day) => (
          <div key={day.day_number} className="rounded-2xl border border-border bg-background px-4 py-4 space-y-3">
            <div>
              <div className="text-sm font-medium text-foreground">
                Day {day.day_number} — {day.title}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">{day.summary}</div>
            </div>

            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Day rationale:</span> {day.day_rationale}
            </div>

            {day.slots?.length > 0 ? (
              <div className="grid gap-3">
                {day.slots.map((slot, index) => (
                  <SlotCard key={`${day.day_number}-${slot.slot_type}-${index}`} slot={slot} />
                ))}
              </div>
            ) : null}

            {day.fallback_candidate_names?.length > 0 ? (
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">Day-level fallback direction:</span>{' '}
                {day.fallback_candidate_names.join(', ')}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {candidates.length > 0 ? (
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Candidate places
          </div>
          <div className="space-y-2">
            {candidates.map((candidate, index) => (
              <div
                key={`${candidate.location_id}-${index}`}
                className="rounded-xl border border-border bg-background px-3 py-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-foreground">{candidate.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {candidate.city}, {candidate.country} · {candidate.category}
                    </div>
                  </div>
                  <div className="text-xs font-medium text-muted-foreground">
                    Score {candidate.score}
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {candidate.why_selected}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MessageBubble({ message, onChipClick }) {
  if (message.role === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-end"
      >
        <div className="max-w-[80%] px-4 py-3 rounded-2xl rounded-br-md bg-primary text-primary-foreground text-sm">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3"
    >
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-sunset flex items-center justify-center flex-shrink-0 mt-1">
        <Sparkles className="w-3.5 h-3.5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</div>

        {message.type === 'trip_plan' || message.type === 'trip_plan_enriched' ? (
          <PlanningSessionCard
            planningSession={message.planningSession}
            chips={message.chips}
            onChipClick={onChipClick}
          />
        ) : null}

        {message.type === 'trip_plan_enriched' ? (
          <ItinerarySkeletonCard planningSession={message.planningSession} />
        ) : null}

        {message.places?.length > 0 ? (
          <div className="mt-4 space-y-2">
            {message.places.map((place, i) => (
              <PlaceCard
                key={i}
                name={place.name}
                category={place.category}
                rating={place.rating}
                description={place.description}
                reason={place.why_recommended}
                image={undefined}
                distance={undefined}
                onSave={undefined}
                onClick={undefined}
              />
            ))}
          </div>
        ) : null}

        {message.type === 'destination_guide' ? (
          <InsightSection
            reviewInsight={message.reviewInsight}
            chips={message.chips}
            onChipClick={onChipClick}
          />
        ) : null}
      </div>
    </motion.div>
  );
}