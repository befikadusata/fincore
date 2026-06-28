'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';

interface Preference {
  channel: 'in_app' | 'email';
  event_type: string;
  enabled: boolean;
}

interface PreferencesData {
  preferences: Preference[];
}

const EVENT_LABELS: Record<string, string> = {
  loan_approved: 'Loan approved',
  loan_disbursed: 'Loan disbursed',
  repayment_due: 'Repayment due soon',
  workflow_assigned: 'Workflow step assigned to me',
  payment_failed: 'Subscription payment failed',
};

const CHANNELS: Array<{ key: 'in_app' | 'email'; label: string }> = [
  { key: 'in_app', label: 'In-App' },
  { key: 'email', label: 'Email' },
];

export function NotificationsTab() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: async () => {
      const { data } = await api.get<PreferencesData>('/api/v1/notifications/preferences/');
      return data;
    },
  });

  const mutation = useMutation({
    mutationFn: (prefs: Preference[]) =>
      api.patch('/api/v1/notifications/preferences/', { preferences: prefs }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notification-preferences'] }),
  });

  function isEnabled(channel: string, eventType: string): boolean {
    return (
      data?.preferences?.find(
        (p) => p.channel === channel && p.event_type === eventType
      )?.enabled ?? true
    );
  }

  function toggle(channel: 'in_app' | 'email', eventType: string) {
    if (!data) return;
    const current = isEnabled(channel, eventType);
    const existing = data.preferences ?? [];
    const updated = existing.some((p) => p.channel === channel && p.event_type === eventType)
      ? existing.map((p) =>
          p.channel === channel && p.event_type === eventType
            ? { ...p, enabled: !current }
            : p
        )
      : [...existing, { channel, event_type: eventType, enabled: !current }];
    mutation.mutate(updated);
  }

  if (isLoading) {
    return <div className="p-6 text-sm text-secondary">Loading…</div>;
  }

  return (
    <div className="p-6 flex flex-col gap-4">
      {CHANNELS.map((channel) => (
        <Card key={channel.key}>
          <div className="p-5">
            <h3 className="text-base font-semibold text-primary mb-4">
              {channel.label} Notifications
            </h3>
            <div className="flex flex-col gap-4">
              {Object.entries(EVENT_LABELS).map(([eventType, label]) => {
                const enabled = isEnabled(channel.key, eventType);
                return (
                  <div key={eventType} className="flex items-center justify-between">
                    <span className="text-sm text-primary">{label}</span>
                    <button
                      role="switch"
                      aria-checked={enabled}
                      onClick={() => toggle(channel.key, eventType)}
                      className={[
                        'relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent',
                        'transition-colors duration-fast cursor-pointer',
                        'focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2',
                        enabled
                          ? 'bg-[var(--color-brand)]'
                          : 'bg-[var(--color-border-strong)]',
                      ].join(' ')}
                    >
                      <span
                        aria-hidden="true"
                        className={[
                          'pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm',
                          'transform transition-transform duration-fast',
                          enabled ? 'translate-x-4' : 'translate-x-0',
                        ].join(' ')}
                      />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
