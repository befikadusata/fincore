'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table, TableToolbar } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';
import { LoanProductModal, type LoanProduct } from '@/components/finance/LoanProductModal';
import { formatAmount, formatDate } from '@/lib/format';

const m = (v: string | number) => Math.round(parseFloat(String(v ?? 0)) * 100);

export default function LoanProductsPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<LoanProduct | null>(null);
  const [deleting, setDeleting] = useState<LoanProduct | null>(null);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['loan-products'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/finance/loan-products/');
      return (data?.results ?? data) as LoanProduct[];
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post('/api/v1/finance/loan-products/', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['loan-products'] });
      toast.success('Loan product created');
      setShowCreate(false);
    },
    onError: () => toast.error('Failed to create loan product'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.patch(`/api/v1/finance/loan-products/${id}/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['loan-products'] });
      toast.success('Loan product updated');
      setEditing(null);
    },
    onError: () => toast.error('Failed to update loan product'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/finance/loan-products/${id}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['loan-products'] });
      toast.success('Loan product deleted');
      setDeleting(null);
    },
    onError: () => toast.error('Failed to delete loan product'),
  });

  const filtered = products.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Loan Products</h1>
          <p className="text-sm text-secondary mt-1">Configure interest types, rates, and limits</p>
        </div>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          New product
        </Button>
      </div>

      <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
        <TableToolbar
          searchPlaceholder="Search products…"
          searchValue={search}
          onSearchChange={setSearch}
        />
        {isLoading ? (
          <div className="p-8 text-center text-sm text-secondary">Loading…</div>
        ) : (
          <Table<LoanProduct>
            keyExtractor={(p) => p.id}
            rows={filtered}
            onRowClick={(p) => setEditing(p)}
            columns={[
              {
                key: 'name',
                header: 'Name',
                render: (p) => <span className="font-medium text-primary">{p.name}</span>,
              },
              {
                key: 'type',
                header: 'Interest type',
                render: (p) => (
                  <Badge variant="neutral">
                    {p.interest_type === 'flat' ? 'Flat' : 'Reducing Balance'}
                  </Badge>
                ),
              },
              {
                key: 'rate',
                header: 'Rate',
                colType: 'rate',
                render: (p) => `${(parseFloat(p.interest_rate) * 100).toFixed(2)}%`,
              },
              {
                key: 'term',
                header: 'Term (months)',
                render: (p) => `${p.min_term_months} – ${p.max_term_months}`,
              },
              {
                key: 'amount',
                header: 'Amount range',
                colType: 'amount',
                render: (p) =>
                  `${formatAmount(m(p.min_amount))} – ${formatAmount(m(p.max_amount))}`,
              },
              {
                key: 'status',
                header: 'Status',
                render: (p) => (
                  <Badge variant={p.is_active ? 'success' : 'neutral'}>
                    {p.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                ),
              },
              {
                key: 'created',
                header: 'Created',
                colType: 'date',
                render: (p) => formatDate(p.created_at),
              },
              {
                key: 'actions',
                header: '',
                render: (p) => (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); setDeleting(p); }}
                  >
                    Delete
                  </Button>
                ),
              },
            ]}
            emptyState={
              <EmptyState
                title="No loan products"
                description="Create a loan product to start accepting applications."
                action={{ label: 'New product', onClick: () => setShowCreate(true) }}
              />
            }
          />
        )}
      </div>

      {/* Create modal */}
      <LoanProductModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSubmit={(data) => createMutation.mutate(data)}
        loading={createMutation.isPending}
      />

      {/* Edit modal */}
      <LoanProductModal
        open={!!editing}
        onClose={() => setEditing(null)}
        onSubmit={(data) => editing && updateMutation.mutate({ id: editing.id, body: data })}
        loading={updateMutation.isPending}
        product={editing}
      />

      {/* Delete confirmation */}
      <Modal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Delete loan product"
        size="sm"
        footer={
          <ModalFooter
            onCancel={() => setDeleting(null)}
            onConfirm={() => deleting && deleteMutation.mutate(deleting.id)}
            confirmLabel="Delete"
            confirmVariant="danger"
            loading={deleteMutation.isPending}
          />
        }
      >
        <p className="text-base text-secondary">
          Delete <span className="font-semibold text-primary">{deleting?.name}</span>? This cannot be undone.
        </p>
      </Modal>
    </div>
  );
}
