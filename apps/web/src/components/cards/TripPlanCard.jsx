import { motion } from 'framer-motion';
import {
  MapPin,
  Calendar,
  Layers,
  Heart,
  Camera,
  GitBranch,
  Clock3,
  Route,
  Sparkles,
  Bookmark,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import moment from 'moment';

const statusColors = {
  planning: 'bg-secondary text-secondary-foreground',
  upcoming: 'bg-ocean-light text-ocean',
  active: 'bg-accent/10 text-accent',
  completed: 'bg-sage-light text-sage',
};

const fallbackThemes = [
  {
    shell: 'bg-gradient-to-br from-accent/10 via-sunset-light to-accent/5',
    glow: 'bg-accent/15',
    accent: 'text-accent',
    chip: 'bg-accent/10 text-accent',
  },
  {
    shell: 'bg-gradient-to-br from-ocean-light via-background to-ocean/10',
    glow: 'bg-ocean/10',
    accent: 'text-ocean',
    chip: 'bg-ocean/10 text-ocean',
  },
  {
    shell: 'bg-gradient-to-br from-sage-light via-background to-sage/10',
    glow: 'bg-sage/10',
    accent: 'text-sage',
    chip: 'bg-sage/10 text-sage',
  },
  {
    shell: 'bg-gradient-to-br from-lavender-light via-background to-lavender/10',
    glow: 'bg-lavender/10',
    accent: 'text-lavender',
    chip: 'bg-lavender/10 text-lavender',
  },
];

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function buildPhotoCandidates(trip) {
  const candidates = [];

  safeArray(trip?.itinerary_skeleton).forEach((day) => {
    safeArray(day?.slots).forEach((slot) => {
      safeArray(slot?.assigned_place_photos).forEach((photo) => {
        if (photo?.image_url) {
          candidates.push({
            url: photo.image_url,
            role: 'itinerary_slot',
          });
        }
      });
    });
  });

  safeArray(trip?.candidate_places).forEach((place) => {
    safeArray(place?.photos).forEach((photo, index) => {
      if (photo?.image_url) {
        candidates.push({
          url: photo.image_url,
          role: index === 0 ? 'place_card' : 'place_supporting',
        });
      }
    });
  });

  const seen = new Set();
  return candidates.filter((item) => {
    if (!item?.url || seen.has(item.url)) return false;
    seen.add(item.url);
    return true;
  });
}

function getPreferredPhoto(trip, variant) {
  const candidates = buildPhotoCandidates(trip);
  if (!candidates.length) return null;

  if (variant === 'workspace') {
    return candidates.find((item) => item.role === 'itinerary_slot')?.url || candidates[0].url;
  }

  if (variant === 'history') {
    return candidates.find((item) => item.role === 'place_card')?.url || candidates[0].url;
  }

  return candidates[0].url;
}

function getThemeIndex(seed) {
  const value = String(seed || 'wayfarer');
  let hash = 0;

  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % fallbackThemes.length;
  }

  return Math.abs(hash) % fallbackThemes.length;
}

function getDurationLabel(trip) {
  const days = trip?.parsed_constraints?.duration_days || trip?.itinerary_skeleton?.length || 0;
  if (!days) return 'Duration pending';
  return `${days} ${days === 1 ? 'day' : 'days'}`;
}

function getCompanionLabel(trip) {
  const groupType = trip?.companions || trip?.parsed_constraints?.group_type;
  if (!groupType) return 'Flexible group';
  return groupType.charAt(0).toUpperCase() + groupType.slice(1);
}

function getInterestLabel(trip) {
  const interests = safeArray(trip?.parsed_constraints?.interests).slice(0, 2);
  if (!interests.length) return 'General discovery';
  return interests.map((item) => item.replaceAll('_', ' ')).join(' · ');
}

function getTripSummary(trip, variant) {
  const destination = trip?.destination || trip?.parsed_constraints?.destination || 'your destination';
  const duration = getDurationLabel(trip);
  const interests = getInterestLabel(trip);
  const versions = trip?.current_version_number || 0;
  const saved = trip?.selected_places_count || 0;
  const replacements = trip?.replaced_slots_count || 0;

  if (variant === 'workspace') {
    return `Planning workspace for ${destination}. ${duration}, ${interests}, ${versions} version${versions === 1 ? '' : 's'} tracked.`;
  }

  if (variant === 'history') {
    return `Travel memory for ${destination}. ${saved} saved place${saved === 1 ? '' : 's'} and ${replacements} routed change${replacements === 1 ? '' : 's'} captured.`;
  }

  return `Saved trip for ${destination}. ${duration}, ${saved} saved place${saved === 1 ? '' : 's'}, ${versions} version${versions === 1 ? '' : 's'}.`;
}

function renderFallbackVisual(trip, variant) {
  const theme = fallbackThemes[getThemeIndex(`${trip?.trip_id || trip?.title}_${variant}`)];
  const title = trip?.destination || trip?.title || 'Trip';
  const label =
    variant === 'workspace'
      ? 'Planning workspace'
      : variant === 'history'
      ? 'Travel memory'
      : 'Saved trip';

  return (
    <div className={`relative h-full w-full overflow-hidden ${theme.shell}`}>
      <div className={`absolute -right-10 -top-10 h-32 w-32 rounded-full blur-2xl ${theme.glow}`} />
      <div className={`absolute -bottom-12 -left-8 h-28 w-28 rounded-full blur-2xl ${theme.glow}`} />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.35),transparent_35%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,transparent_0%,rgba(255,255,255,0.08)_100%)]" />

      <div className="relative flex h-full flex-col justify-between p-4">
        <div className={`inline-flex w-fit items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-semibold ${theme.chip}`}>
          {variant === 'workspace' ? <Sparkles className="h-3 w-3" /> : <Bookmark className="h-3 w-3" />}
          {label}
        </div>

        <div>
          <div className={`mb-2 inline-flex items-center gap-2 ${theme.accent}`}>
            <Route className="h-4 w-4" />
            <span className="text-xs font-medium">Image fallback active</span>
          </div>
          <div className="text-lg font-semibold text-foreground">{title}</div>
          <div className="mt-1 text-xs text-muted-foreground">
            {trip?.parsed_constraints?.interests?.length
              ? getInterestLabel(trip)
              : 'Imagery will strengthen as more itinerary places are saved.'}
          </div>
        </div>
      </div>
    </div>
  );
}

function buildMetaRows(trip, variant) {
  const versionCount = trip?.current_version_number || 0;
  const selectedPlacesCount = trip?.selected_places_count || 0;
  const replacedSlotsCount = trip?.replaced_slots_count || 0;
  const skippedCount = trip?.skipped_recommendations_count || 0;
  const photoCount =
    safeArray(trip?.candidate_places).reduce((total, item) => total + safeArray(item?.photos).length, 0) || 0;

  if (variant === 'workspace') {
    return [
      { icon: Layers, label: `${versionCount} versions` },
      { icon: Heart, label: `${selectedPlacesCount} saved` },
      { icon: Route, label: `${replacedSlotsCount} slot updates` },
    ];
  }

  if (variant === 'history') {
    return [
      { icon: GitBranch, label: `${versionCount} versions` },
      { icon: Heart, label: `${selectedPlacesCount} saved` },
      { icon: Camera, label: `${photoCount} photos` },
    ];
  }

  return [
    { icon: Layers, label: `${versionCount} versions` },
    { icon: Heart, label: `${selectedPlacesCount} saved` },
    { icon: Clock3, label: `${skippedCount} skipped` },
  ];
}

export default function TripPlanCard({ trip, variant = 'workspace' }) {
  const image = getPreferredPhoto(trip, variant);
  const summary = getTripSummary(trip, variant);
  const metaRows = buildMetaRows(trip, variant);
  const statusClass = statusColors[trip?.status] || 'bg-secondary text-muted-foreground';

  return (
    <Link to={`/itinerary?trip=${trip.trip_id}`}>
      <motion.div
        whileHover={{ y: -3 }}
        className={`group overflow-hidden rounded-2xl border transition-all duration-300 ${
          variant === 'workspace'
            ? 'border-border bg-card hover:border-accent/30 hover:shadow-lg'
            : variant === 'history'
            ? 'border-sage/15 bg-card hover:border-sage/25 hover:shadow-lg'
            : 'border-border bg-card hover:border-ocean/20 hover:shadow-lg'
        }`}
      >
        <div className="relative h-40 overflow-hidden bg-secondary">
          {image ? (
            <>
              <img
                src={image}
                alt={trip.destination || trip.title}
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />
            </>
          ) : (
            renderFallbackVisual(trip, variant)
          )}

          <div className="absolute left-3 top-3 flex items-center gap-2">
            <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold capitalize ${statusClass}`}>
              {trip.status}
            </span>
            {variant === 'workspace' ? (
              <span className="rounded-full bg-black/40 px-2.5 py-1 text-[10px] font-semibold text-white backdrop-blur-sm">
                Planning workspace
              </span>
            ) : variant === 'history' ? (
              <span className="rounded-full bg-black/40 px-2.5 py-1 text-[10px] font-semibold text-white backdrop-blur-sm">
                Travel memory
              </span>
            ) : (
              <span className="rounded-full bg-black/40 px-2.5 py-1 text-[10px] font-semibold text-white backdrop-blur-sm">
                Saved trip
              </span>
            )}
          </div>

          {image ? (
            <div className="absolute bottom-3 left-3 right-3">
              <div className="text-lg font-semibold text-white">{trip.title}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-white/85">
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5" />
                  {trip.destination || 'Destination pending'}
                </span>
                <span>•</span>
                <span>{getDurationLabel(trip)}</span>
              </div>
            </div>
          ) : null}
        </div>

        <div className="p-4">
          {!image ? (
            <>
              <h3 className="font-semibold transition-colors group-hover:text-accent">{trip.title}</h3>
              <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <MapPin className="h-3 w-3" />
                {trip.destination || 'Destination pending'}
              </div>
            </>
          ) : null}

          {trip.start_date ? (
            <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              {moment(trip.start_date).format('MMM D')}
              {' — '}
              {trip.end_date ? moment(trip.end_date).format('MMM D, YYYY') : 'TBD'}
            </div>
          ) : (
            <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
              <Clock3 className="h-3 w-3" />
              {getDurationLabel(trip)} · {getCompanionLabel(trip)}
            </div>
          )}

          <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">{summary}</p>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {safeArray(trip?.parsed_constraints?.interests)
              .slice(0, 3)
              .map((interest) => (
                <span
                  key={interest}
                  className={`rounded-full px-2 py-0.5 text-[10px] capitalize ${
                    variant === 'history'
                      ? 'bg-sage-light text-sage'
                      : variant === 'workspace'
                      ? 'bg-accent/10 text-accent'
                      : 'bg-secondary text-secondary-foreground'
                  }`}
                >
                  {String(interest).replaceAll('_', ' ')}
                </span>
              ))}
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-3 text-[11px] text-muted-foreground">
            {metaRows.map((item) => {
              const Icon = item.icon;
              return (
                <span key={item.label} className="inline-flex items-center gap-1">
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </span>
              );
            })}
          </div>
        </div>
      </motion.div>
    </Link>
  );
}