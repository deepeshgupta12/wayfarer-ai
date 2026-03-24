import { useState } from 'react';
import { motion } from 'framer-motion';
import { Navigation, MapPin, Coffee, Utensils, TreePine, Gem, Zap, Users, Loader2, Sparkles } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import PlaceCard from '../components/cards/PlaceCard';
import LoadingState from '../components/ui/LoadingState';

const quickModes = [
  { id: 'food', label: 'Food Now', icon: Utensils, emoji: '🍽️' },
  { id: 'coffee', label: 'Quick Coffee', icon: Coffee, emoji: '☕' },
  { id: 'walk', label: 'Relaxed Walk', icon: TreePine, emoji: '🚶' },
  { id: 'hidden', label: 'Something Underrated', icon: Gem, emoji: '💎' },
  { id: 'quick', label: 'Quick Stop', icon: Zap, emoji: '⚡' },
  { id: 'family', label: 'Family-Safe', icon: Users, emoji: '👨‍👩‍👧' },
];

export default function Nearby() {
  const [activeMode, setActiveMode] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locationGranted, setLocationGranted] = useState(null);

  const handleModeSelect = async (mode) => {
    setActiveMode(mode.id);
    setLoading(true);

    const result = await base44.integrations.Core.InvokeLLM({
      prompt: `You are Wayfarer's on-ground AI assistant. The user wants: "${mode.label}".
Generate 5 realistic, specific place recommendations for a traveller looking for this right now.
Include name, category (restaurant/cafe/park/attraction/experience/hidden_gem), rating (4.0-5.0), description, and a short reason why this fits the request.
Make them feel real, specific, and varied. Include some hidden gems.`,
      response_json_schema: {
        type: "object",
        properties: {
          places: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                category: { type: "string" },
                rating: { type: "number" },
                description: { type: "string" },
                distance: { type: "string" },
                reason: { type: "string" },
                is_hidden_gem: { type: "boolean" }
              }
            }
          },
          context_note: { type: "string" }
        }
      }
    });

    setResults(result.places || []);
    setLoading(false);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent/20 to-sunset/20 flex items-center justify-center">
            <Navigation className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold">Nearby</h1>
            <p className="text-sm text-muted-foreground">On-ground intelligence, right now</p>
          </div>
        </div>
      </motion.div>

      {/* Quick Mode Selector */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <h3 className="text-sm font-medium text-muted-foreground mb-3">What are you looking for?</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {quickModes.map((mode) => {
            const Icon = mode.icon;
            return (
              <motion.button
                key={mode.id}
                whileTap={{ scale: 0.97 }}
                onClick={() => handleModeSelect(mode)}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all ${
                  activeMode === mode.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-muted-foreground/30 bg-card'
                }`}
              >
                <span className="text-2xl">{mode.emoji}</span>
                <span className="font-medium text-sm">{mode.label}</span>
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Results */}
      {loading ? (
        <LoadingState message="Finding the best spots nearby..." />
      ) : results.length > 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-3"
        >
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-accent" />
            <h3 className="font-semibold text-sm">Recommendations for you</h3>
            <span className="text-xs text-muted-foreground">({results.length} found)</span>
          </div>
          {results.map((place, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <PlaceCard
                name={place.name}
                category={place.category}
                rating={place.rating}
                description={place.description}
                distance={place.distance}
                reason={place.reason}
                isGem={place.is_hidden_gem}
              />
            </motion.div>
          ))}
        </motion.div>
      ) : !activeMode ? (
        <div className="text-center py-16">
          <motion.div
            animate={{ y: [0, -5, 0] }}
            transition={{ duration: 3, repeat: Infinity }}
            className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4"
          >
            <MapPin className="w-7 h-7 text-muted-foreground" />
          </motion.div>
          <h3 className="font-semibold mb-2">Your live travel companion</h3>
          <p className="text-sm text-muted-foreground max-w-xs mx-auto">
            Select what you're looking for and get context-aware recommendations instantly.
          </p>
        </div>
      ) : null}
    </div>
  );
}