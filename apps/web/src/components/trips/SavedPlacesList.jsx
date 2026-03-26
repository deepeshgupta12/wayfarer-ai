import PlaceCard from '../cards/PlaceCard';
import { motion } from 'framer-motion';

export default function SavedPlacesList({ places }) {
  return (
    <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {places.map((place, i) => (
        <motion.div
          key={place.id || place.location_id || `${place.name}-${i}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
        >
          <PlaceCard
            name={place.name}
            image={place.image_url}
            category={place.category}
            rating={place.rating}
            description={place.description}
            reason={place.reason_saved}
            isGem={place.is_hidden_gem}
          />
        </motion.div>
      ))}
    </div>
  );
}