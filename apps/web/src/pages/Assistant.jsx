import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, MapPin, Star, Bookmark, ArrowRight, RotateCcw, Plus } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import LoadingState from '../components/ui/LoadingState';
import PlaceCard from '../components/cards/PlaceCard';

const suggestedChips = [
  "Where should I go in April?",
  "Best food cities in Southeast Asia",
  "Hidden gems near Barcelona",
  "Family-friendly beach destinations",
  "Weekend trip from London",
];

const sampleCards = [
  { name: 'Tsukiji Outer Market', image: 'https://images.unsplash.com/photo-1553621042-f6e147245754?w=300&h=200&fit=crop', category: 'food', rating: 4.8, description: 'Fresh sushi and street food paradise. Best visited early morning.' },
  { name: 'Fushimi Inari Shrine', image: 'https://images.unsplash.com/photo-1478436127897-769e1b3f0f36?w=300&h=200&fit=crop', category: 'attraction', rating: 4.9, description: 'Iconic vermillion torii gates. Go at sunrise to avoid crowds.' },
];

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;
    setInput('');

    const userMsg = { role: 'user', content: msg, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    const result = await base44.integrations.Core.InvokeLLM({
      prompt: `You are Wayfarer, a premium AI travel assistant. You have deep knowledge of destinations worldwide. 
Be warm, knowledgeable, and specific. Include specific place names, practical tips, and explain why recommendations fit the traveller.
When recommending places, format with clear names and brief descriptions.
Keep responses concise but rich in useful detail.

User question: ${msg}`,
      response_json_schema: {
        type: "object",
        properties: {
          response: { type: "string" },
          places: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                category: { type: "string" },
                rating: { type: "number" },
                description: { type: "string" },
                why_recommended: { type: "string" }
              }
            }
          },
          follow_up_suggestions: {
            type: "array",
            items: { type: "string" }
          }
        }
      }
    });

    const assistantMsg = {
      role: 'assistant',
      content: result.response,
      places: result.places || [],
      chips: result.follow_up_suggestions || [],
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, assistantMsg]);
    setIsLoading(false);
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="h-screen flex flex-col max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-sunset flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="font-semibold text-sm">Wayfarer Assistant</h1>
            <p className="text-xs text-muted-foreground">Your intelligent travel companion</p>
          </div>
        </div>
        <button
          onClick={() => setMessages([])}
          className="p-2 rounded-lg hover:bg-secondary transition-colors text-muted-foreground"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {isEmpty ? (
          <EmptyChat onSuggestionClick={handleSend} />
        ) : (
          <div className="space-y-6">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} onChipClick={handleSend} />
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-sunset flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-white" />
                </div>
                <LoadingState compact message="Researching destinations..." />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 sm:px-6 py-4 border-t border-border">
        <div className="relative max-w-3xl mx-auto">
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask me about destinations, itineraries, or travel tips..."
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

function EmptyChat({ onSuggestionClick }) {
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
      <p className="text-muted-foreground text-sm max-w-sm mb-8">
        I'm your AI travel companion. Ask me about destinations, hidden gems, itineraries, or local tips — I'll give you personalized, review-backed answers.
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
        
        {message.places?.length > 0 && (
          <div className="mt-4 space-y-2">
            {message.places.map((place, i) => (
              <PlaceCard
                key={i}
                name={place.name}
                category={place.category}
                rating={place.rating}
                description={place.description}
                reason={place.why_recommended}
              />
            ))}
          </div>
        )}

        {message.chips?.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {message.chips.map((chip, i) => (
              <button
                key={i}
                onClick={() => onChipClick(chip)}
                className="px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors border border-border"
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}