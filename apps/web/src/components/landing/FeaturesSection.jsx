import { motion } from 'framer-motion';
import { Compass, MessageCircle, Map, Navigation, Brain, Gem } from 'lucide-react';

const features = [
  {
    icon: Compass,
    title: 'Smart Discovery',
    description: 'Explore destinations matched to your travel style, budget, and interests. Every suggestion backed by real traveller reviews.',
    color: 'bg-ocean-light text-ocean',
  },
  {
    icon: MessageCircle,
    title: 'AI Travel Assistant',
    description: 'Converse with an intelligent planner that knows places deeply. Ask anything — from hidden cafés to the best time to visit.',
    color: 'bg-accent/10 text-accent',
  },
  {
    icon: Map,
    title: 'Personalized Itineraries',
    description: 'Generate day-by-day plans tailored to you. Swap activities, adjust pace, and understand why each recommendation was made.',
    color: 'bg-sage-light text-sage',
  },
  {
    icon: Navigation,
    title: 'On-Ground Intelligence',
    description: 'Live recommendations while you travel. Find what\'s great nearby, right now, based on your context and preferences.',
    color: 'bg-sunset-light text-sunset',
  },
  {
    icon: Brain,
    title: 'Evolving Memory',
    description: 'Wayfarer learns from every trip. Your preferences, feedback, and experiences shape smarter future recommendations.',
    color: 'bg-lavender-light text-lavender',
  },
  {
    icon: Gem,
    title: 'Hidden Gems',
    description: 'Discover lesser-known spots that match your style. Intelligently surfaced from review patterns and local knowledge.',
    color: 'bg-accent/10 text-accent',
  },
];

export default function FeaturesSection() {
  return (
    <section id="features" className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-4">Everything you need to travel smarter</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            From first inspiration to post-trip memories, Wayfarer is your intelligent travel companion at every stage.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="group p-6 rounded-2xl bg-card border border-border hover:shadow-lg hover:border-border/80 transition-all duration-300"
              >
                <div className={`w-12 h-12 rounded-xl ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-lg mb-2">{feature.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}