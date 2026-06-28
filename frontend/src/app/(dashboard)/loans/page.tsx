'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table, TableToolbar } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { LoanStatusBadge } from '@/components/domain/LoanStatusBadge';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { formatLoanId, formatDate } from '@/lib/format';
import { loanStatusRailClass } from '@/lib/status';
import { LoanDetailDrawer, type Loan } from '@/components/finance/LoanDetailDrawer';
import { CreateLoanModal } from '@/components/finance/CreateLoanModal';

const m = (v: string | number | null | undefined) =>
  Math.round(parseFloat(String(v ?? 0)) * 100);

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'CREATED', label: 'Created' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'UNDER_REVIEW', label: 'Under Review' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'DISBURSED', label: 'Disbursed' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'DEFAULTED', label: 'Defaulted' },
];

export default function LoansPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: loans = [], isLoading } = useQuery({
    queryKey: ['loans'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/finance/loans/');
      return (data?.results ?? data) as Loan[];
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<Loan>('/api/v1/finance/loans/', body),
    onSuccess: ({ data }) => {
      qc.invalidateQueries({ queryKey: ['loans'] });
      toast.success('Loan application created');
      setShowCreate(false);
      setSelectedLoan(data);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to create loan';
      toast.error(msg);
    },
  });

  const filtered = loans.filter((loan) => {
    const matchesSearch =
      !search ||
      formatLoanId(loan.id).toLowerCase().includes(search.toLowerCase()) ||
      (loan.borrower_name ?? '').toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || loan.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  function handleLoanUpdated() {
    qc.invalidateQueries({ queryKey: ['loans'] });
    qc.invalidateQueries({ queryKey: ['loan-summary'] });
  }

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Loans</h1>
          <p className="text-sm text-secondary mt-1">Manage the full loan lifecycle</p>
        </div>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          New application
        </Button>
      </div>

      <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
        <TableToolbar
          searchPlaceholder="Search by ID or borrower…"
          searchValue={search}
          onSearchChange={setSearch}
        >
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-44"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>
        </TableToolbar>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-secondary">Loading…</div>
        ) : (
          <Table<Loan>
            keyExtractor={(l) => l.id}
            rows={filtered}
            rowClassName={(l) => loanStatusRailClass(l.status)}
            onRowClick={(l) => setSelectedLoan(l)}
            columns={[
              {
                key: 'id',
                header: 'Loan ID',
                colType: 'id',
                render: (l) => formatLoanId(l.id),
              },
              {
                key: 'borrower',
                header: 'Borrower',
                render: (l) => (
                  <span className="font-medium text-primary">{l.borrower_name ?? '—'}</span>
                ),
              },
              {
                key: 'product',
                header: 'Product',
                render: (l) => (
                  <span className="text-secondary text-sm">{l.product_name ?? '—'}</span>
                ),
              },
              {
                key: 'amount',
                header: 'Principal',
                colType: 'amount',
                render: (l) => <AmountDisplay amount={m(l.principal_amount)} />,
              },
              {
                key: 'outstanding',
                header: 'Outstanding',
                colType: 'amount',
                render: (l) => <AmountDisplay amount={m(l.outstanding_balance)} />,
              },
              {
                key: 'status',
                header: 'Status',
                render: (l) => <LoanStatusBadge status={l.status} />,
              },
              {
                key: 'created',
                header: 'Created',
                colType: 'date',
                render: (l) => formatDate(l.created_at),
              },
            ]}
            emptyState={
              <EmptyState
                title="No loans yet"
                description="Create a loan product, then submit your first application."
                action={{ label: 'New application', onClick: () => setShowCreate(true) }}
              />
            }
          />
        )}
      </div>

      <LoanDetailDrawer
        open={!!selectedLoan}
        onClose={() => setSelectedLoan(null)}
        loan={selectedLoan}
        onUpdated={handleLoanUpdated}
      />

      <CreateLoanModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSubmit={(data) => createMutation.mutate(data)}
        loading={createMutation.isPending}
      />
    </div>
  );
}
