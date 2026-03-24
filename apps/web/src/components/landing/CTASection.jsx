import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';

export default function CTASection() {
  return (
    <section id="how" className="py-24 px-4">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="relative rounded-3xl overflow-hidden p-10 sm:p-16 text-center"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-primary via-primary to-primary/90" />
          <div className="absolute inset-0 opacity-10">
            <div className="absolute top-10 left-10 w-40 h-40 rounded-full bg-accent blur-3xl" />
            <div className="absolute bottom-10 right-10 w-60 h-60 rounded-full bg-ocean blur-3xl" />
          </div>
          
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 text-primary-foreground text-sm font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Free to start
            </div>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold text-primary-foreground mb-4">
              Your next great trip starts here
            </h2>
            <p className="text-primary-foreground/70 max-w-lg mx-auto mb-8">
              Tell us how you like to travel, and we'll show you destinations, plans, and hidden gems that fit your style perfectly.
            </p>
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-2 px-8 py-4 bg-accent text-accent-foreground rounded-xl font-medium hover:opacity-90 transition-opacity"
            >
              Create Your Travel Profile
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}