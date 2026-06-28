'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Drawer } from '@/components/ui/Drawer';
import { Tabs } from '@/components/ui/Tabs';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { LoanStatusBadge } from '@/components/domain/LoanStatusBadge';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { formatLoanId, formatDate, formatElapsed } from '@/lib/format';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';

export interface WorkflowTask {
  id: string;
  instance_id: string;
  entity_id: string;
  entity_type: string;
  borrower_name: string;
  amount: number;
  loan_term_months?: number;
  loan_status?: string;
  product_name?: string;
  outstanding_balance?: number;
  step_type: string;
  submitted_at: string;
  is_read?: boolean;
  comments?: StepComment[];
}

export interface StepComment {
  id: string;
  actor_name: string;
  action: string;
  comment: string;
  created_at: string;
}

type StepAction = 'APPROVE' | 'REJECT' | 'RETURN';

interface ConfirmState {
  action: StepAction;
  comment: string;
}

const ACTION_LABELS: Record<StepAction, string> = {
  APPROVE: 'Approve',
  REJECT: 'Reject',
  RETURN: 'Return',
};

const ACTION_SUCCESS: Record<StepAction, string> = {
  APPROVE: 'Loan approved and borrower notified.',
  REJECT: 'Loan application rejected.',
  RETURN: 'Application returned for revision.',
};

interface StepDetailDrawerProps {
  open: boolean;
  onClose: () => void;
  task: WorkflowTask | null;
  onActioned: () => void;
}

export function StepDetailDrawer({ open, onClose, task, onActioned }: StepDetailDrawerProps) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);

  const actionMutation = useMutation({
    mutationFn: ({ action, comment }: { action: StepAction; comment: string }) =>
      api.post(`/api/v1/workflow/steps/${task!.id}/action/`, { action, comment }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['workflow-tasks'] });
      qc.invalidateQueries({ queryKey: ['loans'] });
      toast.success(ACTION_SUCCESS[vars.action]);
      setConfirm(null);
      onActioned();
      onClose();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Action failed';
      toast.error(msg);
    },
  });

  if (!task) return null;

  const stepLabel =
    task.step_type === 'approval'
      ? 'Loan Approval'
      : task.step_type.charAt(0).toUpperCase() + task.step_type.slice(1);

  const comments = task.comments ?? [];

  const footer = (
    <div className="flex gap-3">
      <Button
        variant="secondary"
        onClick={() => setConfirm({ action: 'RETURN', comment: '' })}
      >
        Return
      </Button>
      <Button
        variant="danger"
        onClick={() => setConfirm({ action: 'REJECT', comment: '' })}
      >
        Reject
      </Button>
      <Button
        variant="primary"
        onClick={() => setConfirm({ action: 'APPROVE', comment: '' })}
      >
        Approve
      </Button>
    </div>
  );

  return (
    <>
      <Drawer
        open={open}
        onClose={onClose}
        title={formatLoanId(task.entity_id)}
        footer={footer}
      >
        <div className="flex flex-col gap-6">
          {/* Header summary */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3 flex-wrap">
              {task.loan_status ? (
                <LoanStatusBadge status={task.loan_status} />
              ) : (
                <Badge variant="info">{stepLabel}</Badge>
              )}
              <span className="text-xs font-mono text-tertiary">
                {formatElapsed(task.submitted_at)}
              </span>
            </div>
            <p className="text-sm text-secondary">
              <span className="font-medium text-primary">{task.borrower_name}</span>
              {task.product_name && (
                <> &middot; {task.product_name}</>
              )}
            </p>
          </div>

          {/* Key amounts */}
          <div className="grid grid-cols-2 gap-3">
            <AmountSummary label="Principal" value={<AmountDisplay amount={task.amount} />} />
            {task.outstanding_balance !== undefined && (
              <AmountSummary label="Outstanding" value={<AmountDisplay amount={task.outstanding_balance} />} />
            )}
            {task.loan_term_months !== undefined && (
              <AmountSummary
                label="Term"
                value={<span className="font-mono font-semibold text-sm text-primary">{task.loan_term_months} months</span>}
              />
            )}
          </div>

          {/* Tabs */}
          <Tabs
            tabs={[
              {
                label: 'Detail',
                content: (
                  <dl className="divide-y divide-[color:var(--color-border-default)] pt-2">
                    <InfoRow label="Loan ID" value={<span className="font-mono text-sm">{formatLoanId(task.entity_id)}</span>} />
                    <InfoRow label="Borrower" value={task.borrower_name} />
                    {task.product_name && <InfoRow label="Product" value={task.product_name} />}
                    <InfoRow label="Principal" value={<AmountDisplay amount={task.amount} />} />
                    {task.loan_term_months && (
                      <InfoRow label="Term" value={`${task.loan_term_months} months`} />
                    )}
                    {task.loan_status && (
                      <InfoRow label="Status" value={<LoanStatusBadge status={task.loan_status} />} />
                    )}
                    <InfoRow label="Step type" value={stepLabel} />
                    <InfoRow label="Submitted" value={formatDate(task.submitted_at)} />
                  </dl>
                ),
              },
              {
                label: `Comments${comments.length ? ` (${comments.length})` : ''}`,
                content: (
                  <div className="pt-2 flex flex-col gap-3">
                    {comments.length === 0 ? (
                      <p className="text-sm text-tertiary text-center py-8">No comments yet.</p>
                    ) : (
                      comments.map((c) => (
                        <div
                          key={c.id}
                          className="flex flex-col gap-1 py-3 border-b border-[color:var(--color-border-default)] last:border-b-0"
                        >
                          <div className="flex items-center gap-2">
                            <Badge variant="neutral">{c.action}</Badge>
                            <span className="text-sm font-medium text-primary">{c.actor_name}</span>
                            <span className="ml-auto text-xs font-mono text-tertiary whitespace-nowrap">
                              {formatDate(c.created_at)}
                            </span>
                          </div>
                          {c.comment && (
                            <p className="text-sm text-secondary mt-1 pl-1">{c.comment}</p>
                          )}
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

      {/* Confirmation modal */}
      {confirm && (
        <ActionConfirmModal
          action={confirm.action}
          comment={confirm.comment}
          onCommentChange={(v) => setConfirm((s) => s ? { ...s, comment: v } : s)}
          onCancel={() => setConfirm(null)}
          onConfirm={() => actionMutation.mutate({ action: confirm.action, comment: confirm.comment })}
          loading={actionMutation.isPending}
        />
      )}
    </>
  );
}

function AmountSummary({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-sunken rounded-lg px-3 py-2.5">
      <p className="text-xs text-tertiary">{label}</p>
      <div className="mt-0.5">{value}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex justify-between py-2.5 text-sm">
      <dt className="text-secondary">{label}</dt>
      <dd className="text-primary font-medium text-right">{value}</dd>
    </div>
  );
}

const ACTION_MODAL_COPY: Record<StepAction, { title: string; description: string; confirmLabel: string; confirmVariant: 'primary' | 'danger' }> = {
  APPROVE: {
    title: 'Approve application',
    description: 'Approving will advance this loan to the next step. The borrower will be notified.',
    confirmLabel: 'Approve',
    confirmVariant: 'primary',
  },
  REJECT: {
    title: 'Reject application',
    description: 'Rejecting will permanently close this loan application. This cannot be undone.',
    confirmLabel: 'Reject',
    confirmVariant: 'danger',
  },
  RETURN: {
    title: 'Return for revision',
    description: 'The application will be returned to the previous step for correction.',
    confirmLabel: 'Return',
    confirmVariant: 'primary',
  },
};

function ActionConfirmModal({
  action,
  comment,
  onCommentChange,
  onCancel,
  onConfirm,
  loading,
}: {
  action: StepAction;
  comment: string;
  onCommentChange: (v: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
  loading: boolean;
}) {
  const copy = ACTION_MODAL_COPY[action];
  return (
    <Modal
      open
      onClose={onCancel}
      title={copy.title}
      size="md"
      footer={
        <ModalFooter
          onCancel={onCancel}
          onConfirm={onConfirm}
          confirmLabel={copy.confirmLabel}
          confirmVariant={copy.confirmVariant}
          loading={loading}
        />
      }
    >
      <div className="flex flex-col gap-4">
        <p className="text-sm text-secondary">{copy.description}</p>
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-primary" htmlFor="action-comment">
            Comment <span className="text-tertiary font-normal">(optional)</span>
          </label>
          <textarea
            id="action-comment"
            value={comment}
            onChange={(e) => onCommentChange(e.target.value)}
            rows={3}
            placeholder={`Add a note for ${ACTION_LABELS[action].toLowerCase()}…`}
            className={[
              'w-full rounded-lg border border-[color:var(--color-border-default)]',
              'bg-surface px-3 py-2 text-sm text-primary placeholder:text-tertiary resize-none',
              'focus:outline-none focus:border-[color:var(--color-border-focus)]',
              'focus:ring-2 focus:ring-[var(--color-border-focus)] focus:ring-opacity-30',
            ].join(' ')}
          />
        </div>
      </div>
    </Modal>
  );
}
