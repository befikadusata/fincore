'use client';

import { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Tabs } from '@/components/ui/Tabs';
import { ProfileTab } from './ProfileTab';
import { MembersTab } from './MembersTab';
import { RolesTab } from './RolesTab';
import { NotificationsTab } from './NotificationsTab';

const TABS = ['profile', 'members', 'roles', 'notifications', 'billing'] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  profile: 'Profile',
  members: 'Members',
  roles: 'Roles',
  notifications: 'Notifications',
  billing: 'Billing',
};

function SettingsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawTab = searchParams.get('tab') as Tab | null;
  const tab: Tab = TABS.includes(rawTab as Tab) ? (rawTab as Tab) : 'profile';
  const tabIndex = TABS.indexOf(tab);

  function handleTabChange(idx: number) {
    const next = TABS[idx];
    router.replace(next === 'profile' ? '/settings' : `/settings?tab=${next}`);
  }

  const tabs = TABS.map((t) => ({
    label: TAB_LABELS[t],
    content: <TabContent tab={t} />,
  }));

  return (
    <div className="min-h-full">
      <div className="px-6 pt-6 pb-0 border-b border-[color:var(--color-border-default)]">
        <h1 className="text-2xl font-bold text-primary mb-4">Organization Settings</h1>
      </div>
      <Tabs selectedIndex={tabIndex} onChange={handleTabChange} tabs={tabs} />
    </div>
  );
}

function TabContent({ tab }: { tab: Tab }) {
  if (tab === 'profile') return <ProfileTab />;
  if (tab === 'members') return <MembersTab />;
  if (tab === 'roles') return <RolesTab />;
  if (tab === 'notifications') return <NotificationsTab />;
  return (
    <div className="p-6">
      <p className="text-secondary text-base">Billing settings — coming in Phase 4.7.</p>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-secondary">Loading…</div>}>
      <SettingsContent />
    </Suspense>
  );
}
