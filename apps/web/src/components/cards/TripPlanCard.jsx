import { motion } from 'framer-motion';
import { MapPin, Calendar, Layers, Heart, Camera } from 'lucide-react';
import { Link } from 'react-router-dom';
import moment from 'moment';

const defaultImages = [
  'https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=800&h=500&fit=crop',
  'https://images.unsplash.com/photo-1585208798174-6cedd86e019a?w=800&h=500&fit=crop',
  'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800&h=500&fit=crop',
];

const statusColors = {
  planning: 'bg-secondary text-secondary-foreground',
  upcoming: 'bg-ocean-light text-ocean',
  active: 'bg-accent/10 text-accent',
  completed: 'bg-sage-light text-sage',
};

function getTripImage(trip) {
  const firstSlotPhoto = trip?.itinerary_skeleton?.flatMap((day) => day?.slots || []).flatMap((slot) => slot?.assigned_place_photos || [])[0]?.image_url;
  return firstSlotPhoto || trip?.destination_image || defaultImages[Math.floor(Math.random() * defaultImages.length)];
}

export default function TripPlanCard({ trip }) {
  const image = getTripImage(trip);
  const versionCount = trip.current_version_number || 0;
  const selectedPlacesCount = trip.selected_places_count || 0;
  const photoCount = trip?.candidate_places?.reduce((acc, item) => acc + (item?.photos?.length || 0), 0) || 0;

  return (
    <Link to={`/itinerary?trip=${trip.trip_id}`}>
      <motion.div
        whileHover={{ y: -3 }}
        className="group rounded-2xl overflow-hidden bg-card border border-border hover:shadow-lg transition-all duration-300"
      >
        <div className="relative h-36 overflow-hidden bg-secondary">
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

          <div className="flex items-center gap-3 text-[11px] text-muted-foreground pt-1 flex-wrap">
            <span className="inline-flex items-center gap-1">
              <Layers className="w-3 h-3" />
              {versionCount} versions
            </span>
            <span className="inline-flex items-center gap-1">
              <Heart className="w-3 h-3" />
              {selectedPlacesCount} saved
            </span>
            <span className="inline-flex items-center gap-1">
              <Camera className="w-3 h-3" />
              {photoCount} photos
            </span>
          </div>
        </div>
      </motion.div>
    </Link>
  );
}
