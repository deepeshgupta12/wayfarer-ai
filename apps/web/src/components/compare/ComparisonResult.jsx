import { motion } from 'framer-motion';
import { Trophy, Users, Heart, UserCircle, Sparkles } from 'lucide-react';

export default function ComparisonResult({ data }) {
  if (!data) return null;

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
      {/* Headers */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
        <div className="p-5 rounded-2xl bg-card border border-border text-center">
          <h3 className="font-serif text-xl font-bold">{data.destination_a?.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{data.destination_a?.tagline}</p>
          <p className="text-xs text-accent mt-2">Best for: {data.destination_a?.best_for}</p>
        </div>
        <div className="text-lg font-bold text-muted-foreground">VS</div>
        <div className="p-5 rounded-2xl bg-card border border-border text-center">
          <h3 className="font-serif text-xl font-bold">{data.destination_b?.name}</h3>
          <p className="text-sm text-muted-foreground mt-1">{data.destination_b?.tagline}</p>
          <p className="text-xs text-accent mt-2">Best for: {data.destination_b?.best_for}</p>
        </div>
      </div>

      {/* Dimensions */}
      <div className="space-y-3">
        <h3 className="font-semibold text-lg mb-4">Detailed Comparison</h3>
        {data.dimensions?.map((dim, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="p-4 rounded-xl bg-card border border-border"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-medium text-sm">{dim.name}</span>
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
                  transition={{ delay: 0.3 + i * 0.05, duration: 0.5 }}
                  className={`h-full rounded-full ${dim.score_a >= dim.score_b ? 'bg-accent' : 'bg-muted-foreground/40'}`}
                />
              </div>
              <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${dim.score_b * 10}%` }}
                  transition={{ delay: 0.3 + i * 0.05, duration: 0.5 }}
                  className={`h-full rounded-full ${dim.score_b >= dim.score_a ? 'bg-accent' : 'bg-muted-foreground/40'}`}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-2">
              <p className="text-xs text-muted-foreground">{dim.note_a}</p>
              <p className="text-xs text-muted-foreground">{dim.note_b}</p>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Verdict */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-accent/5 to-sage-light border border-accent/10">
        <div className="flex items-start gap-3 mb-4">
          <Trophy className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold mb-2">AI Verdict</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{data.verdict}</p>
          </div>
        </div>
      </div>

      {/* By Traveller Type */}
      <div className="grid sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-ocean" />
            <h4 className="font-medium text-sm">Solo Travellers</h4>
          </div>
          <p className="text-xs text-muted-foreground">{data.recommendation_solo}</p>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Heart className="w-4 h-4 text-sunset" />
            <h4 className="font-medium text-sm">Couples</h4>
          </div>
          <p className="text-xs text-muted-foreground">{data.recommendation_couple}</p>
        </div>
        <div className="p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 mb-2">
            <UserCircle className="w-4 h-4 text-sage" />
            <h4 className="font-medium text-sm">Families</h4>
          </div>
          <p className="text-xs text-muted-foreground">{data.recommendation_family}</p>
        </div>
      </div>
    </motion.div>
  );
}