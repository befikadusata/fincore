'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table, TableToolbar } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { formatDate } from '@/lib/format';

interface WorkflowDefinition {
  id: string;
  name: string;
  trigger: string;
  version: number;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
}

const EMPTY_CONFIG = JSON.stringify(
  {
    steps: [
      {
        name: 'Review',
        type: 'approval',
        assignee_role: 'loan_officer',
        actions: ['APPROVE', 'REJECT', 'RETURN'],
      },
    ],
  },
  null,
  2
);

export default function WorkflowPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState('');
  const [modalState, setModalState] = useState<
    | { mode: 'create' }
    | { mode: 'edit'; definition: WorkflowDefinition }
    | null
  >(null);

  const { data: definitions = [], isLoading } = useQuery({
    queryKey: ['workflow-definitions'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/workflow/definitions/');
      return (data?.results ?? data) as WorkflowDefinition[];
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post('/api/v1/workflow/definitions/', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflow-definitions'] });
      toast.success('Workflow definition created');
      setModalState(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to create workflow';
      toast.error(msg);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.put(`/api/v1/workflow/definitions/${id}/`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflow-definitions'] });
      toast.success('Workflow definition updated');
      setModalState(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to update workflow';
      toast.error(msg);
    },
  });

  const filtered = definitions.filter(
    (d) =>
      !search ||
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.trigger.toLowerCase().includes(search.toLowerCase())
  );

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Workflows</h1>
          <p className="text-sm text-secondary mt-1">Manage approval workflow definitions</p>
        </div>
        <Button variant="primary" onClick={() => setModalState({ mode: 'create' })}>
          New workflow
        </Button>
      </div>

      <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
        <TableToolbar
          searchPlaceholder="Search by name or trigger…"
          searchValue={search}
          onSearchChange={setSearch}
        />

        {isLoading ? (
          <div className="p-8 text-center text-sm text-secondary">Loading…</div>
        ) : (
          <Table<WorkflowDefinition>
            keyExtractor={(d) => d.id}
            rows={filtered}
            onRowClick={(d) => setModalState({ mode: 'edit', definition: d })}
            columns={[
              {
                key: 'name',
                header: 'Name',
                render: (d) => (
                  <span className="font-medium text-primary">{d.name}</span>
                ),
              },
              {
                key: 'trigger',
                header: 'Trigger',
                render: (d) => (
                  <span className="font-mono text-sm text-secondary">{d.trigger}</span>
                ),
              },
              {
                key: 'version',
                header: 'Version',
                colType: 'count',
                render: (d) => d.version,
              },
              {
                key: 'status',
                header: 'Status',
                render: (d) => (
                  <Badge variant={d.is_active ? 'success' : 'neutral'}>
                    {d.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                ),
              },
              {
                key: 'created',
                header: 'Created',
                colType: 'date',
                render: (d) => formatDate(d.created_at),
              },
            ]}
            emptyState={
              <EmptyState
                title="No workflows yet"
                description="Create a workflow definition to enable approval flows for loans and other entities."
                action={{ label: 'New workflow', onClick: () => setModalState({ mode: 'create' }) }}
              />
            }
          />
        )}
      </div>

      {modalState && (
        <WorkflowDefinitionModal
          mode={modalState.mode}
          definition={modalState.mode === 'edit' ? modalState.definition : undefined}
          loading={isPending}
          onClose={() => setModalState(null)}
          onSubmit={(name, trigger, isActive, configJson) => {
            let config: Record<string, unknown>;
            try {
              config = JSON.parse(configJson);
            } catch {
              toast.error('Invalid JSON in workflow config');
              return;
            }
            const body = { name, trigger, is_active: isActive, config };
            if (modalState.mode === 'edit') {
              updateMutation.mutate({ id: modalState.definition.id, body });
            } else {
              createMutation.mutate(body);
            }
          }}
        />
      )}
    </div>
  );
}

interface WorkflowDefinitionModalProps {
  mode: 'create' | 'edit';
  definition?: WorkflowDefinition;
  loading: boolean;
  onClose: () => void;
  onSubmit: (name: string, trigger: string, isActive: boolean, configJson: string) => void;
}

function WorkflowDefinitionModal({
  mode,
  definition,
  loading,
  onClose,
  onSubmit,
}: WorkflowDefinitionModalProps) {
  const [name, setName] = useState(definition?.name ?? '');
  const [trigger, setTrigger] = useState(definition?.trigger ?? '');
  const [isActive, setIsActive] = useState(definition?.is_active ?? true);
  const [configJson, setConfigJson] = useState(
    definition ? JSON.stringify(definition.config, null, 2) : EMPTY_CONFIG
  );
  const [jsonError, setJsonError] = useState('');

  function handleConfigChange(v: string) {
    setConfigJson(v);
    try {
      JSON.parse(v);
      setJsonError('');
    } catch {
      setJsonError('Invalid JSON');
    }
  }

  function handleSubmit() {
    if (!name.trim()) return;
    if (!trigger.trim()) return;
    onSubmit(name.trim(), trigger.trim(), isActive, configJson);
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={mode === 'create' ? 'New workflow' : 'Edit workflow'}
      size="lg"
      footer={
        <ModalFooter
          onCancel={onClose}
          onConfirm={handleSubmit}
          confirmLabel={mode === 'create' ? 'Create' : 'Save'}
          loading={loading}
        />
      }
    >
      <div className="flex flex-col gap-5">
        {/* Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-primary" htmlFor="wf-name">
            Name <span className="text-[var(--color-danger-text)]">*</span>
          </label>
          <input
            id="wf-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Loan Approval"
            className={[
              'w-full rounded-lg border border-[color:var(--color-border-default)]',
              'bg-surface px-3 py-2 text-sm text-primary placeholder:text-tertiary',
              'focus:outline-none focus:border-[color:var(--color-border-focus)]',
              'focus:ring-2 focus:ring-[var(--color-border-focus)] focus:ring-opacity-30',
            ].join(' ')}
          />
        </div>

        {/* Trigger */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-primary" htmlFor="wf-trigger">
            Trigger event <span className="text-[var(--color-danger-text)]">*</span>
          </label>
          <input
            id="wf-trigger"
            type="text"
            value={trigger}
            onChange={(e) => setTrigger(e.target.value)}
            placeholder="e.g. loan.submitted"
            className={[
              'w-full rounded-lg rounded-lg border border-[color:var(--color-border-default)]',
              'bg-surface px-3 py-2 text-sm font-mono text-primary placeholder:text-tertiary',
              'focus:outline-none focus:border-[color:var(--color-border-focus)]',
              'focus:ring-2 focus:ring-[var(--color-border-focus)] focus:ring-opacity-30',
            ].join(' ')}
          />
        </div>

        {/* Active toggle */}
        <label className="flex items-center gap-3 cursor-pointer">
          <div className="relative">
            <input
              type="checkbox"
              className="sr-only peer"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <div className="w-10 h-6 rounded-full bg-[var(--color-neutral-bg)] peer-checked:bg-brand transition-colors duration-fast" />
            <div className="absolute left-1 top-1 w-4 h-4 rounded-full bg-white transition-transform duration-fast peer-checked:translate-x-4 shadow-sm" />
          </div>
          <span className="text-sm font-medium text-primary">Active</span>
          <span className="text-sm text-tertiary">
            {isActive ? 'This workflow will run on matching events.' : 'This workflow is disabled.'}
          </span>
        </label>

        {/* Config JSON */}
        <div className="flex flex-col gap-1.5">
          <label className="text-sm font-medium text-primary" htmlFor="wf-config">
            Workflow config <span className="text-tertiary font-normal">(JSON)</span>
          </label>
          <textarea
            id="wf-config"
            value={configJson}
            onChange={(e) => handleConfigChange(e.target.value)}
            rows={12}
            spellCheck={false}
            className={[
              'w-full rounded-lg border',
              jsonError
                ? 'border-[color:var(--color-danger-border)]'
                : 'border-[color:var(--color-border-default)]',
              'bg-sunken px-3 py-2 text-sm font-mono text-primary resize-y',
              'focus:outline-none focus:border-[color:var(--color-border-focus)]',
              'focus:ring-2 focus:ring-[var(--color-border-focus)] focus:ring-opacity-30',
            ].join(' ')}
          />
          {jsonError && (
            <p className="text-xs text-[var(--color-danger-text)]">{jsonError}</p>
          )}
        </div>
      </div>
    </Modal>
  );
}
