import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Bell,
  AlertCircle,
  Sparkles,
  Lightbulb,
  Clock,
  Check,
  Loader2,
  RefreshCw,
  XCircle,
  Route,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import EmptyState from '../components/ui/EmptyState';
import PlaceCard from '../components/cards/PlaceCard';
import {
  inspectProactiveAlerts,
  listProactiveAlerts,
  listSavedTrips,
  refreshTravellerPersonaFromMemory,
  resolveProactiveAlert,
} from '@/api/wayfarerApi';
import { getOrCreateTravellerId, replaceTravellerPersona } from '@/lib/travellerProfile';
import { cacheSavedTrips, getCachedSavedTrips } from '@/lib/tripStorage';

const typeIcons = {
  signal_blocker: AlertCircle,
  closure_risk: Sparkles,
  quality_risk: Lightbulb,
  timing_conflict: Clock,
  fallback_gap: Bell,
};

const severityStyles = {
  high: 'border-destructive/20 bg-destructive/5',
  medium: 'border-accent/20 bg-accent/5',
  low: 'border-border bg-card',
};

function getActiveTrip(trips = []) {
  return trips.find((trip) => ['active', 'upcoming', 'planning'].includes(trip.status)) || trips[0] || null;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function buildEvidenceLines(alert) {
  return safeArray(alert?.evidence).slice(0, 3).map((item, index) => {
    if (item?.type === 'recent_signal') {
      return `Recent signal: ${item.signal_type || 'unknown signal'}`;
    }
    if (item?.type === 'freshness_status') {
      return `Freshness: ${item.operational_status || 'unknown'}${item.open_now === false ? ' • not open now' : ''}`;
    }
    if (item?.type === 'time_window_check') {
      return `Time window: ${item.available_minutes || 0} min available vs ${item.estimated_visit_minutes || 0} min estimated`;
    }
    if (item?.type === 'quality_risk') {
      return `Quality risk: ${item.quality_risk_score || 0}${safeArray(item.quality_flags).length ? ` • ${safeArray(item.quality_flags).join(', ')}` : ''}`;
    }
    if (item?.type === 'fallback_check') {
      return `Fallback coverage: ${item.slot_alternative_count || 0} slot alternatives, ${item.fallback_candidate_count || 0} fallback candidates`;
    }
    if (item?.type === 'slot_state') {
      return item.detail || 'Slot state issue detected';
    }
    return item?.detail || `Evidence ${index + 1}`;
  });
}

export default function Notifications() {
  const travellerId = getOrCreateTravellerId();
  const [isRunningInspection, setIsRunningInspection] = useState(false);
  const [actionState, setActionState] = useState({});
  const [errorMessage, setErrorMessage] = useState('');

  const { data: trips = [], refetch: refetchTrips } = useQuery({
    queryKey: ['notifications-trips', travellerId],
    queryFn: async () => {
      const response = await listSavedTrips(travellerId, 50);
      cacheSavedTrips(travellerId, response.items || []);
      return response.items || [];
    },
    initialData: getCachedSavedTrips(travellerId),
  });

  const activeTrip = useMemo(() => getActiveTrip(trips), [trips]);

  const {
    data: alertResponse,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['notifications-alerts', activeTrip?.trip_id],
    enabled: Boolean(activeTrip?.trip_id),
    queryFn: async () => listProactiveAlerts(activeTrip.trip_id, { limit: 100 }),
    initialData: { items: [] },
  });

  const alerts = alertResponse?.items || [];
  const unreadCount = alerts.filter((item) => item.status === 'generated').length;

  const runInspection = async () => {
    if (!activeTrip?.trip_id) return;
    setIsRunningInspection(true);
    setErrorMessage('');
    try {
      await inspectProactiveAlerts({
        traveller_id: activeTrip.traveller_id,
        trip_id: activeTrip.trip_id,
        planning_session_id: activeTrip.planning_session_id,
        source_surface: 'notifications_page',
        current_day_only: false,
        max_days_to_check: 4,
      });
      await Promise.all([refetch(), refetchTrips()]);
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to inspect active trip alerts right now.');
    } finally {
      setIsRunningInspection(false);
    }
  };

  const updateAlertStatus = async (alertId, status, options = {}) => {
    setActionState((prev) => ({ ...prev, [alertId]: status }));
    try {
      await resolveProactiveAlert(alertId, {
        status,
        source_surface: 'notifications_page',
        resolution_reason:
          options.resolution_reason ||
          (status === 'resolved' ? 'Resolved from notifications page' : 'Ignored from notifications page'),
        payload: options.payload || {},
      });
      await refetch();
      // Fire-and-forget persona refresh — alert resolution signals travel preference data.
      refreshTravellerPersonaFromMemory(travellerId)
        .then((updated) => { if (updated) replaceTravellerPersona(updated); })
        .catch(() => {});
    } catch (error) {
      setErrorMessage(error?.message || 'Unable to update alert status right now.');
    } finally {
      setActionState((prev) => {
        const next = { ...prev };
        delete next[alertId];
        return next;
      });
    }
  };

  const adaptAlert = async (alert, alternative) => {
    await updateAlertStatus(alert.alert_id, 'resolved', {
      resolution_reason: 'Adapted using suggested alternative',
      payload: {
        action: 'adapt',
        selected_alternative_id: alternative.location_id,
        selected_alternative_name: alternative.name,
        selected_alternative_source: alternative.source || 'alert_alternative',
      },
    });
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 lg:py-10">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="font-serif text-3xl font-bold mb-1">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            {activeTrip?.title ? `${unreadCount} open alert${unreadCount === 1 ? '' : 's'} for ${activeTrip.title}` : 'No active trip selected'}
          </p>
        </div>
        <button
          onClick={runInspection}
          disabled={!activeTrip?.trip_id || isRunningInspection}
          className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-2 text-sm font-medium hover:border-accent/30 disabled:opacity-50"
        >
          {isRunningInspection ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Run check
        </button>
      </motion.div>

      <div className="rounded-2xl border border-border bg-card p-4 mb-6">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Route className="w-4 h-4 text-accent" />
          Pseudo-scheduled monitoring model
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          These alerts are generated from a proactive monitoring loop layered on top of your active itinerary. Wayfarer checks closure risk, timing conflicts, quality drift, and fallback gaps before the traveller runs into them manually.
        </p>
      </div>

      {errorMessage ? (
        <div className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive mb-6">
          {errorMessage}
        </div>
      ) : null}

      {isLoading ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center text-sm text-muted-foreground">Loading proactive alerts…</div>
      ) : alerts.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="No proactive alerts"
          description="Run a proactive inspection to check for closure risks, timing issues, and freshness changes in your active itinerary."
        />
      ) : (
        <div className="space-y-4">
          {alerts.map((alert, index) => {
            const Icon = typeIcons[alert.alert_type] || Bell;
            const isBusy = Boolean(actionState[alert.alert_id]);
            const evidenceLines = buildEvidenceLines(alert);

            return (
              <motion.div
                key={alert.alert_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.04 }}
                className={`rounded-2xl border p-4 ${severityStyles[alert.severity] || 'border-border bg-card'}`}
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-card flex items-center justify-center border border-border/60">
                    <Icon className="w-4 h-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-sm">{alert.title}</h3>
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium capitalize text-muted-foreground">
                        {alert.severity}
                      </span>
                      <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-medium capitalize text-muted-foreground">
                        {alert.status.replaceAll('_', ' ')}
                      </span>
                    </div>

                    <p className="text-sm text-muted-foreground mt-2">{alert.message}</p>

                    {(alert.location_name || alert.slot_type || alert.day_number) ? (
                      <div className="text-[11px] text-muted-foreground mt-2">
                        {alert.location_name ? <span>{alert.location_name}</span> : null}
                        {alert.day_number ? <span>{alert.location_name ? ' • ' : ''}Day {alert.day_number}</span> : null}
                        {alert.slot_type ? <span>{alert.day_number || alert.location_name ? ' • ' : ''}{alert.slot_type}</span> : null}
                      </div>
                    ) : null}

                    {evidenceLines.length ? (
                      <div className="mt-3 rounded-xl bg-card/80 border border-border/60 p-3">
                        <div className="text-xs font-medium mb-2">Why this was flagged</div>
                        <div className="space-y-1">
                          {evidenceLines.map((line) => (
                            <div key={line} className="text-xs text-muted-foreground">
                              • {line}
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {safeArray(alert.alternatives).length ? (
                      <div className="mt-4">
                        <div className="text-xs font-medium mb-3">Suggested alternatives</div>
                        <div className="space-y-3">
                          {safeArray(alert.alternatives).slice(0, 3).map((item) => (
                            <PlaceCard
                              key={item.location_id || item.name}
                              name={item.name}
                              category={item.category}
                              rating={item.rating}
                              description={item.summary_line || item.why_alternative || 'Suggested as a proactive fallback.'}
                              reason={item.why_alternative}
                              photos={item.photos || []}
                              tags={item.visual_signal?.top_tags?.map((tag) => tag.tag) || []}
                              showSaveButton={false}
                              trailing={
                                <button
                                  onClick={() => adaptAlert(alert, item)}
                                  disabled={isBusy}
                                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium bg-accent/10 text-accent hover:bg-accent/15 disabled:opacity-50"
                                >
                                  {isBusy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Route className="w-3 h-3" />}
                                  Adapt
                                </button>
                              }
                            />
                          ))}
                        </div>
                      </div>
                    ) : null}

                    <div className="flex gap-2 mt-4 flex-wrap">
                      <button
                        onClick={() => updateAlertStatus(alert.alert_id, 'resolved')}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium bg-accent/10 text-accent hover:bg-accent/15 disabled:opacity-50"
                      >
                        {isBusy && actionState[alert.alert_id] === 'resolved' ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                        Resolve
                      </button>
                      <button
                        onClick={() => updateAlertStatus(alert.alert_id, 'ignored')}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-xs font-medium bg-secondary text-muted-foreground hover:text-foreground disabled:opacity-50"
                      >
                        {isBusy && actionState[alert.alert_id] === 'ignored' ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
                        Ignore
                      </button>
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