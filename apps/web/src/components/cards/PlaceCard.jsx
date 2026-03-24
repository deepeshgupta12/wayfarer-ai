import { motion } from 'framer-motion';
import { Star, MapPin, Bookmark, ExternalLink, Clock } from 'lucide-react';
import { useState } from 'react';

export default function PlaceCard({ name, image, category, rating, description, reason, distance, tags = [], isGem = false, onSave, onClick }) {
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
  };

  return (
    <motion.div
      whileHover={{ y: -2 }}
      onClick={onClick}
      className="group cursor-pointer rounded-xl overflow-hidden bg-card border border-border hover:shadow-md transition-all duration-200"
    >
      <div className="flex gap-3 p-3">
        {image && (
          <div className="relative w-20 h-20 rounded-lg overflow-hidden flex-shrink-0">
            <img src={image} alt={name} className="w-full h-full object-cover" />
            {isGem && (
              <div className="absolute bottom-0 left-0 right-0 bg-accent/90 text-accent-foreground text-[9px] font-bold text-center py-0.5">
                GEM
              </div>
            )}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="font-semibold text-sm truncate">{name}</h4>
              <div className="flex items-center gap-2 mt-0.5">
                {category && (
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${categoryColors[category] || 'bg-secondary text-secondary-foreground'}`}>
                    {category}
                  </span>
                )}
                {rating && (
                  <div className="flex items-center gap-0.5">
                    <Star className="w-3 h-3 fill-accent text-accent" />
                    <span className="text-xs font-medium">{rating}</span>
                  </div>
                )}
                {distance && (
                  <div className="flex items-center gap-0.5 text-muted-foreground">
                    <MapPin className="w-3 h-3" />
                    <span className="text-xs">{distance}</span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setSaved(!saved); onSave?.(); }}
              className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors"
            >
              <Bookmark className={`w-4 h-4 ${saved ? 'fill-primary text-primary' : 'text-muted-foreground'}`} />
            </button>
          </div>
          {description && (
            <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{description}</p>
          )}
          {reason && (
            <p className="text-xs text-accent mt-1 italic">"{reason}"</p>
          )}
        </div>
      </div>
    </motion.div>
  );
}