import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, ArrowLeft, Sparkles, Check } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import OnboardingStep from '../components/onboarding/OnboardingStep';

const steps = [
  {
    id: 'welcome',
    title: 'Welcome to Wayfarer',
    subtitle: 'Let\'s build your travel profile in 2 minutes. This helps us find places that truly fit you.',
  },
  {
    id: 'social_mode',
    title: 'Who do you usually travel with?',
    subtitle: 'This shapes how we suggest accommodations, activities, and pacing.',
    type: 'single',
    options: [
      { value: 'solo', label: 'Solo', emoji: '🎒', desc: 'Just me and the world' },
      { value: 'couple', label: 'With a partner', emoji: '💕', desc: 'Romantic getaways' },
      { value: 'friends', label: 'With friends', emoji: '👥', desc: 'Group adventures' },
      { value: 'family', label: 'With family', emoji: '👨‍👩‍👧‍👦', desc: 'Kid-friendly fun' },
    ],
  },
  {
    id: 'budget',
    title: 'What\'s your typical travel budget?',
    subtitle: 'We\'ll prioritize recommendations that match your comfort zone.',
    type: 'single',
    options: [
      { value: 'budget', label: 'Budget', emoji: '🏕️', desc: 'Hostels, street food, local transport' },
      { value: 'moderate', label: 'Moderate', emoji: '🏨', desc: 'Mid-range hotels, nice restaurants' },
      { value: 'premium', label: 'Premium', emoji: '✨', desc: 'Boutique stays, curated experiences' },
      { value: 'luxury', label: 'Luxury', emoji: '🏰', desc: 'The finest of everything' },
    ],
  },
  {
    id: 'pace',
    title: 'How do you like to pace your trips?',
    subtitle: 'This helps us plan the right number of activities per day.',
    type: 'single',
    options: [
      { value: 'slow', label: 'Slow & relaxed', emoji: '🧘', desc: '2-3 activities, lots of downtime' },
      { value: 'moderate', label: 'Balanced', emoji: '🚶', desc: '4-5 activities with breaks' },
      { value: 'fast', label: 'Action-packed', emoji: '🏃', desc: 'Fill every moment' },
      { value: 'intense', label: 'Non-stop', emoji: '⚡', desc: 'See & do everything possible' },
    ],
  },
  {
    id: 'interests',
    title: 'What draws you to a destination?',
    subtitle: 'Select all that excite you. We use this to calibrate recommendations.',
    type: 'multi',
    options: [
      { value: 'food', label: 'Food & Cuisine', emoji: '🍜' },
      { value: 'culture', label: 'Culture & History', emoji: '🏛️' },
      { value: 'adventure', label: 'Adventure & Outdoors', emoji: '🏔️' },
      { value: 'art', label: 'Art & Architecture', emoji: '🎨' },
      { value: 'nature', label: 'Nature & Wildlife', emoji: '🌿' },
      { value: 'nightlife', label: 'Nightlife & Music', emoji: '🎵' },
      { value: 'wellness', label: 'Wellness & Spa', emoji: '🧖' },
      { value: 'local', label: 'Local Neighborhoods', emoji: '🏘️' },
      { value: 'shopping', label: 'Shopping & Markets', emoji: '🛍️' },
      { value: 'photography', label: 'Photography', emoji: '📸' },
      { value: 'romance', label: 'Romance', emoji: '💫' },
      { value: 'beach', label: 'Beach & Coast', emoji: '🏖️' },
    ],
  },
  {
    id: 'biases',
    title: 'Rate what matters most to you',
    subtitle: 'Slide to show how much each aspect matters when you travel.',
    type: 'sliders',
    sliders: [
      { key: 'food', label: 'Amazing Food', emoji: '🍽️' },
      { key: 'culture', label: 'Rich Culture', emoji: '🎭' },
      { key: 'adventure', label: 'Adventure', emoji: '🧗' },
      { key: 'comfort', label: 'Comfort & Luxury', emoji: '🛋️' },
      { key: 'local_exploration', label: 'Local Discovery', emoji: '🗺️' },
      { key: 'nature', label: 'Nature & Scenery', emoji: '🌄' },
    ],
  },
];

export default function Onboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState({
    social_mode: '',
    budget: '',
    pace: '',
    interests: [],
    biases: { food: 50, culture: 50, adventure: 50, comfort: 50, local_exploration: 50, nature: 50 },
  });
  const [saving, setSaving] = useState(false);

  const step = steps[currentStep];
  const progress = ((currentStep) / (steps.length - 1)) * 100;

  const canProceed = () => {
    if (step.id === 'welcome') return true;
    if (step.type === 'single') return answers[step.id];
    if (step.type === 'multi') return answers[step.id]?.length >= 2;
    if (step.type === 'sliders') return true;
    return true;
  };

  const handleSelect = (value) => {
    if (step.type === 'single') {
      setAnswers({ ...answers, [step.id]: value });
    } else if (step.type === 'multi') {
      const current = answers[step.id] || [];
      setAnswers({
        ...answers,
        [step.id]: current.includes(value) ? current.filter(v => v !== value) : [...current, value],
      });
    }
  };

  const handleSlider = (key, value) => {
    setAnswers({
      ...answers,
      biases: { ...answers.biases, [key]: value },
    });
  };

  const handleNext = async () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      setSaving(true);
      const user = await base44.auth.me();
      const biasesNormalized = {};
      Object.entries(answers.biases).forEach(([k, v]) => {
        biasesNormalized[k] = v / 100;
      });
      await base44.entities.TravellerProfile.create({
        user_email: user.email,
        display_name: user.full_name,
        social_mode: answers.social_mode,
        budget_level: answers.budget,
        travel_pace: answers.pace,
        interests: answers.interests,
        experience_biases: biasesNormalized,
        onboarding_completed: true,
      });
      navigate('/discover');
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Progress bar */}
      <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-secondary">
        <motion.div
          className="h-full bg-accent"
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-serif text-lg font-semibold">Wayfarer</span>
        </div>
        <span className="text-xs text-muted-foreground">{currentStep + 1} of {steps.length}</span>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-lg">
          <AnimatePresence mode="wait">
            <OnboardingStep
              key={step.id}
              step={step}
              answers={answers}
              onSelect={handleSelect}
              onSlider={handleSlider}
            />
          </AnimatePresence>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 sm:px-6 py-6 flex items-center justify-between">
        <button
          onClick={() => currentStep > 0 && setCurrentStep(currentStep - 1)}
          className={`flex items-center gap-1.5 text-sm font-medium transition-opacity ${currentStep === 0 ? 'opacity-0 pointer-events-none' : 'text-muted-foreground hover:text-foreground'}`}
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={!canProceed() || saving}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {saving ? 'Setting up...' : currentStep === steps.length - 1 ? 'Complete Setup' : 'Continue'}
          {!saving && (currentStep === steps.length - 1 ? <Check className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />)}
        </button>
      </div>
    </div>
  );
}