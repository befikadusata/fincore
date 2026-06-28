'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Table } from '@/components/ui/Table';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { AmountDisplay } from '@/components/domain/AmountDisplay';
import { useToast } from '@/components/ui/Toast';
import { formatDate } from '@/lib/format';
import type { BadgeVariant } from '@/lib/status';

interface PlanFeature {
  id: string;
  name: string;
  codename: string;
  description: string;
}

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  monthly_price: number;
  annual_price: number;
  currency: string;
  is_active: boolean;
  features: PlanFeature[];
}

interface Subscription {
  id: string;
  plan: string;
  plan_name: string;
  status: string;
  billing_cycle: string;
  current_period_end: string | null;
  trial_end: string | null;
  cancelled_at: string | null;
}

interface Invoice {
  id: string;
  invoice_number: string;
  status: string;
  amount: string;
  currency: string;
  due_date: string;
  paid_at: string | null;
  created_at: string;
}

type SubStatus = 'active' | 'trialing' | 'past_due' | 'cancelled' | 'expired';

const subStatusRail: Record<SubStatus, 'success' | 'warning' | 'danger'> = {
  active:   'success',
  trialing: 'success',
  past_due: 'warning',
  cancelled:'danger',
  expired:  'danger',
};

const subStatusBadge: Record<SubStatus, BadgeVariant> = {
  active:   'success',
  trialing: 'info',
  past_due: 'warning',
  cancelled:'danger',
  expired:  'danger',
};

const invoiceBadge: Record<string, BadgeVariant> = {
  paid:      'success',
  issued:    'info',
  overdue:   'danger',
  draft:     'neutral',
  cancelled: 'neutral',
  refunded:  'neutral',
};

function m(v: string): number {
  return Math.round(parseFloat(v) * 100);
}

export function BillingTab() {
  const qc = useQueryClient();
  const { toast } = useToast();

  const [upgradePlan, setUpgradePlan] = useState<Plan | null>(null);
  const [checkoutInvoiceId, setCheckoutInvoiceId] = useState<string | null>(null);

  const { data: subscriptions = [], isLoading: subLoading } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: async () => {
      const { data } = await api.get<{ results: Subscription[] } | Subscription[]>(
        '/api/v1/billing/subscriptions/'
      );
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });

  const { data: plans = [], isLoading: plansLoading } = useQuery({
    queryKey: ['plans'],
    queryFn: async () => {
      const { data } = await api.get<{ results: Plan[] } | Plan[]>('/api/v1/plans/');
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });

  const { data: invoices = [], isLoading: invoiceLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: async () => {
      const { data } = await api.get<{ results: Invoice[] } | Invoice[]>(
        '/api/v1/billing/invoices/'
      );
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  });

  const subscription = subscriptions[0] ?? null;

  const changePlanMutation = useMutation({
    mutationFn: async ({ subId, planId }: { subId: string; planId: string }) => {
      await api.post(`/api/v1/billing/subscriptions/${subId}/change-plan/`, { plan: planId });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['subscriptions'] });
      toast.success('Plan updated successfully');
      setUpgradePlan(null);
    },
    onError: () => toast.error('Failed to change plan'),
  });

  const checkoutMutation = useMutation({
    mutationFn: async (invoiceId: string) => {
      const { data } = await api.post<{ checkout_url: string }>(
        `/api/v1/billing/invoices/${invoiceId}/checkout/`
      );
      return data;
    },
    onSuccess: (data) => {
      setCheckoutInvoiceId(null);
      window.location.href = data.checkout_url;
    },
    onError: () => {
      setCheckoutInvoiceId(null);
      toast.error('Could not initialize payment. Please try again.');
    },
  });

  const statusRailVariant = subscription
    ? (subStatusRail[subscription.status as SubStatus] ?? 'neutral')
    : undefined;

  const renewalDate = subscription?.current_period_end
    ? formatDate(subscription.current_period_end)
    : subscription?.trial_end
    ? formatDate(subscription.trial_end)
    : null;

  return (
    <div className="p-6 flex flex-col gap-8">
      {/* Subscription status */}
      <section>
        <h2 className="text-xl font-semibold text-primary mb-4">Subscription</h2>
        {subLoading ? (
          <div className="text-sm text-secondary py-4">Loading…</div>
        ) : !subscription ? (
          <Card>
            <div className="p-5">
              <EmptyState
                title="No active subscription"
                description="Choose a plan below to get started."
              />
            </div>
          </Card>
        ) : (
          <Card statusRail={statusRailVariant as 'success' | 'warning' | 'danger' | undefined}>
            <div className="p-5 flex items-start justify-between gap-4 flex-wrap">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-semibold text-primary">
                    {subscription.plan_name}
                  </span>
                  <Badge variant={subStatusBadge[subscription.status as SubStatus] ?? 'neutral'}>
                    {subscription.status.replace('_', ' ')}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-sm text-secondary">
                  <span className="capitalize">{subscription.billing_cycle} billing</span>
                  {renewalDate && (
                    <span>
                      {subscription.status === 'cancelled' ? 'Cancelled at' : 'Renews'}{' '}
                      <span className="font-mono text-primary">{renewalDate}</span>
                    </span>
                  )}
                </div>
              </div>
              {plans.length > 0 && subscription.status !== 'cancelled' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    setUpgradePlan(plans.find((p) => p.id !== subscription.plan) ?? null)
                  }
                >
                  Change plan
                </Button>
              )}
            </div>
          </Card>
        )}
      </section>

      {/* Plan comparison */}
      {!plansLoading && plans.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold text-primary mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {plans.map((plan) => {
              const isCurrent = subscription?.plan === plan.id;
              return (
                <div
                  key={plan.id}
                  className={[
                    'rounded-lg border bg-surface shadow-sm overflow-hidden',
                    isCurrent
                      ? 'border-[color:var(--color-brand)] ring-1 ring-[var(--color-brand)]'
                      : 'border-[color:var(--color-border-default)]',
                  ].join(' ')}
                >
                  <div className="p-5 flex flex-col gap-4 h-full">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-base font-semibold text-primary">{plan.name}</span>
                      {isCurrent && <Badge variant="success">Current plan</Badge>}
                    </div>

                    <div>
                      <AmountDisplay amount={plan.monthly_price * 100} currency={plan.currency} size="2xl" />
                      <span className="text-sm text-secondary ml-1">/ month</span>
                    </div>

                    {plan.description && (
                      <p className="text-sm text-secondary">{plan.description}</p>
                    )}

                    {plan.features.length > 0 && (
                      <ul className="flex flex-col gap-1.5 flex-1">
                        {plan.features.map((f) => (
                          <li key={f.id} className="flex items-start gap-2 text-sm text-primary">
                            <span className="text-[var(--color-success-text)] flex-shrink-0 mt-0.5">✓</span>
                            <span>{f.name}</span>
                          </li>
                        ))}
                      </ul>
                    )}

                    {!isCurrent && subscription && (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => setUpgradePlan(plan)}
                      >
                        Upgrade to {plan.name}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Invoice history */}
      <section>
        <h2 className="text-xl font-semibold text-primary mb-4">Invoices</h2>
        {invoiceLoading ? (
          <div className="text-sm text-secondary py-4">Loading…</div>
        ) : invoices.length === 0 ? (
          <Card>
            <div className="p-5">
              <EmptyState title="No invoices yet." description="" />
            </div>
          </Card>
        ) : (
          <Table<Invoice>
            keyExtractor={(inv) => inv.id}
            rows={invoices}
            columns={[
              {
                key: 'date',
                header: 'Date',
                colType: 'date',
                render: (inv) => formatDate(inv.created_at),
              },
              {
                key: 'invoice_number',
                header: 'Invoice #',
                colType: 'id',
                render: (inv) => inv.invoice_number,
              },
              {
                key: 'amount',
                header: 'Amount',
                colType: 'amount',
                render: (inv) => (
                  <AmountDisplay amount={m(inv.amount)} currency={inv.currency} />
                ),
              },
              {
                key: 'due_date',
                header: 'Due Date',
                colType: 'date',
                render: (inv) => formatDate(inv.due_date),
              },
              {
                key: 'status',
                header: 'Status',
                render: (inv) => (
                  <Badge variant={invoiceBadge[inv.status] ?? 'neutral'}>
                    {inv.status}
                  </Badge>
                ),
              },
              {
                key: 'actions',
                header: '',
                render: (inv) =>
                  inv.status !== 'paid' && inv.status !== 'cancelled' ? (
                    <Button
                      variant="primary"
                      size="sm"
                      loading={checkoutMutation.isPending && checkoutInvoiceId === inv.id}
                      onClick={() => {
                        setCheckoutInvoiceId(inv.id);
                        checkoutMutation.mutate(inv.id);
                      }}
                    >
                      Pay Now
                    </Button>
                  ) : null,
              },
            ]}
          />
        )}
      </section>

      {/* Upgrade confirmation modal */}
      <Modal
        open={!!upgradePlan}
        onClose={() => setUpgradePlan(null)}
        title={`Upgrade to ${upgradePlan?.name ?? ''}`}
        size="md"
        footer={
          <ModalFooter
            onCancel={() => setUpgradePlan(null)}
            onConfirm={() => {
              if (upgradePlan && subscription) {
                changePlanMutation.mutate({ subId: subscription.id, planId: upgradePlan.id });
              }
            }}
            confirmLabel="Confirm upgrade"
            loading={changePlanMutation.isPending}
          />
        }
      >
        {upgradePlan && (
          <div className="flex flex-col gap-3">
            <p className="text-base text-secondary">
              Upgrade to{' '}
              <span className="font-semibold text-primary">{upgradePlan.name}</span>?
              Your next invoice will be{' '}
              <span className="font-mono font-semibold text-primary">
                {upgradePlan.currency}{' '}
                {(upgradePlan.monthly_price).toLocaleString()}
              </span>{' '}
              per month.
            </p>
            <p className="text-sm text-tertiary">
              The change takes effect immediately.
            </p>
          </div>
        )}
      </Modal>
    </div>
  );
}
