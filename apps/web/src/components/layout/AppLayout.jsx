import { Outlet, Link, useLocation } from 'react-router-dom';
import { Compass, Map, Briefcase, Navigation, User, MessageCircle, Bell, Sparkles } from 'lucide-react';
import { useState, useEffect } from 'react';
import { base44 } from '@/api/base44Client';
import { motion, AnimatePresence } from 'framer-motion';

const navItems = [
  { path: '/discover', label: 'Discover', icon: Compass },
  { path: '/assistant', label: 'Assistant', icon: MessageCircle },
  { path: '/plan', label: 'Plan', icon: Map },
  { path: '/trips', label: 'Trips', icon: Briefcase },
  { path: '/nearby', label: 'Nearby', icon: Navigation },
];

export default function AppLayout() {
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(3);
  const [user, setUser] = useState(null);

  useEffect(() => {
    base44.auth.me().then(setUser).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex fixed left-0 top-0 bottom-0 w-[72px] flex-col items-center py-6 bg-card border-r border-border z-50">
        <Link to="/" className="mb-8">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
        </Link>
        
        <nav className="flex-1 flex flex-col items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`relative w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 group ${
                  isActive 
                    ? 'bg-primary text-primary-foreground shadow-md' 
                    : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="absolute left-full ml-3 px-2.5 py-1 rounded-md bg-foreground text-background text-xs font-medium opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>

        <div className="flex flex-col items-center gap-2">
          <Link
            to="/notifications"
            className={`relative w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-200 ${
              location.pathname === '/notifications' 
                ? 'bg-primary text-primary-foreground' 
                : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
            }`}
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-2 right-2 w-4 h-4 bg-accent text-accent-foreground text-[10px] font-bold rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </Link>
          <Link
            to="/profile"
            className={`w-10 h-10 rounded-full overflow-hidden border-2 transition-all duration-200 ${
              location.pathname === '/profile' ? 'border-primary' : 'border-transparent hover:border-muted-foreground/30'
            }`}
          >
            <div className="w-full h-full bg-gradient-to-br from-accent/20 to-sage/20 flex items-center justify-center">
              <User className="w-4 h-4 text-muted-foreground" />
            </div>
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:ml-[72px] min-h-screen pb-20 lg:pb-0">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Mobile Bottom Nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 glass border-t border-border z-50">
        <div className="flex items-center justify-around px-2 py-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-0.5 px-3 py-1.5 rounded-xl transition-all duration-200 ${
                  isActive 
                    ? 'text-primary' 
                    : 'text-muted-foreground'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : ''}`} />
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}