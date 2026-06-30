'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';

export function ProfileTab() {
  const { user, setAuth, accessToken, refreshToken } = useAuthStore();
  const { activeTenant } = useTenantStore();
  const { toast } = useToast();
  const [firstName, setFirstName] = useState(user?.first_name ?? '');
  const [lastName, setLastName] = useState(user?.last_name ?? '');

  const updateProfile = useMutation({
    mutationFn: (data: { first_name: string; last_name: string }) =>
      api.patch('/api/v1/auth/me/', data).then((r) => r.data),
    onSuccess: (updated) => {
      setAuth(updated, accessToken!, refreshToken!);
      toast.success('Profile updated');
    },
    onError: () => toast.error('Failed to update profile'),
  });

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    updateProfile.mutate({ first_name: firstName.trim(), last_name: lastName.trim() });
  }

  return (
    <div className="p-6 flex flex-col gap-6 max-w-2xl">
      <Card>
        <CardHeader title="Personal information" />
        <CardBody>
          <form onSubmit={handleSave} className="flex flex-col gap-5">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label htmlFor="first-name" className="text-sm font-medium text-primary">
                  First name
                </label>
                <Input
                  id="first-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Abebe"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="last-name" className="text-sm font-medium text-primary">
                  Last name
                </label>
                <Input
                  id="last-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Tadesse"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-primary">Email address</label>
              <Input value={user?.email ?? ''} disabled />
              <span className="text-sm text-tertiary">Email cannot be changed.</span>
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                loading={updateProfile.isPending}
              >
                Save changes
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      {activeTenant && (
        <Card>
          <CardHeader title="Organization" />
          <CardBody>
            <div className="flex flex-col gap-3">
              <Row label="Name" value={activeTenant.name} />
              <Row label="Slug" value={activeTenant.slug} mono />
              <Row label="Status" value={activeTenant.status} capitalize />
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  mono,
  capitalize,
}: {
  label: string;
  value: string;
  mono?: boolean;
  capitalize?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 border-b border-[color:var(--color-border-default)] last:border-b-0">
      <span className="text-sm text-secondary w-28 flex-shrink-0">{label}</span>
      <span
        className={[
          'text-sm text-primary',
          mono ? 'font-mono' : 'font-medium',
          capitalize ? 'capitalize' : '',
        ].join(' ')}
      >
        {value}
      </span>
    </div>
  );
}
