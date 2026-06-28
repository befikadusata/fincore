'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/format';

interface AuditLog {
  id: string;
  created_at: string;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  changes: Record<string, unknown> | null;
}

interface AuditResponse {
  count: number;
  results: AuditLog[];
}

const COMMON_ACTIONS = [
  'created', 'updated', 'deleted',
  'submitted', 'approved', 'rejected',
  'disbursed', 'repaid', 'activated', 'deactivated',
];

export default function AuditPage() {
  const [actorSearch, setActorSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', actorSearch, actionFilter, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (actorSearch) params.set('actor', actorSearch);
      if (actionFilter) params.set('action', actionFilter);
      if (startDate) params.set('start_date', startDate);
      if (endDate) params.set('end_date', endDate);
      const qs = params.toString();
      const { data } = await api.get<AuditResponse>(
        `/api/v1/audit/logs/${qs ? `?${qs}` : ''}`
      );
      return data;
    },
  });

  const logs = data?.results ?? [];

  function summarizeChanges(changes: Record<string, unknown> | null): string {
    if (!changes) return '—';
    const keys = Object.keys(changes);
    if (keys.length === 0) return '—';
    if (keys.length <= 2) return keys.join(', ');
    return `${keys.slice(0, 2).join(', ')} +${keys.length - 2} more`;
  }

  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">Audit Log</h1>
        <p className="text-sm text-secondary mt-1">Immutable record of all system actions</p>
      </div>

      <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-3 p-4 border-b border-[color:var(--color-border-default)] bg-surface flex-wrap">
          <div className="flex-1 min-w-[180px] max-w-xs">
            <Input
              value={actorSearch}
              onChange={(e) => setActorSearch(e.target.value)}
              placeholder="Search by actor…"
            />
          </div>
          <Select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="w-44"
          >
            <option value="">All actions</option>
            {COMMON_ACTIONS.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </Select>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-36"
            />
            <span className="text-xs text-tertiary">to</span>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-36"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-sm text-secondary">Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-8">
            <EmptyState
              title="No audit entries"
              description="Audit entries appear here as actions are performed in the system."
            />
          </div>
        ) : (
          <Table<AuditLog>
            keyExtractor={(row) => row.id}
            rows={logs}
            columns={[
              {
                key: 'timestamp',
                header: 'Timestamp',
                colType: 'date',
                render: (row) => formatDate(row.created_at),
              },
              {
                key: 'actor',
                header: 'Actor',
                render: (row) => (
                  <span className="text-sm text-primary">{row.actor_name ?? '—'}</span>
                ),
              },
              {
                key: 'action',
                header: 'Action',
                render: (row) => <Badge variant="neutral">{row.action}</Badge>,
              },
              {
                key: 'entity_type',
                header: 'Entity Type',
                render: (row) => (
                  <span className="text-sm text-secondary capitalize">{row.entity_type}</span>
                ),
              },
              {
                key: 'entity_id',
                header: 'Entity ID',
                colType: 'id',
                render: (row) => row.entity_id.slice(0, 8),
              },
              {
                key: 'changes',
                header: 'Changes',
                render: (row) => (
                  <span className="text-xs font-mono text-secondary">
                    {summarizeChanges(row.changes)}
                  </span>
                ),
              },
            ]}
          />
        )}
      </div>
    </div>
  );
}
