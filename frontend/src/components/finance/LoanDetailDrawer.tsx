'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Drawer } from '@/components/ui/Drawer';
import { Tabs } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoanStatusBadge } from '@/components/domain/LoanStatusBadge';
import { LoanTimeline } from '@/components/domain/LoanTimeline';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { RepaymentSchedule } from '@/components/domain/RepaymentSchedule';
import { formatLoanId, formatDate, formatAmount } from '@/lib/format';
import { useToast } from '@/components/ui/Toast';
import { RepaymentModal } from './RepaymentModal';
import api from '@/lib/api';

const m = (v: string | number | null | undefined) =>
  Math.round(parseFloat(String(v ?? 0)) * 100);

export interface Loan {
  id: string;
  product: string;
  product_name: string | null;
  borrower: string;
  borrower_name: string | null;
  approved_by: string | null;
  principal_amount: string;
  interest_amount: string;
  total_amount: string;
  outstanding_balance: string;
  term_months: number;
  currency: string;
  status: string;
  submitted_at: string | null;
  approved_at: string | null;
  disbursed_at: string | null;
  completed_at: string | null;
  notes: string;
  created_at: string;
}

interface ScheduleData {
  installments: Array<{
    id: string;
    installment_number: number;
    due_date: string;
    principal_amount: string;
    interest_amount: string;
    total_amount: string;
    penalty_amount?: string;
    status: string;
  }>;
}

interface AuditEntry {
  id: string;
  action: string;
  actor_name?: string;
  changes: Record<string, unknown>;
  created_at: string;
}

interface LoanDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  loan: Loan | null;
  onUpdated: () => void;
}

export function LoanDetailDrawer({ open, onClose, loan, onUpdated }: LoanDetailDrawerProps) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [showRepay, setShowRepay] = useState(false);

  const { data: freshLoan } = useQuery({
    queryKey: ['loan', loan?.id],
    queryFn: async () => {
      const { data } = await api.get<Loan>(`/api/v1/finance/loans/${loan!.id}/`);
      return data;
    },
    enabled: open && !!loan?.id,
    staleTime: 0,
  });

  const currentLoan = freshLoan ?? loan!;

  const { data: schedule } = useQuery({
    queryKey: ['loan-schedule', loan?.id],
    queryFn: async () => {
      const { data } = await api.get<ScheduleData>(`/api/v1/finance/loans/${loan!.id}/schedule/`);
      return data;
    },
    enabled: open && !!loan?.id,
  });

  const { data: history } = useQuery({
    queryKey: ['loan-history', loan?.id],
    queryFn: async () => {
      const { data } = await api.get(
        `/api/v1/audit/logs/?entity_type=loan&entity_id=${loan!.id}`
      );
      return (data?.results ?? data) as AuditEntry[];
    },
    enabled: open && !!loan?.id,
  });

  function useLoanAction(action: string, successMsg: string) {
    return useMutation({
      mutationFn: () => api.post(`/api/v1/finance/loans/${currentLoan.id}/${action}/`),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: ['loan', currentLoan.id] });
        qc.invalidateQueries({ queryKey: ['loans'] });
        qc.invalidateQueries({ queryKey: ['loan-summary'] });
        toast.success(successMsg);
        onUpdated();
        onClose();
      },
      onError: (err: unknown) => {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Action failed';
        toast.error(msg);
      },
    });
  }

  const submitMutation = useLoanAction('submit', 'Loan submitted for review');
  const approveMutation = useLoanAction('approve', 'Loan approved');
  const disburseMutation = useLoanAction('disburse', 'Loan disbursed');

  const repayMutation = useMutation({
    mutationFn: (amount: string) =>
      api.post(`/api/v1/finance/loans/${currentLoan.id}/repay/`, { amount }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['loans'] });
      qc.invalidateQueries({ queryKey: ['loan-schedule', currentLoan.id] });
      qc.invalidateQueries({ queryKey: ['loan-summary'] });
      toast.success('Payment recorded');
      setShowRepay(false);
      onUpdated();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Payment failed';
      toast.error(msg);
    },
  });

  if (!loan) return null;

  const installments = schedule?.installments?.map((inst) => ({
    ...inst,
    principal_amount: m(inst.principal_amount),
    interest_amount: m(inst.interest_amount),
    total_amount: m(inst.total_amount),
    penalty_amount: inst.penalty_amount ? m(inst.penalty_amount) : undefined,
  })) ?? [];

  const infoRows: Array<{ label: string; value: React.ReactNode }> = [
    { label: 'Product', value: currentLoan.product_name ?? '—' },
    { label: 'Borrower', value: currentLoan.borrower_name ?? '—' },
    { label: 'Principal', value: <AmountDisplay amount={m(currentLoan.principal_amount)} /> },
    { label: 'Interest', value: <AmountDisplay amount={m(currentLoan.interest_amount)} /> },
    { label: 'Total', value: <AmountDisplay amount={m(currentLoan.total_amount)} /> },
    { label: 'Outstanding', value: <AmountDisplay amount={m(currentLoan.outstanding_balance)} /> },
    { label: 'Term', value: `${currentLoan.term_months} months` },
    { label: 'Currency', value: currentLoan.currency },
    ...(currentLoan.submitted_at ? [{ label: 'Submitted', value: formatDate(currentLoan.submitted_at) }] : []),
    ...(currentLoan.approved_at ? [{ label: 'Approved', value: formatDate(currentLoan.approved_at) }] : []),
    ...(currentLoan.disbursed_at ? [{ label: 'Disbursed', value: formatDate(currentLoan.disbursed_at) }] : []),
    ...(currentLoan.completed_at ? [{ label: 'Completed', value: formatDate(currentLoan.completed_at) }] : []),
    ...(currentLoan.notes ? [{ label: 'Notes', value: currentLoan.notes }] : []),
  ];

  const footer = (
    <div className="flex gap-3">
      {currentLoan.status === 'created' && (
        <Button variant="primary" onClick={() => submitMutation.mutate()} loading={submitMutation.isPending}>
          Submit for review
        </Button>
      )}
      {(currentLoan.status === 'submitted' || currentLoan.status === 'under_review') && (
        <Button variant="primary" onClick={() => approveMutation.mutate()} loading={approveMutation.isPending}>
          Approve
        </Button>
      )}
      {currentLoan.status === 'approved' && (
        <Button variant="primary" onClick={() => disburseMutation.mutate()} loading={disburseMutation.isPending}>
          Disburse
        </Button>
      )}
      {(currentLoan.status === 'disbursed' || currentLoan.status === 'active') && (
        <Button variant="primary" onClick={() => setShowRepay(true)}>
          Record repayment
        </Button>
      )}
    </div>
  );

  return (
    <>
      <Drawer open={open} onClose={onClose} title={formatLoanId(currentLoan.id)} footer={footer}>
        <div className="flex flex-col gap-6">
          {/* Status + timeline */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <LoanStatusBadge status={currentLoan.status} />
              <span className="text-sm text-tertiary font-mono">{formatDate(currentLoan.created_at)}</span>
            </div>
            <LoanTimeline currentStatus={currentLoan.status} />
          </div>

          {/* Key amounts summary */}
          <div className="grid grid-cols-3 gap-3">
            <AmountSummary label="Principal" value={formatAmount(m(currentLoan.principal_amount))} />
            <AmountSummary label="Total" value={formatAmount(m(currentLoan.total_amount))} />
            <AmountSummary label="Outstanding" value={formatAmount(m(currentLoan.outstanding_balance))} />
          </div>

          {/* Tabs */}
          <Tabs
            tabs={[
              {
                label: 'Info',
                content: (
                  <div className="pt-4">
                    <dl className="divide-y divide-[color:var(--color-border-default)]">
                      {infoRows.map((row) => (
                        <div key={row.label} className="flex justify-between py-2.5 text-sm">
                          <dt className="text-secondary">{row.label}</dt>
                          <dd className="text-primary font-medium text-right">{row.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ),
              },
              {
                label: 'Schedule',
                content: (
                  <div className="pt-4">
                    {installments.length > 0 ? (
                      <RepaymentSchedule installments={installments} />
                    ) : (
                      <p className="text-sm text-tertiary text-center py-8">No schedule yet.</p>
                    )}
                  </div>
                ),
              },
              {
                label: 'History',
                content: (
                  <div className="pt-4 flex flex-col gap-2">
                    {!history?.length ? (
                      <p className="text-sm text-tertiary text-center py-8">No history entries.</p>
                    ) : (
                      history.map((entry) => (
                        <div
                          key={entry.id}
                          className="flex items-start justify-between py-2.5 border-b border-[color:var(--color-border-default)] last:border-b-0"
                        >
                          <div>
                            <Badge variant="neutral">{entry.action}</Badge>
                            {entry.actor_name && (
                              <span className="ml-2 text-sm text-secondary">{entry.actor_name}</span>
                            )}
                          </div>
                          <span className="text-xs font-mono text-tertiary whitespace-nowrap">
                            {formatDate(entry.created_at)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                ),
              },
            ]}
          />
        </div>
      </Drawer>

      <RepaymentModal
        open={showRepay}
        onClose={() => setShowRepay(false)}
        loan={currentLoan}
        onSubmit={(amount) => repayMutation.mutate(amount)}
        loading={repayMutation.isPending}
      />
    </>
  );
}

function AmountSummary({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-sunken rounded-lg px-3 py-2.5">
      <p className="text-xs text-tertiary">{label}</p>
      <p className="font-mono font-semibold text-sm text-primary mt-0.5">{value}</p>
    </div>
  );
}
