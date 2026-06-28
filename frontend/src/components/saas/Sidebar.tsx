'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useAuthStore } from '@/stores/auth';
import { useUIStore } from '@/stores/ui';
import { TenantSwitcher } from './TenantSwitcher';

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  exactMatch?: boolean;
}

interface NavSection {
  label: string;
  items: NavItem[];
}

function NavLink({ href, label, icon, badge, exactMatch }: NavItem) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const hrefPath = href.split('?')[0];
  const hrefSearch = href.includes('?') ? href.slice(href.indexOf('?') + 1) : '';
  const currentSearch = searchParams.toString();

  let isActive: boolean;
  if (href.includes('?')) {
    isActive = pathname === hrefPath && currentSearch === hrefSearch;
  } else if (exactMatch) {
    isActive = pathname === href && currentSearch === '';
  } else {
    isActive = pathname.startsWith(href);
  }

  return (
    <Link
      href={href}
      className={[
        'flex items-center gap-3 px-3 py-2 rounded text-sm font-medium transition-colors duration-fast',
        isActive
          ? 'bg-[var(--color-brand-subtle)] text-[var(--color-brand-text)] font-semibold'
          : 'text-secondary hover:bg-sunken hover:text-primary',
      ].join(' ')}
    >
      <span className="w-4 h-4 flex-shrink-0">{icon}</span>
      <span className="flex-1 truncate">{label}</span>
      {badge !== undefined && badge > 0 && (
        <span className="ml-auto min-w-[20px] h-5 rounded-full bg-[var(--color-danger-bg)] text-[var(--color-danger-text)] text-xs font-semibold flex items-center justify-center px-1.5">
          {badge}
        </span>
      )}
    </Link>
  );
}

function NavSection({ label, items }: NavSection) {
  return (
    <div>
      <p className="px-3 pt-3 pb-1 text-xs font-semibold uppercase tracking-widest text-tertiary">
        {label}
      </p>
      <div className="flex flex-col gap-0.5">
        {items.map((item) => (
          <NavLink key={item.href} {...item} />
        ))}
      </div>
    </div>
  );
}

const NAV: NavSection[] = [
  {
    label: 'Overview',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: <GridIcon />, exactMatch: true },
    ],
  },
  {
    label: 'Lending',
    items: [
      { href: '/loans/products', label: 'Loan Products', icon: <TagIcon /> },
      { href: '/loans', label: 'Loans', icon: <BriefcaseIcon /> },
      { href: '/wallets', label: 'Wallets', icon: <WalletIcon /> },
    ],
  },
  {
    label: 'Workflow',
    items: [
      { href: '/workflow/tasks', label: 'My Tasks', icon: <CheckCircleIcon /> },
      { href: '/workflow', label: 'Workflows', icon: <RefreshIcon /> },
    ],
  },
  {
    label: 'Finance',
    items: [
      { href: '/reports', label: 'Reports', icon: <ChartIcon /> },
      { href: '/audit', label: 'Audit Log', icon: <BookIcon /> },
    ],
  },
  {
    label: 'Settings',
    items: [
      { href: '/settings', label: 'Profile', icon: <BuildingIcon />, exactMatch: true },
      { href: '/settings?tab=members', label: 'Members', icon: <UsersIcon /> },
      { href: '/settings?tab=roles', label: 'Roles', icon: <LockIcon /> },
      { href: '/settings?tab=notifications', label: 'Notifications', icon: <BellNavIcon /> },
      { href: '/settings?tab=billing', label: 'Billing', icon: <CreditCardIcon /> },
    ],
  },
];

function UserFooter() {
  const { user, clearAuth } = useAuthStore();
  const { theme, setTheme } = useUIStore();

  return (
    <div className="border-t border-[color:var(--color-border-default)] p-3 flex flex-col gap-1">
      <button
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className="flex items-center gap-3 px-3 py-2 rounded text-sm font-medium text-secondary hover:bg-sunken hover:text-primary transition-colors duration-fast w-full text-left"
      >
        <span className="w-4 h-4 flex-shrink-0">{theme === 'dark' ? <SunIcon /> : <MoonIcon />}</span>
        {theme === 'dark' ? 'Light mode' : 'Dark mode'}
      </button>

      {user && (
        <div className="flex items-center gap-3 px-3 py-2 rounded">
          <span className="w-7 h-7 rounded-full bg-[var(--color-brand-subtle)] text-[var(--color-brand-text)] text-xs font-bold flex items-center justify-center flex-shrink-0">
            {(user.first_name?.[0] ?? user.email[0]).toUpperCase()}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary truncate">
              {user.first_name ? `${user.first_name} ${user.last_name}`.trim() : user.email}
            </p>
            <p className="text-xs text-tertiary truncate">{user.email}</p>
          </div>
          <button
            onClick={clearAuth}
            aria-label="Sign out"
            className="text-tertiary hover:text-primary transition-colors duration-fast flex-shrink-0"
          >
            <LogoutIcon />
          </button>
        </div>
      )}
    </div>
  );
}

function SidebarInner() {
  return (
    <aside className="w-60 h-screen bg-surface border-r border-[color:var(--color-border-default)] flex flex-col flex-shrink-0 sticky top-0 overflow-hidden">
      <TenantSwitcher />
      <nav className="flex-1 overflow-y-auto px-2 py-3 flex flex-col gap-2">
        {NAV.map((section) => (
          <NavSection key={section.label} {...section} />
        ))}
      </nav>
      <UserFooter />
    </aside>
  );
}

export function Sidebar() {
  return (
    <Suspense fallback={<SidebarSkeleton />}>
      <SidebarInner />
    </Suspense>
  );
}

function SidebarSkeleton() {
  return (
    <aside className="w-60 h-screen bg-surface border-r border-[color:var(--color-border-default)] flex-shrink-0 sticky top-0" />
  );
}

/* Icons */

function BellNavIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zm0 16a2 2 0 01-1.732-1h3.464A2 2 0 0110 18z" clipRule="evenodd" /></svg>
  );
}

function GridIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M4.25 2A2.25 2.25 0 002 4.25v2.5A2.25 2.25 0 004.25 9h2.5A2.25 2.25 0 009 6.75v-2.5A2.25 2.25 0 006.75 2h-2.5zm0 9A2.25 2.25 0 002 13.25v2.5A2.25 2.25 0 004.25 18h2.5A2.25 2.25 0 009 15.75v-2.5A2.25 2.25 0 006.75 11h-2.5zm6.5-9A2.25 2.25 0 008.5 4.25v2.5A2.25 2.25 0 0010.75 9h2.5A2.25 2.25 0 0015.5 6.75v-2.5A2.25 2.25 0 0013.25 2h-2.5zm0 9A2.25 2.25 0 008.5 13.25v2.5A2.25 2.25 0 0010.75 18h2.5A2.25 2.25 0 0015.5 15.75v-2.5A2.25 2.25 0 0013.25 11h-2.5z" clipRule="evenodd" /></svg>
  );
}

function TagIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M5.5 3A2.5 2.5 0 003 5.5v2.879a2.5 2.5 0 00.732 1.767l6.5 6.5a2.5 2.5 0 003.536 0l2.878-2.878a2.5 2.5 0 000-3.536l-6.5-6.5A2.5 2.5 0 008.38 3H5.5zM6 7a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" /></svg>
  );
}

function BriefcaseIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M6 3.75A2.75 2.75 0 018.75 1h2.5A2.75 2.75 0 0114 3.75v.443c.572.055 1.14.122 1.706.2C17.053 4.582 18 5.75 18 7.07v3.469c0 1.126-.694 2.191-1.83 2.54-1.952.599-4.024.921-6.17.921s-4.219-.322-6.17-.921C2.694 12.73 2 11.665 2 10.539V7.07c0-1.321.947-2.489 2.294-2.676A41.047 41.047 0 016 4.193V3.75zm6.5 0v.325a41.622 41.622 0 00-5 0V3.75c0-.69.56-1.25 1.25-1.25h2.5c.69 0 1.25.56 1.25 1.25zM10 10a1 1 0 00-1 1v.01a1 1 0 001 1h.01a1 1 0 001-1V11a1 1 0 00-1-1H10z" clipRule="evenodd" /><path d="M3 15.055v-.684c.278.075.565.14.857.198a48.97 48.97 0 006.286.666 48.97 48.97 0 006.286-.666c.292-.057.579-.123.857-.198v.684c0 1.347-.985 2.51-2.33 2.674a49.98 49.98 0 01-9.474 0C3.985 17.565 3 16.402 3 15.055z" /></svg>
  );
}

function WalletIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M1 4.25a3.733 3.733 0 012.25-.75h13.5c.844 0 1.623.279 2.25.75A2.25 2.25 0 0016.75 2H3.25A2.25 2.25 0 001 4.25zM1 7.25a3.733 3.733 0 012.25-.75h13.5c.844 0 1.623.279 2.25.75A2.25 2.25 0 0016.75 5H3.25A2.25 2.25 0 001 7.25zM7 8a1 1 0 000 2 2 2 0 012 2v1a2 2 0 01-2 2H3.25A2.25 2.25 0 011 12.75v-1.5A2.25 2.25 0 013.25 9H7z" /><path fillRule="evenodd" d="M12.5 9a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9.75A.75.75 0 0112.5 9z" clipRule="evenodd" /></svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" /></svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clipRule="evenodd" /></svg>
  );
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 003 0v-13A1.5 1.5 0 0015.5 2zM9.5 6A1.5 1.5 0 008 7.5v9a1.5 1.5 0 003 0v-9A1.5 1.5 0 009.5 6zM3.5 10A1.5 1.5 0 002 11.5v5a1.5 1.5 0 003 0v-5A1.5 1.5 0 003.5 10z" /></svg>
  );
}

function BookIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" /></svg>
  );
}

function BuildingIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M1 2.75A.75.75 0 011.75 2h10.5a.75.75 0 010 1.5H12v13.75a.75.75 0 01-.75.75h-1.5a.75.75 0 01-.75-.75v-2.5a.75.75 0 00-.75-.75h-2.5a.75.75 0 00-.75.75v2.5a.75.75 0 01-.75.75h-2.5a.75.75 0 010-1.5H2V3.5h-.25A.75.75 0 011 2.75zM4 5.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zM4.5 9a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM8 5.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zM8.5 9a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1zM14.25 6a.75.75 0 00-.75.75V17H18V6.75a.75.75 0 00-.75-.75h-3zm.5 3.5a.5.5 0 01.5-.5h1a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1zm.5 3.5a.5.5 0 00-.5.5v1a.5.5 0 00.5.5h1a.5.5 0 00.5-.5v-1a.5.5 0 00-.5-.5h-1z" clipRule="evenodd" /></svg>
  );
}

function UsersIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 17a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.575c.176.479-.005.964-.46 1.127a13.41 13.41 0 01-3.768.986z" /></svg>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" /></svg>
  );
}

function CreditCardIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M2.5 4A1.5 1.5 0 001 5.5V6h18v-.5A1.5 1.5 0 0017.5 4h-15zM19 8.5H1v6A1.5 1.5 0 002.5 16h15a1.5 1.5 0 001.5-1.5v-6zM3 13.25a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5a.75.75 0 01-.75-.75zm4.75-.75a.75.75 0 000 1.5h3.5a.75.75 0 000-1.5h-3.5z" clipRule="evenodd" /></svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.06l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06L5.403 4.343a.75.75 0 00-1.06 1.06l1.06 1.06z" /></svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M7.455 2.004a.75.75 0 01.26.77 7 7 0 009.958 7.967.75.75 0 011.067.853A8.5 8.5 0 116.647 1.921a.75.75 0 01.808.083z" clipRule="evenodd" /></svg>
  );
}

function LogoutIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fillRule="evenodd" d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z" clipRule="evenodd" /><path fillRule="evenodd" d="M6 10a.75.75 0 01.75-.75h9.546l-1.048-.943a.75.75 0 111.004-1.114l2.5 2.25a.75.75 0 010 1.114l-2.5 2.25a.75.75 0 11-1.004-1.114l1.048-.943H6.75A.75.75 0 016 10z" clipRule="evenodd" /></svg>
  );
}
