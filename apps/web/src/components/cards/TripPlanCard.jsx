import { motion } from 'framer-motion';
import { Calendar, MapPin, Layers, Heart } from 'lucide-react';
import { Link } from 'react-router-dom';
import moment from 'moment';

const statusColors = {
  planning: 'bg-ocean-light text-ocean',
  upcoming: 'bg-sage-light text-sage',
  active: 'bg-accent/10 text-accent',
  completed: 'bg-secondary text-muted-foreground',
};

const defaultImages = [
  'https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=600&h=300&fit=crop',
  'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?w=600&h=300&fit=crop',
  'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=600&h=300&fit=crop',
];

export default function TripPlanCard({ trip }) {
  const image =
    trip.destination_image || defaultImages[Math.floor(Math.random() * defaultImages.length)];

  const versionCount = trip.current_version_number || 0;
  const selectedPlacesCount = trip.selected_places_count || 0;

  return (
    <Link to={`/itinerary?trip=${trip.trip_id}`}>
      <motion.div
        whileHover={{ y: -3 }}
        className="group rounded-2xl overflow-hidden bg-card border border-border hover:shadow-lg transition-all duration-300"
      >
        <div className="relative h-36 overflow-hidden">
          <img
            src={image}
            alt={trip.destination || trip.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
          <span
            className={`absolute top-3 left-3 px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
              statusColors[trip.status] || 'bg-secondary text-muted-foreground'
            }`}
          >
            {trip.status}
          </span>
        </div>

        <div className="p-4">
          <h3 className="font-semibold mb-1 group-hover:text-accent transition-colors">
            {trip.title}
          </h3>

          <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
            <MapPin className="w-3 h-3" />
            {trip.destination || 'Destination pending'}
          </div>

          {trip.start_date ? (
            <div className="flex items-center gap-1 text-xs text-muted-foreground mb-2">
              <Calendar className="w-3 h-3" />
              {moment(trip.start_date).format('MMM D')}
              {' — '}
              {trip.end_date ? moment(trip.end_date).format('MMM D, YYYY') : 'TBD'}
            </div>
          ) : null}

          <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-1">
            <span className="inline-flex items-center gap-1">
              <Layers className="w-3 h-3" />
              {versionCount} versions
            </span>
            <span className="inline-flex items-center gap-1">
              <Heart className="w-3 h-3" />
              {selectedPlacesCount} saved
            </span>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}