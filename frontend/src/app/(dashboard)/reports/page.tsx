'use client';

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { AmountDisplay } from '@/components/domain/AmountDisplay';

const m = (v: string | number | null | undefined) =>
  Math.round(parseFloat(String(v ?? 0)) * 100);

interface TrialBalanceAccount {
  account_id: string;
  code: string;
  name: string;
  account_type: string;
  total_debits: string;
  total_credits: string;
  net_balance: string;
}

interface TrialBalanceData {
  accounts: TrialBalanceAccount[];
  total_debits: string;
  total_credits: string;
  balanced: boolean;
}

const ACCOUNT_TYPE_VARIANT: Record<string, 'success' | 'info' | 'warning' | 'danger' | 'neutral' | 'purple'> = {
  ASSET:     'info',
  LIABILITY: 'warning',
  EQUITY:    'purple',
  REVENUE:   'success',
  EXPENSE:   'danger',
};

export default function ReportsPage() {
  const { data: tb, isLoading } = useQuery({
    queryKey: ['trial-balance'],
    queryFn: async () => {
      const { data } = await api.get<TrialBalanceData>('/api/v1/finance/ledger/trial-balance/');
      return data;
    },
  });

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Trial Balance</h1>
          <p className="text-sm text-secondary mt-1">Double-entry ledger reconciliation</p>
        </div>
        {tb && (
          <Badge variant={tb.balanced ? 'success' : 'danger'}>
            {tb.balanced ? 'Balanced' : 'Out of balance'}
          </Badge>
        )}
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-sm text-secondary">Loading…</div>
      ) : !tb?.accounts?.length ? (
        <EmptyState
          title="No ledger entries"
          description="Trial balance data appears after the first loan disbursement."
        />
      ) : (
        <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
          <Table<TrialBalanceAccount>
            keyExtractor={(row) => row.account_id}
            rows={tb.accounts}
            columns={[
              {
                key: 'code',
                header: 'Code',
                colType: 'id',
                render: (row) => row.code,
              },
              {
                key: 'name',
                header: 'Account',
                render: (row) => (
                  <span className="font-medium text-primary">{row.name}</span>
                ),
              },
              {
                key: 'type',
                header: 'Type',
                render: (row) => (
                  <Badge variant={ACCOUNT_TYPE_VARIANT[row.account_type] ?? 'neutral'}>
                    {row.account_type}
                  </Badge>
                ),
              },
              {
                key: 'debits',
                header: 'Debit',
                colType: 'amount',
                render: (row) => <AmountDisplay amount={m(row.total_debits)} />,
              },
              {
                key: 'credits',
                header: 'Credit',
                colType: 'amount',
                render: (row) => <AmountDisplay amount={m(row.total_credits)} />,
              },
              {
                key: 'net',
                header: 'Net Balance',
                colType: 'amount',
                render: (row) => (
                  <span className="font-mono font-bold text-primary">
                    <AmountDisplay amount={m(row.net_balance)} />
                  </span>
                ),
              },
            ]}
          />

          {/* Totals row */}
          <div className="flex items-center justify-end gap-12 px-4 py-3 bg-sunken border-t border-[color:var(--color-border-default)]">
            <div className="text-right">
              <p className="text-xs text-tertiary uppercase tracking-widest font-semibold">Total Debits</p>
              <AmountDisplay amount={m(tb.total_debits)} size="lg" />
            </div>
            <div className="text-right">
              <p className="text-xs text-tertiary uppercase tracking-widest font-semibold">Total Credits</p>
              <AmountDisplay amount={m(tb.total_credits)} size="lg" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
