import { motion } from 'framer-motion';
import { Star, Heart, Sparkles, Image as ImageIcon, Map } from 'lucide-react';
import { useMemo, useState } from 'react';

function getPrimaryPhoto({ photos = [], image }) {
  if (Array.isArray(photos) && photos.length > 0) {
    return photos[0]?.image_url || null;
  }
  return image || null;
}

export default function DestinationCard({
  name,
  image,
  photos = [],
  country,
  city,
  matchScore,
  tags = [],
  rating,
  isGem = false,
  onClick,
  compact = false,
  subtitle,
  description,
  typeLabel = 'Destination',
  showLikeButton = true,
}) {
  const [liked, setLiked] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);

  const primaryImage = getPrimaryPhoto({ photos, image });
  const locationLabel = useMemo(() => subtitle || country || city || '', [subtitle, country, city]);

  if (compact) {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        onClick={onClick}
        className="group cursor-pointer rounded-xl overflow-hidden bg-card border border-border hover:shadow-lg transition-shadow duration-300"
      >
        <div className="relative h-36 overflow-hidden bg-secondary">
          {primaryImage && !imageFailed ? (
            <img
              src={primaryImage}
              alt={name}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
              <div className="flex flex-col items-center gap-2">
                <ImageIcon className="w-5 h-5" />
                <span className="text-[11px]">Image unavailable</span>
              </div>
            </div>
          )}

          <div className="absolute top-2 left-2 flex items-center gap-2 flex-wrap">
            {typeLabel ? (
              <div className="px-2 py-0.5 rounded-full bg-background/90 text-foreground text-[10px] font-semibold backdrop-blur-sm inline-flex items-center gap-1">
                <Map className="w-3 h-3" />
                {typeLabel}
              </div>
            ) : null}

            {matchScore ? (
              <div className="px-2 py-0.5 rounded-full bg-primary/80 text-primary-foreground text-[10px] font-semibold backdrop-blur-sm">
                {matchScore}% match
              </div>
            ) : null}
          </div>
        </div>

        <div className="p-3">
          <h4 className="font-semibold text-sm truncate">{name}</h4>
          <p className="text-xs text-muted-foreground">{locationLabel}</p>

          {description ? (
            <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{description}</p>
          ) : null}

          {tags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[10px]"
                >
                  {String(tag).replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      whileHover={{ y: -4 }}
      onClick={onClick}
      className="group cursor-pointer rounded-2xl overflow-hidden bg-card border border-border hover:shadow-xl transition-all duration-300"
    >
      <div className="relative h-52 overflow-hidden bg-secondary">
        {primaryImage && !imageFailed ? (
          <img
            src={primaryImage}
            alt={name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            <div className="flex flex-col items-center gap-2">
              <ImageIcon className="w-7 h-7" />
              <span className="text-xs">Image unavailable</span>
            </div>
          </div>
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />

        <div className="absolute top-3 left-3 flex items-center gap-2 flex-wrap">
          {typeLabel ? (
            <div className="px-2.5 py-1 rounded-full bg-background/90 text-foreground text-xs font-semibold backdrop-blur-sm">
              {typeLabel}
            </div>
          ) : null}

          {matchScore ? (
            <div className="px-2.5 py-1 rounded-full bg-primary/80 text-primary-foreground text-xs font-semibold backdrop-blur-sm flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              {matchScore}% match
            </div>
          ) : null}

          {isGem ? (
            <div className="px-2.5 py-1 rounded-full bg-accent/90 text-accent-foreground text-xs font-semibold backdrop-blur-sm">
              Hidden Gem
            </div>
          ) : null}
        </div>

        {showLikeButton ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setLiked(!liked);
            }}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center hover:bg-white/40 transition-colors"
          >
            <Heart className={`w-4 h-4 ${liked ? 'fill-red-500 text-red-500' : 'text-white'}`} />
          </button>
        ) : null}

        <div className="absolute bottom-3 left-3 right-3">
          <h3 className="text-white font-semibold text-lg mb-0.5">{name}</h3>
          <p className="text-white/80 text-sm">{locationLabel}</p>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          {rating ? (
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-accent text-accent" />
              <span className="text-sm font-medium">{rating}</span>
            </div>
          ) : (
            <div />
          )}
        </div>

        {description ? (
          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{description}</p>
        ) : null}

        {tags.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs capitalize"
              >
                {String(tag).replaceAll('_', ' ')}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}