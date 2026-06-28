'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Input, InputAmount } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import api from '@/lib/api';
import type { LoanProduct } from './LoanProductModal';

interface FormState {
  product_id: string;
  principal_amount: string;
  term_months: string;
  notes: string;
}

const empty: FormState = { product_id: '', principal_amount: '', term_months: '', notes: '' };

interface CreateLoanModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: Record<string, unknown>) => void;
  loading: boolean;
}

export function CreateLoanModal({ open, onClose, onSubmit, loading }: CreateLoanModalProps) {
  const [form, setForm] = useState<FormState>(empty);
  const [errors, setErrors] = useState<Partial<FormState>>({});

  const { data: products = [] } = useQuery({
    queryKey: ['loan-products'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/finance/loan-products/');
      return (data?.results ?? data) as LoanProduct[];
    },
    enabled: open,
  });

  const selectedProduct = products.find((p) => p.id === form.product_id);

  useEffect(() => {
    if (open) {
      setForm(empty);
      setErrors({});
    }
  }, [open]);

  useEffect(() => {
    if (selectedProduct) {
      setForm((f) => ({
        ...f,
        term_months: f.term_months || String(selectedProduct.min_term_months),
      }));
    }
  }, [selectedProduct]);

  function set(key: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate(): boolean {
    const e: Partial<FormState> = {};
    if (!form.product_id) e.product_id = 'Select a product';
    if (!form.principal_amount || parseFloat(form.principal_amount) <= 0) e.principal_amount = 'Required';
    if (!form.term_months || parseInt(form.term_months) < 1) e.term_months = 'Min 1 month';
    if (selectedProduct) {
      const amount = parseFloat(form.principal_amount);
      const min = parseFloat(selectedProduct.min_amount);
      const max = parseFloat(selectedProduct.max_amount);
      if (amount < min || amount > max) {
        e.principal_amount = `Must be between ETB ${min.toLocaleString()} and ETB ${max.toLocaleString()}`;
      }
      const months = parseInt(form.term_months);
      if (months < selectedProduct.min_term_months || months > selectedProduct.max_term_months) {
        e.term_months = `Must be between ${selectedProduct.min_term_months} and ${selectedProduct.max_term_months} months`;
      }
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit() {
    if (!validate()) return;
    onSubmit({
      product: form.product_id,
      principal_amount: form.principal_amount,
      term_months: parseInt(form.term_months),
      notes: form.notes.trim(),
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New Loan Application"
      size="lg"
      footer={
        <ModalFooter
          onCancel={onClose}
          onConfirm={handleSubmit}
          confirmLabel="Submit application"
          loading={loading}
        />
      }
    >
      <div className="flex flex-col gap-5">
        <Field label="Loan product" required error={errors.product_id}>
          <Select value={form.product_id} onChange={(e) => set('product_id', e.target.value)}>
            <option value="">Select a product…</option>
            {products
              .filter((p) => p.is_active)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </Select>
        </Field>

        {selectedProduct && (
          <div className="flex items-center gap-6 px-4 py-3 bg-sunken rounded-lg text-sm text-secondary font-mono">
            <span>Rate: {(parseFloat(selectedProduct.interest_rate) * 100).toFixed(1)}%</span>
            <span>Type: {selectedProduct.interest_type === 'flat' ? 'Flat' : 'Reducing Balance'}</span>
            <span>Term: {selectedProduct.min_term_months}–{selectedProduct.max_term_months} mo</span>
          </div>
        )}

        <Field label="Principal amount (ETB)" required error={errors.principal_amount}>
          <InputAmount
            value={form.principal_amount}
            onChange={(e) => set('principal_amount', e.target.value)}
            placeholder="0.00"
            error={!!errors.principal_amount}
          />
        </Field>

        <Field label="Term (months)" required error={errors.term_months}>
          <Input
            type="number"
            min="1"
            max="360"
            value={form.term_months}
            onChange={(e) => set('term_months', e.target.value)}
            placeholder="12"
            error={!!errors.term_months}
          />
        </Field>

        <Field label="Notes">
          <textarea
            value={form.notes}
            onChange={(e) => set('notes', e.target.value)}
            placeholder="Optional notes"
            rows={2}
            className="w-full px-3 py-2 rounded border border-[color:var(--color-border-default)] bg-surface text-primary text-base font-sans placeholder:text-tertiary focus:outline-none focus:border-[var(--color-border-focus)] focus:shadow-[0_0_0_3px_rgba(230,172,0,0.18)] hover:border-[color:var(--color-border-strong)] transition-colors resize-none"
          />
        </Field>
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
