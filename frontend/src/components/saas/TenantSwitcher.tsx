'use client';

import { useState } from 'react';
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import { useToast } from '@/components/ui/Toast';
import { CreateOrgModal } from './CreateOrgModal';

export function TenantSwitcher() {
  const { user, setAuth } = useAuthStore();
  const { activeTenant, tenants, setActiveTenant, setTenants } = useTenantStore();
  const { toast } = useToast();
  const [showCreate, setShowCreate] = useState(false);

  async function handleSwitch(tenantId: string) {
    if (tenantId === activeTenant?.id) return;
    try {
      const { data } = await api.post('/api/v1/tenants/switch/', { tenant_id: tenantId });
      const { refreshToken } = useAuthStore.getState();
      setAuth(user!, data.access, data.refresh ?? refreshToken ?? '');
      const next = tenants.find((t) => t.id === tenantId);
      if (next) {
        setActiveTenant(next);
        toast.success('Switched to ' + next.name);
      }
    } catch {
      toast.error('Failed to switch organization');
    }
  }

  function handleOrgCreated(tenant: { id: string; name: string; slug: string; status: string }) {
    setTenants([...tenants, tenant]);
    setActiveTenant(tenant);
    setShowCreate(false);
  }

  return (
    <>
      <div className="h-14 flex items-center justify-between px-4 border-b border-[color:var(--color-border-default)] flex-shrink-0">
        <span className="text-xl font-bold tracking-tight text-primary">
          Fin<span className="text-brand">Core</span>
        </span>

        <Menu as="div" className="relative">
          <MenuButton className="flex items-center gap-1 max-w-[130px] px-2 py-1 rounded text-sm font-medium text-secondary hover:bg-sunken hover:text-primary transition-colors duration-fast focus-visible:outline-2 focus-visible:outline-[var(--color-border-focus)] focus-visible:outline-offset-2">
            <span className="truncate">{activeTenant?.name ?? 'Select org'}</span>
            <ChevronDownIcon />
          </MenuButton>

          <MenuItems
            anchor="bottom start"
            className="z-[300] mt-1 w-56 rounded-lg border border-[color:var(--color-border-default)] bg-surface shadow-xl focus:outline-none"
          >
            <div className="px-3 py-2 text-xs font-semibold uppercase tracking-widest text-tertiary border-b border-[color:var(--color-border-default)]">
              Organizations
            </div>

            <div className="py-1 max-h-48 overflow-y-auto">
              {tenants.map((tenant) => (
                <MenuItem key={tenant.id} as="button" onClick={() => handleSwitch(tenant.id)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-secondary hover:bg-sunken hover:text-primary data-[active]:bg-sunken data-[active]:text-primary transition-colors duration-fast"
                >
                  <span className="truncate flex-1">{tenant.name}</span>
                  {tenant.id === activeTenant?.id && <CheckIcon />}
                </MenuItem>
              ))}
            </div>

            <div className="border-t border-[color:var(--color-border-default)] py-1">
              <MenuItem as="button"
                onClick={() => setShowCreate(true)}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-secondary hover:bg-sunken hover:text-primary data-[active]:bg-sunken data-[active]:text-primary transition-colors duration-fast"
              >
                <PlusIcon />
                New organization
              </MenuItem>
            </div>
          </MenuItems>
        </Menu>
      </div>

      <CreateOrgModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleOrgCreated}
      />
    </>
  );
}

function ChevronDownIcon() {
  return (
    <svg className="w-3.5 h-3.5 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clipRule="evenodd" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4 text-brand flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
    </svg>
  );
}
