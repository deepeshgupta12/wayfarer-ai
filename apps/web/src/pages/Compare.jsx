import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import LoadingState from '../components/ui/LoadingState';
import ComparisonResult from '../components/compare/ComparisonResult';
import { compareDestinations, createTravellerMemory } from '@/api/wayfarerApi';
import { getOrCreateTravellerId, getTravellerPersona } from '@/lib/travellerProfile';

export default function Compare() {
  const [destA, setDestA] = useState('');
  const [destB, setDestB] = useState('');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleCompare = async () => {
    if (!destA.trim() || !destB.trim()) return;

    setLoading(true);
    setComparison(null);
    setErrorMessage('');

    try {
      const travellerId = getOrCreateTravellerId();
      const persona = getTravellerPersona();

      const payload = {
        destination_a: destA.trim(),
        destination_b: destB.trim(),
        traveller_type: persona?.signals?.group_type || 'solo',
        interests: persona?.signals?.interests || [],
        pace_preference: persona?.signals?.pace_preference || 'balanced',
        budget: persona?.signals?.travel_style || 'midrange',
        duration_days: 4,
      };

      const result = await compareDestinations(payload);
      setComparison(result);

      await createTravellerMemory({
        traveller_id: travellerId,
        event_type: 'destination_comparison_generated',
        source_surface: 'compare_page',
        payload: {
          destination_a: result.destination_a?.name || payload.destination_a,
          destination_b: result.destination_b?.name || payload.destination_b,
          traveller_type: payload.traveller_type,
          interests: payload.interests,
          winner:
            (result.destination_a?.weighted_score || 0) >= (result.destination_b?.weighted_score || 0)
              ? result.destination_a?.name
              : result.destination_b?.name,
        },
      });
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to compare destinations right now.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlanDestination = (destinationName) => {
    if (!destinationName) return;
    navigate(`/assistant?prompt=${encodeURIComponent(`I have 4 days in ${destinationName} for a personalized trip`)}`);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <Link to="/discover" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Discover
        </Link>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Compare Destinations</h1>
        <p className="text-muted-foreground mb-8">Structured, persona-weighted comparison connected directly to planning flows</p>
      </motion.div>

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
            placeholder="e.g., Prague"
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
            placeholder="e.g., Budapest"
            value={destB}
            onChange={(e) => setDestB(e.target.value)}
            className="w-full px-4 py-3 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </motion.div>

      <div className="flex justify-center mb-8">
        <button
          onClick={handleCompare}
          disabled={!destA.trim() || !destB.trim() || loading}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? 'Comparing...' : 'Compare with Wayfarer'}
        </button>
      </div>

      {loading ? <LoadingState message="Comparing destinations with persona-weighted backend scoring..." /> : null}

      {errorMessage ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive mb-6">
          {errorMessage}
        </div>
      ) : null}

      {comparison ? <ComparisonResult data={comparison} onPlanDestination={handlePlanDestination} /> : null}
    </div>
  );
}