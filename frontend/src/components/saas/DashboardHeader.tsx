'use client';

import { NotificationBell } from './NotificationBell';

export function DashboardHeader() {
  return (
    <header className="h-12 flex-shrink-0 bg-surface border-b border-[color:var(--color-border-default)] flex items-center justify-end px-4">
      <NotificationBell />
    </header>
  );
}
