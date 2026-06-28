'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/components/ui/Toast';

export default function BillingSuccessPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toast } = useToast();

  useEffect(() => {
    qc.invalidateQueries({ queryKey: ['subscriptions'] });
    qc.invalidateQueries({ queryKey: ['invoices'] });
    toast.success('Payment successful', 'Your subscription is now active.');
    const timer = setTimeout(() => {
      router.replace('/settings?tab=billing');
    }, 2500);
    return () => clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-6">
      <div className="w-16 h-16 rounded-full bg-[var(--color-success-bg)] flex items-center justify-center">
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-[var(--color-success-text)]"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <h1 className="text-2xl font-bold text-primary">Payment successful</h1>
      <p className="text-base text-secondary max-w-sm">
        Your payment was processed. Redirecting you back to billing…
      </p>
    </div>
  );
}
