import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Sparkles, Compass, Map, Brain, Navigation, ArrowRight, Star, Users, Globe, ChevronRight } from 'lucide-react';
import HeroSection from '../components/landing/HeroSection';
import FeaturesSection from '../components/landing/FeaturesSection';
import DestinationShowcase from '../components/landing/DestinationShowcase';
import TestimonialSection from '../components/landing/TestimonialSection';
import CTASection from '../components/landing/CTASection';

export default function Landing() {
  return (
    <div className="min-h-screen bg-background">
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
              <Sparkles className="w-4.5 h-4.5 text-primary-foreground" />
            </div>
            <span className="font-serif text-xl font-semibold tracking-tight">Wayfarer</span>
          </Link>
          <nav className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Features</a>
            <a href="#destinations" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Destinations</a>
            <a href="#how" className="text-sm text-muted-foreground hover:text-foreground transition-colors">How It Works</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link to="/discover" className="px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-xl hover:opacity-90 transition-opacity">
              Start Planning
            </Link>
          </div>
        </div>
      </header>

      <HeroSection />
      <FeaturesSection />
      <DestinationShowcase />
      <TestimonialSection />
      <CTASection />

      <footer className="border-t border-border py-12 px-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-serif text-lg font-semibold">Wayfarer</span>
          </div>
          <p className="text-sm text-muted-foreground">© 2026 Wayfarer. AI-powered travel intelligence.</p>
        </div>
      </footer>
    </div>
  );
}