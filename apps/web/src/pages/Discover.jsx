import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles, TrendingUp, Gem, Globe, ArrowRight } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DestinationCard from '../components/cards/DestinationCard';
import LoadingState from '../components/ui/LoadingState';
import { generateDestinationGuide, searchDestinations } from '@/api/wayfarerApi';
import { getPersonaUpdatedEventName, getTravellerPersona, getOrCreateTravellerId } from '@/lib/travellerProfile';

const categories = [
  { label: 'For You', icon: Sparkles },
  { label: 'Search', icon: Globe },
  { label: 'Guided Picks', icon: TrendingUp },
  { label: 'Hidden Gems', icon: Gem },
];

function deriveSearchSeed(persona) {
  if (!persona?.signals?.interests?.length) return 'Kyoto';
  const interests = persona.signals.interests;
  if (interests.includes('food') && interests.includes('culture')) return 'Kyoto';
  if (interests.includes('nightlife')) return 'Lisbon';
  if (interests.includes('nature')) return 'Prague';
  return 'Tokyo';
}

export default function Discover() {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState('For You');
  const [searchQuery, setSearchQuery] = useState('');
  const [liveResults, setLiveResults] = useState([]);
  const [featuredGuides, setFeaturedGuides] = useState([]);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [resultsError, setResultsError] = useState('');
  const [persona, setPersona] = useState(null);

  useEffect(() => {
    const refreshPersona = () => {
      setPersona(getTravellerPersona());
    };

    refreshPersona();

    const personaEventName = getPersonaUpdatedEventName();
    window.addEventListener('storage', refreshPersona);
    window.addEventListener('focus', refreshPersona);
    window.addEventListener(personaEventName, refreshPersona);

    return () => {
      window.removeEventListener('storage', refreshPersona);
      window.removeEventListener('focus', refreshPersona);
      window.removeEventListener(personaEventName, refreshPersona);
    };
  }, []);

  const seededQuery = useMemo(() => deriveSearchSeed(persona), [persona]);

  useEffect(() => {
    let active = true;

    async function loadDestinations() {
      setIsLoadingResults(true);
      setResultsError('');

      try {
        const response = await searchDestinations({
          query: searchQuery.trim() || seededQuery,
          traveller_id: getOrCreateTravellerId(),
          traveller_type: persona?.signals?.group_type || 'solo',
          interests: persona?.signals?.interests || [],
        });

        if (active) {
          setLiveResults(response.results || []);
        }
      } catch (error) {
        if (active) {
          setResultsError(error?.message || 'Unable to load destination results right now.');
          setLiveResults([]);
        }
      } finally {
        if (active) {
          setIsLoadingResults(false);
        }
      }
    }

    loadDestinations();
    return () => {
      active = false;
    };
  }, [persona, searchQuery, seededQuery]);

  useEffect(() => {
    let active = true;
    async function loadGuides() {
      const seeds = Array.from(new Set([seededQuery, 'Kyoto', 'Tokyo'])).slice(0, 3);
      try {
        const guides = await Promise.all(
          seeds.map((destination) =>
            generateDestinationGuide({
              destination,
              traveller_id: getOrCreateTravellerId(),
              duration_days: 3,
              traveller_type: persona?.signals?.group_type || 'solo',
              interests: persona?.signals?.interests || [],
              pace_preference: persona?.signals?.pace_preference || 'balanced',
              budget: persona?.signals?.travel_style || 'midrange',
            })
          )
        );
        if (active) setFeaturedGuides(guides);
      } catch {
        if (active) setFeaturedGuides([]);
      }
    }
    loadGuides();
    return () => {
      active = false;
    };
  }, [persona, seededQuery]);

  const searchCards = liveResults.map((item) => ({
    key: item.location_id,
    name: item.name,
    country: item.country,
    city: item.city,
    rating: item.rating,
    matchScore: undefined,
    photos: item.photos || [],
    tags: [item.category],
  }));

  const guideCards = featuredGuides.map((guide) => ({
    key: guide.destination,
    name: guide.destination,
    country: guide.destination,
    rating: null,
    matchScore: undefined,
    photos: guide.featured_photos || [],
    tags: guide.suggested_areas?.slice(0, 4) || [],
    isGem: false,
    description: guide.overview,
  }));

  const gemCards = featuredGuides.flatMap((guide) =>
    (guide.hidden_gems || []).map((gem) => ({
      key: `${guide.destination}-${gem.location_id}`,
      name: gem.name,
      country: gem.country,
      city: gem.city,
      rating: gem.rating,
      matchScore: undefined,
      photos: gem.photos || [],
      tags: gem.fit_reasons || [],
      isGem: true,
      description: gem.why_hidden_gem,
    }))
  );

  const cardsToRender =
    activeCategory === 'Guided Picks'
      ? guideCards
      : activeCategory === 'Hidden Gems'
      ? gemCards
      : searchCards;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Discover</h1>
        <p className="text-muted-foreground">Backend-powered destination exploration with photo-rich guide and hidden gem signals</p>
      </motion.div>

      <div className="flex flex-col md:flex-row gap-4 md:items-center md:justify-between mb-8">
        <div className="flex gap-1 p-1 bg-secondary/60 rounded-xl w-fit overflow-x-auto">
          {categories.map((category) => {
            const Icon = category.icon;
            return (
              <button
                key={category.label}
                onClick={() => setActiveCategory(category.label)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                  activeCategory === category.label
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {category.label}
              </button>
            );
          })}
        </div>

        <div className="relative w-full md:max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder={`Search destinations like ${seededQuery}`}
            className="w-full pl-10 pr-4 py-3 rounded-xl border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
      </div>

      {resultsError ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive mb-6">
          {resultsError}
        </div>
      ) : null}

      {isLoadingResults && activeCategory !== 'Guided Picks' ? <LoadingState message="Loading destinations..." /> : null}

      {activeCategory === 'Guided Picks' && featuredGuides.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {featuredGuides.map((guide, index) => (
            <motion.div key={guide.destination} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }} className="rounded-2xl border border-border bg-card p-4">
              <DestinationCard
                compact
                name={guide.destination}
                country={`${guide.traveller_type} • ${guide.duration_days} days`}
                photos={guide.featured_photos || []}
                tags={guide.suggested_areas || []}
                onClick={() => navigate(`/assistant?prompt=${encodeURIComponent(`Create a guide for ${guide.destination}`)}`)}
              />
              <p className="text-sm text-muted-foreground mt-3 line-clamp-3">{guide.overview}</p>
              <div className="mt-3 flex items-center justify-between">
                <div className="text-xs text-muted-foreground">{guide.hidden_gems?.length || 0} hidden gems</div>
                <Link to={`/assistant?prompt=${encodeURIComponent(`Plan ${guide.destination} for me`)}`} className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline">
                  Plan <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      ) : null}

      {activeCategory !== 'Guided Picks' && cardsToRender.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {cardsToRender.map((card, index) => (
            <motion.div key={card.key} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
              <DestinationCard
                name={card.name}
                country={card.country || card.city}
                rating={card.rating}
                photos={card.photos}
                tags={card.tags}
                isGem={card.isGem}
                onClick={() => navigate(`/assistant?prompt=${encodeURIComponent(`I want to explore ${card.name}`)}`)}
              />
            </motion.div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
