'use client';

import { useState } from 'react';
import api from '@/lib/api';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { useToast } from '@/components/ui/Toast';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (tenant: { id: string; name: string; slug: string; status: string }) => void;
}

type Step = 'form' | 'confirm';

function toSlug(name: string) {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

export function CreateOrgModal({ open, onClose, onCreated }: Props) {
  const { toast } = useToast();
  const [step, setStep] = useState<Step>('form');
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugEdited, setSlugEdited] = useState(false);
  const [nameError, setNameError] = useState('');
  const [slugError, setSlugError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleClose() {
    setStep('form');
    setName('');
    setSlug('');
    setSlugEdited(false);
    setNameError('');
    setSlugError('');
    onClose();
  }

  function handleNameChange(val: string) {
    setName(val);
    setNameError('');
    if (!slugEdited) {
      setSlug(toSlug(val));
    }
  }

  function handleSlugChange(val: string) {
    setSlug(val);
    setSlugEdited(true);
    setSlugError('');
  }

  function validateForm() {
    let ok = true;
    if (name.trim().length < 2) {
      setNameError('Name must be at least 2 characters.');
      ok = false;
    }
    if (!/^[a-z0-9-]+$/.test(slug) || slug.length < 2) {
      setSlugError('Slug must be lowercase letters, numbers, and hyphens (min 2 chars).');
      ok = false;
    }
    return ok;
  }

  function handleNext() {
    if (validateForm()) setStep('confirm');
  }

  async function handleCreate() {
    setLoading(true);
    try {
      const { data } = await api.post('/api/v1/tenants/', { name: name.trim(), slug });
      toast.success('Organization created', name.trim());
      onCreated(data);
      handleClose();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { name?: string[]; slug?: string[]; detail?: string } } })
        ?.response?.data;
      if (detail?.name) setNameError(detail.name[0]);
      else if (detail?.slug) setSlugError(detail.slug[0]);
      else toast.error('Failed to create organization');
      setStep('form');
    } finally {
      setLoading(false);
    }
  }

  const formFooter = (
    <ModalFooter
      onCancel={handleClose}
      onConfirm={handleNext}
      confirmLabel="Next"
    />
  );

  const confirmFooter = (
    <>
      <button
        onClick={() => setStep('form')}
        className="inline-flex items-center px-4 py-2 text-sm font-semibold rounded border border-[color:var(--color-border-strong)] bg-transparent text-primary hover:bg-sunken transition-colors duration-fast"
      >
        Back
      </button>
      <ModalFooter
        onCancel={handleClose}
        onConfirm={handleCreate}
        confirmLabel="Create organization"
        loading={loading}
      />
    </>
  );

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={step === 'form' ? 'New organization' : 'Confirm new organization'}
      size="md"
      footer={step === 'form' ? formFooter : confirmFooter}
    >
      {step === 'form' ? (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="org-name" className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]">
              Organization name
            </label>
            <Input
              id="org-name"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              placeholder="Nile Credit"
              error={!!nameError}
              autoFocus
            />
            {nameError && <span className="text-sm text-[var(--color-danger-text)]">{nameError}</span>}
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="org-slug" className="text-sm font-medium text-primary after:ml-0.5 after:content-['*'] after:text-[var(--color-danger-text)]">
              URL slug
            </label>
            <Input
              id="org-slug"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              placeholder="nile-credit"
              error={!!slugError}
            />
            {slugError ? (
              <span className="text-sm text-[var(--color-danger-text)]">{slugError}</span>
            ) : (
              <span className="text-sm text-tertiary">Used in API paths. Lowercase, hyphens only.</span>
            )}
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-base text-secondary">
            Create <span className="font-semibold text-primary">{name.trim()}</span> as a new organization?
          </p>
          <div className="rounded-lg border border-[color:var(--color-border-default)] bg-sunken px-4 py-3 flex flex-col gap-2">
            <Row label="Name" value={name.trim()} />
            <Row label="Slug" value={slug} mono />
          </div>
          <p className="text-sm text-tertiary">
            You will be the owner. You can invite members after creation.
          </p>
        </div>
      )}
    </Modal>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-sm text-secondary">{label}</span>
      <span className={`text-sm text-primary ${mono ? 'font-mono' : 'font-medium'}`}>{value}</span>
    </div>
  );
}
