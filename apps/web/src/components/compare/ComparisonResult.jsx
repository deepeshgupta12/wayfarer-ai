import { motion } from 'framer-motion';
import { Trophy, Route, Scale, ChevronRight, Camera } from 'lucide-react';

function renderHero(side) {
  const photo = side?.hero_photos?.[0]?.image_url;
  if (!photo) return null;

  return (
    <div className="mt-3 h-32 rounded-xl overflow-hidden bg-secondary">
      <img src={photo} alt={side?.name} className="w-full h-full object-cover" />
    </div>
  );
}

export default function ComparisonResult({ data, onPlanDestination }) {
  if (!data) return null;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4 items-stretch">
        <div className="p-5 rounded-2xl bg-card border border-border text-center">
          <h3 className="font-serif text-xl font-bold">{data.destination_a?.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{data.destination_a?.tagline}</p>
          <p className="text-xs text-accent mt-2">Best for: {data.destination_a?.best_for}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Weighted score: <span className="font-semibold">{data.destination_a?.weighted_score}</span>
          </p>
          {data.destination_a?.hero_photos?.length ? (
            <div className="text-[11px] text-muted-foreground mt-2 inline-flex items-center gap-1">
              <Camera className="w-3 h-3" />
              {data.destination_a.hero_photos.length} ranked photos
            </div>
          ) : null}
          {renderHero(data.destination_a)}
        </div>

        <div className="hidden lg:flex text-lg font-bold text-muted-foreground items-center justify-center">VS</div>

        <div className="p-5 rounded-2xl bg-card border border-border text-center">
          <h3 className="font-serif text-xl font-bold">{data.destination_b?.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{data.destination_b?.tagline}</p>
          <p className="text-xs text-accent mt-2">Best for: {data.destination_b?.best_for}</p>
          <p className="text-xs text-muted-foreground mt-2">
            Weighted score: <span className="font-semibold">{data.destination_b?.weighted_score}</span>
          </p>
          {data.destination_b?.hero_photos?.length ? (
            <div className="text-[11px] text-muted-foreground mt-2 inline-flex items-center gap-1">
              <Camera className="w-3 h-3" />
              {data.destination_b.hero_photos.length} ranked photos
            </div>
          ) : null}
          {renderHero(data.destination_b)}
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="font-semibold text-lg mb-4">Structured Comparison</h3>

        {data.dimensions?.map((dim, i) => (
          <motion.div
            key={dim.name || i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="p-4 rounded-xl bg-card border border-border"
          >
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="font-medium text-sm">{dim.name}</span>
                <div className="text-[11px] text-muted-foreground mt-1">Weight {dim.weight}</div>
              </div>

              <div className="flex items-center gap-3">
                <span className={`text-sm font-bold ${dim.score_a >= dim.score_b ? 'text-accent' : 'text-muted-foreground'}`}>
                  {dim.score_a}/10
                </span>
                <span className="text-xs text-muted-foreground">vs</span>
                <span className={`text-sm font-bold ${dim.score_b >= dim.score_a ? 'text-accent' : 'text-muted-foreground'}`}>
                  {dim.score_b}/10
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${dim.score_a * 10}%` }}
                  transition={{ delay: 0.2 + i * 0.03, duration: 0.45 }}
                  className={`h-full rounded-full ${dim.score_a >= dim.score_b ? 'bg-accent' : 'bg-muted-foreground/40'}`}
                />
              </div>

              <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${dim.score_b * 10}%` }}
                  transition={{ delay: 0.2 + i * 0.03, duration: 0.45 }}
                  className={`h-full rounded-full ${dim.score_b >= dim.score_a ? 'bg-accent' : 'bg-muted-foreground/40'}`}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-2">
              <p className="text-xs text-muted-foreground">{dim.note_a}</p>
              <p className="text-xs text-muted-foreground">{dim.note_b}</p>
            </div>

            <div className="mt-2 text-[11px] text-muted-foreground">
              Winner: <span className="font-medium capitalize">{String(dim.winner).replace('_', ' ')}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="p-6 rounded-2xl bg-gradient-to-br from-accent/5 to-sage-light border border-accent/10 space-y-4">
        <div className="flex items-start gap-3">
          <Trophy className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold mb-2">Verdict</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{data.verdict}</p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <Route className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold mb-2">Planning Recommendation</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{data.planning_recommendation}</p>
          </div>
        </div>

        {data.next_step_suggestions?.length > 0 ? (
          <div className="flex items-start gap-3">
            <Scale className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h3 className="font-semibold">Next Step Suggestions</h3>
              {data.next_step_suggestions.map((item, index) => (
                <div key={index} className="text-sm text-muted-foreground flex items-center gap-2">
                  <ChevronRight className="w-3.5 h-3.5" />
                  {item}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {data.youd_also_love?.length ? (
        <div className="rounded-2xl border border-border bg-card p-5">
          <h3 className="font-semibold mb-3">You’d also love</h3>
          <div className="grid gap-3 md:grid-cols-2">
            {data.youd_also_love.slice(0, 4).map((item) => (
              <div key={item.location_id} className="rounded-xl border border-border p-3">
                <div className="font-medium text-sm">{item.name}</div>
                <div className="text-xs text-muted-foreground mt-1">{item.reason}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid sm:grid-cols-2 gap-4">
        {(data.plan_start_options?.length ? data.plan_start_options : [
          { destination: data.destination_a?.name },
          { destination: data.destination_b?.name },
        ]).map((option) => (
          <button
            key={option.destination}
            onClick={() => onPlanDestination?.(option.destination, option)}
            className="p-4 rounded-xl bg-card border border-border text-left hover:border-accent/30 transition-colors"
          >
            <div className="font-medium text-sm">Plan {option.destination}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {option.recommended ? 'Recommended branch from comparison.' : 'Open the planner with this destination as the active branch.'}
            </div>
          </button>
        ))}
      </div>
    </motion.div>
  );
}
