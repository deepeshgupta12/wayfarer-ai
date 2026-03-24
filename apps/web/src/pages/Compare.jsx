import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Plus, Sparkles, Loader2, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { base44 } from '@/api/base44Client';
import LoadingState from '../components/ui/LoadingState';
import ComparisonResult from '../components/compare/ComparisonResult';

export default function Compare() {
  const [destA, setDestA] = useState('');
  const [destB, setDestB] = useState('');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCompare = async () => {
    if (!destA || !destB) return;
    setLoading(true);
    setComparison(null);

    const result = await base44.integrations.Core.InvokeLLM({
      prompt: `Compare these two travel destinations in detail: "${destA}" vs "${destB}".
Evaluate across these dimensions: Vibe, Food Scene, Walkability, Value for Money, Romance, Family-Friendliness, Cultural Richness, Safety, Nightlife, Nature & Scenery.
Give each a score from 1-10 and a brief explanation.
Also provide an overall recommendation based on different traveller types.
Be specific, evidence-backed, and helpful for decision-making.`,
      response_json_schema: {
        type: "object",
        properties: {
          destination_a: {
            type: "object",
            properties: {
              name: { type: "string" },
              tagline: { type: "string" },
              best_for: { type: "string" },
              image_hint: { type: "string" }
            }
          },
          destination_b: {
            type: "object",
            properties: {
              name: { type: "string" },
              tagline: { type: "string" },
              best_for: { type: "string" },
              image_hint: { type: "string" }
            }
          },
          dimensions: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                score_a: { type: "number" },
                score_b: { type: "number" },
                note_a: { type: "string" },
                note_b: { type: "string" }
              }
            }
          },
          verdict: { type: "string" },
          recommendation_solo: { type: "string" },
          recommendation_couple: { type: "string" },
          recommendation_family: { type: "string" }
        }
      }
    });

    setComparison(result);
    setLoading(false);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <Link to="/discover" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Discover
        </Link>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Compare Destinations</h1>
        <p className="text-muted-foreground mb-8">Side-by-side evaluation to help you decide</p>
      </motion.div>

      {/* Input */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid sm:grid-cols-[1fr_auto_1fr] gap-4 items-end mb-10"
      >
        <div>
          <label className="text-sm font-medium mb-1.5 block">Destination A</label>
          <input
            type="text"
            placeholder="e.g., Barcelona"
            value={destA}
            onChange={(e) => setDestA(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex items-center justify-center py-2">
          <span className="text-sm font-bold text-muted-foreground">VS</span>
        </div>
        <div>
          <label className="text-sm font-medium mb-1.5 block">Destination B</label>
          <input
            type="text"
            placeholder="e.g., Lisbon"
            value={destB}
            onChange={(e) => setDestB(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </motion.div>

      <div className="flex justify-center mb-10">
        <button
          onClick={handleCompare}
          disabled={!destA || !destB || loading}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? 'Comparing...' : 'Compare with AI'}
        </button>
      </div>

      {loading && <LoadingState message="Analyzing both destinations across multiple dimensions..." />}
      {comparison && <ComparisonResult data={comparison} />}
    </div>
  );
}