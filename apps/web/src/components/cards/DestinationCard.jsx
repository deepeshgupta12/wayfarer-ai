import { motion } from 'framer-motion';
import { Star, Heart, Sparkles } from 'lucide-react';
import { useState } from 'react';

export default function DestinationCard({ name, image, country, matchScore, tags = [], rating, isGem = false, onClick, compact = false }) {
  const [liked, setLiked] = useState(false);

  if (compact) {
    return (
      <motion.div
        whileHover={{ y: -2 }}
        onClick={onClick}
        className="group cursor-pointer rounded-xl overflow-hidden bg-card border border-border hover:shadow-lg transition-shadow duration-300"
      >
        <div className="relative h-32 overflow-hidden">
          <img src={image} alt={name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
          {matchScore && (
            <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-primary/80 text-primary-foreground text-[10px] font-semibold backdrop-blur-sm">
              {matchScore}% match
            </div>
          )}
        </div>
        <div className="p-3">
          <h4 className="font-semibold text-sm truncate">{name}</h4>
          <p className="text-xs text-muted-foreground">{country}</p>
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
      <div className="relative h-52 overflow-hidden">
        <img src={image} alt={name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
        
        <div className="absolute top-3 left-3 flex items-center gap-2">
          {matchScore && (
            <div className="px-2.5 py-1 rounded-full bg-primary/80 text-primary-foreground text-xs font-semibold backdrop-blur-sm flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              {matchScore}% match
            </div>
          )}
          {isGem && (
            <div className="px-2.5 py-1 rounded-full bg-accent/90 text-accent-foreground text-xs font-semibold backdrop-blur-sm">
              Hidden Gem
            </div>
          )}
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); setLiked(!liked); }}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center hover:bg-white/40 transition-colors"
        >
          <Heart className={`w-4 h-4 ${liked ? 'fill-red-500 text-red-500' : 'text-white'}`} />
        </button>

        <div className="absolute bottom-3 left-3 right-3">
          <h3 className="text-white font-semibold text-lg mb-0.5">{name}</h3>
          <p className="text-white/80 text-sm">{country}</p>
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          {rating && (
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-accent text-accent" />
              <span className="text-sm font-medium">{rating}</span>
            </div>
          )}
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.slice(0, 4).map((tag, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}