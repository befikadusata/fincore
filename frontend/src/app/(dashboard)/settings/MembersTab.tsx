'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';

interface MemberRole { id: string; name: string; slug: string }
interface MemberUser { id: string; email: string; first_name: string; last_name: string }
interface Member { id: string; user: MemberUser; status: string; roles: MemberRole[]; created_at: string }
interface Role { id: string; name: string; slug: string }

function useMembersQuery() {
  return useQuery({
    queryKey: ['members'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/members/');
      return (data?.results ?? data) as Member[];
    },
  });
}

function useRolesQuery() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/roles/');
      return (data?.results ?? data) as Role[];
    },
  });
}

export function MembersTab() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data: members = [], isLoading } = useMembersQuery();
  const { data: roles = [] } = useRolesQuery();

  const [showInvite, setShowInvite] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRoleId, setInviteRoleId] = useState('');
  const [emailError, setEmailError] = useState('');

  const inviteMutation = useMutation({
    mutationFn: async ({ email, roleId }: { email: string; roleId: string }) => {
      const { data } = await api.post('/api/v1/members/invite/', { email });
      if (roleId) {
        await api.post(`/api/v1/roles/${roleId}/assign_members/`, {
          user_ids: [data.user.id],
        });
      }
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] });
      toast.success('Invitation sent');
      closeInviteModal();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { email?: string[] } } })?.response?.data?.email?.[0];
      if (msg) setEmailError(msg);
      else toast.error('Failed to send invitation');
    },
  });

  const removeMutation = useMutation({
    mutationFn: (memberId: string) =>
      api.post(`/api/v1/members/${memberId}/remove/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] });
      toast.success('Member removed');
      setRemoveTarget(null);
    },
    onError: () => toast.error('Failed to remove member'),
  });

  function closeInviteModal() {
    setShowInvite(false);
    setInviteEmail('');
    setInviteRoleId('');
    setEmailError('');
  }

  function submitInvite() {
    if (!inviteEmail.trim()) { setEmailError('Email is required.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(inviteEmail)) { setEmailError('Enter a valid email address.'); return; }
    inviteMutation.mutate({ email: inviteEmail.trim(), roleId: inviteRoleId });
  }

  function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    submitInvite();
  }

  const displayName = (u: MemberUser) =>
    u.first_name ? `${u.first_name} ${u.last_name}`.trim() : u.email;

  return (
    <div className="p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-primary">Members</h2>
        <Button variant="primary" size="sm" onClick={() => setShowInvite(true)}>
          Invite member
        </Button>
      </div>

      {isLoading ? (
        <div className="text-secondary text-sm py-8 text-center">Loading…</div>
      ) : (
        <Table<Member>
          keyExtractor={(m) => m.id}
          columns={[
            {
              key: 'name',
              header: 'Member',
              render: (m) => (
                <div>
                  <p className="font-medium text-primary">{displayName(m.user)}</p>
                  <p className="text-xs text-tertiary font-mono">{m.user.email}</p>
                </div>
              ),
            },
            {
              key: 'roles',
              header: 'Roles',
              render: (m) =>
                m.roles.length ? (
                  <div className="flex flex-wrap gap-1">
                    {m.roles.map((r) => (
                      <Badge key={r.id} variant="neutral">{r.name}</Badge>
                    ))}
                  </div>
                ) : (
                  <span className="text-tertiary text-sm">—</span>
                ),
            },
            {
              key: 'status',
              header: 'Status',
              render: (m) => (
                <Badge variant={m.status === 'active' ? 'success' : m.status === 'invited' ? 'info' : 'neutral'}>
                  {m.status}
                </Badge>
              ),
            },
            {
              key: 'actions',
              header: '',
              render: (m) => (
                <Button
                  variant="danger"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); setRemoveTarget(m); }}
                >
                  Remove
                </Button>
              ),
            },
          ]}
          rows={members}
          emptyState={
            <EmptyState
              title="No members yet"
              description="Invite your team members to collaborate."
              action={{ label: 'Invite member', onClick: () => setShowInvite(true) }}
            />
          }
        />
      )}

      {/* Invite modal */}
      <Modal
        open={showInvite}
        onClose={closeInviteModal}
        title="Invite member"
        size="md"
        footer={
          <ModalFooter
            onCancel={closeInviteModal}
            onConfirm={submitInvite}
            confirmLabel="Invite"
            loading={inviteMutation.isPending}
          />
        }
      >
        <form onSubmit={handleInvite} className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="invite-email" className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]">
              Email address
            </label>
            <Input
              id="invite-email"
              type="email"
              value={inviteEmail}
              onChange={(e) => { setInviteEmail(e.target.value); setEmailError(''); }}
              placeholder="colleague@example.com"
              error={!!emailError}
              autoFocus
            />
            {emailError && <span className="text-sm text-[var(--color-danger-text)]">{emailError}</span>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="invite-role" className="text-sm font-medium text-primary">
              Role <span className="text-tertiary font-normal">(optional)</span>
            </label>
            <Select
              id="invite-role"
              value={inviteRoleId}
              onChange={(e) => setInviteRoleId(e.target.value)}
            >
              <option value="">No role</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </Select>
          </div>
        </form>
      </Modal>

      {/* Remove confirmation modal */}
      <Modal
        open={!!removeTarget}
        onClose={() => setRemoveTarget(null)}
        title="Remove member"
        size="sm"
        footer={
          <ModalFooter
            onCancel={() => setRemoveTarget(null)}
            onConfirm={() => removeTarget && removeMutation.mutate(removeTarget.id)}
            confirmLabel="Remove"
            confirmVariant="danger"
            loading={removeMutation.isPending}
          />
        }
      >
        <p className="text-base text-secondary">
          Remove <span className="font-semibold text-primary">{removeTarget ? displayName(removeTarget.user) : ''}</span> from this organization?
          They will lose access immediately.
        </p>
      </Modal>
    </div>
  );
}
