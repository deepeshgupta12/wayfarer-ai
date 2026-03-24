import { useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, AlertCircle, Sparkles, Lightbulb, Clock, Check, Trash2 } from 'lucide-react';
import EmptyState from '../components/ui/EmptyState';

const sampleNotifications = [
  {
    id: 1,
    type: 'alert',
    title: 'Schedule Change Alert',
    body: 'The Tsukiji Outer Market on Day 2 of your Tokyo trip is closed on Wednesdays. We recommend visiting Toyosu Market instead — it\'s equally rated and matches your food interests.',
    time: '2 hours ago',
    read: false,
    priority: 'high',
    confidence: 95,
  },
  {
    id: 2,
    type: 'recommendation',
    title: 'Hidden Gem Near Your Hotel',
    body: 'Café Kitsune in Omotesandō is just 5 min walk from where you\'re staying. Highly rated by food-loving solo travellers and rarely crowded in mornings.',
    time: '5 hours ago',
    read: false,
    priority: 'medium',
    confidence: 88,
  },
  {
    id: 3,
    type: 'insight',
    title: 'Better Time to Visit',
    body: 'Based on recent visitor patterns, Fushimi Inari Shrine is least crowded between 6-7am. Your current plan has you arriving at 10am. Want to adjust?',
    time: '1 day ago',
    read: true,
    priority: 'medium',
    confidence: 92,
  },
  {
    id: 4,
    type: 'reminder',
    title: 'Trip Memory Available',
    body: 'Your Lisbon trip ended a week ago. Rate your experience and help Wayfarer improve your future recommendations.',
    time: '3 days ago',
    read: true,
    priority: 'low',
    confidence: null,
  },
];

const typeIcons = {
  alert: AlertCircle,
  recommendation: Sparkles,
  insight: Lightbulb,
  reminder: Clock,
};

const typeColors = {
  alert: 'bg-destructive/10 text-destructive',
  recommendation: 'bg-accent/10 text-accent',
  insight: 'bg-ocean-light text-ocean',
  reminder: 'bg-sage-light text-sage',
};

export default function Notifications() {
  const [notifications, setNotifications] = useState(sampleNotifications);

  const markAsRead = (id) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-serif text-3xl font-bold mb-1">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
          </p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => setNotifications(prev => prev.map(n => ({ ...n, read: true })))}
            className="text-sm text-primary font-medium hover:underline"
          >
            Mark all read
          </button>
        )}
      </motion.div>

      {notifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No notifications"
          description="When Wayfarer has useful alerts, recommendations, or insights about your trips, they'll appear here."
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((notif, i) => {
            const Icon = typeIcons[notif.type] || Bell;
            return (
              <motion.div
                key={notif.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => markAsRead(notif.id)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  notif.read
                    ? 'bg-card border-border'
                    : 'bg-card border-primary/20 shadow-sm'
                }`}
              >
                <div className="flex gap-3">
                  <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${typeColors[notif.type]}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className={`text-sm ${notif.read ? 'font-medium' : 'font-semibold'}`}>
                          {notif.title}
                          {!notif.read && <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent ml-2 -mt-1" />}
                        </h4>
                        <span className="text-xs text-muted-foreground">{notif.time}</span>
                      </div>
                      {notif.confidence && (
                        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-secondary text-muted-foreground flex-shrink-0">
                          {notif.confidence}% confident
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">{notif.body}</p>
                    <div className="flex items-center gap-3 mt-3">
                      <button className="text-xs font-medium text-primary hover:underline">View Details</button>
                      <button className="text-xs font-medium text-accent hover:underline">Take Action</button>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}