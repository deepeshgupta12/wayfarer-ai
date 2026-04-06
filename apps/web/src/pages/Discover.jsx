import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Sparkles, TrendingUp, Gem, Globe, ArrowRight, Compass } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import DestinationCard from '../components/cards/DestinationCard';
import PlaceCard from '../components/cards/PlaceCard';
import LoadingState from '../components/ui/LoadingState';
import { generateDestinationGuide, searchDestinations } from '@/api/wayfarerApi';
import {
  getPersonaUpdatedEventName,
  getTravellerPersona,
  getOrCreateTravellerId,
} from '@/lib/travellerProfile';

const categories = [
  { label: 'For You', icon: Sparkles },
  { label: 'Search', icon: Globe },
  { label: 'Guided Picks', icon: TrendingUp },
  { label: 'Hidden Gems', icon: Gem },
];

const DESTINATION_LIKE_CATEGORIES = new Set([
  'city',
  'region',
  'country',
  'island',
  'neighborhood',
  'district',
]);

const PLACE_LIKE_CATEGORIES = new Set([
  'market',
  'park',
  'museum',
  'temple',
  'restaurant',
  'attraction',
  'place',
  'riverfront',
]);

// Maps persona signals to a primary seed destination.
function deriveSearchSeed(persona) {
  const interests = persona?.signals?.interests || [];
  const pace = persona?.signals?.pace_preference || 'balanced';
  const style = persona?.signals?.travel_style || 'midrange';
  const group = persona?.signals?.group_type || 'solo';

  if (interests.includes('adventure') && interests.includes('nature')) return 'Queenstown';
  if (interests.includes('wellness') && pace === 'relaxed') return 'Ubud';
  if (interests.includes('luxury') || style === 'luxury') return 'Dubai';
  if (interests.includes('nightlife') && group === 'friends') return 'Barcelona';
  if (interests.includes('nightlife')) return 'Lisbon';
  if (interests.includes('food') && interests.includes('culture') && group === 'couple') return 'Rome';
  if (interests.includes('food') && interests.includes('culture')) return 'Kyoto';
  if (interests.includes('culture') && interests.includes('adventure')) return 'Istanbul';
  if (interests.includes('nature') && group === 'family') return 'Sydney';
  if (interests.includes('nature')) return 'Prague';
  if (group === 'family') return 'Singapore';
  if (group === 'couple') return 'Paris';
  if (style === 'budget') return 'Bangkok';
  return 'Tokyo';
}

// Returns a complementary second seed that differs from the primary.
// Keeps guide cards diverse without hammering unrelated hardcodes.
function deriveSecondSeed(persona, primarySeed) {
  const interests = persona?.signals?.interests || [];
  const group = persona?.signals?.group_type || 'solo';
  const style = persona?.signals?.travel_style || 'midrange';

  const CANDIDATES = [
    interests.includes('food') ? 'Tokyo' : null,
    interests.includes('culture') ? 'Lisbon' : null,
    interests.includes('adventure') ? 'Medellin' : null,
    interests.includes('nature') ? 'Queenstown' : null,
    group === 'couple' ? 'Kyoto' : null,
    group === 'family' ? 'Amsterdam' : null,
    style === 'budget' ? 'Hanoi' : null,
    'Seoul',
    'Barcelona',
    'Cape Town',
  ].filter(Boolean);

  return CANDIDATES.find((c) => c !== primarySeed) || 'Seoul';
}

function normalizeCategory(value) {
  return String(value || '').trim().toLowerCase();
}

function uniqueBy(items, keyGetter) {
  const seen = new Set();
  return items.filter((item) => {
    const key = keyGetter(item);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isDestinationLike(item) {
  return DESTINATION_LIKE_CATEGORIES.has(normalizeCategory(item?.category));
}

function isPlaceLike(item) {
  return PLACE_LIKE_CATEGORIES.has(normalizeCategory(item?.category));
}

function buildGuidePrompt(destination) {
  return `Create a guide for ${destination}`;
}

function buildExplorePrompt(name) {
  return `I want to explore ${name}`;
}

function buildPlanPrompt(destination) {
  return `Plan ${destination} for me`;
}

export default function Discover() {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState('For You');
  const [searchQuery, setSearchQuery] = useState('');
  const [liveResults, setLiveResults] = useState([]);
  const [featuredGuides, setFeaturedGuides] = useState([]);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [isLoadingGuides, setIsLoadingGuides] = useState(false);
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
  const travellerId = useMemo(() => getOrCreateTravellerId(), []);

  useEffect(() => {
    let active = true;

    async function loadDestinations() {
      setIsLoadingResults(true);
      setResultsError('');

      try {
        const response = await searchDestinations({
          query: searchQuery.trim() || seededQuery,
          traveller_id: travellerId,
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
  }, [persona, searchQuery, seededQuery, travellerId]);

  useEffect(() => {
    let active = true;

    async function loadGuides() {
      setIsLoadingGuides(true);

      const primarySeed = seededQuery || deriveSearchSeed(persona);
      const secondSeed = deriveSecondSeed(persona, primarySeed);
      const seeds = Array.from(new Set([primarySeed, secondSeed])).slice(0, 2);

      try {
        const guides = await Promise.all(
          seeds.map((destination) =>
            generateDestinationGuide({
              destination,
              traveller_id: travellerId,
              duration_days: 3,
              traveller_type: persona?.signals?.group_type || 'solo',
              interests: persona?.signals?.interests || [],
              pace_preference: persona?.signals?.pace_preference || 'balanced',
              budget: persona?.signals?.travel_style || 'midrange',
            })
          )
        );

        if (active) {
          setFeaturedGuides(
            uniqueBy(
              (guides || []).filter((guide) => guide?.destination),
              (guide) => guide.destination
            )
          );
        }
      } catch {
        if (active) {
          setFeaturedGuides([]);
        }
      } finally {
        if (active) {
          setIsLoadingGuides(false);
        }
      }
    }

    loadGuides();

    return () => {
      active = false;
    };
  }, [persona, seededQuery, travellerId]);

  const destinationResults = useMemo(
    () => uniqueBy(liveResults.filter((item) => isDestinationLike(item)), (item) => item.location_id),
    [liveResults]
  );

  const placeResults = useMemo(
    () => uniqueBy(liveResults.filter((item) => isPlaceLike(item)), (item) => item.location_id),
    [liveResults]
  );

  const guideCards = useMemo(
    () =>
      uniqueBy(
        featuredGuides.map((guide) => ({
          key: guide.destination,
          destination: guide.destination,
          name: guide.destination,
          country: guide.destination,
          subtitle: `${guide.traveller_type} • ${guide.duration_days} days`,
          photos: guide.featured_photos || [],
          tags: (guide.suggested_areas || []).slice(0, 4),
          description: guide.overview,
          hiddenGemCount: (guide.hidden_gems || []).length,
        })),
        (item) => item.destination
      ),
    [featuredGuides]
  );

  const gemCards = useMemo(
    () =>
      uniqueBy(
        featuredGuides.flatMap((guide) =>
          (guide.hidden_gems || [])
            .filter((gem) => !DESTINATION_LIKE_CATEGORIES.has(normalizeCategory(gem.category)))
            .map((gem) => ({
              key: `${guide.destination}-${gem.location_id}`,
              location_id: gem.location_id,
              name: gem.name,
              city: gem.city,
              country: gem.country,
              category: gem.category,
              rating: gem.rating,
              photos: gem.photos || [],
              tags: gem.fit_reasons || [],
              description: gem.why_hidden_gem,
              reason: `From ${guide.destination} hidden-gem picks`,
              sourceDestination: guide.destination,
            }))
        ),
        (item) => item.location_id
      ),
    [featuredGuides]
  );

  const personaSummary =
    persona?.summary ||
    'Complete onboarding to improve Discover curation, compare weighting, and guide quality.';

  const showSearchLoading = isLoadingResults && activeCategory !== 'Guided Picks' && activeCategory !== 'For You';
  const showGuideLoading = isLoadingGuides && (activeCategory === 'Guided Picks' || activeCategory === 'For You');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Discover</h1>
        <p className="text-muted-foreground">
          Curated destination exploration with clearer destination picks, place-level gems, and stronger visual fallbacks.
        </p>
      </motion.div>

      <div className="rounded-2xl border border-border bg-card p-5 mb-8">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center flex-shrink-0">
            <Compass className="w-5 h-5 text-accent" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold mb-1">Your current discovery lens</div>
            <p className="text-sm text-muted-foreground">{personaSummary}</p>
          </div>
        </div>
      </div>

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

      {showSearchLoading ? <LoadingState message="Loading curated destination results..." /> : null}
      {showGuideLoading ? <LoadingState message="Refreshing guided picks..." /> : null}

      {activeCategory === 'For You' ? (
        <div className="space-y-10">
          <section>
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold">Guided picks for you</h2>
                <p className="text-sm text-muted-foreground">
                  Destination-grade guides matched to your current travel profile.
                </p>
              </div>
              <button
                onClick={() => setActiveCategory('Guided Picks')}
                className="text-sm font-medium text-accent hover:underline"
              >
                View all
              </button>
            </div>

            {guideCards.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {guideCards.slice(0, 3).map((guide, index) => (
                  <motion.div
                    key={guide.key}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="rounded-2xl border border-border bg-card p-4"
                  >
                    <DestinationCard
                      compact
                      typeLabel="Destination guide"
                      name={guide.name}
                      subtitle={guide.subtitle}
                      photos={guide.photos}
                      tags={guide.tags}
                      description={guide.description}
                      onClick={() =>
                        navigate(`/assistant?prompt=${encodeURIComponent(buildGuidePrompt(guide.destination))}`)
                      }
                    />
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div className="text-xs text-muted-foreground">
                        {guide.hiddenGemCount} hidden gems surfaced
                      </div>
                      <Link
                        to={`/assistant?prompt=${encodeURIComponent(buildPlanPrompt(guide.destination))}`}
                        className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
                      >
                        Plan <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </motion.div>
                ))}
              </div>
            ) : !isLoadingGuides ? (
              <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
                Guided picks are not available right now.
              </div>
            ) : null}
          </section>

          <section>
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold">Destination matches</h2>
                <p className="text-sm text-muted-foreground">
                  Cleaner destination results separated from place-level exploration.
                </p>
              </div>
              <button
                onClick={() => setActiveCategory('Search')}
                className="text-sm font-medium text-accent hover:underline"
              >
                Search view
              </button>
            </div>

            {destinationResults.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {destinationResults.slice(0, 6).map((card, index) => (
                  <motion.div
                    key={card.location_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <DestinationCard
                      typeLabel="Destination"
                      name={card.name}
                      country={card.country}
                      city={card.city}
                      rating={card.rating}
                      photos={card.photos || []}
                      tags={[card.category]}
                      onClick={() =>
                        navigate(`/assistant?prompt=${encodeURIComponent(buildExplorePrompt(card.name))}`)
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : !isLoadingResults ? (
              <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
                No destination matches are available right now.
              </div>
            ) : null}
          </section>

          <section>
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="text-lg font-semibold">Hidden gem places</h2>
                <p className="text-sm text-muted-foreground">
                  Place-level picks only, filtered away from broad destination cards.
                </p>
              </div>
              <button
                onClick={() => setActiveCategory('Hidden Gems')}
                className="text-sm font-medium text-accent hover:underline"
              >
                View all
              </button>
            </div>

            {gemCards.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                {gemCards.slice(0, 4).map((card, index) => (
                  <motion.div
                    key={card.key}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <PlaceCard
                      name={card.name}
                      category={card.category}
                      rating={card.rating}
                      photos={card.photos}
                      tags={card.tags}
                      description={card.description}
                      reason={card.reason}
                      isGem
                      showSaveButton={false}
                      onClick={() =>
                        navigate(`/assistant?prompt=${encodeURIComponent(buildExplorePrompt(card.name))}`)
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : !isLoadingGuides ? (
              <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
                No hidden-gem place picks are available right now.
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      {activeCategory === 'Guided Picks' ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {guideCards.map((guide, index) => (
            <motion.div
              key={guide.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="rounded-2xl border border-border bg-card p-4"
            >
              <DestinationCard
                compact
                typeLabel="Destination guide"
                name={guide.name}
                subtitle={guide.subtitle}
                photos={guide.photos}
                tags={guide.tags}
                description={guide.description}
                onClick={() =>
                  navigate(`/assistant?prompt=${encodeURIComponent(buildGuidePrompt(guide.destination))}`)
                }
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <div className="text-xs text-muted-foreground">
                  {guide.hiddenGemCount} hidden gems surfaced
                </div>
                <Link
                  to={`/assistant?prompt=${encodeURIComponent(buildPlanPrompt(guide.destination))}`}
                  className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
                >
                  Plan <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      ) : null}

      {activeCategory === 'Search' ? (
        <div className="space-y-8">
          <section>
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Destination results</h2>
              <p className="text-sm text-muted-foreground">
                High-level destinations, districts, and neighborhoods.
              </p>
            </div>

            {destinationResults.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {destinationResults.map((card, index) => (
                  <motion.div
                    key={card.location_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <DestinationCard
                      typeLabel="Destination"
                      name={card.name}
                      country={card.country}
                      city={card.city}
                      rating={card.rating}
                      photos={card.photos || []}
                      tags={[card.category]}
                      onClick={() =>
                        navigate(`/assistant?prompt=${encodeURIComponent(buildExplorePrompt(card.name))}`)
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : !isLoadingResults ? (
              <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
                No destination-grade results found for this search.
              </div>
            ) : null}
          </section>

          <section>
            <div className="mb-4">
              <h2 className="text-lg font-semibold">Place-level results</h2>
              <p className="text-sm text-muted-foreground">
                Markets, parks, museums, and other specific places.
              </p>
            </div>

            {placeResults.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                {placeResults.map((card, index) => (
                  <motion.div
                    key={card.location_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <PlaceCard
                      name={card.name}
                      category={card.category}
                      rating={card.rating}
                      photos={card.photos || []}
                      tags={[card.city, card.country].filter(Boolean)}
                      description={`Explore ${card.name} in ${card.city}.`}
                      showSaveButton={false}
                      onClick={() =>
                        navigate(`/assistant?prompt=${encodeURIComponent(buildExplorePrompt(card.name))}`)
                      }
                    />
                  </motion.div>
                ))}
              </div>
            ) : !isLoadingResults ? (
              <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
                No place-level results found for this search.
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      {activeCategory === 'Hidden Gems' ? (
        <div className="grid gap-4 md:grid-cols-2">
          {gemCards.map((card, index) => (
            <motion.div
              key={card.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <PlaceCard
                name={card.name}
                category={card.category}
                rating={card.rating}
                photos={card.photos}
                tags={card.tags}
                description={card.description}
                reason={card.reason}
                isGem
                showSaveButton={false}
                onClick={() =>
                  navigate(`/assistant?prompt=${encodeURIComponent(buildExplorePrompt(card.name))}`)
                }
              />
            </motion.div>
          ))}
        </div>
      ) : null}
    </div>
  );
}