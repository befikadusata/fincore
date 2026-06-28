'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { formatAmount } from '@/lib/format';

const m = (v: string | number | null | undefined) =>
  Math.round(parseFloat(String(v ?? 0)) * 100);

interface LoanSummary {
  active_count: number;
  completed_count: number;
  defaulted_count: number;
  total_outstanding: string;
  total_disbursed: string;
  overdue_installments: number;
}

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['loan-summary'],
    queryFn: async () => {
      const { data } = await api.get<LoanSummary>('/api/v1/finance/loans/summary/');
      return data;
    },
  });

  const kpis = [
    {
      label: 'Active Loans',
      value: isLoading ? '—' : String(summary?.active_count ?? 0),
      sub: `${summary?.completed_count ?? 0} completed · ${summary?.defaulted_count ?? 0} defaulted`,
    },
    {
      label: 'Total Disbursed',
      value: isLoading ? '—' : formatAmount(m(summary?.total_disbursed ?? 0)),
      sub: 'All time',
    },
    {
      label: 'Outstanding Balance',
      value: isLoading ? '—' : formatAmount(m(summary?.total_outstanding ?? 0)),
      sub: 'Active loans',
    },
    {
      label: 'Overdue Installments',
      value: isLoading ? '—' : String(summary?.overdue_installments ?? 0),
      sub: 'Requires attention',
      warn: (summary?.overdue_installments ?? 0) > 0,
    },
  ];

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Dashboard</h1>
        <p className="text-sm text-secondary mt-1">Loan portfolio overview</p>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <Card key={kpi.label}>
            <div className="p-5 flex flex-col gap-1">
              <span className="text-sm text-secondary">{kpi.label}</span>
              <span
                className={[
                  'text-3xl font-mono font-bold',
                  kpi.warn ? 'text-[var(--color-warning-text)]' : 'text-primary',
                ].join(' ')}
              >
                {isLoading ? (
                  <span className="block h-9 w-24 bg-sunken animate-pulse rounded" />
                ) : (
                  kpi.value
                )}
              </span>
              {kpi.sub && !isLoading && (
                <span className="text-xs text-tertiary">{kpi.sub}</span>
              )}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <QuickLink href="/loans" label="Manage Loans" desc="View and act on your loan portfolio" />
        <QuickLink href="/loans/products" label="Loan Products" desc="Configure interest rates and terms" />
        <QuickLink href="/reports" label="Trial Balance" desc="Double-entry ledger reconciliation" />
      </div>
    </div>
  );
}

function QuickLink({ href, label, desc }: { href: string; label: string; desc: string }) {
  return (
    <Link href={href} className="block group">
      <Card className="hover:border-[color:var(--color-border-strong)] transition-colors cursor-pointer">
        <div className="p-5">
          <h3 className="text-base font-semibold text-primary group-hover:text-[var(--color-brand-text)] transition-colors">
            {label}
          </h3>
          <p className="text-sm text-secondary mt-1">{desc}</p>
        </div>
      </Card>
    </Link>
  );
}
