'use client';

import { useState, useEffect } from 'react';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Input, InputAmount } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';

export interface LoanProduct {
  id: string;
  name: string;
  description: string;
  interest_type: string;
  interest_rate: string;
  min_term_months: number;
  max_term_months: number;
  min_amount: string;
  max_amount: string;
  currency: string;
  is_active: boolean;
  created_at: string;
}

interface FormState {
  name: string;
  description: string;
  interest_type: string;
  interest_rate: string;
  min_term_months: string;
  max_term_months: string;
  min_amount: string;
  max_amount: string;
}

const empty: FormState = {
  name: '',
  description: '',
  interest_type: 'flat',
  interest_rate: '',
  min_term_months: '',
  max_term_months: '',
  min_amount: '',
  max_amount: '',
};

interface LoanProductModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, unknown>) => void;
  loading: boolean;
  product?: LoanProduct | null;
}

export function LoanProductModal({
  open,
  onClose,
  onSubmit,
  loading,
  product,
}: LoanProductModalProps) {
  const [form, setForm] = useState<FormState>(empty);
  const [errors, setErrors] = useState<Partial<FormState>>({});

  useEffect(() => {
    if (open) {
      if (product) {
        setForm({
          name: product.name,
          description: product.description ?? '',
          interest_type: product.interest_type,
          interest_rate: product.interest_rate,
          min_term_months: String(product.min_term_months),
          max_term_months: String(product.max_term_months),
          min_amount: product.min_amount,
          max_amount: product.max_amount,
        });
      } else {
        setForm(empty);
      }
      setErrors({});
    }
  }, [open, product]);

  function set(key: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate(): boolean {
    const e: Partial<FormState> = {};
    if (!form.name.trim()) e.name = 'Required';
    if (!form.interest_rate || isNaN(parseFloat(form.interest_rate))) e.interest_rate = 'Required';
    if (!form.min_term_months || parseInt(form.min_term_months) < 1) e.min_term_months = 'Min 1';
    if (!form.max_term_months || parseInt(form.max_term_months) < 1) e.max_term_months = 'Min 1';
    if (!form.min_amount || parseFloat(form.min_amount) <= 0) e.min_amount = 'Required';
    if (!form.max_amount || parseFloat(form.max_amount) <= 0) e.max_amount = 'Required';
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    onSubmit({
      name: form.name.trim(),
      description: form.description.trim(),
      interest_type: form.interest_type,
      interest_rate: form.interest_rate,
      min_term_months: parseInt(form.min_term_months),
      max_term_months: parseInt(form.max_term_months),
      min_amount: form.min_amount,
      max_amount: form.max_amount,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={product ? 'Edit Loan Product' : 'New Loan Product'}
      size="lg"
      footer={
        <ModalFooter
          onCancel={onClose}
          onConfirm={handleSubmit}
          confirmLabel={product ? 'Save changes' : 'Create product'}
          loading={loading}
        />
      }
    >
      <div className="flex flex-col gap-5">
        <Field label="Product name" required error={errors.name}>
          <Input
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="e.g. Personal Loan"
            error={!!errors.name}
            autoFocus
          />
        </Field>

        <Field label="Description">
          <textarea
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="Optional description"
            rows={2}
            className="w-full px-3 py-2 rounded border border-[color:var(--color-border-default)] bg-surface text-primary text-base font-sans placeholder:text-tertiary focus:outline-none focus:border-[var(--color-border-focus)] focus:shadow-[0_0_0_3px_rgba(230,172,0,0.18)] hover:border-[color:var(--color-border-strong)] transition-colors resize-none"
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Interest type" required>
            <Select value={form.interest_type} onChange={(e) => set('interest_type', e.target.value)}>
              <option value="flat">Flat</option>
              <option value="reducing_balance">Reducing Balance</option>
            </Select>
          </Field>

          <Field label="Interest rate (e.g. 0.12 = 12%)" required error={errors.interest_rate}>
            <Input
              type="number"
              step="0.001"
              value={form.interest_rate}
              onChange={(e) => set('interest_rate', e.target.value)}
              placeholder="0.12"
              error={!!errors.interest_rate}
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Min term (months)" required error={errors.min_term_months}>
            <Input
              type="number"
              min="1"
              value={form.min_term_months}
              onChange={(e) => set('min_term_months', e.target.value)}
              placeholder="1"
              error={!!errors.min_term_months}
            />
          </Field>

          <Field label="Max term (months)" required error={errors.max_term_months}>
            <Input
              type="number"
              min="1"
              value={form.max_term_months}
              onChange={(e) => set('max_term_months', e.target.value)}
              placeholder="60"
              error={!!errors.max_term_months}
            />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Min amount (ETB)" required error={errors.min_amount}>
            <InputAmount
              value={form.min_amount}
              onChange={(e) => set('min_amount', e.target.value)}
              placeholder="0.00"
              error={!!errors.min_amount}
            />
          </Field>

          <Field label="Max amount (ETB)" required error={errors.max_amount}>
            <InputAmount
              value={form.max_amount}
              onChange={(e) => set('max_amount', e.target.value)}
              placeholder="0.00"
              error={!!errors.max_amount}
            />
          </Field>
        </div>
      </div>
    </Modal>
  );
}

function Field({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-primary">
        {label}
        {required && <span className="ml-0.5 text-[var(--color-danger-text)]">*</span>}
      </label>
      {children}
      {error && <span className="text-sm text-[var(--color-danger-text)]">{error}</span>}
    </div>
  );
}
