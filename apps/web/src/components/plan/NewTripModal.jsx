import { useEffect, useMemo, useRef, useState } from 'react';
import { Sparkles, Loader2, MapPin, Check, ChevronDown } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  enrichTripPlan,
  parseAndSaveTripBrief,
  promoteTripPlanToSavedTrip,
  searchDestinations,
} from '@/api/wayfarerApi';
import { getOrCreateTravellerId } from '@/lib/travellerProfile';
import { cacheSavedTrip, cacheTripPlan } from '@/lib/tripStorage';

const INTEREST_OPTIONS = [
  { value: 'food', label: 'Food' },
  { value: 'culture', label: 'Culture' },
  { value: 'nature', label: 'Nature' },
  { value: 'adventure', label: 'Adventure' },
  { value: 'nightlife', label: 'Nightlife' },
  { value: 'luxury', label: 'Luxury' },
  { value: 'wellness', label: 'Wellness' },
];

const DEFAULT_DESTINATION_OPTIONS = ['Tokyo', 'Kyoto', 'Lisbon', 'Prague', 'Budapest'];

function calculateDurationDays(startDate, endDate) {
  if (!startDate || !endDate) {
    return 5;
  }

  const start = new Date(startDate);
  const end = new Date(endDate);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) {
    return 5;
  }

  const diffMs = end.getTime() - start.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1;

  return Math.max(1, diffDays);
}

function buildPlanningBrief({
  destination,
  durationDays,
  groupType,
  budget,
  pacePreference,
  interests,
}) {
  const interestText = interests.join(' and ');
  return `I have ${durationDays} days in ${destination} for a ${groupType} trip, ${budget} budget, ${pacePreference} pace, love ${interestText}`;
}

function formatDestinationLabel(result) {
  const name = result?.name || '';
  const city = result?.city || '';
  const country = result?.country || '';

  if (city && country && city !== name) {
    return `${name}, ${city}, ${country}`;
  }

  if (country) {
    return `${name}, ${country}`;
  }

  return name;
}

function buildFallbackDestinationResults(query) {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return DEFAULT_DESTINATION_OPTIONS.map((name) => ({
      location_id: `fallback_${name.toLowerCase()}`,
      name,
      city: name,
      country: '',
      category: 'city',
      rating: 0,
      review_count: 0,
    }));
  }

  return DEFAULT_DESTINATION_OPTIONS.filter((name) =>
    name.toLowerCase().includes(normalizedQuery)
  ).map((name) => ({
    location_id: `fallback_${name.toLowerCase()}`,
    name,
    city: name,
    country: '',
    category: 'city',
    rating: 0,
    review_count: 0,
  }));
}

export default function NewTripModal({ onClose, onCreated }) {
  const [destinationInput, setDestinationInput] = useState('');
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [destinationResults, setDestinationResults] = useState(
    buildFallbackDestinationResults('')
  );
  const [searchingDestinations, setSearchingDestinations] = useState(false);
  const [showDestinationDropdown, setShowDestinationDropdown] = useState(false);

  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [groupType, setGroupType] = useState('solo');
  const [budget, setBudget] = useState('midrange');
  const [pacePreference, setPacePreference] = useState('balanced');
  const [interests, setInterests] = useState(['food', 'culture']);

  const [generating, setGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const durationDays = useMemo(
    () => calculateDurationDays(startDate, endDate),
    [startDate, endDate]
  );

  const dropdownRef = useRef(null);

  useEffect(() => {
    const trimmedQuery = destinationInput.trim();

    if (!trimmedQuery) {
      setDestinationResults(buildFallbackDestinationResults(''));
      setSearchingDestinations(false);
      return undefined;
    }

    let cancelled = false;

    const timeoutId = window.setTimeout(async () => {
      setSearchingDestinations(true);

      try {
        const response = await searchDestinations({
          query: trimmedQuery,
          traveller_type: groupType,
          interests,
        });

        if (cancelled) return;

        const results = Array.isArray(response?.results) ? response.results : [];
        setDestinationResults(
          results.length > 0 ? results : buildFallbackDestinationResults(trimmedQuery)
        );
      } catch {
        if (cancelled) return;
        setDestinationResults(buildFallbackDestinationResults(trimmedQuery));
      } finally {
        if (!cancelled) {
          setSearchingDestinations(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [destinationInput, groupType, interests]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDestinationDropdown(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleInterest = (interestValue) => {
    setInterests((prev) => {
      if (prev.includes(interestValue)) {
        if (prev.length === 1) return prev;
        return prev.filter((item) => item !== interestValue);
      }

      if (prev.length >= 3) return prev;
      return [...prev, interestValue];
    });
  };

  const handleDestinationInputChange = (event) => {
    setDestinationInput(event.target.value);
    setSelectedDestination(null);
    setShowDestinationDropdown(true);
    setErrorMessage('');
  };

  const handleDestinationSelect = (result) => {
    setSelectedDestination(result);
    setDestinationInput(result.name);
    setShowDestinationDropdown(false);
    setErrorMessage('');
  };

  const handleCreate = async () => {
    if (!selectedDestination?.name) {
      setErrorMessage('Please select a destination from the dropdown suggestions.');
      return;
    }

    setGenerating(true);
    setErrorMessage('');

    try {
      const travellerId = getOrCreateTravellerId();

      const brief = buildPlanningBrief({
        destination: selectedDestination.name,
        durationDays,
        groupType,
        budget,
        pacePreference,
        interests,
      });

      const parsedPlan = await parseAndSaveTripBrief({
        traveller_id: travellerId,
        brief,
        source_surface: 'planner_modal',
      });

      cacheTripPlan(parsedPlan);

      if ((parsedPlan.missing_fields || []).length > 0) {
        throw new Error(
          `Planner could not generate a complete trip plan. Missing: ${parsedPlan.missing_fields.join(', ')}`
        );
      }

      const enrichedPlan = await enrichTripPlan(parsedPlan.planning_session_id);
      cacheTripPlan(enrichedPlan);

      const destinationName =
        enrichedPlan?.parsed_constraints?.destination || selectedDestination.name;
      const title = `${destinationName} ${enrichedPlan.itinerary_skeleton.length}-day plan`;

      const savedTrip = await promoteTripPlanToSavedTrip(enrichedPlan.planning_session_id, {
        title,
        start_date: startDate || null,
        end_date: endDate || null,
        companions: groupType,
        status: 'planning',
        source_surface: 'planner_modal',
      });

      cacheSavedTrip(savedTrip);

      onCreated?.(savedTrip);
      onClose?.();
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to generate your trip right now.');
    } finally {
      setGenerating(false);
    }
  };

  const canGenerate =
    Boolean(selectedDestination?.name) && !generating && interests.length > 0;

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">Plan a New Trip</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          <div ref={dropdownRef} className="relative">
            <label className="text-sm font-medium mb-1.5 block">Where to?</label>

            <div className="relative">
              <input
                type="text"
                placeholder="Search destinations like Tokyo, Kyoto, Lisbon..."
                value={destinationInput}
                onChange={handleDestinationInputChange}
                onFocus={() => setShowDestinationDropdown(true)}
                className="w-full px-3 py-2.5 pr-10 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
              <ChevronDown className="w-4 h-4 text-muted-foreground absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {selectedDestination ? (
              <div className="mt-2 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-primary">
                <Check className="w-3 h-3" />
                {formatDestinationLabel(selectedDestination)}
              </div>
            ) : null}

            {showDestinationDropdown ? (
              <div className="absolute z-50 mt-2 w-full rounded-2xl border border-border bg-card shadow-xl overflow-hidden">
                <div className="max-h-64 overflow-y-auto">
                  {searchingDestinations ? (
                    <div className="flex items-center gap-2 px-3 py-3 text-sm text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Searching destinations...
                    </div>
                  ) : destinationResults.length > 0 ? (
                    destinationResults.map((result) => {
                      const isSelected =
                        selectedDestination?.location_id === result.location_id;

                      return (
                        <button
                          key={result.location_id}
                          type="button"
                          onClick={() => handleDestinationSelect(result)}
                          className={`w-full text-left px-3 py-3 border-b border-border last:border-b-0 transition-colors ${
                            isSelected ? 'bg-primary/5' : 'hover:bg-secondary/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-sm font-medium text-foreground">
                                {result.name}
                              </div>
                              <div className="text-xs text-muted-foreground mt-0.5">
                                {[result.city, result.country, result.category]
                                  .filter(Boolean)
                                  .join(' · ')}
                              </div>
                            </div>

                            <div className="flex items-center gap-1 text-xs text-muted-foreground">
                              <MapPin className="w-3 h-3" />
                              Select
                            </div>
                          </div>
                        </button>
                      );
                    })
                  ) : (
                    <div className="px-3 py-3 text-sm text-muted-foreground">
                      No destinations found. Try a broader city name.
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Group Type</label>
              <select
                value={groupType}
                onChange={(e) => setGroupType(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="solo">Solo</option>
                <option value="couple">Couple</option>
                <option value="family">Family</option>
                <option value="friends">Friends</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1.5 block">Budget</label>
              <select
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              >
                <option value="budget">Budget</option>
                <option value="midrange">Midrange</option>
                <option value="luxury">Luxury</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Pace</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'relaxed', label: 'Relaxed' },
                { value: 'balanced', label: 'Balanced' },
                { value: 'fast', label: 'Fast' },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setPacePreference(option.value)}
                  className={`px-3 py-2 rounded-xl border text-sm transition-colors ${
                    pacePreference === option.value
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-secondary/40 text-foreground'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-1.5 block">Interests (up to 3)</label>
            <div className="flex flex-wrap gap-2">
              {INTEREST_OPTIONS.map((option) => {
                const selected = interests.includes(option.value);

                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleInterest(option.value)}
                    className={`px-3 py-1.5 rounded-full border text-xs font-medium transition-colors ${
                      selected
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-secondary/40 text-foreground'
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rounded-xl bg-secondary/40 border border-border px-3 py-2.5 text-xs text-muted-foreground">
            This trip will be created as a backend-saved trip with version history and structured signals. Local storage is used only for cache convenience.
          </div>

          {errorMessage ? (
            <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {errorMessage}
            </div>
          ) : null}

          <button
            onClick={handleCreate}
            disabled={!canGenerate}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating itinerary...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate AI Itinerary
              </>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}