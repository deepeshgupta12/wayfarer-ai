import { useLocation, Link } from 'react-router-dom';
import { base44 } from '@/api/base44Client';
import { useQuery } from '@tanstack/react-query';
import { Compass, Home } from 'lucide-react';

export default function PageNotFound() {
    const location = useLocation();
    const pageName = location.pathname.substring(1);

    const { data: authData, isFetched } = useQuery({
        queryKey: ['user'],
        queryFn: async () => {
            try {
                const user = await base44.auth.me();
                return { user, isAuthenticated: true };
            } catch (error) {
                return { user: null, isAuthenticated: false };
            }
        }
    });
    
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
                
                {isFetched && authData?.isAuthenticated && authData?.user?.role === 'admin' && (
                    <div className="mb-6 p-4 bg-accent/5 rounded-xl border border-accent/10">
                        <p className="text-xs text-muted-foreground">
                            <strong>Admin:</strong> This page hasn't been implemented yet.
                        </p>
                    </div>
                )}
                
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
    )
}