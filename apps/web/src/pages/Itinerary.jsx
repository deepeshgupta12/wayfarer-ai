import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Share2,
  Sparkles,
  Calendar,
  MapPin,
  RefreshCw,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { base44 } from '@/api/base44Client';
import LoadingState from '../components/ui/LoadingState';
import ActivityCard from '../components/cards/ActivityCard';

function normalizeDayActivities(day) {
  if (Array.isArray(day.activities) && day.activities.length > 0) {
    return day.activities;
  }

  if (Array.isArray(day.slots) && day.slots.length > 0) {
    return day.slots.map((slot) => ({
      time: slot.label,
      name: slot.assigned_place_name || 'Flexible slot',
      description: slot.summary,
      type: 'culture',
      location: slot.assigned_place_name || day.title,
      rating: undefined,
      reason: slot.rationale,
      fallbackNames: slot.fallback_candidate_names || [],
      slotType: slot.slot_type,
    }));
  }

  return [];
}

export default function Itinerary() {
  const [trip, setTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedDay, setExpandedDay] = useState(0);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tripId = urlParams.get('trip');
    if (tripId) {
      base44.entities.Trip.filter({ id: tripId }).then((trips) => {
        if (trips.length > 0) setTrip(trips[0]);
        setLoading(false);
      });
    } else {
      base44.entities.Trip.list('-created_date', 1).then((trips) => {
        if (trips.length > 0) setTrip(trips[0]);
        setLoading(false);
      });
    }
  }, []);

  if (loading) return <LoadingState message="Loading your itinerary..." />;
  if (!trip) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <h2 className="font-serif text-2xl font-bold mb-3">No itinerary found</h2>
        <p className="text-muted-foreground mb-6">Create a trip first to see your itinerary here.</p>
        <Link to="/plan" className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium">
          Go to Planner
        </Link>
      </div>
    );
  }

  const itinerary = trip.itinerary || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <Link
          to="/plan"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to trips
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold mb-1">{trip.title}</h1>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" /> {trip.destination}
              </span>
              {trip.start_date && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" /> {trip.start_date}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="px-3 py-2 rounded-lg border border-border text-sm hover:bg-secondary transition-colors">
              <Share2 className="w-4 h-4" />
            </button>
            <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20 transition-colors">
              <RefreshCw className="w-3.5 h-3.5" /> Regenerate
            </button>
          </div>
        </div>
      </motion.div>

      <div className="grid lg:grid-cols-[1fr_320px] gap-8">
        <div className="space-y-4">
          {itinerary.length > 0 ? (
            itinerary.map((day, i) => {
              const activities = normalizeDayActivities(day);

              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="rounded-2xl bg-card border border-border overflow-hidden"
                >
                  <button
                    onClick={() => setExpandedDay(expandedDay === i ? -1 : i)}
                    className="w-full flex items-center justify-between p-4 hover:bg-secondary/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                        D{day.day || day.day_number || i + 1}
                      </div>
                      <div className="text-left">
                        <h3 className="font-semibold text-sm">{day.title || `Day ${day.day || i + 1}`}</h3>
                        <p className="text-xs text-muted-foreground">{activities.length} activities</p>
                      </div>
                    </div>
                    {expandedDay === i ? (
                      <ChevronUp className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>
                  {expandedDay === i && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="px-4 pb-4 space-y-3"
                    >
                      {day.summary ? (
                        <div className="text-sm text-muted-foreground">{day.summary}</div>
                      ) : null}

                      {day.day_rationale ? (
                        <div className="text-xs text-muted-foreground">
                          <span className="font-medium">Day rationale:</span> {day.day_rationale}
                        </div>
                      ) : null}

                      {activities.map((activity, j) => (
                        <ActivityCard key={j} {...activity} index={j} onSwap={() => {}} />
                      ))}

                      {day.fallback_candidate_names?.length > 0 ? (
                        <div className="text-xs text-muted-foreground pt-1">
                          <span className="font-medium">Fallback direction:</span>{' '}
                          {day.fallback_candidate_names.join(', ')}
                        </div>
                      ) : null}
                    </motion.div>
                  )}
                </motion.div>
              );
            })
          ) : (
            <div className="p-8 rounded-2xl bg-card border border-border text-center">
              <Sparkles className="w-8 h-8 text-accent mx-auto mb-3" />
              <h3 className="font-semibold mb-1">No itinerary yet</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Let AI generate a personalized day-by-day plan for this trip.
              </p>
              <button className="px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium">
                Generate Itinerary
              </button>
            </div>
          )}
        </div>

        <div className="hidden lg:block space-y-4">
          <div className="p-4 rounded-2xl bg-card border border-border sticky top-6">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent" /> AI Insights
            </h3>
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-accent/5 border border-accent/10">
                <p className="text-xs text-muted-foreground">
                  This itinerary workspace now distinguishes between a true slot replacement and a case where the current option still remains the strongest fit.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-sage-light border border-sage/10">
                <p className="text-xs text-muted-foreground">
                  <strong>Tip:</strong> Use slot replacement when one part of the day feels too packed instead of rebuilding the whole trip.
                </p>
              </div>
              <div className="p-3 rounded-xl bg-ocean-light border border-ocean/10">
                <p className="text-xs text-muted-foreground">
                  <strong>Alternative:</strong> Day-level fallback candidates now act as the clearer next-best options when a stronger replacement exists.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}