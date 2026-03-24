import { useMemo, useRef, useState, useEffect } from 'react';
// @ts-ignore
import { motion } from 'framer-motion';
// @ts-ignore
import { Send, Sparkles, Plus } from 'lucide-react';
import LoadingState from '../components/ui/LoadingState';
import PlaceCard from '../components/cards/PlaceCard';
import { createTravellerMemory, generateDestinationGuide } from '@/api/wayfarerApi';
import { getOrCreateTravellerId, getTravellerPersona } from '@/lib/travellerProfile';

const suggestedChips = [
  '3 days in Kyoto for food and culture',
  'Couple-friendly Lisbon guide',
  'Relaxed Prague itinerary',
  'Best city for a family cultural break',
  'Hidden gem city for food lovers',
];

function deriveGuidePayload(rawInput, persona) {
  const normalized = rawInput.toLowerCase();

  let destination = 'Kyoto';
  if (normalized.includes('lisbon')) destination = 'Lisbon';
  else if (normalized.includes('prague')) destination = 'Prague';
  else if (normalized.includes('kyoto')) destination = 'Kyoto';

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

function buildAssistantMessageFromGuide(result) {
  return {
    role: 'assistant',
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

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const persona = useMemo(() => getTravellerPersona(), []);
  const travellerId = useMemo(() => getOrCreateTravellerId(), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;

    setInput('');
    setErrorMessage('');

    const payload = deriveGuidePayload(msg, persona);
    const userMsg = { role: 'user', content: msg, timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
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
        },
      });
    } catch (error) {
      setErrorMessage(error.message || 'Unable to generate a destination guide right now.');
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
              Persona-aware destination guide powered by the V1 backend
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
                <LoadingState compact message="Building your destination guide..." />
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
            placeholder="Ask for a destination guide, e.g. 3 days in Kyoto for food and culture..."
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
        Ask for a destination guide and Wayfarer will use the current V1 backend contracts to build a structured response.
      </p>
      <p className="text-xs text-muted-foreground max-w-md mb-8">
        {persona?.summary
          ? persona.summary
          : 'Complete onboarding first to make destination guidance more personalized.'}
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
              <span className="font-medium">
                {reviewInsight.standout_themes.join(', ')}
              </span>
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

        {message.places?.length > 0 ? (
          <div className="mt-4 space-y-2">
            {message.places.map((place, i) => (
              <PlaceCard
                key={i}
                name={place.name}
                category={place.category}
                rating={place.rating}
                description={place.description}
                reason={place.why_recommended} image={undefined} distance={undefined} onSave={undefined} onClick={undefined}              />
            ))}
          </div>
        ) : null}

        <InsightSection
          reviewInsight={message.reviewInsight}
          chips={message.chips}
          onChipClick={onChipClick}
        />
      </div>
    </motion.div>
  );
}