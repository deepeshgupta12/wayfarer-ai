import { motion } from 'framer-motion';
import { Slider } from '@/components/ui/slider';
import { Sparkles } from 'lucide-react';

export default function OnboardingStep({ step, answers, onSelect, onSlider }) {
  if (step.id === 'welcome') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="text-center"
      >
        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 3, repeat: Infinity }}
          className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center mx-auto mb-8"
        >
          <Sparkles className="w-9 h-9 text-accent" />
        </motion.div>
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-4">{step.title}</h1>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">{step.subtitle}</p>
      </motion.div>
    );
  }

  if (step.type === 'single' || step.type === 'multi') {
    const selected = step.type === 'single' ? answers[step.id] : (answers[step.id] || []);
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
      >
        <h2 className="font-serif text-2xl sm:text-3xl font-bold mb-2">{step.title}</h2>
        <p className="text-muted-foreground mb-8">{step.subtitle}</p>
        <div className={`grid gap-3 ${step.type === 'multi' ? 'grid-cols-2 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2'}`}>
          {step.options.map((opt) => {
            const isSelected = step.type === 'single' ? selected === opt.value : selected.includes(opt.value);
            return (
              <motion.button
                key={opt.value}
                whileTap={{ scale: 0.97 }}
                onClick={() => onSelect(opt.value)}
                className={`relative p-4 rounded-xl border-2 text-left transition-all duration-200 ${
                  isSelected
                    ? 'border-primary bg-primary/5 shadow-sm'
                    : 'border-border hover:border-muted-foreground/30 bg-card'
                }`}
              >
                <span className="text-2xl mb-2 block">{opt.emoji}</span>
                <span className="font-medium text-sm block">{opt.label}</span>
                {opt.desc && <span className="text-xs text-muted-foreground block mt-0.5">{opt.desc}</span>}
                {isSelected && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center"
                  >
                    <svg className="w-3 h-3 text-primary-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </motion.div>
                )}
              </motion.button>
            );
          })}
        </div>
        {step.type === 'multi' && (
          <p className="text-xs text-muted-foreground mt-4">Select at least 2 interests</p>
        )}
      </motion.div>
    );
  }

  if (step.type === 'sliders') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
      >
        <h2 className="font-serif text-2xl sm:text-3xl font-bold mb-2">{step.title}</h2>
        <p className="text-muted-foreground mb-8">{step.subtitle}</p>
        <div className="space-y-6">
          {step.sliders.map((s) => (
            <div key={s.key} className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                  {s.emoji} {s.label}
                </span>
                <span className="text-xs text-muted-foreground font-medium">
                  {answers.biases[s.key] <= 25 ? 'Not important' : answers.biases[s.key] <= 50 ? 'Nice to have' : answers.biases[s.key] <= 75 ? 'Important' : 'Essential'}
                </span>
              </div>
              <Slider
                value={[answers.biases[s.key]]}
                onValueChange={([v]) => onSlider(s.key, v)}
                max={100}
                step={1}
                className="w-full"
              />
            </div>
          ))}
        </div>
      </motion.div>
    );
  }

  return null;
}