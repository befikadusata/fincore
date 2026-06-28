'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: string;
}

interface TenantState {
  activeTenant: Tenant | null;
  tenants: Tenant[];
  setActiveTenant: (tenant: Tenant) => void;
  setTenants: (tenants: Tenant[]) => void;
  clearTenants: () => void;
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      activeTenant: null,
      tenants: [],
      setActiveTenant: (tenant) => set({ activeTenant: tenant }),
      setTenants: (tenants) => set({ tenants }),
      clearTenants: () => set({ activeTenant: null, tenants: [] }),
    }),
    { name: 'fincore-tenant' },
  ),
);
