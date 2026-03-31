import { motion } from 'framer-motion';
import { Star, MapPin, Bookmark, Gem } from 'lucide-react';
import { useMemo, useState } from 'react';

function getPrimaryPhoto({ photos = [], image }) {
  if (Array.isArray(photos) && photos.length > 0) {
    return photos[0]?.image_url || null;
  }
  return image || null;
}

function getTagsFromPhotos(photos = []) {
  if (!Array.isArray(photos) || photos.length === 0) return [];
  const tagSet = new Set();

  photos.slice(0, 3).forEach((photo) => {
    (photo?.tags || []).forEach((tag) => {
      if (tagSet.size < 4 && tag) tagSet.add(tag);
    });
  });

  return Array.from(tagSet);
}

function getFallbackTone(category, isGem) {
  const normalized = String(category || '').toLowerCase();

  if (isGem) return 'from-accent/25 via-sunset/20 to-lavender/25';
  if (normalized === 'market' || normalized === 'restaurant' || normalized === 'cafe') {
    return 'from-sunset/20 via-accent/10 to-ocean/15';
  }
  if (normalized === 'park' || normalized === 'nature') {
    return 'from-sage/25 via-ocean/10 to-accent/10';
  }
  if (normalized === 'district' || normalized === 'neighborhood' || normalized === 'city') {
    return 'from-ocean/20 via-lavender/10 to-accent/10';
  }
  return 'from-secondary via-accent/10 to-sage/10';
}

function getInitials(name) {
  return String(name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0]?.toUpperCase())
    .join('');
}

export default function PlaceCard({
  name,
  image,
  photos = [],
  category,
  rating,
  description,
  reason,
  distance,
  tags = [],
  isGem = false,
  onSave,
  onClick,
  trailing,
  showSaveButton = true,
}) {
  const [saved, setSaved] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const categoryColors = {
    restaurant: 'bg-sunset-light text-sunset',
    cafe: 'bg-ocean-light text-ocean',
    attraction: 'bg-lavender-light text-lavender',
    museum: 'bg-sage-light text-sage',
    park: 'bg-sage-light text-sage',
    hotel: 'bg-ocean-light text-ocean',
    experience: 'bg-accent/10 text-accent',
    hidden_gem: 'bg-accent/10 text-accent',
    area: 'bg-accent/10 text-accent',
    city: 'bg-accent/10 text-accent',
    neighborhood: 'bg-accent/10 text-accent',
    district: 'bg-accent/10 text-accent',
    market: 'bg-sunset-light text-sunset',
    riverfront: 'bg-ocean-light text-ocean',
    place: 'bg-secondary text-secondary-foreground',
  };

  const normalizedCategory = category === 'suggested area' ? 'area' : category;
  const primaryImage = getPrimaryPhoto({ photos, image });
  const fallbackTone = getFallbackTone(normalizedCategory, isGem);
  const initials = getInitials(name);

  const derivedTags = useMemo(() => {
    if (Array.isArray(tags) && tags.length > 0) return tags.slice(0, 4);
    return getTagsFromPhotos(photos);
  }, [photos, tags]);

  return (
    <motion.div
      whileHover={{ y: -2 }}
      onClick={onClick}
      className="group cursor-pointer rounded-xl overflow-hidden bg-card border border-border hover:shadow-md transition-all duration-200"
    >
      <div className="flex gap-3 p-3">
        {primaryImage && !imageFailed ? (
          <div className="relative w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 bg-secondary">
            <img
              src={primaryImage}
              alt={name}
              className="w-full h-full object-cover"
              onError={() => setImageFailed(true)}
            />
            {isGem ? (
              <div className="absolute bottom-0 left-0 right-0 bg-accent/90 text-accent-foreground text-[9px] font-bold text-center py-0.5 inline-flex items-center justify-center gap-1">
                <Gem className="w-2.5 h-2.5" />
                GEM
              </div>
            ) : null}
          </div>
        ) : (
          <div className={`w-24 h-24 rounded-lg bg-gradient-to-br ${fallbackTone} flex items-end p-2 flex-shrink-0`}>
            <div className="min-w-0">
              <div className="text-lg font-serif font-semibold text-foreground/90">{initials || 'WF'}</div>
              <div className="text-[10px] text-muted-foreground truncate">{normalizedCategory || 'place'}</div>
            </div>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="font-semibold text-sm truncate">{name}</h4>

              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                {normalizedCategory ? (
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium capitalize ${
                      categoryColors[normalizedCategory] || 'bg-secondary text-secondary-foreground'
                    }`}
                  >
                    {normalizedCategory}
                  </span>
                ) : null}

                {rating ? (
                  <div className="flex items-center gap-0.5">
                    <Star className="w-3 h-3 fill-accent text-accent" />
                    <span className="text-xs font-medium">{rating}</span>
                  </div>
                ) : null}

                {distance ? (
                  <div className="flex items-center gap-0.5 text-muted-foreground">
                    <MapPin className="w-3 h-3" />
                    <span className="text-xs">{distance}</span>
                  </div>
                ) : null}
              </div>
            </div>

            <div className="flex items-start gap-2">
              {trailing ? <div onClick={(e) => e.stopPropagation()}>{trailing}</div> : null}

              {showSaveButton ? (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSaved(!saved);
                    onSave?.();
                  }}
                  className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors"
                >
                  <Bookmark className={`w-4 h-4 ${saved ? 'fill-primary text-primary' : 'text-muted-foreground'}`} />
                </button>
              ) : null}
            </div>
          </div>

          {description ? (
            <p className="text-xs text-muted-foreground mt-1.5 line-clamp-3">{description}</p>
          ) : null}

          {reason ? <p className="text-xs text-accent mt-1.5">{reason}</p> : null}

          {derivedTags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {derivedTags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[10px] capitalize"
                >
                  {String(tag).replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}