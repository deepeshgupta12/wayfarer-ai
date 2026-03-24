import { useState } from 'react';
import { motion } from 'framer-motion';
import { Briefcase, Heart, Clock, Star, Filter } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { base44 } from '@/api/base44Client';
import EmptyState from '../components/ui/EmptyState';
import LoadingState from '../components/ui/LoadingState';
import TripPlanCard from '../components/cards/TripPlanCard';
import SavedPlacesList from '../components/trips/SavedPlacesList';

const tabs = [
  { id: 'trips', label: 'My Trips', icon: Briefcase },
  { id: 'saved', label: 'Saved Places', icon: Heart },
  { id: 'history', label: 'Past Trips', icon: Clock },
];

export default function Trips() {
  const [activeTab, setActiveTab] = useState('trips');

  const { data: trips, isLoading: tripsLoading } = useQuery({
    queryKey: ['trips'],
    queryFn: () => base44.entities.Trip.list('-created_date', 50),
  });

  const { data: savedPlaces, isLoading: placesLoading } = useQuery({
    queryKey: ['savedPlaces'],
    queryFn: () => base44.entities.SavedPlace.list('-created_date', 50),
  });

  const activeTripsList = trips?.filter(t => ['planning', 'upcoming', 'active'].includes(t.status)) || [];
  const pastTripsList = trips?.filter(t => t.status === 'completed') || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Your Trips</h1>
        <p className="text-muted-foreground">Your travel memory — past, present, and future</p>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-secondary/60 rounded-xl w-fit mb-8">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {activeTab === 'trips' && (
        tripsLoading ? <LoadingState message="Loading trips..." /> :
        activeTripsList.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No active trips"
            description="Your upcoming and in-progress trips will appear here. Start planning your next adventure!"
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {activeTripsList.map((trip, i) => (
              <motion.div key={trip.id} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <TripPlanCard trip={trip} />
              </motion.div>
            ))}
          </div>
        )
      )}

      {activeTab === 'saved' && (
        placesLoading ? <LoadingState message="Loading saved places..." /> :
        !savedPlaces || savedPlaces.length === 0 ? (
          <EmptyState
            icon={Heart}
            title="No saved places yet"
            description="Places you save from recommendations and discoveries will appear here for easy access."
          />
        ) : (
          <SavedPlacesList places={savedPlaces} />
        )
      )}

      {activeTab === 'history' && (
        tripsLoading ? <LoadingState message="Loading history..." /> :
        pastTripsList.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No past trips"
            description="Completed trips and your travel memories will live here. Wayfarer learns from each trip to improve future recommendations."
          />
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {pastTripsList.map((trip, i) => (
              <motion.div key={trip.id} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <TripPlanCard trip={trip} />
              </motion.div>
            ))}
          </div>
        )
      )}

      {/* Memory Insight */}
      {activeTab === 'history' && pastTripsList.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-10 p-5 rounded-2xl bg-gradient-to-r from-lavender-light to-sage-light border border-lavender/10"
        >
          <div className="flex items-start gap-3">
            <Star className="w-5 h-5 text-lavender flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-sm mb-1">Your Travel Intelligence is Growing</h3>
              <p className="text-xs text-muted-foreground">
                With {pastTripsList.length} completed {pastTripsList.length === 1 ? 'trip' : 'trips'}, Wayfarer is learning your preferences. Future recommendations will be even more personalized.
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}