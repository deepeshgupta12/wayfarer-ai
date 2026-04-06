import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Clock,
  MapPin,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Sparkles,
  CheckCircle2,
  Star,
} from 'lucide-react';

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
  alternatives = [],
  replacementStatus = 'original',
  slotType,
  continuityNote,
  movementNote,
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [swapping, setSwapping] = useState(null);

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

  const hasAlternatives = Array.isArray(alternatives) && alternatives.length > 0;

  function handleExpandClick() {
    if (hasAlternatives) {
      setIsExpanded((prev) => !prev);
    }
    if (onExpand) onExpand();
  }

  async function handleUseThis(alt) {
    if (swapping || !onSwap) return;
    setSwapping(alt.location_id || alt.name);
    try {
      await onSwap(alt);
    } finally {
      setSwapping(null);
      setIsExpanded(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="group relative flex gap-3 p-3 rounded-xl hover:bg-secondary/50 transition-colors"
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

          {hasAlternatives ? (
            <span className="inline-flex items-center rounded-full border border-accent/20 bg-accent/5 px-2 py-0.5 text-[10px] font-medium text-accent">
              {alternatives.length} alternative{alternatives.length === 1 ? '' : 's'}
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

        {continuityNote ? (
          <div className="mt-2 text-[11px] text-muted-foreground">
            <span className="font-medium">Continuity:</span> {continuityNote}
          </div>
        ) : null}

        {movementNote ? (
          <div className="mt-1 text-[11px] text-muted-foreground">
            <span className="font-medium">Movement:</span> {movementNote}
          </div>
        ) : null}

        {fallbackNames?.length > 0 && !hasAlternatives ? (
          <div className="mt-2 text-[11px] text-muted-foreground">
            Fallback options: <span className="font-medium">{fallbackNames.join(', ')}</span>
          </div>
        ) : null}

        {/* Action row */}
        <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {onSwap && !hasAlternatives && (
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
          {hasAlternatives && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleExpandClick();
              }}
              className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {isExpanded ? 'Hide alternatives' : 'See alternatives'}
            </button>
          )}
          {!hasAlternatives && (
            <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
              <ChevronRight className="w-3 h-3" />
              Details
            </button>
          )}
        </div>

        {/* Alternatives expansion panel */}
        <AnimatePresence>
          {isExpanded && hasAlternatives && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-3 rounded-xl border border-accent/15 bg-accent/3 divide-y divide-border/60">
                <div className="px-3 py-2 text-[11px] font-semibold text-accent flex items-center gap-1.5">
                  <Sparkles className="w-3 h-3" />
                  Alternative picks for this slot
                </div>
                {alternatives.slice(0, 4).map((alt) => {
                  const altKey = alt.location_id || alt.name;
                  const isBusy = swapping === altKey;
                  return (
                    <div
                      key={altKey}
                      className="flex items-start justify-between gap-3 px-3 py-2.5"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-medium">{alt.name || alt.place_name}</span>
                          {alt.category ? (
                            <span className="text-[10px] text-muted-foreground capitalize">{alt.category}</span>
                          ) : null}
                          {alt.score != null ? (
                            <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground">
                              <Star className="w-2.5 h-2.5" />
                              {Number(alt.score).toFixed(1)}
                            </span>
                          ) : null}
                        </div>
                        {(alt.rationale || alt.summary_line) && (
                          <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                            {alt.rationale || alt.summary_line}
                          </p>
                        )}
                      </div>
                      <button
                        onClick={() => handleUseThis(alt)}
                        disabled={Boolean(swapping)}
                        className="flex-shrink-0 inline-flex items-center gap-1 rounded-lg bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent hover:bg-accent/20 disabled:opacity-50 transition-colors"
                      >
                        {isBusy ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          <CheckCircle2 className="w-3 h-3" />
                        )}
                        Use this
                      </button>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
