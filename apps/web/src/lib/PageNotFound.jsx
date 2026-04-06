import { useLocation, Link } from 'react-router-dom';
import { Compass, Home } from 'lucide-react';

export default function PageNotFound() {
    const location = useLocation();
    const pageName = location.pathname.substring(1);

    return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-background">
            <div className="max-w-md w-full text-center">
                <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-6">
                    <Compass className="w-7 h-7 text-muted-foreground" />
                </div>
                <h1 className="font-serif text-5xl font-bold text-muted-foreground/30 mb-4">404</h1>
                <h2 className="text-xl font-semibold mb-2">Off the beaten path</h2>
                <p className="text-sm text-muted-foreground mb-8">
                    The page <span className="font-medium">"{pageName}"</span> doesn't exist. Let's get you back on track.
                </p>

                <div className="flex items-center justify-center gap-3">
                    <Link to="/" className="inline-flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity">
                        <Home className="w-4 h-4" />
                        Go Home
                    </Link>
                    <Link to="/discover" className="inline-flex items-center gap-2 px-4 py-2.5 bg-secondary text-secondary-foreground rounded-xl text-sm font-medium hover:bg-secondary/80 transition-colors">
                        <Compass className="w-4 h-4" />
                        Discover
                    </Link>
                </div>
            </div>
        </div>
    );
}
