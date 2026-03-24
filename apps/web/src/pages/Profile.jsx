import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { User, Settings, Sparkles, Globe, Heart, Utensils, Mountain, Palette, MapPin, TreePine, Music, Coffee, ChevronRight, LogOut } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import { useQuery } from '@tanstack/react-query';
import LoadingState from '../components/ui/LoadingState';
import { Slider } from '@/components/ui/slider';
import { Link } from 'react-router-dom';

const interestIcons = {
  food: Utensils,
  culture: Palette,
  adventure: Mountain,
  nature: TreePine,
  nightlife: Music,
  wellness: Coffee,
  local: MapPin,
};

export default function Profile() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    base44.auth.me().then(setUser).catch(() => {});
  }, []);

  const { data: profiles, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => base44.entities.TravellerProfile.list('-created_date', 1),
  });

  const profile = profiles?.[0];

  if (isLoading) return <LoadingState message="Loading profile..." />;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        {/* User Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center">
            <User className="w-7 h-7 text-muted-foreground" />
          </div>
          <div>
            <h1 className="font-serif text-2xl font-bold">{user?.full_name || 'Traveller'}</h1>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        {/* Travel Profile */}
        {profile ? (
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Style</p>
                <p className="font-semibold text-sm capitalize">{profile.social_mode || '—'}</p>
              </div>
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Budget</p>
                <p className="font-semibold text-sm capitalize">{profile.budget_level || '—'}</p>
              </div>
              <div className="p-4 rounded-xl bg-card border border-border text-center">
                <p className="text-xs text-muted-foreground mb-1">Pace</p>
                <p className="font-semibold text-sm capitalize">{profile.travel_pace || '—'}</p>
              </div>
            </div>

            {/* Interests */}
            {profile.interests?.length > 0 && (
              <div className="p-5 rounded-2xl bg-card border border-border">
                <h3 className="font-semibold text-sm mb-3">Your Interests</h3>
                <div className="flex flex-wrap gap-2">
                  {profile.interests.map((interest) => (
                    <span key={interest} className="px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-xs font-medium capitalize">
                      {interest}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Experience Biases */}
            {profile.experience_biases && (
              <div className="p-5 rounded-2xl bg-card border border-border">
                <h3 className="font-semibold text-sm mb-4">Experience Priorities</h3>
                <div className="space-y-4">
                  {Object.entries(profile.experience_biases).map(([key, value]) => (
                    <div key={key} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium capitalize">{key.replace('_', ' ')}</span>
                        <span className="text-xs text-muted-foreground">{Math.round(value * 100)}%</span>
                      </div>
                      <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${value * 100}%` }}
                          transition={{ delay: 0.3, duration: 0.5 }}
                          className="h-full bg-accent rounded-full"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Intelligence Card */}
            <div className="p-5 rounded-2xl bg-gradient-to-br from-lavender-light to-ocean-light border border-lavender/10">
              <div className="flex items-start gap-3">
                <Sparkles className="w-5 h-5 text-lavender flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-sm mb-1">Your Travel Intelligence</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Wayfarer is continuously learning from your preferences, trip feedback, and interactions. 
                    The more you use it, the better your recommendations become.
                  </p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-2">
              <Link to="/onboarding" className="flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:bg-secondary/30 transition-colors">
                <div className="flex items-center gap-3">
                  <Settings className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Edit Travel Preferences</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </Link>
              <button
                onClick={() => base44.auth.logout()}
                className="w-full flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:bg-secondary/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <LogOut className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Sign Out</span>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-7 h-7 text-muted-foreground" />
            </div>
            <h3 className="font-semibold mb-2">No travel profile yet</h3>
            <p className="text-sm text-muted-foreground mb-6">Complete your travel persona to get personalized recommendations.</p>
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium"
            >
              <Sparkles className="w-4 h-4" />
              Set Up Profile
            </Link>
          </div>
        )}
      </motion.div>
    </div>
  );
}