import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

const destinations = [
  { name: 'Tokyo', country: 'Japan', image: 'https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=600&h=400&fit=crop', vibe: 'Culture · Food · Tech' },
  { name: 'Barcelona', country: 'Spain', image: 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=600&h=400&fit=crop', vibe: 'Art · Beach · Nightlife' },
  { name: 'Cape Town', country: 'South Africa', image: 'https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=600&h=400&fit=crop', vibe: 'Nature · Wine · Adventure' },
  { name: 'Marrakech', country: 'Morocco', image: 'https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=600&h=400&fit=crop', vibe: 'Souks · Riads · Spice' },
];

export default function DestinationShowcase() {
  return (
    <section id="destinations" className="py-24 px-4 bg-secondary/30">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="flex items-end justify-between mb-10"
        >
          <div>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold mb-3">Popular destinations</h2>
            <p className="text-muted-foreground">Curated by our AI based on trending travel patterns</p>
          </div>
          <Link to="/discover" className="hidden sm:flex items-center gap-1 text-sm font-medium text-primary hover:gap-2 transition-all">
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {destinations.map((dest, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="group cursor-pointer"
            >
              <Link to="/discover">
                <div className="relative rounded-2xl overflow-hidden aspect-[3/4]">
                  <img src={dest.image} alt={dest.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent" />
                  <div className="absolute bottom-4 left-4 right-4">
                    <h3 className="text-white font-semibold text-xl">{dest.name}</h3>
                    <p className="text-white/70 text-sm">{dest.country}</p>
                    <p className="text-white/50 text-xs mt-1">{dest.vibe}</p>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}