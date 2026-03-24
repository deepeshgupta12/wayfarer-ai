import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles, Play } from 'lucide-react';

const destinations = [
  { name: 'Kyoto', image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=400&h=500&fit=crop', tag: '94% match' },
  { name: 'Lisbon', image: 'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=400&h=500&fit=crop', tag: 'Hidden Gems' },
  { name: 'Medellín', image: 'https://images.unsplash.com/photo-1599491142898-f tried3c29f?w=400&h=500&fit=crop', tag: 'Trending' },
];

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-sage-light/30" />
        <motion.div
          animate={{ scale: [1, 1.02, 1], opacity: [0.03, 0.06, 0.03] }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute top-20 right-20 w-[500px] h-[500px] rounded-full bg-accent/10 blur-3xl"
        />
        <motion.div
          animate={{ scale: [1, 1.03, 1], opacity: [0.04, 0.07, 0.04] }}
          transition={{ duration: 10, repeat: Infinity, delay: 2 }}
          className="absolute bottom-20 left-10 w-[400px] h-[400px] rounded-full bg-ocean/10 blur-3xl"
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent/10 text-accent text-sm font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Travel Intelligence
            </div>
            <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.1] mb-6 tracking-tight">
              Travel that
              <br />
              <span className="text-gradient">understands</span>
              <br />
              you.
            </h1>
            <p className="text-lg text-muted-foreground max-w-lg mb-8 leading-relaxed">
              Discover destinations that match your style. Build personalized itineraries. 
              Get intelligent recommendations that improve with every trip.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                to="/onboarding"
                className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-primary text-primary-foreground rounded-xl font-medium hover:opacity-90 transition-opacity text-sm"
              >
                Start Your Journey
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/discover"
                className="inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-secondary text-secondary-foreground rounded-xl font-medium hover:bg-secondary/80 transition-colors text-sm"
              >
                Explore Destinations
              </Link>
            </div>

            <div className="flex items-center gap-6 mt-10 pt-8 border-t border-border">
              <div>
                <div className="text-2xl font-bold">50K+</div>
                <div className="text-xs text-muted-foreground">Destinations</div>
              </div>
              <div className="w-px h-8 bg-border" />
              <div>
                <div className="text-2xl font-bold">2M+</div>
                <div className="text-xs text-muted-foreground">Reviews Analyzed</div>
              </div>
              <div className="w-px h-8 bg-border" />
              <div>
                <div className="text-2xl font-bold">98%</div>
                <div className="text-xs text-muted-foreground">Match Accuracy</div>
              </div>
            </div>
          </motion.div>

          {/* Right - Destination Cards Stack */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
            className="relative hidden lg:block"
          >
            <div className="relative h-[520px]">
              {/* Floating Cards */}
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 4, repeat: Infinity }}
                className="absolute top-0 right-0 w-64 rounded-2xl overflow-hidden shadow-2xl border border-border/50"
              >
                <img src="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=400&h=280&fit=crop" alt="Kyoto" className="w-full h-40 object-cover" />
                <div className="p-4 bg-card">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold">Kyoto, Japan</h4>
                      <p className="text-xs text-muted-foreground">Culture · Temples · Food</p>
                    </div>
                    <div className="px-2 py-1 rounded-full bg-sage-light text-sage text-xs font-semibold">94% match</div>
                  </div>
                </div>
              </motion.div>

              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 5, repeat: Infinity, delay: 1 }}
                className="absolute top-36 left-0 w-56 rounded-2xl overflow-hidden shadow-xl border border-border/50"
              >
                <img src="https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=400&h=240&fit=crop" alt="Lisbon" className="w-full h-32 object-cover" />
                <div className="p-3 bg-card">
                  <h4 className="font-semibold text-sm">Lisbon, Portugal</h4>
                  <p className="text-xs text-muted-foreground">Charm · Seafood · Hills</p>
                </div>
              </motion.div>

              <motion.div
                animate={{ y: [0, -5, 0] }}
                transition={{ duration: 4.5, repeat: Infinity, delay: 0.5 }}
                className="absolute bottom-8 right-8 w-60 p-4 rounded-2xl bg-card shadow-xl border border-border/50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-accent" />
                  <span className="text-xs font-medium text-accent">AI Insight</span>
                </div>
                <p className="text-sm">"Based on your love for street food and walkable cities, Lisbon is your top match this season."</p>
              </motion.div>

              {/* Decorative elements */}
              <div className="absolute top-20 left-32 w-3 h-3 rounded-full bg-accent/40 animate-pulse-soft" />
              <div className="absolute bottom-40 right-40 w-2 h-2 rounded-full bg-sage/40 animate-pulse-soft" />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}