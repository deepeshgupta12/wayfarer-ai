import { motion } from 'framer-motion';
import { Clock, MapPin, RefreshCw, ChevronRight, Sparkles } from 'lucide-react';

export default function ActivityCard({
  time,
  name,
  description,
  type,
  location,
  reason,
  image,
  onSwap,
  onExpand,
  index = 0,
  fallbackNames = [],
  replacementStatus = 'original',
  slotType,
}) {
  const typeIcons = {
    food: '🍽️',
    culture: '🏛️',
    adventure: '🎯',
    nature: '🌿',
    shopping: '🛍️',
    relaxation: '☕',
    nightlife: '🌙',
    transport: '🚗',
  };

  const replacementBadge =
    replacementStatus === 'replaced'
      ? 'Replacement applied'
      : replacementStatus === 'retained_best_fit'
        ? 'Strongest fit retained'
        : null;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group relative flex gap-3 p-3 rounded-xl hover:bg-secondary/50 transition-colors cursor-pointer"
      onClick={onExpand}
    >
      <div className="flex flex-col items-center flex-shrink-0 pt-1">
        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm">
          {typeIcons[type] || '📍'}
        </div>
        <div className="w-px flex-1 bg-border mt-2" />
      </div>

      <div className="flex-1 min-w-0 pb-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            {time && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground mb-1">
                <Clock className="w-3 h-3" />
                {time}
              </div>
            )}
            <h4 className="font-medium text-sm">{name}</h4>
            {location && (
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-0.5">
                <MapPin className="w-3 h-3" />
                {location}
              </div>
            )}
          </div>
          {image && (
            <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
              <img src={image} alt={name} className="w-full h-full object-cover" />
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-2">
          {slotType ? (
            <span className="inline-flex items-center rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground capitalize">
              {slotType}
            </span>
          ) : null}

          {replacementBadge ? (
            <span className="inline-flex items-center rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              {replacementBadge}
            </span>
          ) : null}
        </div>

        {description && (
          <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{description}</p>
        )}

        {reason && (
          <div className="flex items-start gap-1.5 mt-2 p-2 rounded-lg bg-accent/5 border border-accent/10">
            <Sparkles className="w-3 h-3 text-accent mt-0.5 flex-shrink-0" />
            <p className="text-xs text-accent">{reason}</p>
          </div>
        )}

        {fallbackNames?.length > 0 ? (
          <div className="mt-2 text-[11px] text-muted-foreground">
            Fallback options: <span className="font-medium">{fallbackNames.join(', ')}</span>
          </div>
        ) : null}

        <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {onSwap && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSwap();
              }}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Swap
            </button>
          )}
          <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <ChevronRight className="w-3 h-3" />
            Details
          </button>
        </div>
      </div>
    </motion.div>
  );
}