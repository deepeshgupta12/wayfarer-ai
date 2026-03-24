import { motion } from 'framer-motion';

export default function EmptyState({ icon: Icon, title, description, action, actionLabel, className = "" }) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex flex-col items-center justify-center py-16 px-6 text-center ${className}`}
    >
      {Icon && (
        <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mb-5">
          <Icon className="w-7 h-7 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground text-sm max-w-sm mb-6">{description}</p>
      {action && (
        <button 
          onClick={action}
          className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
        >
          {actionLabel}
        </button>
      )}
    </motion.div>
  );
}