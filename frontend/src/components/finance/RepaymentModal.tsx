'use client';

import { useState, useEffect } from 'react';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { InputAmount } from '@/components/ui/Input';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { formatLoanId } from '@/lib/format';

const m = (v: string | number) => Math.round(parseFloat(String(v ?? 0)) * 100);

interface Loan {
  id: string;
  outstanding_balance: string;
  currency: string;
}

interface RepaymentModalProps {
  open: boolean;
  onClose: () => void;
  loan: Loan | null;
  onSubmit: (amount: string) => void;
  loading: boolean;
}

export function RepaymentModal({ open, onClose, loan, onSubmit, loading }: RepaymentModalProps) {
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setAmount('');
      setError('');
    }
  }, [open]);

  function handleSubmit() {
    const val = parseFloat(amount);
    if (!amount || isNaN(val) || val <= 0) {
      setError('Enter a valid amount');
      return;
    }
    if (loan && val > parseFloat(loan.outstanding_balance)) {
      setError('Amount exceeds outstanding balance');
      return;
    }
    onSubmit(amount);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Record Repayment"
      size="md"
      footer={
        <ModalFooter
          onCancel={onClose}
          onConfirm={handleSubmit}
          confirmLabel="Record payment"
          loading={loading}
        />
      }
    >
      {loan && (
        <div className="flex flex-col gap-5">
          <div className="px-4 py-3 bg-sunken rounded-lg flex items-center justify-between">
            <span className="text-sm text-secondary font-mono">{formatLoanId(loan.id)}</span>
            <div className="text-right">
              <p className="text-xs text-tertiary">Outstanding balance</p>
              <AmountDisplay amount={m(loan.outstanding_balance)} size="lg" />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-primary">
              Payment amount (ETB)<span className="ml-0.5 text-[var(--color-danger-text)]">*</span>
            </label>
            <InputAmount
              value={amount}
              onChange={(e) => { setAmount(e.target.value); setError(''); }}
              placeholder="0.00"
              error={!!error}
              autoFocus
            />
            {error && <span className="text-sm text-[var(--color-danger-text)]">{error}</span>}
          </div>
        </div>
      )}
    </Modal>
  );
}
