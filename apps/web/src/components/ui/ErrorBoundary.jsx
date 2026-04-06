import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

/**
 * Generic React error boundary.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <SomeChildThatMightCrash />
 *   </ErrorBoundary>
 *
 * Accepts an optional `fallback` prop for a custom fallback UI.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
    this.handleReset = this.handleReset.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Log to console so devs can see the error during development.
    // In production this is the correct place to forward to Sentry/DataDog.
    console.error('[ErrorBoundary] Uncaught error:', error, info);
  }

  handleReset() {
    this.setState({ hasError: false, error: null });
  }

  render() {
    const { hasError, error } = this.state;
    const { children, fallback } = this.props;

    if (!hasError) return children;

    if (fallback) return fallback;

    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center">
        <AlertTriangle className="mb-3 h-8 w-8 text-destructive" />
        <h3 className="mb-1 text-sm font-semibold text-destructive">Something went wrong</h3>
        <p className="mb-4 text-xs text-muted-foreground">
          {error?.message || 'An unexpected error occurred in this section.'}
        </p>
        <button
          type="button"
          onClick={this.handleReset}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium hover:bg-secondary"
        >
          <RefreshCw className="h-3 w-3" />
          Try again
        </button>
      </div>
    );
  }
}
