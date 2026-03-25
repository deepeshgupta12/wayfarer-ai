import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus, Sparkles, Calendar, MapPin } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import EmptyState from '../components/ui/EmptyState';
import LoadingState from '../components/ui/LoadingState';
import TripPlanCard from '../components/cards/TripPlanCard';
import NewTripModal from '../components/plan/NewTripModal';
import { listStoredTrips } from '@/lib/tripStorage';

export default function Plan() {
  const [showNewTrip, setShowNewTrip] = useState(false);

  const {
    data: trips = [],
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['stored-trips'],
    queryFn: async () => listStoredTrips(),
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-8"
      >
        <div>
          <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Plan</h1>
          <p className="text-muted-foreground">Build and manage your trip itineraries</p>
        </div>

        <button
          onClick={() => setShowNewTrip(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">New Trip</span>
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid sm:grid-cols-3 gap-3 mb-10"
      >
        <Link
          to="/assistant"
          className="group p-4 rounded-xl bg-gradient-to-br from-accent/5 to-accent/10 border border-accent/10 hover:border-accent/20 transition-all"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h3 className="font-medium text-sm">AI-Generate Itinerary</h3>
              <p className="text-xs text-muted-foreground">Let AI plan your perfect trip</p>
            </div>
          </div>
        </Link>

        <Link
          to="/compare"
          className="group p-4 rounded-xl bg-gradient-to-br from-ocean/5 to-ocean/10 border border-ocean/10 hover:border-ocean/20 transition-all"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-ocean/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <MapPin className="w-5 h-5 text-ocean" />
            </div>
            <div>
              <h3 className="font-medium text-sm">Compare Destinations</h3>
              <p className="text-xs text-muted-foreground">Side-by-side evaluation</p>
            </div>
          </div>
        </Link>

        <Link
          to="/discover"
          className="group p-4 rounded-xl bg-gradient-to-br from-sage/5 to-sage/10 border border-sage/10 hover:border-sage/20 transition-all"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sage/20 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Calendar className="w-5 h-5 text-sage" />
            </div>
            <div>
              <h3 className="font-medium text-sm">Explore Destinations</h3>
              <p className="text-xs text-muted-foreground">Find your next adventure</p>
            </div>
          </div>
        </Link>
      </motion.div>

      {isLoading ? (
        <LoadingState message="Loading your trips..." />
      ) : !trips || trips.length === 0 ? (
        <EmptyState
          icon={MapPin}
          title="No trips yet"
          description="Start planning your next adventure. Create a trip and let our AI help build the perfect itinerary."
          action={() => setShowNewTrip(true)}
          actionLabel="Plan Your First Trip"
        />
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {trips.map((trip, i) => (
            <motion.div
              key={trip.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <TripPlanCard trip={trip} />
            </motion.div>
          ))}
        </div>
      )}

      {showNewTrip ? (
        <NewTripModal
          onClose={() => setShowNewTrip(false)}
          onCreated={() => {
            refetch();
          }}
        />
      ) : null}
    </div>
  );
}