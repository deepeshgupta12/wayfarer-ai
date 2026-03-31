import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import LoadingState from '../components/ui/LoadingState';
import ComparisonResult from '../components/compare/ComparisonResult';
import {
  compareDestinations,
  createTravellerMemory,
  createTripPlanFromComparison,
} from '@/api/wayfarerApi';
import { getOrCreateTravellerId, getTravellerPersona } from '@/lib/travellerProfile';
import { cacheTripPlan } from '@/lib/tripStorage';

const STARTER_PAIRS = [
  ['Prague', 'Budapest'],
  ['Kyoto', 'Tokyo'],
  ['Lisbon', 'Prague'],
];

function deriveDuration(persona) {
  const pace = persona?.signals?.pace_preference || 'balanced';
  if (pace === 'relaxed') return 5;
  if (pace === 'fast') return 3;
  return 4;
}

export default function Compare() {
  const [destA, setDestA] = useState('');
  const [destB, setDestB] = useState('');
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [creatingPlan, setCreatingPlan] = useState('');
  const navigate = useNavigate();

  const travellerId = useMemo(() => getOrCreateTravellerId(), []);
  const persona = getTravellerPersona();
  const recommendedDuration = deriveDuration(persona);

  const handleCompare = async () => {
    if (!destA.trim() || !destB.trim()) return;

    setLoading(true);
    setComparison(null);
    setErrorMessage('');

    try {
      const payload = {
        destination_a: destA.trim(),
        destination_b: destB.trim(),
        traveller_type: persona?.signals?.group_type || 'solo',
        interests: persona?.signals?.interests || [],
        pace_preference: persona?.signals?.pace_preference || 'balanced',
        budget: persona?.signals?.travel_style || 'midrange',
        duration_days: recommendedDuration,
        traveller_id: travellerId,
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
          comparison_id: result.comparison_id,
        },
      });
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to compare destinations right now.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlanDestination = async (destinationName, option) => {
    if (!comparison || !destinationName) return;

    setCreatingPlan(destinationName);
    setErrorMessage('');

    try {
      const plan = await createTripPlanFromComparison({
        traveller_id: travellerId,
        source_surface: 'compare',
        duration_days: recommendedDuration,
        group_type: persona?.signals?.group_type || 'solo',
        interests: persona?.signals?.interests || [],
        pace_preference: persona?.signals?.pace_preference || 'balanced',
        budget: persona?.signals?.travel_style || 'midrange',
        comparison_context: {
          comparison_id: comparison.comparison_id,
          source_surface: 'compare',
          destination_a: comparison.destination_a?.name,
          destination_b: comparison.destination_b?.name,
          selected_branch: option?.branch || null,
          selected_destination: destinationName,
          selected_location_id: option?.location_id || null,
          verdict: comparison.verdict,
          planning_recommendation: comparison.planning_recommendation,
          options: (comparison.plan_start_options || []).map((item) => ({
            branch: item.branch,
            location_id: item.location_id,
            destination: item.destination,
            weighted_score: item.weighted_score,
            why_pick_this: item.recommended
              ? 'Recommended from comparison result.'
              : 'Alternate branch from comparison result.',
          })),
        },
      });

      cacheTripPlan(plan);
      navigate(
        `/assistant?planning_session_id=${encodeURIComponent(
          plan.planning_session_id
        )}&prompt=${encodeURIComponent(`Plan ${destinationName} using my selected comparison branch`)}`
      );
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to create planning branch from comparison.');
    } finally {
      setCreatingPlan('');
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to="/discover"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Discover
        </Link>

        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Compare Destinations</h1>
        <p className="text-muted-foreground mb-6">
          Decision-oriented destination comparison tied directly to itinerary planning.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-border bg-card p-5 mb-8"
      >
        <div className="flex flex-wrap gap-2 mb-4">
          {STARTER_PAIRS.map(([a, b]) => (
            <button
              key={`${a}-${b}`}
              onClick={() => {
                setDestA(a);
                setDestB(b);
              }}
              className="px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors border border-border"
            >
              {a} vs {b}
            </button>
          ))}
        </div>

        <div className="grid sm:grid-cols-[1fr_auto_1fr] gap-4 items-end">
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
        </div>

        <div className="mt-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="text-sm text-muted-foreground">
            Comparison duration lens: <span className="font-medium text-foreground">{recommendedDuration} days</span>
          </div>

          <button
            onClick={handleCompare}
            disabled={!destA.trim() || !destB.trim() || loading}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? 'Comparing...' : 'Compare with Wayfarer'}
          </button>
        </div>
      </motion.div>

      {loading ? (
        <LoadingState message="Comparing destinations with persona-weighted scoring and visual ranking..." />
      ) : null}

      {creatingPlan ? (
        <div className="rounded-xl border border-accent/20 bg-accent/5 px-4 py-3 text-sm text-accent mb-6">
          Creating planning branch for {creatingPlan}…
        </div>
      ) : null}

      {errorMessage ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive mb-6">
          {errorMessage}
        </div>
      ) : null}

      {comparison ? (
        <ComparisonResult
          data={comparison}
          onPlanDestination={handlePlanDestination}
          durationDays={recommendedDuration}
        />
      ) : null}
    </div>
  );
}