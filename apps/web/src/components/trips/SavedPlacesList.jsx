import { motion } from 'framer-motion';
import PlaceCard from '../cards/PlaceCard';

function buildReason(place) {
  const source = place?.reason_saved || 'Saved from trip';
  const city = place?.city ? ` • ${place.city}` : '';
  return `${source}${city}`;
}

export default function SavedPlacesList({ places }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {places.map((place, index) => (
        <motion.div
          key={place.id || place.location_id || `${place.name}-${index}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.03 }}
        >
          <PlaceCard
            name={place.name}
            image={place.image_url}
            photos={place.photos || []}
            category={place.category}
            rating={place.rating}
            description={place.description}
            reason={buildReason(place)}
            isGem={place.is_hidden_gem}
            tags={place.tags || []}
          />
        </motion.div>
      ))}
    </div>
  );
}