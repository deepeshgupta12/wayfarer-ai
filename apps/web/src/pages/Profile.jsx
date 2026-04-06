import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  User,
  Settings,
  Sparkles,
  Utensils,
  Mountain,
  Palette,
  MapPin,
  TreePine,
  Music,
  Coffee,
  ChevronRight,
  RefreshCw,
  Trash2,
  Loader2,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import LoadingState from '../components/ui/LoadingState';
import {
  deleteTravellerPersona,
  getTravellerPersonaFromApi,
  refreshTravellerPersonaFromMemory,
} from '@/api/wayfarerApi';
import {
  clearTravellerPersona,
  getOrCreateTravellerId,
  replaceTravellerPersona,
} from '@/lib/travellerProfile';

const interestIcons = {
  food: Utensils,
  culture: Palette,
  adventure: Mountain,
  nature: TreePine,
  nightlife: Music,
  wellness: Coffee,
  luxury: Sparkles,
  local: MapPin,
};

const paceLabels = {
  relaxed: 'Slow & relaxed',
  balanced: 'Balanced',
  fast: 'Action-packed',
};

const styleLabels = {
  budget: 'Budget',
  midrange: 'Moderate',
  luxury: 'Luxury',
};

const groupLabels = {
  solo: 'Solo',
  couple: 'With a partner',
  friends: 'With friends',
  family: 'With family',
};

export default function Profile() {
  const travellerId = getOrCreateTravellerId();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState('');
  const [isDeletingPersona, setIsDeletingPersona] = useState(false);

  const {
    data: persona,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['traveller-persona', travellerId],
    queryFn: () => getTravellerPersonaFromApi(travellerId),
    retry: 1,
  });

  const handleDeletePersona = async () => {
    const confirmed = window.confirm(
      'This will permanently delete your travel persona and all saved preferences. Continue?'
    );
    if (!confirmed) return;
    setIsDeletingPersona(true);
    try {
      await deleteTravellerPersona(travellerId);
      clearTravellerPersona();
      await refetch();
    } catch {
      // Silently swallow — the user sees no persona data anyway after clearing
    } finally {
      setIsDeletingPersona(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setRefreshError('');
    try {
      const updated = await refreshTravellerPersonaFromMemory(travellerId);
      replaceTravellerPersona(updated);
      await refetch();
    } catch (err) {
      setRefreshError(err?.message || 'Unable to refresh persona right now.');
    } finally {
      setIsRefreshing(false);
    }
  };

  if (isLoading) return <LoadingState message="Loading your travel profile..." />;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>

        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center">
            <User className="w-7 h-7 text-muted-foreground" />
          </div>
          <div>
            <h1 className="font-serif text-2xl font-bold">
              {persona?.archetype
                ? persona.archetype.replace(/\b\w/g, (c) => c.toUpperCase())
                : 'Traveller'}
            </h1>
            <p className="text-sm text-muted-foreground capitalize">
              {persona?.signals?.group_type
                ? groupLabels[persona.signals.group_type] || persona.signals.group_type
                : 'Your travel profile'}
            </p>
          </div>
        </div>

        {isError || !persona ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-7 h-7 text-muted-foreground" />
            </div>
            <h3 className="font-semibold mb-2">No travel profile yet</h3>
            <p className="text-sm text-muted-foreground mb-6">
              Complete your travel persona to get personalized recommendations.
            </p>
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium"
            >
              <Sparkles className="w-4 h-4" />
              Set Up Profile
            </Link>
          </div>
        ) : (
          <div className="space-y-6">

            {/* Summary card */}
            {persona.summary ? (
              <div className="p-5 rounded-2xl bg-gradient-to-br from-accent/8 to-card border border-accent/15">
                <p className="text-sm text-muted-foreground leading-relaxed italic">
                  &ldquo;{persona.summary}&rdquo;
                </p>
              </div>
            ) : null}

            {/* Quick stats */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Pace</p>
                <p className="font-semibold text-sm capitalize">
                  {paceLabels[persona.signals?.pace_preference] || persona.signals?.pace_preference || '—'}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Budget</p>
                <p className="font-semibold text-sm capitalize">
                  {styleLabels[persona.signals?.travel_style] || persona.signals?.travel_style || '—'}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Style</p>
                <p className="font-semibold text-sm capitalize">
                  {groupLabels[persona.signals?.group_type] || persona.signals?.group_type || '—'}
                </p>
              </div>
            </div>

            {/* Interests */}
            {Array.isArray(persona.signals?.interests) && persona.signals.interests.length > 0 ? (
              <div className="p-5 rounded-2xl bg-card border border-border">
                <h3 className="font-semibold text-sm mb-3">Your Interests</h3>
                <div className="flex flex-wrap gap-2">
                  {persona.signals.interests.map((interest) => {
                    const Icon = interestIcons[interest] || MapPin;
                    return (
                      <span
                        key={interest}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium capitalize"
                      >
                        <Icon className="w-3 h-3" />
                        {interest}
                      </span>
                    );
                  })}
                </div>
              </div>
            ) : null}

            {/* Intelligence card */}
            <div className="p-5 rounded-2xl bg-gradient-to-br from-lavender-light to-ocean-light border border-lavender/10">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-lavender flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-sm mb-1">Your Travel Intelligence</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Wayfarer continuously learns from your preferences, trip feedback, and
                    interactions. The more you use it, the better your recommendations become.
                  </p>
                </div>
              </div>
            </div>

            {/* Refresh error */}
            {refreshError ? (
              <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {refreshError}
              </div>
            ) : null}

            {/* Actions */}
            <div className="space-y-2">
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="w-full flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:bg-secondary/30 transition-colors disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  {isRefreshing
                    ? <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
                    : <RefreshCw className="w-4 h-4 text-muted-foreground" />
                  }
                  <span className="text-sm font-medium">
                    {isRefreshing ? 'Refreshing from memory…' : 'Refresh from travel memory'}
                  </span>
                </div>
                {!isRefreshing && <ChevronRight className="w-4 h-4 text-muted-foreground" />}
              </button>

              <Link
                to="/onboarding"
                className="flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:bg-secondary/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Settings className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Edit Travel Preferences</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </Link>

              <button
                onClick={handleDeletePersona}
                disabled={isDeletingPersona}
                className="w-full flex items-center justify-between p-4 rounded-xl bg-card border border-destructive/20 hover:bg-destructive/5 transition-colors disabled:opacity-50"
              >
                <div className="flex items-center gap-3">
                  {isDeletingPersona
                    ? <Loader2 className="w-4 h-4 text-destructive animate-spin" />
                    : <Trash2 className="w-4 h-4 text-destructive" />
                  }
                  <span className="text-sm font-medium text-destructive">
                    {isDeletingPersona ? 'Deleting…' : 'Reset persona'}
                  </span>
                </div>
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
