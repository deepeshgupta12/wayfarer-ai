import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Trophy,
  Route,
  Scale,
  ChevronRight,
  ArrowRight,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

function getInitials(name) {
  return String(name || '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0]?.toUpperCase())
    .join('');
}

function HeroImage({ side, isWinner = false }) {
  const [failed, setFailed] = useState(false);
  const photo = side?.hero_photos?.[0]?.image_url;
  const initials = getInitials(side?.name);
  const tone = isWinner
    ? 'from-accent/30 via-sunset/20 to-lavender/20'
    : 'from-ocean/20 via-secondary to-sage/15';

  if (!photo || failed) {
    return (
      <div className={`h-44 rounded-2xl bg-gradient-to-br ${tone} border border-border flex items-end p-5`}>
        <div>
          <div className="text-3xl font-serif font-semibold text-foreground/90">{initials || 'WF'}</div>
          <div className="text-sm text-muted-foreground mt-1">
            {side?.city}, {side?.country}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-44 rounded-2xl overflow-hidden bg-secondary border border-border">
      <img
        src={photo}
        alt={side?.name}
        className="w-full h-full object-cover"
        onError={() => setFailed(true)}
      />
    </div>
  );
}

function normalizeWinnerLabel(value) {
  if (value === 'destination_a') return 'Destination A';
  if (value === 'destination_b') return 'Destination B';
  return 'Tie';
}

function getWinningBranch(data) {
  const scoreA = data?.destination_a?.weighted_score || 0;
  const scoreB = data?.destination_b?.weighted_score || 0;

  if (Math.abs(scoreA - scoreB) < 0.15) {
    return 'tie';
  }

  return scoreA >= scoreB ? 'destination_a' : 'destination_b';
}

export default function ComparisonResult({ data, onPlanDestination, durationDays = 4 }) {
  const winningBranch = useMemo(() => getWinningBranch(data), [data]);
  const winner =
    winningBranch === 'destination_a'
      ? data?.destination_a
      : winningBranch === 'destination_b'
      ? data?.destination_b
      : null;

  const rankedDimensions = useMemo(() => {
    return [...(data?.dimensions || [])]
      .sort((a, b) => {
        const deltaA = Math.abs((a.score_a || 0) - (a.score_b || 0));
        const deltaB = Math.abs((b.score_a || 0) - (b.score_b || 0));
        if (deltaB !== deltaA) return deltaB - deltaA;
        return (b.weight || 0) - (a.weight || 0);
      })
      .slice(0, 6);
  }, [data]);

  if (!data) return null;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
      <div className="rounded-2xl border border-accent/20 bg-gradient-to-br from-accent/5 to-sage-light p-5">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-accent mb-2">
              Decision summary
            </div>
            <h2 className="text-2xl font-serif font-bold">
              {winningBranch === 'tie'
                ? `${data.destination_a?.name} and ${data.destination_b?.name} are closely matched`
                : `${winner?.name} is the stronger fit right now`}
            </h2>
            <p className="text-sm text-muted-foreground mt-2 max-w-3xl">{data.verdict}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {(data.plan_start_options || []).map((option) => (
              <button
                key={option.destination}
                onClick={() => onPlanDestination?.(option.destination, option)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                  option.recommended
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-card text-foreground border-border hover:border-accent/30'
                }`}
              >
                {option.recommended ? <CheckCircle2 className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
                Plan {option.destination}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_1fr] gap-4 items-stretch">
        {[data.destination_a, data.destination_b].map((side, index) => {
          const branch = index === 0 ? 'destination_a' : 'destination_b';
          const matchingOption = (data.plan_start_options || []).find((item) => item.branch === branch);
          const isWinner = winningBranch === branch;

          return (
            <div
              key={side?.name || branch}
              className={`rounded-2xl border p-5 ${
                isWinner ? 'border-accent/30 bg-accent/5 shadow-sm' : 'border-border bg-card'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
                    {isWinner ? 'Recommended branch' : 'Alternative branch'}
                  </div>
                  <h3 className="font-serif text-2xl font-bold">{side?.name}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{side?.tagline}</p>
                </div>

                <div className="text-right">
                  <div
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      isWinner ? 'bg-accent text-accent-foreground' : 'bg-secondary text-secondary-foreground'
                    }`}
                  >
                    Score {side?.weighted_score}
                  </div>
                  {isWinner ? (
                    <div className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-accent">
                      <Trophy className="w-3 h-3" />
                      Best current fit
                    </div>
                  ) : null}
                </div>
              </div>

              <HeroImage side={side} isWinner={isWinner} />

              <div className="mt-4 space-y-3">
                <div className="text-sm">
                  <span className="font-medium">Best for:</span>{' '}
                  <span className="text-muted-foreground">{side?.best_for}</span>
                </div>

                {side?.suggested_areas?.length ? (
                  <div className="flex flex-wrap gap-1.5">
                    {side.suggested_areas.slice(0, 4).map((item) => (
                      <span
                        key={item}
                        className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-xs"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                ) : null}

                {side?.review_summary ? (
                  <div className="rounded-xl border border-border bg-background px-3 py-3">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
                      Review signal
                    </div>
                    <div className="text-sm text-muted-foreground">{side.review_summary}</div>
                  </div>
                ) : null}

                <button
                  onClick={() => onPlanDestination?.(side?.name, matchingOption || { destination: side?.name })}
                  className={`w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    isWinner
                      ? 'bg-primary text-primary-foreground hover:opacity-90'
                      : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                  }`}
                >
                  Plan {durationDays} days in {side?.name}
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}

        <div className="hidden lg:flex text-lg font-bold text-muted-foreground items-center justify-center">VS</div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex items-start gap-3 mb-5">
          <Scale className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-lg">What matters most in this decision</h3>
            <p className="text-sm text-muted-foreground">
              These are the clearest differentiators, ranked to make the choice feel more decisive.
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {rankedDimensions.map((dim, i) => (
            <motion.div
              key={dim.name || i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="rounded-xl border border-border bg-background p-4"
            >
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-3">
                <div>
                  <div className="font-medium text-sm">{dim.name}</div>
                  <div className="text-[11px] text-muted-foreground mt-1">Importance weight {dim.weight}</div>
                </div>

                <div className="text-xs">
                  Winner:{' '}
                  <span className="font-semibold text-foreground">{normalizeWinnerLabel(dim.winner)}</span>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-xl bg-card border border-border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm font-medium">{data.destination_a?.name}</div>
                    <div className={`text-sm font-bold ${dim.score_a >= dim.score_b ? 'text-accent' : 'text-foreground'}`}>
                      {dim.score_a}/10
                    </div>
                  </div>
                  <div className="relative h-2 bg-secondary rounded-full overflow-hidden mb-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${dim.score_a * 10}%` }}
                      transition={{ delay: 0.15 + i * 0.03, duration: 0.45 }}
                      className={`h-full rounded-full ${
                        dim.score_a >= dim.score_b ? 'bg-accent' : 'bg-muted-foreground/40'
                      }`}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">{dim.note_a}</p>
                </div>

                <div className="rounded-xl bg-card border border-border p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm font-medium">{data.destination_b?.name}</div>
                    <div className={`text-sm font-bold ${dim.score_b >= dim.score_a ? 'text-accent' : 'text-foreground'}`}>
                      {dim.score_b}/10
                    </div>
                  </div>
                  <div className="relative h-2 bg-secondary rounded-full overflow-hidden mb-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${dim.score_b * 10}%` }}
                      transition={{ delay: 0.15 + i * 0.03, duration: 0.45 }}
                      className={`h-full rounded-full ${
                        dim.score_b >= dim.score_a ? 'bg-accent' : 'bg-muted-foreground/40'
                      }`}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">{dim.note_b}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
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
            <h3 className="font-semibold mb-2">Planning recommendation</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{data.planning_recommendation}</p>
          </div>
        </div>

        {data.next_step_suggestions?.length > 0 ? (
          <div className="flex items-start gap-3">
            <Scale className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h3 className="font-semibold">Next step suggestions</h3>
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
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 className="font-semibold">You’d also love</h3>
              <p className="text-sm text-muted-foreground">
                Strong secondary branches if you want to keep another option alive.
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {data.youd_also_love.slice(0, 4).map((item) => {
              const photo = item?.photos?.[0]?.image_url;
              const initials = getInitials(item?.name);

              return (
                <div key={item.location_id} className="rounded-xl border border-border overflow-hidden bg-background">
                  <div className="h-36 bg-secondary">
                    {photo ? (
                      <img src={photo} alt={item.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-gradient-to-br from-ocean/20 via-secondary to-lavender/15 flex items-end p-4">
                        <div>
                          <div className="text-2xl font-serif font-semibold text-foreground/90">{initials || 'WF'}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {item.city}, {item.country}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-sm">{item.name}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {item.city}, {item.country}
                        </div>
                      </div>
                      <div className="px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[11px] font-medium">
                        {item.category}
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-2 text-[11px] text-accent font-medium">
                      <Sparkles className="w-3 h-3" />
                      {item.match_score}% alternative fit
                    </div>

                    <p className="text-xs text-muted-foreground mt-2">{item.reason}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="grid sm:grid-cols-2 gap-4">
        {(data.plan_start_options?.length
          ? data.plan_start_options
          : [{ destination: data.destination_a?.name }, { destination: data.destination_b?.name }]
        ).map((option) => (
          <button
            key={option.destination}
            onClick={() => onPlanDestination?.(option.destination, option)}
            className={`p-4 rounded-xl text-left transition-colors border ${
              option.recommended
                ? 'bg-accent/5 border-accent/20 hover:border-accent/40'
                : 'bg-card border-border hover:border-accent/30'
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium text-sm">Plan {option.destination}</div>
              {option.recommended ? (
                <span className="px-2 py-0.5 rounded-full bg-accent text-accent-foreground text-[11px] font-semibold">
                  Recommended
                </span>
              ) : null}
            </div>

            <div className="text-xs text-muted-foreground mt-2">
              {option.recommended
                ? 'Start with the stronger branch from this comparison.'
                : 'Keep this as the alternate planning branch.'}
            </div>
          </button>
        ))}
      </div>
    </motion.div>
  );
}