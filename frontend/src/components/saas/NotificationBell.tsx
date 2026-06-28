'use client';

import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/format';

interface Notification {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

interface NotificationListResponse {
  count: number;
  results: Notification[];
}

export function NotificationBell() {
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const { data } = await api.get<NotificationListResponse>('/api/v1/notifications/');
      return data;
    },
    refetchInterval: 30_000,
  });

  const notifications = data?.results ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/v1/notifications/${id}/mark-read/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.post('/api/v1/notifications/mark-all-read/'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  return (
    <Menu as="div" className="relative">
      <MenuButton
        className="relative p-2 rounded text-secondary hover:text-primary hover:bg-sunken transition-colors duration-fast focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2"
        aria-label="Notifications"
      >
        <BellIcon />
        {unreadCount > 0 && (
          <span
            aria-hidden="true"
            className="absolute top-0.5 right-0.5 min-w-[16px] h-4 rounded-full bg-[var(--color-danger-bg)] text-[var(--color-danger-text)] text-[10px] font-bold flex items-center justify-center px-1 leading-none"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </MenuButton>

      <MenuItems
        anchor="bottom end"
        className="z-[300] mt-2 w-80 rounded-lg border border-[color:var(--color-border-default)] bg-surface shadow-xl focus:outline-none overflow-hidden"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[color:var(--color-border-default)]">
          <h3 className="text-sm font-semibold text-primary">Notifications</h3>
          {unreadCount > 0 && (
            <button
              onClick={() => markAllReadMutation.mutate()}
              className="text-xs text-[var(--color-brand-text)] hover:underline"
            >
              Mark all read
            </button>
          )}
        </div>

        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="py-6 px-4">
              <EmptyState
                title="All clear"
                description="No new notifications."
              />
            </div>
          ) : (
            notifications.slice(0, 20).map((n) => (
              <MenuItem key={n.id} as="button"
                onClick={() => { if (!n.is_read) markReadMutation.mutate(n.id); }}
                className={[
                  'w-full text-left px-4 py-3 border-b border-[color:var(--color-border-default)] last:border-b-0',
                  'transition-colors duration-fast data-[active]:bg-sunken',
                  !n.is_read ? 'bg-[var(--color-brand-subtle)]' : '',
                ].join(' ')}
              >
                <div className="flex items-start gap-2">
                  {!n.is_read && (
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--color-danger-rail)] flex-shrink-0" />
                  )}
                  <div className={['flex-1 min-w-0', !n.is_read ? '' : 'pl-3.5'].join(' ')}>
                    <p className={['text-sm truncate', !n.is_read ? 'font-semibold text-primary' : 'text-primary'].join(' ')}>
                      {n.title}
                    </p>
                    <p className="text-xs font-mono text-tertiary mt-0.5">{formatDate(n.created_at)}</p>
                  </div>
                </div>
              </MenuItem>
            ))
          )}
        </div>
      </MenuItems>
    </Menu>
  );
}

function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zm0 16a2 2 0 01-1.732-1h3.464A2 2 0 0110 18z" clipRule="evenodd" />
    </svg>
  );
}
