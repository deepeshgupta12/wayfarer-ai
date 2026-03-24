import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function LoadingState({ message = "Discovering the perfect recommendations...", compact = false }) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 py-4">
        <div className="flex gap-1">
          {[0, 1, 2].map(i => (
            <motion.div
              key={i}
              className="w-2 h-2 rounded-full bg-accent"
              animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
        <span className="text-sm text-muted-foreground">{message}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        className="mb-6"
      >
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center">
          <Sparkles className="w-7 h-7 text-accent" />
        </div>
      </motion.div>
      <motion.p 
        className="text-muted-foreground text-center max-w-xs"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {message}
      </motion.p>
    </div>
  );
}