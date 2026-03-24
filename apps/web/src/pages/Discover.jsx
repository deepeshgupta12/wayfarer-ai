import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Filter, Sparkles, TrendingUp, Gem, Globe, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import DestinationCard from '../components/cards/DestinationCard';

const trendingDestinations = [
  { name: 'Kyoto', country: 'Japan', image: 'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=600&h=400&fit=crop', matchScore: 94, rating: 4.8, tags: ['Culture', 'Temples', 'Food', 'Gardens'] },
  { name: 'Lisbon', country: 'Portugal', image: 'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=600&h=400&fit=crop', matchScore: 91, rating: 4.7, tags: ['Coastal', 'Food', 'Nightlife', 'History'] },
  { name: 'Medellín', country: 'Colombia', image: 'https://images.unsplash.com/photo-1583997052103-b4a1cb974ce5?w=600&h=400&fit=crop', matchScore: 88, rating: 4.6, tags: ['Spring City', 'Culture', 'Cafes', 'Nature'] },
  { name: 'Dubrovnik', country: 'Croatia', image: 'https://images.unsplash.com/photo-1555990538-1e15fdf2c512?w=600&h=400&fit=crop', matchScore: 86, rating: 4.7, tags: ['Old Town', 'Coast', 'History', 'Views'] },
  { name: 'Marrakech', country: 'Morocco', image: 'https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=600&h=400&fit=crop', matchScore: 84, rating: 4.5, tags: ['Souks', 'Riads', 'Spice', 'Desert'] },
  { name: 'Cape Town', country: 'South Africa', image: 'https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=600&h=400&fit=crop', matchScore: 82, rating: 4.8, tags: ['Nature', 'Wine', 'Beach', 'Adventure'] },
];

const hiddenGems = [
  { name: 'Luang Prabang', country: 'Laos', image: 'https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=600&h=400&fit=crop', matchScore: 90, rating: 4.6, tags: ['Temples', 'River', 'Quiet'], isGem: true },
  { name: 'Oaxaca', country: 'Mexico', image: 'https://images.unsplash.com/photo-1570737209810-87a8e7245c18?w=600&h=400&fit=crop', matchScore: 87, rating: 4.7, tags: ['Food', 'Art', 'Indigenous'], isGem: true },
  { name: 'Valletta', country: 'Malta', image: 'https://images.unsplash.com/photo-1561473875-5f5f41204bc1?w=600&h=400&fit=crop', matchScore: 85, rating: 4.5, tags: ['History', 'Baroque', 'Sea'], isGem: true },
];

const categories = [
  { label: 'All', icon: Globe },
  { label: 'For You', icon: Sparkles },
  { label: 'Trending', icon: TrendingUp },
  { label: 'Hidden Gems', icon: Gem },
];

export default function Discover() {
  const [activeCategory, setActiveCategory] = useState('For You');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-serif text-3xl sm:text-4xl font-bold mb-2">Discover</h1>
        <p className="text-muted-foreground">Destinations matched to your travel style</p>
      </motion.div>

      {/* Search */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mb-6">
        <div className="relative max-w-xl">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search destinations, vibes, or experiences..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-3 rounded-xl bg-secondary/60 border border-border text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/30 transition-all"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg hover:bg-background transition-colors">
            <Filter className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </motion.div>

      {/* Categories */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-2 scrollbar-hide">
        {categories.map((cat) => {
          const Icon = cat.icon;
          return (
            <button
              key={cat.label}
              onClick={() => setActiveCategory(cat.label)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
                activeCategory === cat.label
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {cat.label}
            </button>
          );
        })}
      </div>

      {/* AI Recommendation Banner */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-10 p-5 rounded-2xl bg-gradient-to-r from-accent/10 via-sage-light/50 to-ocean-light/50 border border-accent/10"
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-accent" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1">Personalized for you</h3>
            <p className="text-sm text-muted-foreground">
              Based on your love for food, culture, and walkable cities at a moderate pace — here are destinations you'll love this season.
            </p>
          </div>
          <Link to="/assistant" className="flex items-center gap-1 text-sm font-medium text-accent hover:gap-2 transition-all whitespace-nowrap">
            Ask AI <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </motion.div>

      {/* Trending Destinations */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="font-semibold text-xl mb-0.5">Top Matches</h2>
            <p className="text-sm text-muted-foreground">Highest compatibility with your travel profile</p>
          </div>
          <Link to="/compare" className="text-sm font-medium text-primary hover:underline">Compare</Link>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {trendingDestinations.map((dest, i) => (
            <motion.div
              key={dest.name}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <DestinationCard {...dest} onClick={() => {}} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* Hidden Gems */}
      <section className="mb-12">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Gem className="w-5 h-5 text-accent" />
            <div>
              <h2 className="font-semibold text-xl mb-0.5">Hidden Gems</h2>
              <p className="text-sm text-muted-foreground">Lesser-known destinations that match your style</p>
            </div>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {hiddenGems.map((dest, i) => (
            <motion.div
              key={dest.name}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <DestinationCard {...dest} onClick={() => {}} />
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}