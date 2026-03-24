import { useState } from 'react';
import { motion } from 'framer-motion';
import { X, Sparkles, Loader2 } from 'lucide-react';
import { base44 } from '@/api/base44Client';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export default function NewTripModal({ onClose, onCreated }) {
  const [destination, setDestination] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [companions, setCompanions] = useState('');
  const [generating, setGenerating] = useState(false);

  const handleCreate = async () => {
    if (!destination) return;
    setGenerating(true);
    const user = await base44.auth.me();

    // Generate itinerary with AI
    const result = await base44.integrations.Core.InvokeLLM({
      prompt: `Create a detailed travel itinerary for ${destination}${startDate ? ` from ${startDate} to ${endDate}` : ' for 5 days'}. 
      Travel companions: ${companions || 'not specified'}.
      Generate a day-by-day plan with specific activities, times, locations, and why each is recommended.
      Make it realistic, specific, and actionable.`,
      response_json_schema: {
        type: "object",
        properties: {
          title: { type: "string" },
          itinerary: {
            type: "array",
            items: {
              type: "object",
              properties: {
                day: { type: "number" },
                title: { type: "string" },
                activities: {
                  type: "array",
                  items: {
                    type: "object",
                    properties: {
                      time: { type: "string" },
                      name: { type: "string" },
                      description: { type: "string" },
                      type: { type: "string" },
                      location: { type: "string" },
                      reason: { type: "string" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    });

    await base44.entities.Trip.create({
      user_email: user.email,
      title: result.title || `Trip to ${destination}`,
      destination,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      companions: companions,
      itinerary: result.itinerary || [],
      status: 'planning',
    });

    setGenerating(false);
    onCreated();
    onClose();
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">Plan a New Trip</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-2">
          <div>
            <label className="text-sm font-medium mb-1.5 block">Where to?</label>
            <input
              type="text"
              placeholder="e.g., Tokyo, Japan"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1.5 block">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1.5 block">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-1.5 block">Travelling with?</label>
            <input
              type="text"
              placeholder="e.g., Partner, Family of 4"
              value={companions}
              onChange={(e) => setCompanions(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-secondary/60 border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={!destination || generating}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating itinerary...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Generate AI Itinerary
              </>
            )}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}