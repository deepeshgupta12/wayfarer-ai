import { motion } from 'framer-motion';
import { Star, MapPin, Bookmark, Image as ImageIcon } from 'lucide-react';
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
}) {
  const [saved, setSaved] = useState(false);

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
  };

  const normalizedCategory = category === 'suggested area' ? 'area' : category;
  const primaryImage = getPrimaryPhoto({ photos, image });
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
        {primaryImage ? (
          <div className="relative w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 bg-secondary">
            <img src={primaryImage} alt={name} className="w-full h-full object-cover" />
            {isGem ? (
              <div className="absolute bottom-0 left-0 right-0 bg-accent/90 text-accent-foreground text-[9px] font-bold text-center py-0.5">
                GEM
              </div>
            ) : null}
          </div>
        ) : (
          <div className="w-24 h-24 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0 text-muted-foreground">
            <ImageIcon className="w-5 h-5" />
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
            </div>
          </div>

          {description ? (
            <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{description}</p>
          ) : null}

          {reason ? <p className="text-xs text-accent mt-1.5">{reason}</p> : null}

          {derivedTags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {derivedTags.map((tag) => (
                <span key={tag} className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[10px] capitalize">
                  {tag.replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}
