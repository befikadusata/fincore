'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { useToast } from '@/components/ui/Toast';

interface RolePermission { id: string; codename: string }
interface Role { id: string; name: string; slug: string; permissions: RolePermission[] }
interface Permission { id: string; codename: string; description: string }

function toSlug(name: string) {
  return name.toLowerCase().trim()
    .replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').replace(/-+/g, '-');
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

function usePermissionsQuery() {
  return useQuery({
    queryKey: ['permissions'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/permissions/');
      return (data?.results ?? data) as Permission[];
    },
  });
}

export function RolesTab() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const { data: roles = [], isLoading } = useRolesQuery();
  const { data: permissions = [] } = usePermissionsQuery();

  const [editTarget, setEditTarget] = useState<Role | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugEdited, setSlugEdited] = useState(false);
  const [selectedPermIds, setSelectedPermIds] = useState<Set<string>>(new Set());
  const [nameError, setNameError] = useState('');

  function openCreate() {
    setName('');
    setSlug('');
    setSlugEdited(false);
    setSelectedPermIds(new Set());
    setNameError('');
    setEditTarget(null);
    setShowCreate(true);
  }

  function openEdit(role: Role) {
    setName(role.name);
    setSlug(role.slug);
    setSlugEdited(true);
    setSelectedPermIds(new Set(role.permissions.map((p) => p.id)));
    setNameError('');
    setEditTarget(role);
    setShowCreate(true);
  }

  function closeModal() {
    setShowCreate(false);
    setEditTarget(null);
  }

  function handleNameChange(val: string) {
    setName(val);
    setNameError('');
    if (!slugEdited) setSlug(toSlug(val));
  }

  function togglePerm(id: string) {
    setSelectedPermIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (name.trim().length < 1) { setNameError('Name is required.'); throw new Error('validation'); }
      const payload = { name: name.trim(), slug: slug || toSlug(name.trim()) };
      let role: Role;
      if (editTarget) {
        const { data } = await api.patch(`/api/v1/roles/${editTarget.id}/`, payload);
        role = data;
      } else {
        const { data } = await api.post('/api/v1/roles/', payload);
        role = data;
      }
      await api.post(`/api/v1/roles/${role.id}/assign_permissions/`, {
        permission_ids: [...selectedPermIds],
      });
      return role;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] });
      toast.success(editTarget ? 'Role updated' : 'Role created');
      closeModal();
    },
    onError: (err) => {
      if ((err as Error).message === 'validation') return;
      toast.error('Failed to save role');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (roleId: string) => api.delete(`/api/v1/roles/${roleId}/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['roles'] });
      toast.success('Role deleted');
      setDeleteTarget(null);
    },
    onError: () => toast.error('Failed to delete role'),
  });

  return (
    <div className="p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-primary">Roles</h2>
        <Button variant="primary" size="sm" onClick={openCreate}>
          Create role
        </Button>
      </div>

      {isLoading ? (
        <div className="text-secondary text-sm py-8 text-center">Loading…</div>
      ) : roles.length === 0 ? (
        <EmptyState
          title="No roles yet"
          description="Create roles to assign granular permissions to members."
          action={{ label: 'Create role', onClick: openCreate }}
        />
      ) : (
        <div className="flex flex-col gap-3">
          {roles.map((role) => (
            <Card key={role.id}>
              <CardHeader
                title={role.name}
                actions={
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={() => openEdit(role)}>
                      Edit
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => setDeleteTarget(role)}>
                      Delete
                    </Button>
                  </div>
                }
              />
              <CardBody>
                <div className="flex flex-col gap-2">
                  <p className="text-xs font-mono text-tertiary">{role.slug}</p>
                  {role.permissions.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {role.permissions.map((p) => (
                        <Badge key={p.id} variant="neutral">{p.codename}</Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-tertiary">No permissions assigned.</p>
                  )}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit modal */}
      <Modal
        open={showCreate}
        onClose={closeModal}
        title={editTarget ? `Edit role: ${editTarget.name}` : 'Create role'}
        size="lg"
        footer={
          <ModalFooter
            onCancel={closeModal}
            onConfirm={() => saveMutation.mutate()}
            confirmLabel={editTarget ? 'Save changes' : 'Create role'}
            loading={saveMutation.isPending}
          />
        }
      >
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="role-name" className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]">
                Role name
              </label>
              <Input
                id="role-name"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="Loan Officer"
                error={!!nameError}
                autoFocus
              />
              {nameError && <span className="text-sm text-[var(--color-danger-text)]">{nameError}</span>}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="role-slug" className="text-sm font-medium text-primary">
                Slug
              </label>
              <Input
                id="role-slug"
                value={slug}
                onChange={(e) => { setSlug(e.target.value); setSlugEdited(true); }}
                placeholder="loan-officer"
              />
            </div>
          </div>

          {permissions.length > 0 && (
            <div className="flex flex-col gap-3">
              <p className="text-sm font-medium text-primary">Permissions</p>
              <div className="border border-[color:var(--color-border-default)] rounded-lg overflow-hidden max-h-64 overflow-y-auto">
                {permissions.map((perm) => (
                  <label
                    key={perm.id}
                    className="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-sunken transition-colors duration-fast border-b border-[color:var(--color-border-default)] last:border-b-0"
                  >
                    <input
                      type="checkbox"
                      checked={selectedPermIds.has(perm.id)}
                      onChange={() => togglePerm(perm.id)}
                      className="mt-0.5 accent-[var(--color-brand-default)] flex-shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono text-primary">{perm.codename}</p>
                      {perm.description && (
                        <p className="text-xs text-tertiary mt-0.5">{perm.description}</p>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Delete confirmation */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete role"
        size="sm"
        footer={
          <ModalFooter
            onCancel={() => setDeleteTarget(null)}
            onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            confirmLabel="Delete"
            confirmVariant="danger"
            loading={deleteMutation.isPending}
          />
        }
      >
        <p className="text-base text-secondary">
          Delete <span className="font-semibold text-primary">{deleteTarget?.name}</span>? Members with this role will lose associated permissions.
        </p>
      </Modal>
    </div>
  );
}
