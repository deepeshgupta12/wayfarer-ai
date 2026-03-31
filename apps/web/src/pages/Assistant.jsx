import { useRef, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Sparkles, Plus, RefreshCw, Heart, SkipForward } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import LoadingState from '../components/ui/LoadingState';
import PlaceCard from '../components/cards/PlaceCard';
import {
  createTravellerMemory,
  createTripSignal,
  enrichTripPlan,
  getSavedTrip,
  getSimilarPlaces,
  indexDestinationPlaces,
  orchestrateAssistant,
  promoteTripPlanToSavedTrip,
  refreshTravellerPersonaFromMemory,
  replaceTripPlanSlot,
  streamTripPlanEnrichment,
  updateTripPlan,
  listSavedTrips,
  listProactiveAlerts,
} from '@/api/wayfarerApi';
import {
  getOrCreateTravellerId,
  getTravellerPersona,
  getPersonaUpdatedEventName,
  replaceTravellerPersona,
} from '@/lib/travellerProfile';
import {
  cacheSavedTrip,
  cacheSavedTrips,
  cacheTripPlan,
  getCachedSavedTrips,
} from '@/lib/tripStorage';

const suggestedChips = [
  '3 days in Kyoto for food and culture',
  'Couple-friendly Lisbon guide',
  'I have 4 days in Tokyo, mid-budget, love food and calm neighborhoods',
  'Compare Prague and Budapest for a couple trip',
  'Replace Day 2 with something less hectic',
];

const KNOWN_DESTINATIONS = ['Tokyo', 'Kyoto', 'Lisbon', 'Prague', 'Budapest'];

function createMessageId() {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

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

function getLatestPlanningSessionMessage(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.planningSession?.planning_session_id) {
      return message;
    }
  }

  return null;
}

function getLatestSavedTripMessage(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.savedTrip?.trip_id) {
      return message;
    }
  }

  return null;
}

function mergeAssistantContext(baseContext, overrideContext) {
  return {
    traveller_id: overrideContext?.traveller_id || baseContext?.traveller_id || null,
    planning_session_id:
      overrideContext?.planning_session_id || baseContext?.planning_session_id || null,
    trip_id: overrideContext?.trip_id || baseContext?.trip_id || null,
  };
}

function buildAssistantContextFromMessages(messages, travellerId) {
  const latestPlanningSessionMessage = getLatestPlanningSessionMessage(messages);
  const latestSavedTripMessage = getLatestSavedTripMessage(messages);

  return {
    traveller_id: travellerId,
    planning_session_id:
      latestPlanningSessionMessage?.planningSession?.planning_session_id || null,
    trip_id:
      latestSavedTripMessage?.savedTrip?.trip_id ||
      latestPlanningSessionMessage?.savedTrip?.trip_id ||
      null,
  };
}

async function resolveSavedTripFromContext(context, messages, travellerId) {
  if (context?.trip_id) {
    return await getSavedTrip(context.trip_id);
  }

  const latestSavedTripMessage = getLatestSavedTripMessage(messages);
  if (latestSavedTripMessage?.savedTrip?.trip_id) {
    return latestSavedTripMessage.savedTrip;
  }

  const cachedTrips = getCachedSavedTrips(travellerId) || [];
  return cachedTrips[0] || null;
}

function isSlotReplacementFollowUp(rawInput) {
  const lowered = rawInput.toLowerCase().trim();

  if (lowered.includes('swap candidates')) return true;
  if (lowered.includes('replace day')) return true;
  if (lowered.includes('replace morning')) return true;
  if (lowered.includes('replace lunch')) return true;
  if (lowered.includes('replace afternoon')) return true;
  if (lowered.includes('replace evening')) return true;
  if (lowered.includes('less hectic')) return true;

  return false;
}

function inferReplacementPayload(rawInput, planningSession) {
  const lowered = rawInput.toLowerCase().trim();
  const itinerary = planningSession?.itinerary_skeleton || [];
  const fallbackDay = itinerary[0]?.day_number || 1;

  let dayNumber = fallbackDay;
  const dayMatch = lowered.match(/day\s+(\d+)/);
  if (dayMatch) {
    dayNumber = Number(dayMatch[1]);
  }

  let slotType = 'afternoon';
  if (lowered.includes('morning')) slotType = 'morning';
  else if (lowered.includes('lunch')) slotType = 'lunch';
  else if (lowered.includes('afternoon')) slotType = 'afternoon';
  else if (lowered.includes('evening')) slotType = 'evening';

  let replacementMode = 'best_alternative';
  if (lowered.includes('less hectic') || lowered.includes('more relaxed')) {
    replacementMode = 'less_hectic';
  } else if (lowered.includes('food')) {
    replacementMode = 'more_food';
  } else if (lowered.includes('culture')) {
    replacementMode = 'more_culture';
  }

  return {
    day_number: dayNumber,
    slot_type: slotType,
    replacement_mode: replacementMode,
  };
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

function getSlotFromPlanningSession(planningSession, dayNumber, slotType) {
  const day = (planningSession?.itinerary_skeleton || []).find((item) => item.day_number === dayNumber);
  if (!day) return null;
  return (day.slots || []).find((slot) => slot.slot_type === slotType) || null;
}

function buildAssistantMessageFromGuide(result, contentOverride = null) {
  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'destination_guide',
    content: contentOverride || result.overview,
    places:
      result.area_cards?.map((area) => ({
        name: area.name,
        category: area.category || 'area',
        rating: area.rating,
        description: area.summary,
        why_recommended: area.why_it_fits,
      })) || [],
    alternatives: result.youd_also_love || [],
    chips: result.highlights || [],
    reviewSummary: result.review_summary || null,
    reviewInsight: result.review_insight || null,
    reviewSignals: result.review_signals || {},
    reviewAuthenticity: result.review_authenticity || null,
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromComparison(result) {
  const scoreA = result?.destination_a?.weighted_score || 0;
  const scoreB = result?.destination_b?.weighted_score || 0;

  const winner =
    Math.abs(scoreA - scoreB) < 0.15
      ? null
      : scoreA >= scoreB
      ? result?.destination_a?.name
      : result?.destination_b?.name;

  const opening = winner
    ? `${winner} comes out ahead for this decision.`
    : `${result?.destination_a?.name} and ${result?.destination_b?.name} are very closely matched.`;

  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'destination_comparison',
    content: `${opening} I’ve framed the trade-offs so you can move directly into planning instead of reading a raw comparison dump.`,
    comparison: result,
    chips: result.next_step_suggestions || [],
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromLiveRuntime(orchestration, savedTrip = null) {
  const run = orchestration?.payload?.run || orchestration?.run || null;
  const finalOutput =
    run?.final_output || orchestration?.payload?.final_output || orchestration?.final_output || {};
  const recommendations =
    finalOutput.recommendations ||
    finalOutput.alternatives ||
    finalOutput.gems ||
    [];

  const alerts = finalOutput.alerts || [];
  const alertCount = alerts.length;
  const recommendationCount = recommendations.length;

  let opening = finalOutput.message;
  if (!opening) {
    if (finalOutput.agent === 'gem_agent') {
      opening = `I found ${recommendationCount} underrated options that fit your active trip context.`;
    } else if (finalOutput.agent === 'live_replan_agent') {
      opening = `I found ${recommendationCount} better-fit alternatives for the disruption in your active trip.`;
    } else if (finalOutput.agent === 'proactive_monitor_agent') {
      opening = `I checked your active itinerary and found ${alertCount} issue${alertCount === 1 ? '' : 's'} worth reviewing.`;
    } else {
      opening = `I found ${recommendationCount} context-aware options for your active trip right now.`;
    }
  }

  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'live_runtime',
    content: opening,
    liveRuntime: finalOutput,
    savedTrip,
    places: recommendations.map((item) => ({
      location_id: item.location_id,
      name: item.name,
      city: item.city || null,
      category: item.category || 'place',
      rating: item.rating,
      description:
        item.why_recommended ||
        item.gem_reason ||
        item.why_alternative ||
        item.live_reason ||
        null,
      why_recommended:
        item.why_recommended ||
        item.gem_reason ||
        item.why_alternative ||
        item.live_reason ||
        null,
      photos: item.photos || [],
      image_url: item.photos?.[0]?.image_url || null,
      visual_signal: item.visual_signal || null,
    })),
    alerts,
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromTripPlan(result, savedTrip = null) {
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
    id: createMessageId(),
    role: 'assistant',
    type: 'trip_plan',
    content,
    planningSession: result,
    savedTrip,
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

function buildAssistantMessageFromUpdatedTripPlan(result, followupText, savedTrip = null) {
  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'trip_plan',
    content: `I updated your existing planning session based on: "${followupText}".`,
    planningSession: result,
    savedTrip,
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

function buildAssistantMessageFromEnrichedTripPlan(result, savedTrip, followupText = null, contentOverride = null) {
  const dayCount = result.itinerary_skeleton?.length || 0;
  const candidateCount = result.candidate_places?.length || 0;
  const destination = result?.parsed_constraints?.destination || 'your destination';

  const content =
    contentOverride ||
    (followupText
      ? `I reworked your ${destination} itinerary after "${followupText}" and kept the same planning session active. You now have ${candidateCount} candidate places structured across ${dayCount} days.`
      : `I turned your ${destination} brief into a slot-based itinerary. You now have ${candidateCount} candidate places structured across ${dayCount} days, with routing and pacing logic already attached.`);

  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'trip_plan_enriched',
    content,
    planningSession: result,
    savedTrip,
    chips: [
      'Make it more relaxed',
      'Make it food + culture',
      'Change to couple trip',
      'Replace Day 2 with something less hectic',
      'Swap candidates',
    ],
    timestamp: new Date().toISOString(),
  };
}

function buildAssistantMessageFromSlotReplacement(
  result,
  followupText,
  previousPlanningSession,
  replacementPayload,
  savedTrip
) {
  const previousSlot = getSlotFromPlanningSession(
    previousPlanningSession,
    replacementPayload.day_number,
    replacementPayload.slot_type
  );
  const newSlot = getSlotFromPlanningSession(
    result,
    replacementPayload.day_number,
    replacementPayload.slot_type
  );

  const wasChanged =
    previousSlot?.assigned_location_id &&
    newSlot?.assigned_location_id &&
    previousSlot.assigned_location_id !== newSlot.assigned_location_id;

  const content = wasChanged
    ? `I replaced that slot based on "${followupText}" and kept the same planning session active.`
    : `I checked that slot after "${followupText}", but the current option still looks like the strongest fit, so I kept it unchanged.`;

  return {
    id: createMessageId(),
    role: 'assistant',
    type: 'trip_plan_enriched',
    content,
    planningSession: result,
    savedTrip,
    chips: [
      'Replace Day 2 with something less hectic',
      'Replace evening slot',
      'Make it food + culture',
      'Change to couple trip',
    ],
    timestamp: new Date().toISOString(),
  };
}

export default function Assistant() {
  const travellerId = getOrCreateTravellerId();

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [persona, setPersona] = useState(null);
  const [assistantContext, setAssistantContext] = useState({
    traveller_id: travellerId,
    planning_session_id: null,
    trip_id: null,
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

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
    setAssistantContext((prev) => ({
      ...prev,
      traveller_id: travellerId,
    }));
  }, [travellerId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const prompt = params.get('prompt');

    if (prompt) {
      setInput(prompt);
      navigate('/assistant', { replace: true });
    }
  }, [location.search, navigate]);

  const updateMessageById = (messageId, patch) => {
    setMessages((prev) =>
      prev.map((message) => (message.id === messageId ? { ...message, ...patch } : message))
    );
  };

  const ensureSavedTripForPlan = async (plan, fallbackTitle = null) => {
    const savedTripsResponse = await listSavedTrips(travellerId, 100);
    cacheSavedTrips(travellerId, savedTripsResponse.items || []);

    const existing = (savedTripsResponse.items || []).find(
      (item) => item.planning_session_id === plan.planning_session_id
    );

    if (existing) {
      const fresh = await getSavedTrip(existing.trip_id);
      cacheSavedTrip(fresh);
      return fresh;
    }

    const destinationName = plan?.parsed_constraints?.destination || 'Trip';
    const durationDays = plan?.parsed_constraints?.duration_days || plan?.itinerary_skeleton?.length || 0;

    const promoted = await promoteTripPlanToSavedTrip(plan.planning_session_id, {
      title: fallbackTitle || `${destinationName} ${durationDays}-day plan`,
      companions: plan?.parsed_constraints?.group_type || null,
      status: 'planning',
      source_surface: 'assistant',
    });

    cacheSavedTrip(promoted);
    return promoted;
  };

  const handleSavePlace = async (place, context = {}) => {
    const tripId = context?.tripId;
    if (!tripId) return;

    await createTripSignal(tripId, {
      signal_type: 'selected_place',
      location_id: place.location_id || null,
      payload: {
        name: place.name,
        city: place.city || null,
        category: place.category || null,
      },
    });

    const freshTrip = await getSavedTrip(tripId);
    cacheSavedTrip(freshTrip);

    await createTravellerMemory({
      traveller_id: travellerId,
      event_type: 'selected_place_saved',
      source_surface: 'assistant',
      payload: {
        planning_session_id: context?.planningSessionId || null,
        trip_id: tripId,
        location_id: place.location_id || null,
        name: place.name,
        city: place.city || null,
        category: place.category || null,
      },
    });
  };

  const handleSkipAlternative = async (alternative, context = {}) => {
    const tripId = context?.tripId;
    if (!tripId) return;

    await createTripSignal(tripId, {
      signal_type: 'skipped_recommendation',
      location_id: alternative.location_id || null,
      payload: {
        name: alternative.name,
        city: alternative.city || null,
        category: alternative.category || null,
      },
    });

    const freshTrip = await getSavedTrip(tripId);
    cacheSavedTrip(freshTrip);

    await createTravellerMemory({
      traveller_id: travellerId,
      event_type: 'skipped_recommendation',
      source_surface: 'assistant',
      payload: {
        planning_session_id: context?.planningSessionId || null,
        trip_id: tripId,
        location_id: alternative.location_id || null,
        name: alternative.name,
        city: alternative.city || null,
        category: alternative.category || null,
      },
    });
  };

  const handleSend = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;

    setInput('');
    setErrorMessage('');

    const derivedContext = buildAssistantContextFromMessages(messages, travellerId);
    const requestContext = mergeAssistantContext(derivedContext, assistantContext);

    const currentPlanningSessionMessage = getLatestPlanningSessionMessage(messages);
    const currentSavedTripMessage = getLatestSavedTripMessage(messages);
    const currentSavedTrip =
      currentSavedTripMessage?.savedTrip ||
      currentPlanningSessionMessage?.savedTrip ||
      (requestContext.trip_id ? await resolveSavedTripFromContext(requestContext, messages, travellerId) : null);

    const userMsg = {
      id: createMessageId(),
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const orchestration = await orchestrateAssistant({
        message: msg,
        context: requestContext,
        source_surface: 'assistant',
        stream: false,
      });

      const route = orchestration?.route || 'unknown';
      const continuityContext = mergeAssistantContext(
        requestContext,
        orchestration?.continuity_context || {}
      );
      setAssistantContext(continuityContext);

      if (route === 'live_runtime.orchestrate') {
        let boundSavedTrip = currentSavedTrip;
        if (!boundSavedTrip?.trip_id && continuityContext.trip_id) {
          boundSavedTrip = await getSavedTrip(continuityContext.trip_id);
          cacheSavedTrip(boundSavedTrip);
        }

        const liveMessage = buildAssistantMessageFromLiveRuntime(orchestration, boundSavedTrip);

        if (liveMessage.alerts?.length && boundSavedTrip?.trip_id) {
          try {
            const latestAlerts = await listProactiveAlerts(boundSavedTrip.trip_id, { limit: 20 });
            liveMessage.alerts = latestAlerts.items || liveMessage.alerts;
          } catch {
            // keep runtime-provided alerts if list call fails
          }
        }

        await createTravellerMemory({
          traveller_id: travellerId,
          event_type: 'assistant_live_runtime_routed',
          source_surface: 'assistant',
          payload: {
            trip_id: continuityContext.trip_id || null,
            planning_session_id: continuityContext.planning_session_id || null,
            routed_agent: orchestration?.payload?.run?.routed_agent || null,
            user_message: msg,
          },
        });

        setMessages((prev) => [...prev, liveMessage]);
        return;
      }

      if (route === 'destinations.compare') {
        const comparisonResult = orchestration.payload;
        const comparisonMsg = buildAssistantMessageFromComparison(comparisonResult);

        await createTravellerMemory({
          traveller_id: travellerId,
          event_type: 'destination_comparison_generated',
          source_surface: 'assistant',
          payload: {
            destination_a: comparisonResult.destination_a?.name || null,
            destination_b: comparisonResult.destination_b?.name || null,
            user_message: msg,
          },
        });

        setMessages((prev) => [...prev, comparisonMsg]);
        return;
      }

      if (route === 'destinations.guide') {
        const result = orchestration.payload;
        const assistantMsg = buildAssistantMessageFromGuide(result);

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
          },
        });

        setMessages((prev) => [...prev, assistantMsg]);

        try {
          const refreshedPersona = await refreshTravellerPersonaFromMemory(travellerId);
          replaceTravellerPersona(refreshedPersona);
          setPersona(refreshedPersona);
        } catch {
          // non-blocking
        }

        return;
      }

      if (route === 'trip_plans.parse_and_save') {
        const planResult = orchestration.payload;
        cacheTripPlan(planResult);

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

        setAssistantContext((prev) =>
          mergeAssistantContext(prev, {
            traveller_id: travellerId,
            planning_session_id: planResult.planning_session_id,
            trip_id: continuityContext.trip_id || null,
          })
        );

        if ((planResult.missing_fields || []).length === 0) {
          const streamingMessageId = createMessageId();
          const placeholder = buildAssistantMessageFromEnrichedTripPlan(
            planResult,
            null,
            null,
            'Generating your slot-based itinerary...'
          );
          placeholder.id = streamingMessageId;
          setMessages((prev) => [...prev, placeholder]);

          let streamedContent = '';

          const enrichedResult =
            (await streamTripPlanEnrichment(planResult.planning_session_id, {
              onEvent: (event) => {
                if (event?.type === 'content_delta' && event?.content) {
                  streamedContent = `${streamedContent}${event.content}`;
                  updateMessageById(streamingMessageId, {
                    content: streamedContent,
                  });
                }
              },
            })) || (await enrichTripPlan(planResult.planning_session_id));

          cacheTripPlan(enrichedResult);

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

          const indexed = await indexDestinationPlaces({
            destination: enrichedResult.parsed_constraints.destination,
            traveller_type: enrichedResult.parsed_constraints.group_type,
            interests: enrichedResult.parsed_constraints.interests || [],
          });

          if (indexed?.items?.length > 0) {
            const firstCandidateId = enrichedResult.candidate_places?.[0]?.location_id;
            if (firstCandidateId) {
              await getSimilarPlaces({
                source_location_id: firstCandidateId,
                top_k: 3,
                city_filter: enrichedResult.parsed_constraints.destination,
              });
            }
          }

          const savedTrip = await ensureSavedTripForPlan(enrichedResult);
          const freshTrip = await getSavedTrip(savedTrip.trip_id);
          cacheSavedTrip(freshTrip);

          setAssistantContext((prev) =>
            mergeAssistantContext(prev, {
              traveller_id: travellerId,
              planning_session_id: enrichedResult.planning_session_id,
              trip_id: freshTrip.trip_id,
            })
          );

          updateMessageById(
            streamingMessageId,
            buildAssistantMessageFromEnrichedTripPlan(enrichedResult, freshTrip)
          );
        }

        return;
      }

      if (route === 'trip_plans.get_summary') {
        const summaryResult = orchestration.payload;
        cacheTripPlan(summaryResult);

        let savedTrip = currentSavedTrip;
        if (!savedTrip?.trip_id && continuityContext.trip_id) {
          savedTrip = await getSavedTrip(continuityContext.trip_id);
          cacheSavedTrip(savedTrip);
        }

        const planningSessionId =
          summaryResult?.planning_session_id || continuityContext.planning_session_id;

        if (summaryResult.status === 'enriched' && isSlotReplacementFollowUp(msg)) {
          const replacementPayload = inferReplacementPayload(msg, summaryResult);
          const replacedPlan = await replaceTripPlanSlot(planningSessionId, replacementPayload);
          cacheTripPlan(replacedPlan);

          savedTrip = savedTrip || (await ensureSavedTripForPlan(replacedPlan));

          await createTripSignal(savedTrip.trip_id, {
            signal_type: 'replaced_slot',
            location_id:
              getSlotFromPlanningSession(
                replacedPlan,
                replacementPayload.day_number,
                replacementPayload.slot_type
              )?.assigned_location_id || null,
            day_number: replacementPayload.day_number,
            slot_type: replacementPayload.slot_type,
            payload: {
              replacement_mode: replacementPayload.replacement_mode,
              followup_text: msg,
            },
          });

          const freshTrip = await getSavedTrip(savedTrip.trip_id);
          cacheSavedTrip(freshTrip);

          await createTravellerMemory({
            traveller_id: travellerId,
            event_type: 'trip_plan_slot_replaced',
            source_surface: 'assistant',
            payload: {
              planning_session_id: planningSessionId,
              trip_id: freshTrip.trip_id,
              replacement_payload: replacementPayload,
              followup_text: msg,
            },
          });

          setAssistantContext((prev) =>
            mergeAssistantContext(prev, {
              traveller_id: travellerId,
              planning_session_id: replacedPlan.planning_session_id,
              trip_id: freshTrip.trip_id,
            })
          );

          const replacementMsg = buildAssistantMessageFromSlotReplacement(
            replacedPlan,
            msg,
            summaryResult,
            replacementPayload,
            freshTrip
          );
          setMessages((prev) => [...prev, replacementMsg]);
          return;
        }

        const updatePayload = buildTripPlanUpdatePayload(msg);
        if (Object.keys(updatePayload).length > 0) {
          const updatedPlan = await updateTripPlan(planningSessionId, updatePayload);
          cacheTripPlan(updatedPlan);

          await createTravellerMemory({
            traveller_id: travellerId,
            event_type: 'trip_plan_updated',
            source_surface: 'assistant',
            payload: {
              planning_session_id: planningSessionId,
              trip_id: savedTrip?.trip_id || null,
              update_payload: updatePayload,
              missing_fields: updatedPlan.missing_fields || [],
            },
          });

          const updatedMsg = buildAssistantMessageFromUpdatedTripPlan(updatedPlan, msg, savedTrip);
          setMessages((prev) => [...prev, updatedMsg]);

          setAssistantContext((prev) =>
            mergeAssistantContext(prev, {
              traveller_id: travellerId,
              planning_session_id: updatedPlan.planning_session_id,
              trip_id: savedTrip?.trip_id || prev.trip_id || null,
            })
          );

          if ((updatedPlan.missing_fields || []).length === 0) {
            const streamingMessageId = createMessageId();

            const placeholder = buildAssistantMessageFromEnrichedTripPlan(
              updatedPlan,
              savedTrip,
              msg,
              'Regenerating your itinerary...'
            );
            placeholder.id = streamingMessageId;

            setMessages((prev) => [...prev, placeholder]);

            let streamedContent = '';

            const enrichedResult =
              (await streamTripPlanEnrichment(planningSessionId, {
                onEvent: (event) => {
                  if (event?.type === 'content_delta' && event?.content) {
                    streamedContent = `${streamedContent}${event.content}`;
                    updateMessageById(streamingMessageId, {
                      content: streamedContent,
                    });
                  }
                },
              })) || (await enrichTripPlan(planningSessionId));

            cacheTripPlan(enrichedResult);
            savedTrip = await ensureSavedTripForPlan(enrichedResult);
            const freshTrip = await getSavedTrip(savedTrip.trip_id);
            cacheSavedTrip(freshTrip);

            await createTravellerMemory({
              traveller_id: travellerId,
              event_type: 'trip_plan_regenerated',
              source_surface: 'assistant',
              payload: {
                planning_session_id: enrichedResult.planning_session_id,
                trip_id: freshTrip.trip_id,
                candidate_count: (enrichedResult.candidate_places || []).length,
                day_count: (enrichedResult.itinerary_skeleton || []).length,
                destination: enrichedResult.parsed_constraints?.destination || null,
                followup_text: msg,
              },
            });

            setAssistantContext((prev) =>
              mergeAssistantContext(prev, {
                traveller_id: travellerId,
                planning_session_id: enrichedResult.planning_session_id,
                trip_id: freshTrip.trip_id,
              })
            );

            updateMessageById(
              streamingMessageId,
              buildAssistantMessageFromEnrichedTripPlan(enrichedResult, freshTrip, msg)
            );
          }

          return;
        }

        const summaryMessage =
          summaryResult.status === 'enriched'
            ? buildAssistantMessageFromEnrichedTripPlan(
                summaryResult,
                savedTrip,
                msg,
                'I kept your active itinerary context bound and pulled the current summary for this follow-up.'
              )
            : buildAssistantMessageFromUpdatedTripPlan(
                summaryResult,
                msg,
                savedTrip
              );

        setMessages((prev) => [...prev, summaryMessage]);
        return;
      }

      if (route === 'unknown') {
        const fallbackMessage = {
          id: createMessageId(),
          role: 'assistant',
          type: 'assistant_fallback',
          content:
            orchestration?.payload?.message ||
            orchestration?.payload?.error ||
            'I could not confidently map that to a supported flow yet. Try asking for a guide, comparison, trip plan, itinerary follow-up, or live runtime help.',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, fallbackMessage]);
        return;
      }

      const fallbackMessage = {
        id: createMessageId(),
        role: 'assistant',
        type: 'assistant_fallback',
        content: 'I received a route, but the UI does not yet render that response shape.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, fallbackMessage]);
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
              Backend-first planning + destination intelligence
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            setMessages([]);
            setErrorMessage('');
            setAssistantContext({
              traveller_id: travellerId,
              planning_session_id: null,
              trip_id: null,
            });
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
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onChipClick={handleSend}
                onSavePlace={handleSavePlace}
                onSkipAlternative={handleSkipAlternative}
              />
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
        Ask for destination guidance, compare cities, or start a planning brief for your next trip.
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

function PlanningSessionCard({ planningSession, savedTrip, onChipClick, chips }) {
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

      {savedTrip?.trip_id ? (
        <div className="rounded-xl bg-secondary/50 px-3 py-2">
          <div className="text-[11px] uppercase text-muted-foreground mb-1">Saved trip</div>
          <div className="text-sm">{savedTrip.trip_id}</div>
          <div className="text-xs text-muted-foreground mt-1">
            Current version: {savedTrip.current_version_number}
            {savedTrip.history_branch_label ? ` · ${savedTrip.history_branch_label}` : ''}
          </div>
        </div>
      ) : null}

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

function AlternativesSection({ alternatives, onSavePlace, onSkipAlternative, context }) {
  if (!alternatives?.length) return null;

  return (
    <div className="mt-3 space-y-2">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        You’d also love
      </div>

      {alternatives.map((alternative, index) => (
        <div
          key={`${alternative.location_id}-${index}`}
          className="rounded-xl border border-border bg-background px-3 py-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-medium text-foreground">{alternative.name}</div>
              <div className="text-xs text-muted-foreground">
                {alternative.city}, {alternative.country} · {alternative.category}
              </div>
              <div className="mt-1 text-xs text-muted-foreground">
                {alternative.reason || alternative.why_alternative}
              </div>
            </div>
            <div className="text-xs font-medium text-accent">
              {alternative.match_score || alternative.score}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-3">
            <button
              onClick={() =>
                onSavePlace?.(
                  {
                    location_id: alternative.location_id,
                    name: alternative.name,
                    city: alternative.city,
                    category: alternative.category,
                  },
                  context
                )
              }
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
            >
              <Heart className="w-3 h-3" />
              Save
            </button>

            <button
              onClick={() => onSkipAlternative?.(alternative, context)}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
            >
              <SkipForward className="w-3 h-3" />
              Skip
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function SlotCard({ slot, onChipClick, dayNumber, onSavePlace, onSkipAlternative, context }) {
  const replaceChip =
    slot.slot_type === 'evening'
      ? `Replace Day ${dayNumber} evening slot`
      : `Replace Day ${dayNumber} ${slot.slot_type}`;

  const isRetained = (slot.rationale || '').toLowerCase().includes('remains in the');
  const isReplaced = (slot.rationale || '').toLowerCase().includes('now anchors');

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

      {isRetained || isReplaced ? (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {isReplaced ? 'Replacement applied' : 'Strongest fit retained'}
          </span>
        </div>
      ) : null}

      <div className="text-xs text-muted-foreground">{slot.rationale}</div>

      {slot.fallback_candidate_names?.length > 0 ? (
        <div className="text-[11px] text-muted-foreground">
          Fallback options:{' '}
          <span className="font-medium">{slot.fallback_candidate_names.join(', ')}</span>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 pt-1">
        <button
          onClick={() => onChipClick(replaceChip)}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Replace slot
        </button>
      </div>

      <AlternativesSection
        alternatives={slot.alternatives || []}
        onSavePlace={onSavePlace}
        onSkipAlternative={onSkipAlternative}
        context={context}
      />
    </div>
  );
}

function ItinerarySkeletonCard({
  planningSession,
  savedTrip,
  onChipClick,
  onSavePlace,
  onSkipAlternative,
}) {
  const itinerary = planningSession?.itinerary_skeleton || [];
  const candidates = planningSession?.candidate_places || [];
  const context = {
    planningSessionId: planningSession?.planning_session_id || null,
    tripId: savedTrip?.trip_id || null,
  };

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
          <div
            key={day.day_number}
            className="rounded-2xl border border-border bg-background px-4 py-4 space-y-3"
          >
            <div>
              <div className="text-sm font-medium text-foreground">
                Day {day.day_number} — {day.title}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">{day.summary}</div>
            </div>

            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Day rationale:</span> {day.day_rationale}
            </div>

            {day.geo_cluster ? (
              <div className="text-xs text-muted-foreground">
                <span className="font-medium">Geo cluster:</span> {day.geo_cluster}
              </div>
            ) : null}

            {day.slots?.length > 0 ? (
              <div className="grid gap-3">
                {day.slots.map((slot, index) => (
                  <SlotCard
                    key={`${day.day_number}-${slot.slot_type}-${index}`}
                    slot={slot}
                    onChipClick={onChipClick}
                    dayNumber={day.day_number}
                    onSavePlace={onSavePlace}
                    onSkipAlternative={onSkipAlternative}
                    context={context}
                  />
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
                      {candidate.geo_cluster ? ` · ${candidate.geo_cluster}` : ''}
                    </div>
                  </div>
                  <div className="text-xs font-medium text-muted-foreground">
                    Score {candidate.score}
                  </div>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {candidate.why_selected}
                </div>

                <div className="flex flex-wrap gap-2 pt-3">
                  <button
                    onClick={() =>
                      onSavePlace?.(
                        {
                          location_id: candidate.location_id,
                          name: candidate.name,
                          city: candidate.city,
                          category: candidate.category,
                        },
                        context
                      )
                    }
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-background border border-border text-[11px] font-medium text-foreground hover:bg-secondary transition-colors"
                  >
                    <Heart className="w-3 h-3" />
                    Save
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ComparisonCard({ comparison, onChipClick }) {
  if (!comparison) return null;

  return (
    <div className="mt-4 rounded-2xl border border-border bg-card p-4 space-y-4">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">
          Comparison workspace
        </div>
        <div className="text-sm font-medium text-foreground">
          {comparison.destination_a?.name} vs {comparison.destination_b?.name}
        </div>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="rounded-xl bg-secondary/50 px-3 py-3">
          <div className="font-medium text-sm">{comparison.destination_a?.name}</div>
          <div className="text-xs text-muted-foreground mt-1">
            Weighted score: {comparison.destination_a?.weighted_score}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {comparison.destination_a?.best_for}
          </div>
        </div>

        <div className="rounded-xl bg-secondary/50 px-3 py-3">
          <div className="font-medium text-sm">{comparison.destination_b?.name}</div>
          <div className="text-xs text-muted-foreground mt-1">
            Weighted score: {comparison.destination_b?.weighted_score}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            {comparison.destination_b?.best_for}
          </div>
        </div>
      </div>

      <div className="text-xs text-muted-foreground">
        <span className="font-medium">Planning recommendation:</span>{' '}
        {comparison.planning_recommendation}
      </div>

      {comparison.next_step_suggestions?.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {comparison.next_step_suggestions.map((chip, index) => (
            <button
              key={index}
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

function MessageBubble({ message, onChipClick, onSavePlace, onSkipAlternative }) {
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

        {(message.type === 'trip_plan' || message.type === 'trip_plan_enriched') ? (
          <PlanningSessionCard
            planningSession={message.planningSession}
            savedTrip={message.savedTrip}
            chips={message.chips}
            onChipClick={onChipClick}
          />
        ) : null}

        {message.type === 'trip_plan_enriched' ? (
          <ItinerarySkeletonCard
            planningSession={message.planningSession}
            savedTrip={message.savedTrip}
            onChipClick={onChipClick}
            onSavePlace={onSavePlace}
            onSkipAlternative={onSkipAlternative}
          />
        ) : null}

        {message.type === 'destination_comparison' ? (
          <ComparisonCard comparison={message.comparison} onChipClick={onChipClick} />
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
                image={place.image_url || place.photos?.[0]?.image_url || undefined}
                distance={undefined}
                onSave={() =>
                  onSavePlace?.(
                    {
                      location_id: place.location_id || place.name,
                      name: place.name,
                      city: place.city || null,
                      category: place.category,
                    },
                    {
                      planningSessionId: message?.planningSession?.planning_session_id || null,
                      tripId: message?.savedTrip?.trip_id || null,
                    }
                  )
                }
                onClick={undefined}
              />
            ))}
          </div>
        ) : null}

        {message.type === 'live_runtime' && message.alerts?.length > 0 ? (
          <div className="mt-4 rounded-2xl border border-border bg-card p-4">
            <div className="text-sm font-medium mb-3">Live alerts</div>
            <div className="space-y-2">
              {message.alerts.slice(0, 4).map((alert) => (
                <div
                  key={alert.alert_id || `${alert.title}-${alert.day_number || 0}`}
                  className="rounded-xl border border-border p-3"
                >
                  <div className="font-medium text-sm">{alert.title}</div>
                  <div className="text-xs text-muted-foreground mt-1">{alert.message}</div>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {message.type === 'destination_guide' ? (
          <>
            <InsightSection
              reviewInsight={message.reviewInsight}
              chips={message.chips}
              onChipClick={onChipClick}
            />
            <AlternativesSection
              alternatives={message.alternatives}
              onSavePlace={onSavePlace}
              onSkipAlternative={onSkipAlternative}
              context={{
                planningSessionId: message?.planningSession?.planning_session_id || null,
                tripId: message?.savedTrip?.trip_id || null,
              }}
            />
          </>
        ) : null}
      </div>
    </motion.div>
  );
}